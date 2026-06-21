"""Billing tests.

Covers the offline pieces: plan→credit mapping, the unconfigured/unauthorized
guards on the billing endpoints, and the business plan's unlimited gating in
/api/summarize. Real Stripe API calls are not exercised here.
"""

from app.models.user import PlanType, User
from app.services import billing_service, summarizer_service, youtube_service
from app.services.billing_service import PLAN_CREDITS, plan_for_price_id
from app.services.summarizer_service import SummaryResult
from app.services.youtube_service import TranscriptResult
from app.schemas.summary import VideoSummary


def test_plan_credit_mapping():
    assert PLAN_CREDITS[PlanType.free] == 5
    assert PLAN_CREDITS[PlanType.pro] == 100
    assert PLAN_CREDITS[PlanType.business] >= 1_000_000


def test_plan_for_price_id_unknown_returns_none():
    assert plan_for_price_id(None) is None
    assert plan_for_price_id("price_does_not_exist") is None


def _register(client):
    return client.post(
        "/api/auth/register",
        json={"email": "pay@example.com", "password": "supersecret"},
    ).json()


def test_checkout_requires_auth(client):
    resp = client.post("/api/billing/create-checkout-session", json={"plan": "pro"})
    assert resp.status_code in (401, 403)


def test_checkout_unconfigured_returns_503(client):
    token = _register(client)["access_token"]
    resp = client.post(
        "/api/billing/create-checkout-session",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # No STRIPE_SECRET_KEY in the test env → payments unavailable.
    assert resp.status_code == 503


def test_webhook_invalid_signature(client):
    resp = client.post(
        "/api/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "bogus"},
    )
    # Either unconfigured (503) or bad signature (400) — never a 200.
    assert resp.status_code in (400, 503)


def test_business_plan_is_unlimited(client, monkeypatch):
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
            summary=VideoSummary(
                titulo="t", puntos_clave=["a"], resumen_extendido="r", conclusion_cta="c"
            ),
            tokens_used=10,
        ),
    )

    token = _register(client)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Promote the user to business with zero credits.
    me = client.get("/api/auth/me", headers=headers).json()
    from app.core.database import get_db
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    user = db.get(User, me["id"])
    user.plan = PlanType.business
    user.credits_remaining = 0
    db.add(user)
    db.commit()

    # Despite 0 credits, business can still summarize, and credits stay at 0.
    for _ in range(3):
        resp = client.post("/api/summarize", json={"url": "https://youtu.be/vid"}, headers=headers)
        assert resp.status_code == 200, resp.text

    assert client.get("/api/auth/me", headers=headers).json()["credits_remaining"] == 0
