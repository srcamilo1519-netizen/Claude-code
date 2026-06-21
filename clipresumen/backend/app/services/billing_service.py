"""Stripe billing helpers: plan/price mapping and customer bootstrap.

Stripe keys come from settings (TEST keys in dev, LIVE keys in prod — see
app/core/config.py). Nothing here needs to change between test and production.
"""

from __future__ import annotations

import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import PlanType, User

# Credits granted per plan. BUSINESS is effectively unlimited; the summarize
# endpoint additionally skips the credit gate for business users.
BUSINESS_CREDITS = 1_000_000
PLAN_CREDITS: dict[PlanType, int] = {
    PlanType.free: 5,
    PlanType.pro: 100,
    PlanType.business: BUSINESS_CREDITS,
}


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def configure() -> None:
    stripe.api_key = settings.stripe_secret_key


def price_id_for_plan(plan: PlanType) -> str | None:
    return {
        PlanType.pro: settings.stripe_price_pro or None,
        PlanType.business: settings.stripe_price_business or None,
    }.get(plan)


def plan_for_price_id(price_id: str | None) -> PlanType | None:
    if not price_id:
        return None
    if price_id == settings.stripe_price_pro:
        return PlanType.pro
    if price_id == settings.stripe_price_business:
        return PlanType.business
    return None


def ensure_customer(db: Session, user: User) -> str:
    """Return the user's Stripe customer id, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email, metadata={"user_id": str(user.id)}
    )
    user.stripe_customer_id = customer.id
    db.add(user)
    db.commit()
    return customer.id


def apply_plan(db: Session, user: User, plan: PlanType) -> None:
    """Set the user's plan and refill credits to that plan's allowance."""
    user.plan = plan
    user.credits_remaining = PLAN_CREDITS[plan]
    db.add(user)
    db.commit()
