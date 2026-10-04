"""JioFarm — Base Service Template Protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
import requests


@runtime_checkable
class ServiceTemplate(Protocol):
    """Protocol for any telco/service hunter module."""

    id: str
    title: str
    operator: str
    promo: str
    country_id: str
    default_product: str
    description: str

    def check_subscriber(self, session: requests.Session, phone: str) -> bool:
        """Validate if the phone number belongs to the operator."""
        ...

    def send_otp(self, session: requests.Session, phone: str) -> bool:
        """Trigger OTP delivery to the phone number."""
        ...

    def validate_otp(self, session: requests.Session, otp: str) -> bool:
        """Authenticate session using the received OTP."""
        ...

    def hunt(self, session: requests.Session) -> str | None:
        """Scrape or request the promotional activation link."""
        ...
