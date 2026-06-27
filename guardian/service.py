"""
WatermarkPro v2 — Guardian Windows Service
Runs as SYSTEM.  Monitors WatermarkPro.exe in every user session and
restarts it if the process is killed — even via Task Manager.

To TRULY stop the watermark, a user must:
  1. Go to Task Manager → Services → WatermarkProGuardian → Stop
     (requires Administrator credentials)
  OR
  2. Enter the admin password in the watermark's tray → Exit dialog

Build:  pyinstaller --onefile --noconsole --name WatermarkProService service.py
Install: WatermarkProService.exe install
Start:   net start WatermarkProGuardian
         (or sc start WatermarkProGuardian)
"""

import logging
import os
import sys
import time
from pathlib import Path

# Windows Service imports (pywin32)
import servicemanager
import win32event
import win32service
import win32serviceutil

logger = logging.getLogger("WatermarkGuardian")

SERVICE_NAME    = "WatermarkProGuardian"
SERVICE_DISPLAY = "WatermarkPro Guardian"
SERVICE_DESC    = ("Ensures the WatermarkPro screen-watermark policy remains active. "
                   "Stopping this service requires Administrator credentials.")

# Where the user-facing EXE lives (same folder as this service EXE)
_APP_EXE_NAME = "WatermarkPro.exe"
POLL_SECS     = 10       # seconds between process-alive checks
MAX_RESTARTS  = 50       # safety limit per service run


def _app_exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _APP_EXE_NAME
    # Dev mode: look next to this script
    return Path(__file__).parent.parent / "dist" / _APP_EXE_NAME


def _is_running() -> bool:
    """Return True if WatermarkPro.exe is running in any process list."""
    try:
        import psutil
        target = _APP_EXE_NAME.lower()
        return any(
            (p.info.get("name") or "").lower() == target
            for p in psutil.process_iter(["name"])
        )
    except Exception:
        return False


def _launch_in_user_session(exe: Path) -> bool:
    """
    Create WatermarkPro.exe in the active console user's session.
    Must run as SYSTEM to use WTSQueryUserToken.
    """
    if not exe.exists():
        servicemanager.LogErrorMsg(f"WatermarkPro EXE not found: {exe}")
        return False
    try:
        import ctypes
        import ctypes.wintypes as wt
        import win32ts
        import win32process
        import win32security

        # Get active session token
        session_id = win32ts.WTSGetActiveConsoleSessionId()
        if session_id == 0xFFFFFFFF:
            return False  # No active user session yet

        user_token = win32ts.WTSQueryUserToken(session_id)

        # Duplicate to a primary token
        dup_token = win32security.DuplicateTokenEx(
            user_token,
            win32security.SecurityImpersonation,
            None,
            win32security.TokenPrimary,
        )

        # Set up environment and startup info
        env = win32process.CreateEnvironmentBlock(dup_token, False)

        si = win32process.STARTUPINFO()
        si.lpDesktop = "winsta0\\default"
        si.dwFlags   = win32process.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE — no terminal window

        win32process.CreateProcessAsUser(
            dup_token,
            str(exe),        # application path
            None,            # command line
            None,            # process security
            None,            # thread security
            False,           # inherit handles
            win32process.NORMAL_PRIORITY_CLASS | win32process.CREATE_NO_WINDOW,
            env,             # user environment block
            None,            # working directory
            si,              # startup info
        )
        servicemanager.LogInfoMsg(f"Restarted WatermarkPro in session {session_id}")
        return True

    except Exception as e:
        servicemanager.LogErrorMsg(f"Failed to launch in user session: {e}")
        return False


class WatermarkGuardian(win32serviceutil.ServiceFramework):
    _svc_name_         = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY
    _svc_description_  = SERVICE_DESC

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._running    = True

    # ── Service lifecycle ─────────────────────────────────────────────────────

    def SvcStop(self):
        servicemanager.LogInfoMsg("WatermarkPro Guardian: stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)
        self._running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        servicemanager.LogInfoMsg("WatermarkPro Guardian started.")
        self._main_loop()

    # ── Main monitoring loop ──────────────────────────────────────────────────

    def _main_loop(self):
        exe      = _app_exe_path()
        restarts = 0

        while self._running and restarts < MAX_RESTARTS:
            # Wait POLL_SECS seconds, or until stop signal
            rc = win32event.WaitForSingleObject(self._stop_event, POLL_SECS * 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break  # Stop signal received

            if not _is_running():
                restarts += 1
                servicemanager.LogWarningMsg(
                    f"WatermarkPro not found — restarting (#{restarts})"
                )
                _launch_in_user_session(exe)
                # Brief pause before next check to let process start
                time.sleep(3)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Called by SCM — run the service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WatermarkGuardian)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Called from command line: install / remove / start / stop
        win32serviceutil.HandleCommandLine(WatermarkGuardian)
