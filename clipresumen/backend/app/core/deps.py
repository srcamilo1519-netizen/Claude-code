"""Shared FastAPI dependencies.

`get_current_user` is a **temporary** stand-in until Fase 4 wires real JWT
authentication. It get-or-creates a single dev user so the persistence layer
has a `user_id` to attach summaries and usage logs to. Endpoints depend on this
function, so swapping it for token-based auth in Fase 4 won't change their
signatures.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import DEFAULT_FREE_CREDITS, PlanType, User

DEV_USER_EMAIL = "dev@clipresumen.local"


def get_current_user(db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
    if user is None:
        user = User(
            email=DEV_USER_EMAIL,
            password_hash="!unusable",  # placeholder; real hashing arrives in Fase 4
            plan=PlanType.free,
            credits_remaining=DEFAULT_FREE_CREDITS,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
