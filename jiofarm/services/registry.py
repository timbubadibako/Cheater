"""JioFarm — Service Template Registry."""

from __future__ import annotations

from typing import Dict
from jiofarm.services.base import ServiceTemplate
from jiofarm.services.jio import JioGoogleService
from jiofarm.services.canva import CanvaProService
from jiofarm.services.airtel import AirtelThanksService

_SERVICES: Dict[str, ServiceTemplate] = {
    JioGoogleService.id: JioGoogleService(),
    CanvaProService.id: CanvaProService(),
    AirtelThanksService.id: AirtelThanksService(),
}


def list_services() -> list[dict[str, str]]:
    """Return catalog of available service templates."""
    return [
        {
            "id": s.id,
            "title": s.title,
            "operator": s.operator,
            "promo": s.promo,
            "country_id": s.country_id,
            "default_product": s.default_product,
            "description": s.description,
        }
        for s in _SERVICES.values()
    ]


def get_service(service_id: str) -> ServiceTemplate:
    """Retrieve service instance by id."""
    srv = _SERVICES.get(service_id)
    if not srv:
        # fallback to jio-google
        return _SERVICES["jio-google"]
    return srv
