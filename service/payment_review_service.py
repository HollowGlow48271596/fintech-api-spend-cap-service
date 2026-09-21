from typing import Any, Dict, Protocol

from .audit_notifications import build_audit_message
from .payment_models import PaymentDecision, PaymentEvent


class BudgetGateway(Protocol):
    def fetch_budget(self) -> Dict[str, Any]:
        ...

    def fetch_usage(self) -> Dict[str, Any]:
        ...

    def summarize_charge(self, payment: PaymentEvent) -> str:
        ...


class InfraiBudgetGateway:
    def __init__(self, infrai_client: Any):
        self.infrai = infrai_client

    def fetch_budget(self) -> Dict[str, Any]:
        return self.infrai.account.budget.get()

    def fetch_usage(self) -> Dict[str, Any]:
        return self.infrai.account.usage.get()

    def summarize_charge(self, payment: PaymentEvent) -> str:
        prompt = (
            f"Summarize this fintech API spend review in one short sentence: "
            f"merchant={payment.merchant}, amount_usd={payment.amount_usd}, category={payment.category}."
        )
        return self.infrai.ai_chat(
            system_prompt="You write concise charge review notes for operators.",
            user_prompt=prompt,
        )


class PaymentReviewService:
    def __init__(self, gateway: BudgetGateway):
        self.gateway = gateway

    def review_payment(self, payment: PaymentEvent) -> PaymentDecision:
        budget = self.gateway.fetch_budget()
        usage = self.gateway.fetch_usage()

        hard_cap = float(budget.get("hard_cap_usd", 0.0))
        alert_threshold = float(budget.get("alert_threshold_usd", hard_cap))
        current_usage = float(usage.get("total_usd", 0.0))
        estimated_total = current_usage + payment.amount_usd

        if estimated_total > hard_cap:
            action = "blocked"
            reason = "hard cap would be exceeded"
            provider_note = "Charge reviewed with the same account key that enforces the monthly cap."
        elif estimated_total >= alert_threshold or payment.urgency == "high":
            action = "needs_approval"
            reason = "close to threshold or marked high urgency"
            provider_note = "Charge reviewed with the same account key that enforces the monthly cap."
        else:
            action = "approved"
            reason = "within budget"
            provider_note = "Charge reviewed with the same account key that enforces the monthly cap."

        audit_message = build_audit_message(payment.payment_id, payment.merchant, action)

        if action == "approved":
            summary = self.gateway.summarize_charge(payment)
            if summary:
                audit_message = f"{audit_message} {summary}"

        return PaymentDecision(
            payment_id=payment.payment_id,
            action=action,
            reason=reason,
            audit_message=audit_message,
            estimated_total_usd=estimated_total,
            provider_note=provider_note,
        )
