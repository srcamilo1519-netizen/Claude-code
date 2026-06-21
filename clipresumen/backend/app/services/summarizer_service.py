"""Summarization service backed by the Claude (Anthropic) API.

Given a transcript, produces a :class:`VideoSummary` (structured JSON) using
``claude-sonnet-4-6`` with structured outputs. Very long transcripts are split
into chunks, summarized individually (map), and the partial summaries are then
summarized into the final structured result (reduce).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import anthropic

from app.core.config import settings
from app.schemas.summary import VideoSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    """Structured summary plus the total tokens the Claude call(s) consumed."""

    summary: VideoSummary
    tokens_used: int


# ─────────────────────────────────────────────────────────────────────────────
# Domain errors
# ─────────────────────────────────────────────────────────────────────────────
class SummarizerError(Exception):
    """Base class for summarizer failures."""


class SummarizerConfigError(SummarizerError):
    """The service is not configured (e.g. missing API key)."""


class SummarizerRateLimitError(SummarizerError):
    """Anthropic rate-limited the request; retry later."""


class SummarizerTimeoutError(SummarizerError):
    """The Anthropic request timed out."""


class SummarizerResponseError(SummarizerError):
    """The model returned a malformed or unparseable response."""


# ─────────────────────────────────────────────────────────────────────────────
# Tuning constants
# ─────────────────────────────────────────────────────────────────────────────
# Above this length we map-reduce instead of summarizing in a single pass.
MAX_SINGLE_PASS_CHARS = 100_000
# Each chunk stays comfortably below the single-pass threshold.
CHUNK_SIZE_CHARS = 80_000
MAX_TOKENS = 8_000

_SYSTEM_PROMPT = """\
Eres un asistente experto en resumir transcripciones de videos de YouTube.

Reglas estrictas:
- Responde SIEMPRE en español.
- Básate ÚNICAMENTE en el contenido de la transcripción. NO inventes datos,
  cifras, nombres ni afirmaciones que no aparezcan en ella.
- PUNTOS CLAVE: entre 5 y 8 ideas principales.
- RESUMEN EXTENDIDO: 2 o 3 párrafos narrativos.
- TIMESTAMPS RELEVANTES: identifica entre 3 y 5 momentos importantes SOLO si la
  transcripción incluye marcas de tiempo. Si no hay marcas de tiempo, devuelve
  una lista vacía.
- CONCLUSIÓN/CTA: qué puede hacer el espectador con esta información.
"""


def _get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise SummarizerConfigError("ANTHROPIC_API_KEY no está configurada.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _chunk_text(text: str, max_chars: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Split ``text`` into chunks of at most ``max_chars``, on whitespace.

    Avoids cutting words in half by breaking at the last space before the limit.
    """
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        # +1 accounts for the joining space.
        if length + len(word) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = []
            length = 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _usage_tokens(response: object) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    return (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)


def _summarize_chunk(
    client: anthropic.Anthropic, chunk: str, index: int, total: int
) -> tuple[str, int]:
    """Map step: return (summary_text, tokens_used) for one transcript chunk."""
    response = client.messages.create(
        model=settings.summarizer_model,
        max_tokens=MAX_TOKENS,
        system=(
            "Resume de forma concisa y fiel el siguiente fragmento de una "
            "transcripción. No inventes información. Responde en español."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Fragmento {index}/{total}:\n\n{chunk}",
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return text, _usage_tokens(response)


def _structured_summary(client: anthropic.Anthropic, text: str) -> tuple[VideoSummary, int]:
    """Reduce step: return (VideoSummary, tokens_used) via structured outputs."""
    response = client.messages.parse(
        model=settings.summarizer_model,
        max_tokens=MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Resume esta transcripción:\n\n{text}",
            }
        ],
        output_format=VideoSummary,
    )
    summary = response.parsed_output
    if summary is None:
        raise SummarizerResponseError(
            "El modelo no devolvió un resumen con el formato esperado."
        )
    return summary, _usage_tokens(response)


def summarize_transcript(transcript: str) -> SummaryResult:
    """Summarize a transcript into a :class:`SummaryResult`.

    Raises a :class:`SummarizerError` subclass on failure.
    """
    if not transcript or not transcript.strip():
        raise SummarizerResponseError("La transcripción está vacía.")

    client = _get_client()
    tokens = 0

    try:
        text = transcript
        if len(transcript) > MAX_SINGLE_PASS_CHARS:
            chunks = _chunk_text(transcript)
            logger.info("Transcript too long; map-reducing over %d chunks", len(chunks))
            partials = []
            for i, chunk in enumerate(chunks, start=1):
                partial, used = _summarize_chunk(client, chunk, i, len(chunks))
                partials.append(partial)
                tokens += used
            text = "\n\n".join(partials)
        summary, used = _structured_summary(client, text)
        tokens += used
        return SummaryResult(summary=summary, tokens_used=tokens)
    except anthropic.APITimeoutError as exc:
        raise SummarizerTimeoutError("La solicitud a Claude expiró.") from exc
    except anthropic.RateLimitError as exc:
        raise SummarizerRateLimitError(
            "Claude está limitando las solicitudes. Intenta más tarde."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise SummarizerError(f"Error de conexión con Claude: {exc}") from exc
    except anthropic.APIStatusError as exc:
        raise SummarizerError(f"Error de la API de Claude ({exc.status_code}).") from exc
