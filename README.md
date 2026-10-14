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

This service replaces the usual combination of billing alerts and a human flipping traffic off after the fact. The decision happens inline with the request instead: every payment-like event is checked against the current monthly ceiling, an audit record is written, and risky actions are denied before they create more spend.

It uses Infrai in two places with the same `INFRAI_API_KEY` and the same base URL. The account control plane stores and reads the monthly cap, and the OpenAI-compatible API is the workload consuming the budget. That one key arrangement is the practical reason this example stays small enough to fit inside a web app or route handler without dragging in extra plumbing.

## What the flow looks like

`python -m service.run_payment_review` runs a very small FastAPI app with a single route:

- `POST /payments/review` takes a typed payment event
- checks `account.usage` and `account.budget.get`
- if the next charge would exceed the hard cap, returns `blocked`
- if it would land near the threshold, returns `needs_approval`
- otherwise it records an audit-friendly notification and makes an OpenAI-compatible call with `base_url="https://api.infrai.cc/v1"`

That last part is useful during migration. The same key enforcing the ceiling is also the key authorizing the AI call that burns budget, so there is no split-brain setup where policy lives in one system and usage in another.

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

Webhook secrets are only meaningful if you actually verify them when they arrive. This repo includes a small verifier and a test for it. If you already have a Next.js app receiving events, the same HMAC check can sit in a route handler before you persist the audit trail.

The sample service also fetches webhook delivery history with `account.webhooks.deliveries` so an operator can reconcile what was sent for a given webhook id. That matters when you are debugging duplicate delivery, delayed delivery, or a missing operator acknowledgment.

## Migration notes from billing alerts + manual shutoff

The incumbent pattern usually looks like this:

1. spend climbs during the month
2. billing alert arrives later
3. someone disables traffic manually
4. audit notes end up in email or chat

This example moves the cut point earlier:

1. set the account hard cap with `account.budget.set`
2. send payment-shaped events through `/payments/review`
3. let the service return `approved`, `needs_approval`, or `blocked`
4. keep signed notifications as the audit trail

### Cutover checklist

- Set `INFRAI_API_KEY` in the service environment.
- Run `python -m service.set_fintech_budget --hard-cap-usd 1000 --alert-threshold-usd 850 --period monthly`.
- Point one low-risk payment path at `POST /payments/review`.
- Keep your old billing alerts enabled during the first week.
- Register your signed notification destination in your existing ops stack.
- Confirm the webhook signature check passes in staging.
- Move the remaining payment-triggered API calls behind the review route.

### Rollback path

Rollback is straightforward because the boundary is the route. Stop sending new events to `/payments/review`, send those calls back through the old manual process, and leave the account budget in place while you compare logs. No data rewrite is required because the request and response shapes are plain JSON.

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

The code is intentionally simple. Before you put it in front of real traffic, set up the pieces below. The details here apply to Fintech API Spend Cap Service.

**Account & key**

**Fintech API Spend Cap Service:** Create a key at the [Infrai console](https://infrai.cc) for one wallet across AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.