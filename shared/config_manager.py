"""
WatermarkPro v2 — Config Manager
Wraps DatabaseManager with caching, type coercion, and observer pattern.
"""

import getpass
import logging
import socket
from datetime import datetime, time as dtime
from typing import Any, Callable, Dict, List, Optional

from shared.models import CLASSIFICATION_COLORS

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, db):
        self.db = db
        self._observers: List[Callable] = []
        self._cache: Dict[str, str] = {}
        self._refresh_cache()

        self.username: str = getpass.getuser()
        self.hostname: str = socket.gethostname()
        try:
            self.ip_address: str = socket.gethostbyname(self.hostname)
        except Exception:
            self.ip_address = "127.0.0.1"

    def _refresh_cache(self) -> None:
        self._cache = self.db.get_all()

    def get_str(self, key: str, default: str = "") -> str:
        return self._cache.get(key, self.db.get(key, default))

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self._cache.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self._cache.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self._cache.get(key, str(default)).lower() in ("true", "1", "yes", "on")

    def set(self, key: str, value: Any) -> None:
        self.db.set(key, value)
        self._cache[key] = str(value)
        self._notify()

    def bulk_set(self, data: Dict[str, Any]) -> None:
        self.db.bulk_set(data)
        self._refresh_cache()
        self._notify()

    def add_observer(self, fn: Callable) -> None:
        if fn not in self._observers:
            self._observers.append(fn)

    def remove_observer(self, fn: Callable) -> None:
        if fn in self._observers:
            self._observers.remove(fn)

    def _notify(self) -> None:
        for fn in list(self._observers):
            try:
                fn()
            except Exception as e:
                logger.warning("Observer error: %s", e)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def watermark_enabled(self) -> bool:
        return self.get_bool("enabled", True)

    @property
    def watermark_text(self) -> str:
        template = self.get_str("watermark_text",
                                "{classification} | {username} | {hostname} | {datetime}")
        now = datetime.now()
        subs = {
            "{username}":       self.username,
            "{hostname}":       self.hostname,
            "{date}":           now.strftime("%Y-%m-%d"),
            "{time}":           now.strftime("%H:%M"),
            "{datetime}":       now.strftime("%Y-%m-%d  %H:%M"),
            "{classification}": self.get_str("classification", "CONFIDENTIAL"),
            "{department}":     self.get_str("department", ""),
            "{organization}":   self.get_str("organization_name", ""),
            "{ip}":             self.ip_address,
        }
        result = template
        for ph, val in subs.items():
            result = result.replace(ph, val)
        return result

    @property
    def watermark_color(self) -> str:
        color = self.get_str("color", "")
        if not color:
            cls = self.get_str("classification", "CONFIDENTIAL")
            return CLASSIFICATION_COLORS.get(cls, "#AAAAAA")
        return color

    @property
    def font_size(self) -> int:
        return self.get_int("font_size", 20)

    @property
    def font_family(self) -> str:
        return self.get_str("font_family", "Arial")

    @property
    def font_bold(self) -> bool:
        return self.get_bool("font_bold", False)

    @property
    def opacity(self) -> float:
        return max(0.03, min(0.95, self.get_float("opacity", 0.18)))

    @property
    def rotation(self) -> float:
        return self.get_float("rotation", -45)

    @property
    def spacing_x(self) -> int:
        return max(80, self.get_int("spacing_x", 260))

    @property
    def spacing_y(self) -> int:
        return max(60, self.get_int("spacing_y", 160))

    @property
    def update_interval_ms(self) -> int:
        return max(5000, self.get_int("update_interval", 30) * 1000)

    def is_within_schedule(self) -> bool:
        if not self.get_bool("schedule_enabled"):
            return True
        try:
            now = datetime.now().time()
            start = dtime(*[int(x) for x in self.get_str("schedule_start", "08:00").split(":")])
            end   = dtime(*[int(x) for x in self.get_str("schedule_end",   "18:00").split(":")])
            return start <= now <= end
        except Exception:
            return True

    def get_os_info(self) -> str:
        import platform
        return f"{platform.system()} {platform.release()} ({platform.machine()})"
