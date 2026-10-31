"""Pydantic schemas shared by the API, agents and storage layer."""
from __future__ import annotations

from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Seller(BaseModel):
    name: str
    account_age_days: Optional[int] = Field(None, ge=0)
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    verified: bool = False
    paypal_email: Optional[str] = Field(
        None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Seller's PayPal account email. If set, the PayPal order pays the seller directly (payee).",
    )


class Listing(BaseModel):
    """Everything the buyer can see before paying."""

    title: str = Field(..., min_length=2, max_length=300)
    description: str = Field("", max_length=8000)
    category: str = "general"
    price: float = Field(..., gt=0)
    currency: str = "USD"
    market_price: Optional[float] = Field(None, gt=0, description="Typical price, if the buyer knows it")
    seller: Seller
    return_policy: str = Field("", max_length=3000)
    shipping_days: Optional[int] = Field(None, ge=0)
    url: Optional[str] = None
    seller_messages: list[str] = Field(default_factory=list, description="Chat messages from the seller")


class Finding(BaseModel):
    signal: str
    detail: str
    severity: RiskLevel
    points: int = Field(..., ge=0, le=100)


class AgentReport(BaseModel):
    agent: str
    score: int = Field(..., ge=0, le=100, description="0 = safe, 100 = certain risk")
    findings: list[Finding]
    summary: str
    llm_used: bool = False


class Assessment(BaseModel):
    id: str
    created_at: str
    listing: Listing
    reports: list[AgentReport]
    overall_score: int
    risk_level: RiskLevel
    recommendation: str
    summary: str
    questions_for_seller: list[str]
    payment_allowed: bool
    requires_override: bool
    llm_used: bool
    ai_status: str = "ok"  # ok | partial | failed  (failed = rules-only result, LLM unreachable)
    source: str = "manual"  # manual | url
    missing_fields: list[str] = Field(default_factory=list)
    decision: Optional[str] = None  # approved | rejected
    paypal_order_id: Optional[str] = None
    paypal_approve_url: Optional[str] = None
    payment_status: Optional[str] = None
    capture_id: Optional[str] = None
    order_attempts: int = 0
    checkout_locale: Optional[str] = None


class Decision(BaseModel):
    approve: bool
    acknowledge_risk: bool = Field(False, description="Required to approve HIGH/CRITICAL assessments")
    note: Optional[str] = Field(None, max_length=500)


class UrlAnalyzeRequest(BaseModel):
    url: str = Field(..., max_length=2000)
    market_price: Optional[float] = Field(None, gt=0, description="Typical price, if the buyer knows it")
    seller_messages: list[str] = Field(default_factory=list, description="Messages the seller sent the buyer")
    overrides: dict = Field(default_factory=dict, description="Listing fields to set manually, e.g. seller.account_age_days")


class CheckoutOptions(BaseModel):
    locale: Optional[Literal["en-US", "ar-AE", "fr-FR"]] = None
