"""
WatermarkPro v2 — App Monitor  (user_app/monitor.py)
Background thread: hides overlay when an excluded app is focused.
"""

import logging
import sys
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.30   # seconds


class AppMonitor:
    def __init__(self, db, cfg, show_cb: Callable, hide_cb: Callable):
        self._db = db
        self._cfg = cfg
        self._show = show_cb
        self._hide = hide_cb
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_excluded = False
        self._excluded_cache: list = []
        self._cache_ts: float = 0.0

    def start(self):
        if sys.platform != "win32":
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AppMonitor")
        self._thread.start()

    def stop(self):
        self._running = False

    def _get_excluded(self):
        now = time.monotonic()
        if now - self._cache_ts > 10:
            try:
                self._excluded_cache = self._db.get_excluded_names()
                self._cache_ts = now
            except Exception:
                pass
        return self._excluded_cache

    def _foreground_proc(self) -> Optional[str]:
        try:
            import win32gui, win32process, psutil
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except Exception:
            return None

    def _loop(self):
        while self._running:
            try:
                if not self._cfg.watermark_enabled or not self._cfg.is_within_schedule():
                    if not self._last_excluded:
                        self._hide()
                        self._last_excluded = True
                    time.sleep(POLL_INTERVAL)
                    continue

                proc = self._foreground_proc()
                excluded = (proc in self._get_excluded()) if proc else False

                if excluded and not self._last_excluded:
                    self._hide()
                    self._last_excluded = True
                elif not excluded and self._last_excluded:
                    self._show()
                    self._last_excluded = False
            except Exception as e:
                logger.debug("monitor loop: %s", e)

            time.sleep(POLL_INTERVAL)


# ─────────────────────────────────────────────────────────────────────────────

"""
WatermarkPro v2 — User System Tray  (user_app/tray.py)
Minimal menu: Toggle watermark ON/OFF · Contact Admin · Exit (credential-gated)
"""

# ── user_app/tray.py content starts here ─────────────────────────────────────
