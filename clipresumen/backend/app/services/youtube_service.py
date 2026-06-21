"""YouTube transcript extraction service.

Given a YouTube URL this service:

1. Extracts the ``video_id`` (supports ``watch?v=``, ``youtu.be/`` and
   ``shorts/`` URLs).
2. Fetches the transcript via ``youtube-transcript-api``, preferring the
   video's original language and falling back to English/Spanish.
3. Fetches lightweight metadata (title, duration) via ``yt-dlp`` *without*
   downloading the video, to avoid the official Data API quota.
4. Maps library-specific failures to a small set of domain errors.

A basic rate limiter throttles outbound requests so we don't hammer YouTube.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

import yt_dlp
from yt_dlp.utils import DownloadError
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TooManyRequests,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Domain errors
# ─────────────────────────────────────────────────────────────────────────────
class YouTubeServiceError(Exception):
    """Base class for all errors raised by this service."""


class InvalidYouTubeURLError(YouTubeServiceError):
    """The provided string is not a recognizable YouTube URL."""


class VideoNotFoundError(YouTubeServiceError):
    """The video does not exist or has been removed."""


class VideoPrivateError(YouTubeServiceError):
    """The video is private and cannot be accessed."""


class TranscriptNotAvailableError(YouTubeServiceError):
    """The video exists but has no usable transcript."""


class RateLimitedError(YouTubeServiceError):
    """YouTube is rate-limiting our requests; retry later."""


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TranscriptResult:
    video_id: str
    title: str
    duration_seconds: int
    language: str
    transcript: str

    @property
    def transcript_length(self) -> int:
        return len(self.transcript)


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting
# ─────────────────────────────────────────────────────────────────────────────
class _RateLimiter:
    """Process-wide minimum interval between outbound calls (thread-safe)."""

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_call = time.monotonic()


# Minimum ~1s between calls is a conservative default for a single instance.
_rate_limiter = _RateLimiter(min_interval_seconds=1.0)

# Fallback languages tried when the original language transcript is missing.
_FALLBACK_LANGUAGES = ("en", "es")

# Matches the 11-character video id from the common URL shapes:
#   youtube.com/watch?v=<id>, youtu.be/<id>, youtube.com/shorts/<id>,
#   youtube.com/embed/<id>, youtube.com/v/<id>
_VIDEO_ID_RE = re.compile(
    r"""
    (?:
        youtu\.be/                              # short link
      | youtube\.com/(?:                        # full domain variants
            watch\?(?:[^&]*&)*v=
          | shorts/
          | embed/
          | v/
        )
    )
    (?P<id>[0-9A-Za-z_-]{11})
    """,
    re.VERBOSE,
)


def extract_video_id(url: str) -> str:
    """Return the 11-character video id contained in ``url``.

    Raises:
        InvalidYouTubeURLError: if no valid id can be found.
    """
    if not url or not isinstance(url, str):
        raise InvalidYouTubeURLError("URL vacía o no válida.")

    match = _VIDEO_ID_RE.search(url.strip())
    if not match:
        raise InvalidYouTubeURLError(f"No se reconoce como URL de YouTube: {url!r}")
    return match.group("id")


# ─────────────────────────────────────────────────────────────────────────────
# Metadata (yt-dlp) — title + duration only, no download
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_metadata(video_id: str) -> tuple[str, int]:
    """Return ``(title, duration_seconds)`` using yt-dlp metadata extraction."""
    _rate_limiter.wait()
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        message = str(exc).lower()
        if "private" in message:
            raise VideoPrivateError("El video es privado.") from exc
        if any(s in message for s in ("unavailable", "does not exist", "removed", "not exist")):
            raise VideoNotFoundError("El video no existe o fue eliminado.") from exc
        raise YouTubeServiceError(f"No se pudo obtener la metadata: {exc}") from exc

    title = info.get("title") or "Sin título"
    duration = int(info.get("duration") or 0)
    return title, duration


# ─────────────────────────────────────────────────────────────────────────────
# Transcript (youtube-transcript-api)
# ─────────────────────────────────────────────────────────────────────────────
def _preferred_languages(transcript_list) -> list[str]:
    """Build an ordered language preference list.

    Prefers the first manually-created transcript's language (usually the
    original), then any available language, then the English/Spanish fallbacks.
    """
    manual = [t.language_code for t in transcript_list if not t.is_generated]
    generated = [t.language_code for t in transcript_list if t.is_generated]

    ordered: list[str] = []
    for code in (*manual, *generated, *_FALLBACK_LANGUAGES):
        if code not in ordered:
            ordered.append(code)
    return ordered


def _fetch_transcript(video_id: str) -> tuple[str, str]:
    """Return ``(transcript_text, language_code)`` for the video."""
    _rate_limiter.wait()
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(_preferred_languages(transcript_list))
        segments = transcript.fetch()
        language = transcript.language_code
    except TranscriptsDisabled as exc:
        raise TranscriptNotAvailableError(
            "El video no tiene transcripción disponible."
        ) from exc
    except NoTranscriptFound as exc:
        raise TranscriptNotAvailableError(
            "No se encontró transcripción en un idioma compatible."
        ) from exc
    except VideoUnavailable as exc:
        raise VideoNotFoundError("El video no existe o no está disponible.") from exc
    except TooManyRequests as exc:
        raise RateLimitedError(
            "YouTube está limitando las solicitudes. Intenta más tarde."
        ) from exc
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptNotAvailableError(
            f"No se pudo recuperar la transcripción: {exc}"
        ) from exc

    text = " ".join(segment["text"].strip() for segment in segments if segment["text"].strip())
    if not text:
        raise TranscriptNotAvailableError("La transcripción está vacía.")
    return text, language


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def extract_transcript(url: str) -> TranscriptResult:
    """Extract transcript + metadata for a YouTube ``url``.

    Raises one of the :class:`YouTubeServiceError` subclasses on failure.
    """
    video_id = extract_video_id(url)
    logger.info("Extracting transcript for video_id=%s", video_id)

    # Metadata first: it surfaces private/removed videos with clearer errors.
    title, duration = _fetch_metadata(video_id)
    transcript, language = _fetch_transcript(video_id)

    return TranscriptResult(
        video_id=video_id,
        title=title,
        duration_seconds=duration,
        language=language,
        transcript=transcript,
    )
