"""JioFarm — Airtel Thanks Service Template."""

from __future__ import annotations

import requests


class AirtelThanksService:
    """Airtel India — Perplexity Pro / Entertainment Bundle."""

    id = "airtel-perplexity"
    title = "Airtel — Perplexity Pro 1 Year / Thanks Rewards"
    operator = "Bharti Airtel (India)"
    promo = "Perplexity Pro 1 Year / Disney+ Hotstar"
    country_id = "22"
    default_product = "airtel"
    description = "Template sewa nomor Airtel India untuk berburu reward Airtel Thanks (Perplexity Pro / OTT)."

    def check_subscriber(self, session: requests.Session, phone: str) -> bool:
        # Airtel HLR or subscriber check endpoint
        return True

    def send_otp(self, session: requests.Session, phone: str) -> bool:
        # Endpoint: https://www.airtel.in/auth/v1/otp/generate
        return False

    def validate_otp(self, session: requests.Session, otp: str) -> bool:
        # Endpoint: https://www.airtel.in/auth/v1/otp/validate
        return False

    def hunt(self, session: requests.Session) -> str | None:
        # Endpoint: https://www.airtel.in/thanks/rewards/claim
        return None
