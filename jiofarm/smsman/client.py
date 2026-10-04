"""JioFarm — SMS-Man API client.

SMS-Man API v2.0 reference:
- Base: https://api.sms-man.com/control/
- Auth: token parameter in GET/POST requests
- Balance: GET /get-balance?token=$token
- Rent:    GET /get-number?token=$token&country_id=$country_id&application_id=$application_id
- Status:  GET /get-sms?token=$token&request_id=$request_id
- Set:     GET /set-status?token=$token&request_id=$request_id&status=$status
"""

from __future__ import annotations

import threading
import time
from typing import Any

import requests


class SmsManError(Exception):
    pass


class SmsMan:
    """Minimal client for SMS-Man API v2.0."""

    BASE = "https://api.sms-man.com/control"
    MIN_GAP = 1.0  # seconds between API calls

    def __init__(
        self,
        api_key: str,
        country_id: int | str = 22,
        application_id: int | str = "jio",
        currency: str = "USD",
    ) -> None:
        self.key = api_key
        self.country_id = country_id
        self.application_id = application_id
        self.currency = currency
        self._lock = threading.Lock()
        self._last = 0.0
        self._resolved_app_id: int | str | None = None
        self._resolved_country_id: int | str | None = None

    # ----------------------------------------------------------------- low level
    def _request(self, endpoint: str, params: dict[str, Any] | None = None, retries: int = 3) -> Any:
        url = f"{self.BASE}/{endpoint.lstrip('/')}"
        query_params = {"token": self.key, **(params or {})}

        for attempt in range(1, retries + 1):
            with self._lock:
                wait = self.MIN_GAP - (time.time() - self._last)
                if wait > 0:
                    time.sleep(wait)
                self._last = time.time()

            try:
                res = requests.get(url, params=query_params, timeout=20)
                if res.status_code == 429:
                    time.sleep(attempt * 3)
                    continue

                res.raise_for_status()
                data = res.json()

                if isinstance(data, dict) and data.get("success") is False:
                    err_code = data.get("error_code", "")
                    err_msg = data.get("error_msg", "")
                    # "wait_sms" is expected polling status, not an unhandled network error
                    if err_code != "wait_sms":
                        raise SmsManError(f"SMS-Man error [{err_code}]: {err_msg}")

                return data
            except requests.RequestException:
                if attempt == retries:
                    raise
                time.sleep(2)

        raise SmsManError("SMS-Man request failed after retries.")

    # ---------------------------------------------------------------- resolution
    def _get_country_id(self) -> int | str:
        if self._resolved_country_id is not None:
            return self._resolved_country_id

        val = str(self.country_id).strip()
        if val.isdigit():
            self._resolved_country_id = int(val)
            return self._resolved_country_id

        # resolve country title by fetching country list
        try:
            countries = self._request("countries")
            if isinstance(countries, list):
                target = val.lower()
                for c in countries:
                    if isinstance(c, dict) and str(c.get("title", "")).lower() == target:
                        self._resolved_country_id = c.get("id", val)
                        return self._resolved_country_id
        except Exception:
            pass

        self._resolved_country_id = val
        return self._resolved_country_id

    def _get_application_id(self) -> int | str:
        if self._resolved_app_id is not None:
            return self._resolved_app_id

        val = str(self.application_id).strip()
        if val.isdigit():
            self._resolved_app_id = int(val)
            return self._resolved_app_id

        # resolve application by name or code
        try:
            apps = self._request("applications")
            if isinstance(apps, list):
                target = val.lower()
                for app in apps:
                    if not isinstance(app, dict):
                        continue
                    name = str(app.get("name", "")).lower()
                    code = str(app.get("code", "")).lower()
                    if target in (name, code) or target in name:
                        self._resolved_app_id = app.get("id", val)
                        return self._resolved_app_id
        except Exception:
            pass

        self._resolved_app_id = val
        return self._resolved_app_id

    # ---------------------------------------------------------------- high level
    def balance(self) -> float:
        """Return account balance."""
        data = self._request("get-balance")
        if isinstance(data, dict) and "balance" in data:
            return float(data["balance"])
        raise SmsManError(f"Gagal mengambil saldo: {data}")

    def rent(self, max_price: float | None = None) -> tuple[str, str]:
        """Rent a phone number for Jio. Returns (request_id, phone_number)."""
        cid = self._get_country_id()
        aid = self._get_application_id()

        params: dict[str, Any] = {
            "country_id": cid,
            "application_id": aid,
            "currency": self.currency,
        }
        if max_price is not None:
            params["maxPrice"] = max_price

        data = self._request("get-number", params)
        if isinstance(data, dict):
            req_id = data.get("request_id")
            num = data.get("number")
            if req_id and num:
                return str(req_id), str(num)
            if data.get("error_code"):
                raise SmsManError(f"Gagal sewa nomor: {data.get('error_msg') or data.get('error_code')}")

        raise SmsManError(f"Response sewa nomor tidak valid: {data}")

    def status(self, act_id: str) -> tuple[str, str | None]:
        """Check activation status. Returns ('WAIT' | 'OK' | 'CANCEL', code | None)."""
        data = self._request("get-sms", {"request_id": act_id})

        if isinstance(data, dict):
            code = data.get("sms_code")
            if code:
                return "OK", str(code)

            err_code = str(data.get("error_code", "")).lower()
            if err_code == "wait_sms" or not err_code:
                return "WAIT", None

            if any(k in err_code for k in ("cancel", "reject", "expire", "timeout")):
                return "CANCEL", None

            raise SmsManError(f"SMS-Man status error: {data.get('error_msg') or err_code}")

        raise SmsManError(f"Response status tidak valid: {data}")

    def ready(self, act_id: str) -> None:
        """Mark number ready to receive SMS."""
        self._request("set-status", {"request_id": act_id, "status": "ready"})

    def complete(self, act_id: str) -> None:
        """Complete the activation successfully."""
        self._request("set-status", {"request_id": act_id, "status": "close"})

    def cancel(self, act_id: str) -> None:
        """Cancel/reject activation to reclaim balance."""
        self._request("set-status", {"request_id": act_id, "status": "reject"})
