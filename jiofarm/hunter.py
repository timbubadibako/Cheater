"""JioFarm — Core hunt cycle orchestrator.

Ties together SMS provider rentals, Jio authentication, link hunting, and
storage.  Designed to be driven by the CLI layer (``cli.py``) so that the
live-dashboard can observe worker state in real time.

Supports multiple providers: GrizzlySMS, 5SIM.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

import requests

from jiofarm.config import Config
from jiofarm.console import tg_send
from jiofarm.grizzly.refund import RefundWorker
from jiofarm.jio.auth import UA
from jiofarm.jio.check import normalize_phone
from jiofarm.proxy import ProxyManager
from jiofarm.services import ServiceTemplate, get_service
from jiofarm.storage.store import Store


# ------------------------------------------------------------------- provider protocol


class SMSProvider(Protocol):
    """Protocol that every SMS provider client must implement."""

    def balance(self) -> float: ...
    def rent(self, max_price: float | None = None) -> tuple[str, str]: ...
    def ready(self, act_id: str) -> None: ...
    def complete(self, act_id: str) -> None: ...
    def cancel(self, act_id: str) -> None: ...


def poll_otp(provider: SMSProvider, act_id: str, timeout: int = 120, interval: int = 5) -> str:
    """Poll the provider until the OTP arrives or the deadline expires.

    Uses duck-typing: tries ``status()`` first (GrizzlySMS), then ``check()`` (5SIM).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        # GrizzlySMS-style: .status() returns ("WAIT"/"OK"/"CANCEL", code)
        if hasattr(provider, "status"):
            state, code = provider.status(act_id)  # type: ignore[attr-defined]
            if state == "OK" and code:
                return code
            if state == "CANCEL":
                raise Exception("activation cancelled upstream")
        # 5SIM-style: .check() returns ("RECEIVED"/"PENDING"/..., code)
        elif hasattr(provider, "check"):
            status, code = provider.check(act_id)  # type: ignore[attr-defined]
            if status == "RECEIVED" and code:
                return code
            if status in ("CANCELED", "TIMEOUT", "BANNED"):
                raise Exception(f"activation {status}")
        else:
            raise Exception("provider tidak mendukung polling OTP")
        time.sleep(interval)
    raise Exception(f"OTP timeout setelah {timeout}s")


# ------------------------------------------------------------------- worker state


class Phase(Enum):
    IDLE = auto()
    RENTING = auto()
    CHECKING = auto()
    SENDING_OTP = auto()
    WAITING_OTP = auto()
    VALIDATING = auto()
    HUNTING = auto()
    DONE = auto()
    ERROR = auto()


@dataclass
class WorkerState:
    wid: int
    phase: Phase = Phase.IDLE
    phone: str = ""
    act_id: str = ""
    otp: str = ""
    logged_in: bool = False
    link: str | None = None
    error: str = ""
    attempts: int = 0


# ------------------------------------------------------------------- hunt cycle


def hunt_once(
    provider: SMSProvider,
    store: Store,
    refunds: RefundWorker,
    slots: threading.Semaphore,
    cfg: Config,
    state: WorkerState,
    service: ServiceTemplate | None = None,
    proxy_mgr: ProxyManager | None = None,
) -> str | None:
    """Run one complete hunt attempt, updating *state* for live display.

    Returns the link if found, otherwise None.
    """
    if service is None:
        service = get_service("jio-google")
    if proxy_mgr is None and cfg.proxy_url:
        proxy_mgr = ProxyManager(cfg.proxy_url)

    slots.acquire()
    state.phase = Phase.RENTING
    state.phone = ""
    state.act_id = ""
    state.otp = ""
    state.logged_in = False
    state.link = None
    state.error = ""

    try:
        # 1) rent a number --------------------------------------------------
        state.act_id, raw = provider.rent(cfg.effective_max_price)
        state.phone = normalize_phone(raw)

        # 2) create session with proxy -------------------------------------
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.jio.com",
                "Referer": "https://www.jio.com/selfcare/login/",
            }
        )
        if proxy_mgr and proxy_mgr.has_proxy():
            px = proxy_mgr.get_proxy_dict()
            if px:
                s.proxies.update(px)

        # 3) check subscriber -----------------------------------------------
        state.phase = Phase.CHECKING
        if not service.check_subscriber(s, state.phone):
            state.phase = Phase.ERROR
            state.error = f"bukan pelanggan {service.operator}"
            refunds.schedule(state.act_id, 120, aggressive=True)
            return None

        # 4) send OTP -------------------------------------------------------
        state.phase = Phase.SENDING_OTP
        if not service.send_otp(s, state.phone):
            state.phase = Phase.ERROR
            state.error = "OTP gagal dikirim"
            refunds.schedule(state.act_id, cfg.otp_fail_delay)
            return None

        provider.ready(state.act_id)

        # 5) poll OTP -------------------------------------------------------
        state.phase = Phase.WAITING_OTP
        state.otp = poll_otp(provider, state.act_id)

        # 6) validate OTP ---------------------------------------------------
        state.phase = Phase.VALIDATING
        if not service.validate_otp(s, state.otp):
            state.phase = Phase.ERROR
            state.error = "OTP invalid"
            refunds.schedule(state.act_id, cfg.cancel_delay)
            return None

        state.logged_in = True

        # 7) hunt link ------------------------------------------------------
        state.phase = Phase.HUNTING
        link = service.hunt(s)
        provider.complete(state.act_id)

        if link:
            state.link = link
            state.phase = Phase.DONE
            tg_send(
                f"🎯 {service.title} link!\n\nNomor : {state.phone}\nLink :\n{link}",
                cfg.tg_bot_token,
                cfg.tg_chat_id,
            )
        else:
            state.phase = Phase.DONE
            state.error = f"login sukses tapi tidak ada promo {service.promo} aktif"

        return link

    except KeyboardInterrupt:
        raise
    except Exception as e:
        state.phase = Phase.ERROR
        state.error = str(e)
        if state.act_id:
            refunds.schedule(state.act_id, cfg.cancel_delay)
    finally:
        store.save(state.phone, state.act_id, state.otp, state.logged_in, state.link)
        state.attempts += 1
        slots.release()


# ------------------------------------------------------------------- provider factory


def create_provider(cfg: Config) -> SMSProvider:
    """Create the appropriate SMS provider client based on Config."""
    if cfg.provider == "grizzlysms":
        from jiofarm.grizzly.client import GrizzlySMS

        return GrizzlySMS(cfg.api_key)  # type: ignore[return-value]
    elif cfg.provider == "fivesim":
        from jiofarm.fivesim.client import FiveSim

        return FiveSim(cfg.api_key)  # type: ignore[return-value]
    elif cfg.provider == "smsman":
        from jiofarm.smsman.client import SmsMan

        return SmsMan(  # type: ignore[return-value]
            api_key=cfg.api_key,
            country_id=cfg.country_id,
            application_id=cfg.product,
        )
    elif cfg.provider == "smspool":
        from jiofarm.smspool.client import SmsPool

        return SmsPool(  # type: ignore[return-value]
            api_key=cfg.api_key,
            country="IN",
            service=cfg.product or "jio",
        )
    else:
        raise SystemExit(f"Provider tidak dikenal: {cfg.provider}")