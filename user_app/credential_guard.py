"""
WatermarkPro v2 — Credential Guard
Pops an admin-password dialog whenever a user attempts to close the app
(via tray → Exit).  Only the correct admin password allows shutdown.

Killing the process via Task Manager bypasses this dialog, but the
Windows Service Guardian (guardian/service.py) will restart it within
10 seconds — making Task Manager kills effectively useless.
"""

import tkinter as tk
import logging

logger = logging.getLogger(__name__)

# Colours
C_BG    = "#1a1a2e"
C_CARD  = "#16213e"
C_ACCENT = "#4f8ef7"
C_DANGER = "#dd4444"
C_TEXT  = "#e0e0e0"
C_MUTED = "#888888"


class CredentialGuard:
    """Wraps every exit attempt behind an admin-password challenge."""

    def __init__(self, db):
        self.db = db

    def request_exit(self) -> bool:
        """
        Show a password dialog.
        Returns True  → caller should proceed with shutdown.
        Returns False → wrong password; caller should stay running.
        """
        result = {"ok": False}

        root = tk.Tk()
        root.withdraw()

        dialog = _PasswordDialog(root, self.db, result)
        root.wait_window(dialog)

        try:
            root.destroy()
        except Exception:
            pass

        return result["ok"]


class _PasswordDialog(tk.Toplevel):
    """Dark-themed password prompt."""

    def __init__(self, parent, db, result: dict):
        super().__init__(parent)
        self._db = db
        self._result = result
        self._attempts = 0

        self.title("WatermarkPro — Authentication Required")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 400) // 2
        y = (self.winfo_screenheight() - 300) // 2
        self.geometry(f"400x300+{max(0,x)}+{max(0,y)}")

    def _build(self):
        # Lock icon
        tk.Label(self, text="🔒", font=("Arial", 32),
                 bg=C_BG, fg=C_ACCENT).pack(pady=(24, 4))

        tk.Label(self, text="Administrator Credential Required",
                 font=("Arial", 13, "bold"), bg=C_BG, fg=C_TEXT).pack()

        tk.Label(self,
                 text="Enter the admin password to close WatermarkPro.",
                 font=("Arial", 10), bg=C_BG, fg=C_MUTED, wraplength=340).pack(pady=(4, 14))

        # Password entry
        pw_frame = tk.Frame(self, bg=C_BG)
        pw_frame.pack()
        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(
            pw_frame, textvariable=self._pw_var, show="•",
            font=("Arial", 12), width=24,
            bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", bd=6,
        )
        self._pw_entry.pack()
        self._pw_entry.focus_set()
        self._pw_entry.bind("<Return>", lambda _: self._submit())

        # Error label (hidden until wrong password)
        self._err_var = tk.StringVar()
        tk.Label(self, textvariable=self._err_var,
                 fg=C_DANGER, bg=C_BG, font=("Arial", 10)).pack(pady=6)

        # Buttons
        btn_row = tk.Frame(self, bg=C_BG)
        btn_row.pack(pady=8)

        tk.Button(
            btn_row, text="Confirm & Close App",
            command=self._submit,
            font=("Arial", 11, "bold"),
            bg=C_DANGER, fg="white",
            activebackground="#bb2222",
            relief="flat", padx=16, pady=8, cursor="hand2",
        ).pack(side="left", padx=6)

        tk.Button(
            btn_row, text="Cancel",
            command=self._cancel,
            font=("Arial", 11),
            bg=C_CARD, fg=C_TEXT,
            activebackground=C_CARD,
            relief="flat", padx=16, pady=8, cursor="hand2",
        ).pack(side="left", padx=6)

        tk.Label(
            self,
            text="❕ Closing this dialog keeps the watermark running.",
            font=("Arial", 9), bg=C_BG, fg=C_MUTED,
        ).pack(pady=(8, 0))

    def _submit(self):
        pw = self._pw_var.get()
        if self._db.verify_password(pw):
            logger.info("Credential guard: exit authorised")
            self._result["ok"] = True
            self.destroy()
        else:
            self._attempts += 1
            self._pw_var.set("")
            self._pw_entry.focus_set()
            self._err_var.set(
                f"Incorrect password. ({self._attempts} failed attempt{'s' if self._attempts>1 else ''})"
            )
            logger.warning("Credential guard: failed attempt #%d", self._attempts)
            # Log to DB (non-fatal if DB unavailable)
            try:
                import getpass, socket
                self._db.log(
                    "EXIT_AUTH_FAILED",
                    f"Attempt #{self._attempts}",
                    "WARNING",
                    getpass.getuser(),
                    socket.gethostname(),
                )
            except Exception:
                pass

    def _cancel(self):
        logger.info("Credential guard: exit cancelled by user")
        self._result["ok"] = False
        self.destroy()
