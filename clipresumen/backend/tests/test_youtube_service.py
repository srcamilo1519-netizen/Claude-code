"""Tests for the YouTube transcript extraction service.

The unit tests (video-id parsing) run offline and deterministically. The live
extraction test hits YouTube and is marked ``integration`` — it is deselected
by default (see pyproject.toml) and skips gracefully if the network/transcript
is unavailable. Run it with::

    pytest -m integration
"""

import pytest

from app.services import youtube_service
from app.services.youtube_service import (
    InvalidYouTubeURLError,
    extract_video_id,
)

# A widely-available video with captions, used for the live test.
SAMPLE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SAMPLE_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "http://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?list=ABC&v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=xyz",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_valid(url):
    assert extract_video_id(url) == SAMPLE_ID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://vimeo.com/123456789",
        "https://www.youtube.com/",
        "https://www.google.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_invalid(url):
    with pytest.raises(InvalidYouTubeURLError):
        extract_video_id(url)


def test_extract_video_id_rejects_non_string():
    with pytest.raises(InvalidYouTubeURLError):
        extract_video_id(None)  # type: ignore[arg-type]


@pytest.mark.integration
def test_extract_transcript_live():
    try:
        result = youtube_service.extract_transcript(SAMPLE_URL)
    except youtube_service.YouTubeServiceError as exc:
        pytest.skip(f"Live extraction unavailable: {exc}")

    assert result.video_id == SAMPLE_ID
    assert result.title
    assert result.duration_seconds > 0
    assert result.transcript.strip()
    assert result.transcript_length == len(result.transcript)
    assert result.language
