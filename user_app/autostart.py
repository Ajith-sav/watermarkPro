"""
WatermarkPro v2 — Auto-Start via Task Scheduler
Uses Windows Task Scheduler (schtasks) instead of the Registry Run key.

Why Task Scheduler instead of Registry?
  • Registry Run key with python.exe → opens a visible terminal window
  • Task Scheduler with --noconsole EXE → starts silently, exactly like
    Chrome, Spotify, Teams, and other professional Windows applications
  • Task Scheduler tasks are harder to disable accidentally
  • The service guardian separately protects against process kills
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

TASK_NAME  = "WatermarkPro"
TASK_DESC  = "WatermarkPro — Screen Watermark Enforcement"
START_DELAY = "0000:30"   # 30-second delay so desktop is fully loaded first


def _exe_path() -> str:
    """Return the path of the current executable or pythonw.exe launcher."""
    if getattr(sys, "frozen", False):
        # Running as built EXE — just use our path
        return str(Path(sys.executable))
    else:
        # Development mode: use pythonw.exe (suppresses terminal)
        py_dir = Path(sys.executable).parent
        pythonw = py_dir / "pythonw.exe"
        if not pythonw.exists():
            pythonw = Path(sys.executable)           # fall back to python.exe
        main_script = Path(__file__).parent / "main.py"
        return f'"{pythonw}" "{main_script}"'


def _run(args: list) -> tuple:
    """Run a command, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def enable_autostart() -> bool:
    """Register a Task Scheduler task to launch at every user logon."""
    if sys.platform != "win32":
        return False
    try:
        exe = _exe_path()

        # Remove any old entry first
        _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])

        # Create the task
        # /SC ONLOGON       — run when any user logs on
        # /DELAY            — wait 30 s so the shell is ready
        # /IT               — interactive task (can show UI in the user session)
        # /RL LIMITED       — run at standard privilege (no UAC prompt)
        # /F                — force-create / overwrite
        rc, out, err = _run([
            "schtasks", "/Create",
            "/TN",    TASK_NAME,
            "/TR",    exe,
            "/SC",    "ONLOGON",
            "/DELAY", START_DELAY,
            "/IT",
            "/RL",    "LIMITED",
            "/F",
        ])

        if rc == 0:
            logger.info("Task Scheduler task '%s' created.", TASK_NAME)
            return True
        else:
            logger.error("schtasks /Create failed (rc=%d): %s", rc, err)
            return False

    except Exception as e:
        logger.error("enable_autostart error: %s", e)
        return False


def disable_autostart() -> bool:
    """Remove the Task Scheduler logon task."""
    if sys.platform != "win32":
        return False
    try:
        rc, _, err = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        if rc == 0:
            logger.info("Task Scheduler task '%s' removed.", TASK_NAME)
            return True
        logger.warning("schtasks /Delete: %s", err)
        return False
    except Exception as e:
        logger.error("disable_autostart error: %s", e)
        return False


def is_autostart_enabled() -> bool:
    """Return True if the Task Scheduler task exists."""
    if sys.platform != "win32":
        return False
    try:
        rc, out, _ = _run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"])
        return rc == 0 and TASK_NAME.lower() in out.lower()
    except Exception:
        return False


def run_task_now() -> bool:
    """Manually trigger the task (useful for testing)."""
    if sys.platform != "win32":
        return False
    rc, _, err = _run(["schtasks", "/Run", "/TN", TASK_NAME])
    return rc == 0
