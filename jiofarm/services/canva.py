"""JioFarm — Canva Pro Partner & Telco Promo Service Template."""

from __future__ import annotations

import re
import requests

CANVA_LINK_MARKERS = (
    "canva.com/brand/join",
    "canva.com/signup?redeem",
    "canva.com/affiliates",
    "canva.com/q/pro-trial",
    "canva.me/",
)


class CanvaProService:
    """Canva Pro / Teams Partner Promo Link Hunter."""

    id = "canva-pro"
    title = "Canva — Canva Pro (Trial / Teams Hunter)"
    operator = "Canva Partner & Telco Bundle"
    promo = "Canva Pro Subscription / Invite Link"
    country_id = "0"  # Global / Multi-country
    default_product = "canva"
    description = "Sewa nomor SMS (global/telco partner), verifikasi bundle promo Canva, ekstrak link invite/aktivasi Canva Pro."

    def check_subscriber(self, session: requests.Session, phone: str) -> bool:
        """Nomor valid untuk aktivasi promo Canva."""
        return bool(phone and len(phone) >= 8)

    def send_otp(self, session: requests.Session, phone: str) -> bool:
        """Trigger OTP verifikasi nomor untuk klaim promo Canva."""
        # Endpoint partner bundle / gateway Canva OTP
        return True

    def validate_otp(self, session: requests.Session, otp: str) -> bool:
        """Submit OTP untuk autentikasi dan klaim bundle."""
        return bool(otp and len(otp) >= 4)

    def hunt(self, session: requests.Session) -> str | None:
        """Scrape link invite tim atau kupon redeem Canva Pro."""
        # Scan response text for Canva Pro invite links
        return None
