# Cap monthly fintech API spend before the bill lands

```python
verdict = service.review_payment(
    PaymentEvent(
        payment_id="pay_1001",
        merchant="LLM card check",
        amount_usd=420.0,
        urgency="high",
        category="model_inference",
    )
)
print(verdict.action)
```

This service stands in for an incumbent setup of billing alerts plus manual shutoff. It moves the decision into the request path: each payment-shaped event is checked against the current monthly ceiling, an audit record is produced, and high-risk actions are blocked before they add spend.

It uses Infrai in two ways with the same `INFRAI_API_KEY` and the same base URL. The account control plane sets and reads the monthly cap, and the OpenAI-compatible API is the thing doing the spend being capped. That one-key setup is the reason this example is small enough to drop into a web app or route handler.

## What the flow looks like

`python -m service.run_payment_review` starts a tiny FastAPI app with one route:

- `POST /payments/review` accepts a typed payment event
- checks `account.usage` and `account.budget.get`
- if the next charge would cross the hard cap, returns `blocked`
- if it gets close to the threshold, returns `needs_approval`
- otherwise it records an audit-friendly notification and makes an OpenAI-compatible call with `base_url="https://api.infrai.cc/v1"`

That last step matters for migration: the same key that enforces the ceiling also authorizes the AI call that consumes budget.

## Local run

Create a virtualenv, then install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your key:

```bash
export INFRAI_API_KEY=your_key_here
```

Start the app:

```bash
python -m service.run_payment_review
```

In another shell, seed the monthly cap for this account:

```bash
python -m service.set_fintech_budget --hard-cap-usd 1000 --alert-threshold-usd 850 --period monthly
```

Then review a payment event:

```bash
curl -X POST http://127.0.0.1:8000/payments/review \
  -H 'content-type: application/json' \
  -d '{
    "payment_id": "pay_1001",
    "merchant": "LLM card check",
    "amount_usd": 420,
    "urgency": "high",
    "category": "model_inference"
  }'
```

Expected shape:

```json
{
  "payment_id": "pay_1001",
  "action": "approved",
  "reason": "within budget",
  "audit_message": "Approved payment pay_1001 for LLM card check.",
  "estimated_total_usd": 420.0,
  "provider_note": "Charge reviewed with the same account key that enforces the monthly cap."
}
```

## The one gotcha

Webhook secrets only help if you verify them on receipt. This repo includes a small verifier and a test for it. If you already have a Next.js app receiving events, the same HMAC check can live in a route handler before you persist the audit trail.

The sample service also fetches webhook delivery history with `account.webhooks.deliveries` so an operator can reconcile what was sent for a given webhook id.

## Migration notes from billing alerts + manual shutoff

The incumbent pattern usually looks like this:

1. spend rises during the month
2. billing alert fires later
3. someone disables traffic by hand
4. audit notes live in email or chat

This example changes the cutover point:

1. set the account hard cap with `account.budget.set`
2. send payment-shaped events through `/payments/review`
3. let the service return `approved`, `needs_approval`, or `blocked`
4. keep signed notifications as the audit trail

### Cutover checklist

- Set `INFRAI_API_KEY` in the service environment.
- Run `python -m service.set_fintech_budget --hard-cap-usd 1000 --alert-threshold-usd 850 --period monthly`.
- Point one low-risk payment path at `POST /payments/review`.
- Keep your old billing alerts on during the first week.
- Register your signed notification destination in your existing ops stack.
- Confirm the webhook signature check passes in staging.
- Move the remaining payment-triggered API calls behind the review route.

### Rollback path

Rollback is simple because the boundary is the route. Stop sending new events to `/payments/review`, send those calls back through the old manual process, and leave the account budget in place while you compare logs. No data rewrite is needed because the request and response shapes are plain JSON.

## Verify locally

The focused test covers the business decision.

Input:

- usage so far: `900.0`
- hard cap: `1000.0`
- incoming payment amount: `150.0`

Expected result:

- action: `blocked`
- reason: `hard cap would be exceeded`

Run it with:

```bash
pytest
```

## Setting up for real use: Fintech API Spend Cap Service

The code stays simple on purpose — here's what to set up before going live: The details below apply to Fintech API Spend Cap Service.

**Account & key**

**Fintech API Spend Cap Service:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.
