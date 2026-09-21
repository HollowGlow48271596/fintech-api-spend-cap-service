from typing import Literal, Optional

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    payment_id: str = Field(min_length=1)
    merchant: str = Field(min_length=1)
    amount_usd: float = Field(gt=0)
    urgency: Literal["low", "medium", "high"]
    category: Literal["model_inference", "risk_check", "settlement_sync"]


class PaymentDecision(BaseModel):
    payment_id: str
    action: Literal["approved", "needs_approval", "blocked"]
    reason: str
    audit_message: str
    estimated_total_usd: float
    provider_note: Optional[str] = None
