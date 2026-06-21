"""ORM model tests against an in-memory SQLite database.

Validates the schema, defaults, relationships, and cascade behavior without
needing Postgres or the running app.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import PlanType, Summary, UsageLog, User


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _make_user(db) -> User:
    user = User(email="a@b.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_user_defaults(session):
    user = _make_user(session)
    assert user.id is not None
    assert user.plan == PlanType.free
    assert user.credits_remaining == 5
    assert user.created_at is not None


def test_summary_persists_json_and_links_to_user(session):
    user = _make_user(session)
    summary = Summary(
        user_id=user.id,
        youtube_url="https://youtu.be/abc",
        video_title="Demo",
        video_duration=120,
        transcript_length=4000,
        summary_json={"titulo": "t", "puntos_clave": ["a", "b"]},
        processing_time_seconds=3.5,
    )
    session.add(summary)
    session.commit()
    session.refresh(summary)

    assert summary.id is not None
    assert summary.summary_json["puntos_clave"] == ["a", "b"]
    assert summary.user.email == "a@b.com"
    assert user.summaries[0].id == summary.id


def test_usage_log_persists(session):
    user = _make_user(session)
    log = UsageLog(user_id=user.id, action="summarize", tokens_used=1234)
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.id is not None
    assert log.tokens_used == 1234
    assert user.usage_logs[0].action == "summarize"


def test_cascade_delete_removes_children(session):
    user = _make_user(session)
    session.add(
        Summary(
            user_id=user.id,
            youtube_url="https://youtu.be/abc",
            video_title="Demo",
            video_duration=1,
            transcript_length=1,
            summary_json={},
            processing_time_seconds=0.0,
        )
    )
    session.add(UsageLog(user_id=user.id, action="summarize", tokens_used=1))
    session.commit()

    session.delete(user)
    session.commit()

    assert session.query(Summary).count() == 0
    assert session.query(UsageLog).count() == 0
