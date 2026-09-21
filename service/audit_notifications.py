import hashlib
import hmac
import json
from typing import Any, Dict


def build_audit_message(payment_id: str, merchant: str, action: str) -> str:
    verb = {
        "approved": "Approved",
        "needs_approval": "Queued for approval",
        "blocked": "Blocked",
    }[action]
    return f"{verb} payment {payment_id} for {merchant}."


def sign_notification(secret: str, payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return digest


def verify_notification(secret: str, payload: Dict[str, Any], signature: str) -> bool:
    expected = sign_notification(secret, payload)
    return hmac.compare_digest(expected, signature)
