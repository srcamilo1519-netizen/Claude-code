"""Billing request/response schemas."""

from typing import Literal

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "business"]


class RedirectResponse(BaseModel):
    url: str
