"""JioFarm — Jio Google AI Pro Service Implementation."""

from __future__ import annotations

import requests

from jiofarm.jio.auth import jio_send_otp, jio_validate_otp
from jiofarm.jio.check import jio_check_subscriber
from jiofarm.jio.hunt import hunt_link


class JioGoogleService:
    """Jio India + Google AI Pro (Gemini Advanced 2TB) Hunter."""

    id = "jio-google"
    title = "Jio — Google AI Pro (Gemini 2TB)"
    operator = "Reliance Jio (India)"
    promo = "Google One / AI Pro 2TB Subscription"
    country_id = "22"
    default_product = "jio"
    description = "Sewa nomor Jio India, login selfcare, panen link aktivasi resmi Google AI Pro."

    def check_subscriber(self, session: requests.Session, phone: str) -> bool:
        return jio_check_subscriber(phone)

    def send_otp(self, session: requests.Session, phone: str) -> bool:
        return jio_send_otp(session, phone)

    def validate_otp(self, session: requests.Session, otp: str) -> bool:
        return jio_validate_otp(session, otp)

    def hunt(self, session: requests.Session) -> str | None:
        return hunt_link(session)
