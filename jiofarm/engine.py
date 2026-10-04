"""JioFarm — Farm Engine Controller for Web & CLI."""

from __future__ import annotations

import collections
import threading
import time
from typing import Any

from jiofarm.config import Config, load_config
from jiofarm.grizzly.refund import RefundWorker
from jiofarm.hunter import Phase, SMSProvider, WorkerState, create_provider, hunt_once
from jiofarm.proxy import ProxyManager
from jiofarm.services import ServiceTemplate, get_service
from jiofarm.storage.store import Store


class FarmController:
    """Singleton controller managing the live background farm runner."""

    _instance: FarmController | None = None

    @classmethod
    def get_instance(cls) -> FarmController:
        if cls._instance is None:
            cls._instance = FarmController()
        return cls._instance

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.is_running = False
        self.stop_event = threading.Event()
        self.active_threads: list[threading.Thread] = []
        self.workers: list[WorkerState] = []
        self.service: ServiceTemplate = get_service("jio-google")
        self.provider_name: str = "grizzlysms"
        self.found_links: list[str] = []
        self.logs: collections.deque[str] = collections.deque(maxlen=100)
        self.start_time: float = 0.0
        self.cfg: Config = load_config()
        self.proxy_mgr: ProxyManager = ProxyManager(self.cfg.proxy_url)
        self.store = Store(self.cfg.db_path)
        self.provider: SMSProvider | None = None
        self.refunds: RefundWorker | None = None
        self.done_attempts = 0
        self.target_links: int | None = None
        self.max_attempts: int | None = None

    def log(self, msg: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        with self.lock:
            self.logs.append(entry)

    def get_status(self) -> dict[str, Any]:
        with self.lock:
            running = self.is_running
            elapsed = int(time.time() - self.start_time) if running else 0
            workers_data = [
                {
                    "wid": w.wid,
                    "phase": w.phase.name,
                    "phone": w.phone or "-",
                    "status": w.error if w.phase == Phase.ERROR else (w.link or "active" if w.phone else "idle"),
                    "attempts": w.attempts,
                }
                for w in self.workers
            ]
            store_stats = self.store.stats()
            return {
                "running": running,
                "service": {
                    "id": self.service.id,
                    "title": self.service.title,
                    "operator": self.service.operator,
                    "promo": self.service.promo,
                },
                "provider": self.provider_name,
                "proxy_active": self.proxy_mgr.has_proxy(),
                "elapsed_seconds": elapsed,
                "found_links": list(self.found_links),
                "workers": workers_data,
                "logs": list(self.logs),
                "stats": {
                    "session_links": len(self.found_links),
                    "session_attempts": self.done_attempts,
                    "db_total_hunts": store_stats["hunts"],
                    "db_total_logins": store_stats["logins"],
                    "db_total_links": store_stats["links"],
                },
            }

    def start(
        self,
        service_id: str = "jio-google",
        provider_name: str | None = None,
        concurrency: int | None = None,
        max_price: float | None = None,
        count: int | None = None,
        target: int | None = None,
        proxy_url: str | None = None,
    ) -> bool:
        with self.lock:
            if self.is_running:
                return False

            self.is_running = True
            self.stop_event.clear()
            self.start_time = time.time()
            self.found_links.clear()
            self.done_attempts = 0
            self.target_links = target
            self.max_attempts = count

            # Load / apply overrides
            self.cfg = load_config()
            if provider_name:
                self.cfg.provider = provider_name
            self.provider_name = self.cfg.provider

            if proxy_url is not None:
                self.cfg.proxy_url = proxy_url
            self.proxy_mgr = ProxyManager(self.cfg.proxy_url)

            if max_price is not None:
                self.cfg.max_price_override = max_price
            if concurrency is not None:
                self.cfg.concurrency_override = concurrency

            self.service = get_service(service_id)
            try:
                self.provider = create_provider(self.cfg)
            except Exception as e:
                self.is_running = False
                self.log(f"Error inisialisasi provider: {e}")
                return False

            self.refunds = RefundWorker(self.provider, log=lambda m: self.log(f"Refund: {m}"))

            workers_count = self.cfg.effective_concurrency
            self.workers = [WorkerState(wid=i + 1) for i in range(workers_count)]
            slots = threading.Semaphore(workers_count)

            self.log(f"Farm dimulai | Servis: {self.service.title} | Provider: {self.provider_name} | Workers: {workers_count}")
            if self.proxy_mgr.has_proxy():
                self.log(f"Proxy aktif: {len(self.proxy_mgr.proxies)} endpoint")

            # Runner thread that orchestrates worker loops
            runner_thread = threading.Thread(
                target=self._run_loop,
                args=(slots, count, target),
                daemon=True,
            )
            self.active_threads = [runner_thread]
            runner_thread.start()
            return True

    def stop(self) -> None:
        self.stop_event.set()
        self.log("Mengirim sinyal berhenti...")
        with self.lock:
            self.is_running = False

    def _run_loop(
        self,
        slots: threading.Semaphore,
        count: int | None,
        target: int | None,
    ) -> None:
        attempt_lock = threading.Lock()

        def worker_job(ws: WorkerState) -> None:
            while not self.stop_event.is_set():
                with attempt_lock:
                    if count and self.done_attempts >= count:
                        break
                    if target and len(self.found_links) >= target:
                        break
                    self.done_attempts += 1

                self.log(f"Worker #{ws.wid}: memulai perburuan...")
                try:
                    link = hunt_once(
                        self.provider,  # type: ignore[arg-type]
                        self.store,
                        self.refunds,  # type: ignore[arg-type]
                        slots,
                        self.cfg,
                        ws,
                        service=self.service,
                        proxy_mgr=self.proxy_mgr,
                    )
                    if link:
                        with self.lock:
                            self.found_links.append(link)
                        self.log(f"Worker #{ws.wid} 🎯 LINK DITEMUKAN: {link}")
                    elif ws.error:
                        self.log(f"Worker #{ws.wid}: {ws.error}")
                except Exception as e:
                    self.log(f"Worker #{ws.wid} crash: {e}")

                if count and self.done_attempts >= count:
                    break
                if target and len(self.found_links) >= target:
                    break

        threads = []
        for w in self.workers:
            t = threading.Thread(target=worker_job, args=(w,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        with self.lock:
            self.is_running = False
        self.log("Farm berhenti.")
