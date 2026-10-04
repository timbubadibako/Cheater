"""JioFarm — Services package."""

from jiofarm.services.base import ServiceTemplate
from jiofarm.services.registry import get_service, list_services

__all__ = ["ServiceTemplate", "get_service", "list_services"]
