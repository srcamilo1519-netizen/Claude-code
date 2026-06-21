"""Stripe billing endpoints: checkout, customer portal, and webhook."""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import PlanType, User
from app.schemas.billing import CheckoutRequest, RedirectResponse
from app.services import billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _require_stripe() -> None:
    if not billing_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El sistema de pagos no está configurado.",
        )
    billing_service.configure()


@router.post("/create-checkout-session", response_model=RedirectResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    _require_stripe()
    plan = PlanType(payload.plan)
    price_id = billing_service.price_id_for_plan(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Ese plan no está disponible.")

    customer_id = billing_service.ensure_customer(db, current_user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_base_url}/dashboard?checkout=success",
        cancel_url=f"{settings.frontend_base_url}/pricing?checkout=cancel",
        metadata={"user_id": str(current_user.id), "plan": plan.value},
    )
    return RedirectResponse(url=session.url)


@router.get("/portal", response_model=RedirectResponse)
def billing_portal(
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    _require_stripe()
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No tienes una suscripción activa.")
    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/dashboard",
    )
    return RedirectResponse(url=session.url)


# ─────────────────────────────────────────────────────────────────────────────
# Webhook
# ─────────────────────────────────────────────────────────────────────────────
def _user_by_customer(db: Session, customer_id: str | None) -> User | None:
    if not customer_id:
        return None
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def _handle_checkout_completed(db: Session, obj: dict) -> None:
    metadata = obj.get("metadata") or {}
    user = db.get(User, int(metadata["user_id"])) if metadata.get("user_id") else None
    if user is None:
        return
    customer = obj.get("customer")
    if customer and not user.stripe_customer_id:
        user.stripe_customer_id = customer
        db.add(user)
        db.commit()
    plan_value = metadata.get("plan")
    if plan_value in PlanType._value2member_map_:
        billing_service.apply_plan(db, user, PlanType(plan_value))


def _handle_subscription_active(db: Session, obj: dict) -> None:
    user = _user_by_customer(db, obj.get("customer"))
    if user is None:
        return
    try:
        price_id = obj["items"]["data"][0]["price"]["id"]
    except (KeyError, IndexError, TypeError):
        return
    plan = billing_service.plan_for_price_id(price_id)
    if plan and obj.get("status") in ("active", "trialing"):
        billing_service.apply_plan(db, user, plan)


def _handle_subscription_canceled(db: Session, obj: dict) -> None:
    user = _user_by_customer(db, obj.get("customer"))
    if user is not None:
        billing_service.apply_plan(db, user, PlanType.free)


def _handle_invoice_paid(db: Session, obj: dict) -> None:
    # Recurring renewal: refill the current plan's credits.
    user = _user_by_customer(db, obj.get("customer"))
    if user is not None:
        billing_service.apply_plan(db, user, user.plan)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_stripe()
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Firma de webhook inválida.") from exc

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, obj)
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_active(db, obj)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_canceled(db, obj)
    elif event_type == "invoice.payment_succeeded":
        _handle_invoice_paid(db, obj)
    elif event_type == "invoice.payment_failed":
        logger.warning("Stripe payment failed for customer %s", obj.get("customer"))

    return {"received": True}
