"""Auth + credit-gate tests via FastAPI TestClient with an isolated SQLite DB."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.services import summarizer_service, youtube_service
from app.services.summarizer_service import SummaryResult
from app.services.youtube_service import TranscriptResult


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register(client, email="user@example.com", password="supersecret"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_register_returns_tokens(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_conflicts(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_login_and_me(client):
    _register(client, email="a@b.com")
    login = client.post("/api/auth/login", json={"email": "a@b.com", "password": "supersecret"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    profile = me.json()
    assert profile["email"] == "a@b.com"
    assert profile["plan"] == "free"
    assert profile["credits_remaining"] == 5


def test_login_wrong_password(client):
    _register(client, email="a@b.com")
    resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrongpass1"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    # No Authorization header → unauthorized (401/403 depending on Starlette).
    assert client.get("/api/auth/me").status_code in (401, 403)


def test_refresh_rotates_access_token(client):
    tokens = _register(client).json()
    resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_summaries_protected(client):
    assert client.get("/api/summaries").status_code in (401, 403)


def test_credit_gate_returns_402_when_exhausted(client, monkeypatch):
    # Avoid real network/API calls.
    monkeypatch.setattr(
        youtube_service,
        "extract_transcript",
        lambda url: TranscriptResult(
            video_id="vid", title="T", duration_seconds=60, language="es", transcript="hola"
        ),
    )
    monkeypatch.setattr(
        summarizer_service,
        "summarize_transcript",
        lambda text: SummaryResult(
            summary=__import__(
                "app.schemas.summary", fromlist=["VideoSummary"]
            ).VideoSummary(
                titulo="t",
                puntos_clave=["a"],
                resumen_extendido="r",
                conclusion_cta="c",
            ),
            tokens_used=10,
        ),
    )

    token = _register(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    body = {"url": "https://youtu.be/vid"}

    # 5 free credits → 5 successful summaries, then 402.
    for i in range(5):
        ok = client.post("/api/summarize", json=body, headers=headers)
        assert ok.status_code == 200, ok.text

    blocked = client.post("/api/summarize", json=body, headers=headers)
    assert blocked.status_code == 402

    me = client.get("/api/auth/me", headers=headers).json()
    assert me["credits_remaining"] == 0
