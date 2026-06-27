"""
WatermarkPro v2 — Admin Dashboard Entry Point  (admin_app/main.py)
Standalone application — completely separate from the user watermark EXE.
Connect to the same PostgreSQL database from any authorised machine.
"""

import logging
import sys
import tkinter as tk
from pathlib import Path
# ── Autostart proxy (for Settings section) ────────────────────────────────
from user_app.autostart import (enable_autostart, disable_autostart,
                                is_autostart_enabled)

# ── Logging ───────────────────────────────────────────────────────────────────
_LOG_DIR = Path.home() / "AppData" / "Local" / "WatermarkPro" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "watermark_admin.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("admin_main")


def _show_error(title: str, msg: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, f"WatermarkPro Admin — {title}", 0x10)
    except Exception:
        print(f"[ERROR] {title}: {msg}", file=sys.stderr)


def main() -> None:
    # ── Import shared layer ────────────────────────────────────────────────────
    try:
        from shared.config_file    import get_db_kwargs, get_app_value
        from shared.database       import DatabaseManager
        from shared.config_manager import ConfigManager
    except ImportError as e:
        _show_error("Import Error", f"Shared module import failed:\n{e}\n\n"
                    "Ensure shared/ is on sys.path or the EXE was built correctly.")
        sys.exit(1)

    # ── Connect to PostgreSQL ──────────────────────────────────────────────────
    try:
        db_kw = get_db_kwargs()
        db    = DatabaseManager(**db_kw)
        db.ensure_defaults()
        logger.info("Admin connected to PostgreSQL at %s:%s/%s",
                    db_kw["host"], db_kw["port"], db_kw["dbname"])
    except FileNotFoundError as e:
        _show_error("Config Missing", str(e))
        sys.exit(1)
    except Exception as e:
        _show_error("Database Error",
                    f"Cannot connect to PostgreSQL:\n{e}\n\nCheck config.ini.")
        sys.exit(1)

    cfg = ConfigManager(db)

    # ── Tkinter root ───────────────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()


    class _AutostartProxy:
        enable_autostart     = staticmethod(enable_autostart)
        disable_autostart    = staticmethod(disable_autostart)
        is_autostart_enabled = staticmethod(is_autostart_enabled)

    autostart = _AutostartProxy()

    # ── Open login → admin panel ───────────────────────────────────────────────
    from admin_app.dashboard import LoginDialog, AdminPanel
    import getpass

    def _open():
        login = LoginDialog(root, db)
        root.wait_window(login)
        if login.result:
            db.log("ADMIN_LOGIN", "Admin panel opened",
                   "INFO", getpass.getuser(), "")
            panel = AdminPanel(root, db, cfg, autostart)
            panel.protocol("WM_DELETE_WINDOW", lambda: _on_close(panel))
            root.wait_window(panel)
        else:
            db.log("ADMIN_LOGIN_FAILED", "Wrong password",
                   "WARNING", getpass.getuser(), "")
        # Close root after panel is done
        root.after(0, root.quit)

    def _on_close(panel):
        db.log("ADMIN_PANEL_CLOSED", "", "INFO", getpass.getuser(), "")
        panel.destroy()

    root.after(0, _open)
    root.mainloop()
    logger.info("Admin session ended.")


if __name__ == "__main__":
    main()
