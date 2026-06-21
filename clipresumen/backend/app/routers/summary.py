"""Summarization endpoint.

Connects the YouTube extraction service with the Claude summarizer and returns
the final structured result. No authentication yet (added in Fase 4).
"""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.summary import VideoSummary
from app.services import summarizer_service, youtube_service

router = APIRouter(prefix="/api", tags=["summary"])


class SummarizeRequest(BaseModel):
    url: str = Field(description="URL del video de YouTube a resumir.")


class SummarizeResponse(BaseModel):
    video_id: str
    title: str
    duration_seconds: int
    language: str
    transcript_length: int
    summary: VideoSummary
    processing_time_seconds: float


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(payload: SummarizeRequest) -> SummarizeResponse:
    started = time.monotonic()

    # 1. Extract transcript + metadata from YouTube.
    try:
        result = youtube_service.extract_transcript(payload.url)
    except youtube_service.InvalidYouTubeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except youtube_service.VideoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except youtube_service.VideoPrivateError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except youtube_service.TranscriptNotAvailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except youtube_service.RateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except youtube_service.YouTubeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 2. Summarize the transcript with Claude.
    try:
        summary = summarizer_service.summarize_transcript(result.transcript)
    except summarizer_service.SummarizerConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except summarizer_service.SummarizerRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except summarizer_service.SummarizerTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except summarizer_service.SummarizerResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except summarizer_service.SummarizerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SummarizeResponse(
        video_id=result.video_id,
        title=result.title,
        duration_seconds=result.duration_seconds,
        language=result.language,
        transcript_length=result.transcript_length,
        summary=summary,
        processing_time_seconds=round(time.monotonic() - started, 2),
    )
