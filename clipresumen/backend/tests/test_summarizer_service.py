"""Tests for the summarizer service.

Only the offline, deterministic pieces are unit-tested here (chunking,
empty-input guard). The actual Claude call requires an API key and network, so
it is covered by an `integration`-marked test that is deselected by default.
"""

import pytest

from app.services import summarizer_service
from app.services.summarizer_service import (
    SummarizerResponseError,
    _chunk_text,
)


def test_chunk_text_short_returns_single_chunk():
    text = "una transcripción breve"
    assert _chunk_text(text, max_chars=1000) == [text]


def test_chunk_text_respects_max_chars():
    # 500 words of 4 chars + spaces; chunk at 100 chars.
    text = " ".join("word" for _ in range(500))
    chunks = _chunk_text(text, max_chars=100)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    # No content is lost and no words are split.
    rejoined = " ".join(chunks)
    assert rejoined.split() == text.split()


def test_chunk_text_does_not_split_words():
    text = "palabra " * 50
    for chunk in _chunk_text(text, max_chars=20):
        for word in chunk.split():
            assert word == "palabra"


def test_summarize_transcript_rejects_empty():
    with pytest.raises(SummarizerResponseError):
        summarizer_service.summarize_transcript("   ")
