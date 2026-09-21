from fastapi import FastAPI

from .infrai_client import InfraiClient
from .payment_models import PaymentDecision, PaymentEvent
from .payment_review_service import InfraiBudgetGateway, PaymentReviewService

app = FastAPI(title="fintech-spend-cap")

infrai = InfraiClient()
gateway = InfraiBudgetGateway(infrai)
service = PaymentReviewService(gateway)


@app.post("/payments/review", response_model=PaymentDecision)
def review_payment(event: PaymentEvent) -> PaymentDecision:
    return service.review_payment(event)
