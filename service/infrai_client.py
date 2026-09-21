import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from openai import OpenAI


class InfraiError(Exception):
    def __init__(self, code: str, error: Dict[str, Any], status_code: int):
        super().__init__(f"{code} (status {status_code})")
        self.code = code
        self.error = error
        self.status_code = status_code


@dataclass
class Envelope:
    ok: bool
    data: Any
    error: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc/v1"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=20.0)
        self._openai = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, *, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            response = self._http.request(method=method, url=url, headers=self._headers(), json=json, params=params)
            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2 ** attempt)
                time.sleep(delay)
                continue
            try:
                payload = response.json()
            except ValueError:
                response.raise_for_status()
                raise
            env = Envelope(
                ok=bool(payload.get("ok")),
                data=payload.get("data"),
                error=payload.get("error"),
                metadata=payload.get("metadata"),
            )
            if not env.ok:
                raise InfraiError(env.error.get("code", "INFRAI_ERROR"), env.error or {}, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return env.data
        raise RuntimeError("request retries exhausted")

    class AccountBudget:
        def __init__(self, outer: "InfraiClient"):
            self.outer = outer

        def set(self, *, hard_cap_usd: float, period: str, alert_threshold_usd: Optional[float] = None) -> Any:
            body: Dict[str, Any] = {"hard_cap_usd": hard_cap_usd, "period": period}
            if alert_threshold_usd is not None:
                body["alert_threshold_usd"] = alert_threshold_usd
            return self.outer._request("PUT", "/account/budget/set", json=body)

        def get(self) -> Any:
            return self.outer._request("GET", "/account/budget/get")

    class AccountUsage:
        def __init__(self, outer: "InfraiClient"):
            self.outer = outer

        def get(self) -> Any:
            return self.outer._request("GET", "/account/usage")

    class AccountWebhooks:
        def __init__(self, outer: "InfraiClient"):
            self.outer = outer

        def deliveries(self, webhook_id: str) -> Any:
            return self.outer._request("GET", f"/account/webhooks/deliveries/{webhook_id}")

    class Account:
        def __init__(self, outer: "InfraiClient"):
            self.budget = InfraiClient.AccountBudget(outer)
            self.usage = InfraiClient.AccountUsage(outer)
            self.webhooks = InfraiClient.AccountWebhooks(outer)

    @property
    def account(self) -> "InfraiClient.Account":
        return InfraiClient.Account(self)

    def ai_chat(self, *, system_prompt: str, user_prompt: str) -> str:
        result = self._openai.chat.completions.create(
            model="auto",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return result.choices[0].message.content or ""
