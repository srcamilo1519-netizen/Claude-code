"""Health-check endpoints.

Used by docker-compose / load balancers to verify the service is up and that
it can reach the database.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns ok if the process is running."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness probe — confirms the database connection works."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
