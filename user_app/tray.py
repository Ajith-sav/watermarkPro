"""
WatermarkPro v2 — User System Tray (user_app/tray.py)
Minimal tray: toggle ON/OFF · Exit (requires admin password)
No access to the Admin Panel — that is a separate EXE.
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class UserTray:
    def __init__(self, cfg, on_toggle: Callable, on_exit: Callable):
        self._cfg      = cfg
        self._on_toggle = on_toggle
        self._on_exit   = on_exit
        self._icon      = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="UserTray"
        )
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from user_app._icon import make_tray_image

            img = make_tray_image()
            self._icon = pystray.Icon(
                "WatermarkPro",
                icon=img,
                title=f"WatermarkPro — {self._cfg.get_str('organization_name','Org')}",
                menu=self._build_menu(pystray),
            )
            self._icon.run()
        except Exception as e:
            logger.error("UserTray error: %s", e)

    def _build_menu(self, pystray):
        org   = self._cfg.get_str("organization_name", "WatermarkPro")
        on    = self._cfg.watermark_enabled

        def toggle(icon, item):
            self._on_toggle()
            icon.menu = self._build_menu(pystray)

        def exit_app(icon, item):
            self._on_exit(icon)

        return pystray.Menu(
            pystray.MenuItem(f"🛡 {org}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "✅ Watermark ON" if on else "⭕ Watermark OFF",
                toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit  (admin password required)", exit_app),
        )

    def update_menu(self):
        if self._icon:
            try:
                import pystray
                self._icon.menu = self._build_menu(pystray)
                self._icon.update_menu()
            except Exception:
                pass

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
