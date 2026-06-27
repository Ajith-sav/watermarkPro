"""
WatermarkPro v2 — User Application Entry Point
Runs silently (no console window).  Shows watermark overlay, system tray.
Admin panel is a SEPARATE application (WatermarkProAdmin.exe).
"""

import logging
import os
import signal
import sys
import tkinter as tk
from pathlib import Path

# ── Logging (file only — no console in production) ────────────────────────────
_LOG_DIR = Path.home() / "AppData" / "Local" / "WatermarkPro" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[logging.FileHandler(_LOG_DIR / "watermark_user.log", encoding="utf-8")],
)
logger = logging.getLogger("user_main")

# ── Single-instance guard ─────────────────────────────────────────────────────
_MUTEX_NAME = "WatermarkPro_User_v2"


def _acquire_single_instance() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        return ctypes.windll.kernel32.GetLastError() != 183
    except Exception:
        return True


def main():
    if not _acquire_single_instance():
        logger.warning("Another user instance is already running. Exiting.")
        sys.exit(0)

    # ── Connect to PostgreSQL ─────────────────────────────────────────────────
    try:
        from shared.config_file   import get_db_kwargs, get_app_value
        from shared.database      import DatabaseManager
        from shared.config_manager import ConfigManager
    except ImportError as e:
        _show_error(f"Shared module import failed:\n{e}\n\nEnsure shared/ is on the Python path.")
        sys.exit(1)

    try:
        db_kw = get_db_kwargs()
        db    = DatabaseManager(**db_kw)
        db.ensure_defaults()
    except Exception as e:
        _show_error(f"Cannot connect to database:\n{e}\n\nCheck config.ini settings.")
        sys.exit(1)

    cfg = ConfigManager(db)

    # ── Audit helper ──────────────────────────────────────────────────────────
    import getpass, socket, platform

    def audit(event_type, details="", severity="INFO"):
        try:
            db.log(event_type, details, severity,
                   getpass.getuser(), socket.gethostname())
        except Exception:
            pass

    # ── Register this machine ─────────────────────────────────────────────────
    try:
        import platform as _pl
        db.register_user(
            username    = cfg.username,
            hostname    = cfg.hostname,
            department  = cfg.get_str("department"),
            ip_address  = cfg.ip_address,
            app_version = cfg.get_str("app_version", "2.0.0"),
            os_info     = f"{_pl.system()} {_pl.release()}",
        )
    except Exception as e:
        logger.warning("register_user failed: %s", e)

    # ── First-run auto-start via Task Scheduler ───────────────────────────────
    from user_app.autostart import enable_autostart, is_autostart_enabled
    if not is_autostart_enabled():
        if enable_autostart():
            audit("AUTOSTART_ENABLED", "Task Scheduler task created on first run")

    # ── Credential guard (admin password required to exit) ────────────────────
    from user_app.credential_guard import CredentialGuard
    guard = CredentialGuard(db)

    # ── Tkinter root (hidden — just the event loop) ───────────────────────────
    root = tk.Tk()
    root.withdraw()
    root.title("WatermarkPro")
    _apply_icon(root)

    # ── Watermark overlay ─────────────────────────────────────────────────────
    from user_app.overlay import WatermarkManager
    wm = WatermarkManager(cfg)
    wm.start(root)

    # ── App monitor (hides overlay for excluded apps) ─────────────────────────
    from user_app.monitor import AppMonitor
    monitor = AppMonitor(db, cfg, show_cb=wm.show_all, hide_cb=wm.hide_all)
    monitor.start()

    # ── Screenshot detection ──────────────────────────────────────────────────
    _start_screenshot_detection(db, cfg)

    # ── System tray ───────────────────────────────────────────────────────────
    from user_app.tray import UserTray

    def on_toggle():
        cfg.set("enabled", "false" if cfg.watermark_enabled else "true")
        if cfg.watermark_enabled:
            wm.show_all(); audit("WATERMARK_ENABLED",  "Via tray")
        else:
            wm.hide_all(); audit("WATERMARK_DISABLED", "Via tray")
        tray.update_menu()

    def on_exit(icon):
        if guard.request_exit():
            audit("APP_STOPPED", "Admin-authorised exit")
            monitor.stop()
            if icon:
                icon.stop()
            try:
                root.quit(); root.destroy()
            except Exception:
                pass
            sys.exit(0)
        else:
            audit("EXIT_CANCELLED", "Wrong password or cancelled", "WARNING")

    tray = UserTray(cfg, on_toggle=on_toggle, on_exit=on_exit)
    tray.start()

    # ── Initialise watermark state ────────────────────────────────────────────
    if cfg.watermark_enabled and cfg.is_within_schedule():
        wm.show_all()
    else:
        wm.hide_all()

    audit("APP_STARTED", f"v{cfg.get_str('app_version','2.0.0')} user process started")

    # ── Periodic schedule enforcement (every 60 s) ────────────────────────────
    def _tick():
        try:
            if cfg.watermark_enabled and cfg.is_within_schedule():
                if not wm.is_visible():
                    wm.show_all()
            else:
                if wm.is_visible():
                    wm.hide_all()
        except Exception:
            pass
        root.after(60_000, _tick)

    root.after(60_000, _tick)

    signal.signal(signal.SIGINT, lambda *_: on_exit(None))
    logger.info("Entering event loop")
    root.mainloop()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_icon(root: tk.Tk) -> None:
    try:
        from pathlib import Path
        ico = Path(sys.executable).parent / "assets" / "icon.ico" \
              if getattr(sys, "frozen", False) \
              else Path(__file__).parent.parent / "assets" / "icon.ico"
        if ico.exists():
            root.iconbitmap(str(ico))
    except Exception:
        pass


def _show_error(msg: str) -> None:
    """Show a message box without requiring any imports to succeed."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "WatermarkPro — Error", 0x10)
    except Exception:
        print(msg, file=sys.stderr)


def _start_screenshot_detection(db, cfg) -> None:
    if sys.platform != "win32":
        return
    if not cfg.get_bool("screenshot_alert", True):
        return
    import threading, time, ctypes, getpass, socket
    from datetime import datetime

    def _loop():
        last = 0
        while True:
            state = ctypes.windll.user32.GetAsyncKeyState(0x2C)
            if state and not last:
                try:
                    db.log(
                        "SCREENSHOT_DETECTED",
                        f"PrintScreen pressed at {datetime.now():%H:%M:%S}",
                        "SECURITY",
                        getpass.getuser(),
                        socket.gethostname(),
                    )
                except Exception:
                    pass
            last = state
            time.sleep(0.05)

    threading.Thread(target=_loop, daemon=True, name="ScreenshotDetect").start()


if __name__ == "__main__":
    main()
