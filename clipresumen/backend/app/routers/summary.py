"""Summarization + summaries endpoints.

`POST /api/summarize` connects YouTube extraction with the Claude summarizer,
persists the result, and logs token usage. `GET /api/summaries` and
`GET /api/summaries/{id}` read back a user's summaries.

Authentication is not implemented yet (Fase 4); the current user is resolved by
a temporary dev stand-in (see app/core/deps.py).
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.summary import Summary
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.summary import VideoSummary
from app.services import summarizer_service, youtube_service

router = APIRouter(prefix="/api", tags=["summary"])


# ─────────────────────────────────────────────────────────────────────────────
# Request / response schemas
# ─────────────────────────────────────────────────────────────────────────────
class SummarizeRequest(BaseModel):
    url: str = Field(description="URL del video de YouTube a resumir.")


class SummaryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    youtube_url: str
    video_title: str
    video_duration: int
    transcript_length: int
    processing_time_seconds: float
    created_at: datetime


class SummaryDetail(SummaryListItem):
    summary: VideoSummary


class SummarizeResponse(SummaryDetail):
    """Detail of the summary that was just created."""


def _to_detail(record: Summary) -> SummaryDetail:
    return SummaryDetail(
        id=record.id,
        youtube_url=record.youtube_url,
        video_title=record.video_title,
        video_duration=record.video_duration,
        transcript_length=record.transcript_length,
        processing_time_seconds=record.processing_time_seconds,
        created_at=record.created_at,
        summary=VideoSummary.model_validate(record.summary_json),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/summarize", response_model=SummarizeResponse)
def summarize(
    payload: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummarizeResponse:
    started = time.monotonic()

    # 0. Enforce credits before spending any API tokens.
    if current_user.credits_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No te quedan créditos. Mejora tu plan o compra más para seguir resumiendo.",
        )

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
        summary_result = summarizer_service.summarize_transcript(result.transcript)
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

    elapsed = round(time.monotonic() - started, 2)

    # 3. Persist the summary and log token usage.
    record = Summary(
        user_id=current_user.id,
        youtube_url=payload.url,
        video_title=result.title,
        video_duration=result.duration_seconds,
        transcript_length=result.transcript_length,
        summary_json=summary_result.summary.model_dump(),
        processing_time_seconds=elapsed,
    )
    db.add(record)
    db.add(
        UsageLog(
            user_id=current_user.id,
            action="summarize",
            tokens_used=summary_result.tokens_used,
        )
    )
    # Charge one credit for the generated summary.
    current_user.credits_remaining -= 1
    db.add(current_user)
    db.commit()
    db.refresh(record)

    return SummarizeResponse(**_to_detail(record).model_dump())


@router.get("/summaries", response_model=list[SummaryListItem])
def list_summaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Summary]:
    return (
        db.query(Summary)
        .filter(Summary.user_id == current_user.id)
        .order_by(Summary.created_at.desc())
        .all()
    )


@router.get("/summaries/{summary_id}", response_model=SummaryDetail)
def get_summary(
    summary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryDetail:
    record = (
        db.query(Summary)
        .filter(Summary.id == summary_id, Summary.user_id == current_user.id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Resumen no encontrado.")
    return _to_detail(record)
