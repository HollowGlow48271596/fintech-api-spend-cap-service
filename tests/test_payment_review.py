from service.audit_notifications import sign_notification, verify_notification
from service.payment_models import PaymentEvent
from service.payment_review_service import PaymentReviewService


class StubGateway:
    def fetch_budget(self):
        return {"hard_cap_usd": 1000.0, "alert_threshold_usd": 850.0}

    def fetch_usage(self):
        return {"total_usd": 900.0}

    def summarize_charge(self, payment):
        return "Reviewed for operator context."


def test_blocks_payment_when_hard_cap_would_be_exceeded():
    service = PaymentReviewService(StubGateway())
    payment = PaymentEvent(
        payment_id="pay_2002",
        merchant="Model settlement",
        amount_usd=150.0,
        urgency="medium",
        category="model_inference",
    )

    decision = service.review_payment(payment)

    assert decision.action == "blocked"
    assert decision.reason == "hard cap would be exceeded"
    assert decision.estimated_total_usd == 1050.0


def test_verifies_signed_audit_notification():
    payload = {"payment_id": "pay_2002", "action": "blocked"}
    signature = sign_notification("shared-secret", payload)

    assert verify_notification("shared-secret", payload, signature) is True
