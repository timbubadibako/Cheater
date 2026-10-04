"""JioFarm — SMSPool API client.

SMSPool API reference:
- Base: https://api.smspool.net
- Balance: POST /request/balance (key or Bearer token)
- Rent:    POST /purchase/sms (key, country, service, max_price)
- Status:  POST /sms/check (key, orderid)
- Cancel:  POST /sms/cancel (key, orderid)
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any

import requests


class SmsPoolError(Exception):
    pass


class SmsPool:
    """Client for SMSPool API."""

    BASE = "https://api.smspool.net"
    MIN_GAP = 1.0  # seconds between API calls

    def __init__(
        self,
        api_key: str,
        country: str = "15",  # 15 = India in SMSPool
        service: str = "jio",
    ) -> None:
        self.key = api_key
        self.country = country
        self.service = service
        self._lock = threading.Lock()
        self._last = 0.0

    def _post(self, endpoint: str, data: dict[str, Any] | None = None, retries: int = 3) -> Any:
        url = f"{self.BASE}/{endpoint.lstrip('/')}"
        payload = {"key": self.key, **(data or {})}
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
        }

        for attempt in range(1, retries + 1):
            with self._lock:
                wait = self.MIN_GAP - (time.time() - self._last)
                if wait > 0:
                    time.sleep(wait)
                self._last = time.time()

            try:
                res = requests.post(url, data=payload, headers=headers, timeout=20)
                if res.status_code == 429:
                    time.sleep(attempt * 3)
                    continue

                res.raise_for_status()
                return res.json()
            except requests.RequestException:
                if attempt == retries:
                    raise
                time.sleep(2)

        raise SmsPoolError("SMSPool request failed after retries.")

    def balance(self) -> float:
        """Return account balance."""
        data = self._post("request/balance", {"key": self.key})
        if isinstance(data, dict):
            if "balance" in data:
                return float(data["balance"])
            if data.get("success") == 0:
                errors = data.get("errors", [])
                msg = errors[0].get("message") if errors else data.get("message", "Gagal cek saldo")
                raise SmsPoolError(msg)
        raise SmsPoolError(f"Format balance tidak valid: {data}")

    def rent(self, max_price: float | None = None) -> tuple[str, str]:
        """Purchase an SMS activation. Returns (order_id, phone_number)."""
        payload: dict[str, Any] = {
            "country": self.country,
            "service": self.service,
        }
        if max_price is not None:
            payload["max_price"] = max_price

        data = self._post("purchase/sms", payload)
        if isinstance(data, dict):
            if data.get("success") == 1 or "order_id" in data:
                order_id = str(data.get("order_id", ""))
                phone = str(data.get("phonenumber") or data.get("number") or "")
                cc = str(data.get("cc") or "91")
                if cc and not phone.startswith(cc) and not phone.startswith("+"):
                    phone = f"{cc}{phone}"
                if order_id and phone:
                    return order_id, phone

            msg = data.get("message")
            if not msg and data.get("errors"):
                msg = data["errors"][0].get("message")
            raise SmsPoolError(f"Gagal sewa nomor SMSPool: {msg or data}")

        raise SmsPoolError(f"Response order tidak valid: {data}")

    def status(self, act_id: str) -> tuple[str, str | None]:
        """Check order status. Returns ('WAIT' | 'OK' | 'CANCEL', code | None)."""
        data = self._post("sms/check", {"orderid": act_id})

        if isinstance(data, dict):
            st = data.get("status")
            # status: 1 = pending, 2 = cancelled/refunded, 3 = completed, 6 = expired
            if st == 3 or data.get("sms"):
                sms_text = str(data.get("sms", ""))
                match = re.search(r"\b\d{4,8}\b", sms_text)
                code = match.group(0) if match else sms_text
                return "OK", code

            if st in (2, 6):
                return "CANCEL", None

            if st == 1 or data.get("message") == "Pending":
                return "WAIT", None

            msg = str(data.get("message", "")).lower()
            if any(k in msg for k in ("cancel", "refund", "expire")):
                return "CANCEL", None

            return "WAIT", None

        raise SmsPoolError(f"Response status tidak valid: {data}")

    def ready(self, act_id: str) -> None:
        """SMSPool is ready on purchase — no-op."""

    def complete(self, act_id: str) -> None:
        """SMSPool completes automatically — no-op."""

    def cancel(self, act_id: str) -> None:
        """Cancel/refund the order."""
        try:
            self._post("sms/cancel", {"orderid": act_id})
        except Exception as e:
            raise SmsPoolError(f"Gagal refund SMSPool: {e}")
