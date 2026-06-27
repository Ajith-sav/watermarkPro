"""
WatermarkPro v2 — Admin Dashboard UI  (admin_app/dashboard.py)
7-section dark control centre backed by PostgreSQL.
"""

import csv
import getpass
import logging
import platform
import socket
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────────────────────────────
C_BG      = "#0d1117"
C_PANEL   = "#161b22"
C_CARD    = "#1c2333"
C_ACCENT  = "#4f8ef7"
C_ACCENT2 = "#e94560"
C_TEXT    = "#e6edf3"
C_MUTED   = "#8b949e"
C_SUCCESS = "#44bb44"
C_WARNING = "#ddaa22"
C_DANGER  = "#dd4444"
C_SEC     = "#dd8833"

SEV_COLORS = {"INFO": C_TEXT, "WARNING": C_WARNING,
              "ERROR": C_DANGER, "SECURITY": C_SEC}


# ══════════════════════════════════════════════════════════════════════════════
#  Login dialog
# ══════════════════════════════════════════════════════════════════════════════
class LoginDialog(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.result = False
        self.title("WatermarkPro Admin — Login")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._center(380, 270)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

    def _build(self):
        tk.Label(self, text="🛡", font=("Arial", 36), bg=C_BG, fg=C_ACCENT).pack(pady=(20, 2))
        tk.Label(self, text="WatermarkPro Admin", font=("Arial", 14, "bold"),
                 bg=C_BG, fg=C_TEXT).pack()
        tk.Label(self, text="Enter administrator password",
                 font=("Arial", 10), bg=C_BG, fg=C_MUTED).pack(pady=(2, 10))

        self._pw = tk.Entry(self, show="•", font=("Arial", 13), width=22,
                            bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT,
                            relief="flat", bd=6)
        self._pw.pack()
        self._pw.focus_set()
        self._pw.bind("<Return>", lambda _: self._login())

        self._err = tk.Label(self, text="", fg=C_DANGER, bg=C_BG, font=("Arial", 10))
        self._err.pack(pady=5)

        tk.Button(self, text="Login →", command=self._login,
                  font=("Arial", 11, "bold"), bg=C_ACCENT, fg="white",
                  relief="flat", padx=20, pady=7, cursor="hand2").pack()

    def _login(self):
        if self.db.verify_password(self._pw.get()):
            self.result = True
            self.destroy()
        else:
            self._err.config(text="Incorrect password.")
            self._pw.delete(0, "end")


# ══════════════════════════════════════════════════════════════════════════════
#  Main admin panel
# ══════════════════════════════════════════════════════════════════════════════
class AdminPanel(tk.Toplevel):
    def __init__(self, parent, db, cfg, autostart):
        super().__init__(parent)
        self.db        = db
        self.cfg       = cfg
        self.autostart = autostart

        self.title("WatermarkPro — Admin Dashboard")
        self.configure(bg=C_BG)
        self.geometry("1040x700")
        self.minsize(900, 600)
        self._center()
        self._content: tk.Frame | None = None
        self._nav_btns: dict = {}
        self._build_layout()
        self._show("dashboard")

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 1040) // 2
        y = (self.winfo_screenheight() - 700)  // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

    # ── Shell ─────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Sidebar
        side = tk.Frame(self, bg=C_PANEL, width=195)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        logo = tk.Frame(side, bg=C_PANEL, pady=14)
        logo.pack(fill="x")
        tk.Label(logo, text="🛡 WatermarkPro", font=("Arial", 13, "bold"),
                 bg=C_PANEL, fg=C_ACCENT).pack()
        tk.Label(logo, text=f"Admin  ·  v{self.cfg.get_str('app_version','2.0.0')}",
                 font=("Arial", 9), bg=C_PANEL, fg=C_MUTED).pack()

        tk.Frame(side, bg=C_CARD, height=1).pack(fill="x", padx=12, pady=6)

        nav = [
            ("📊", "Dashboard",   "dashboard"),
            ("🎨", "Appearance",  "appearance"),
            ("📝", "Content",     "content"),
            ("🚫", "Exclusions",  "exclusions"),
            ("👥", "Users",       "users"),
            ("📋", "Audit Log",   "logs"),
            ("⚙",  "Settings",   "settings"),
        ]
        for icon, label, key in nav:
            b = tk.Button(side, text=f"  {icon}  {label}",
                          font=("Arial", 11), anchor="w",
                          bg=C_PANEL, fg=C_TEXT, activebackground=C_CARD,
                          relief="flat", bd=0, padx=12, pady=9, cursor="hand2",
                          command=lambda k=key: self._show(k))
            b.pack(fill="x", padx=4, pady=1)
            self._nav_btns[key] = b

        tk.Frame(side, bg=C_PANEL).pack(fill="y", expand=True)
        tk.Label(side, text=f"👤 {getpass.getuser()}",
                 font=("Arial", 9), bg=C_PANEL, fg=C_MUTED).pack(pady=4)

        # Content area
        self._main = tk.Frame(self, bg=C_BG)
        self._main.pack(side="left", fill="both", expand=True)

    def _show(self, key: str):
        for k, b in self._nav_btns.items():
            b.config(bg=C_ACCENT if k == key else C_PANEL,
                     fg="white"  if k == key else C_TEXT)
        if self._content:
            self._content.destroy()
        self._content = tk.Frame(self._main, bg=C_BG)
        self._content.pack(fill="both", expand=True, padx=18, pady=18)
        {
            "dashboard":  self._dashboard,
            "appearance": self._appearance,
            "content":    self._content_tab,
            "exclusions": self._exclusions,
            "users":      self._users,
            "logs":       self._logs,
            "settings":   self._settings,
        }.get(key, self._dashboard)()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _title(self, text):
        tk.Label(self._content, text=text, font=("Arial", 16, "bold"),
                 bg=C_BG, fg=C_TEXT).pack(anchor="w", pady=(0, 12))

    def _card(self, title="") -> tk.Frame:
        outer = tk.Frame(self._content, bg=C_CARD, bd=0)
        outer.pack(fill="x", pady=(0, 10))
        if title:
            tk.Label(outer, text=title, font=("Arial", 11, "bold"),
                     bg=C_CARD, fg=C_ACCENT).pack(anchor="w", padx=14, pady=(10, 2))
        inner = tk.Frame(outer, bg=C_CARD)
        inner.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        return inner

    def _lbl(self, p, t, muted=False):
        return tk.Label(p, text=t, bg=C_CARD,
                        fg=C_MUTED if muted else C_TEXT, font=("Arial", 10))

    def _btn(self, p, text, cmd, color=C_ACCENT):
        return tk.Button(p, text=text, command=cmd,
                         font=("Arial", 10), bg=color, fg="white",
                         activebackground=color, relief="flat",
                         padx=12, pady=5, cursor="hand2")

    def _slider(self, p, label, key, lo, hi, step=1, fmt="{:.0f}"):
        row = tk.Frame(p, bg=C_CARD); row.pack(fill="x", pady=3)
        self._lbl(row, label).pack(side="left", padx=(0, 8))
        val_lbl = tk.Label(row, bg=C_CARD, fg=C_ACCENT,
                           font=("Arial", 10, "bold"), width=7)
        val_lbl.pack(side="right")
        cur = float(self.cfg.get_str(key) or lo)
        def on(v, k=key, lbl=val_lbl):
            fv = float(v)
            lbl.config(text=fmt.format(fv))
            self.cfg.set(k, fv if step < 1 else int(fv))
        sc = tk.Scale(row, from_=lo, to=hi, orient="horizontal", resolution=step,
                      bg=C_CARD, fg=C_TEXT, troughcolor=C_PANEL,
                      highlightthickness=0, bd=0, sliderrelief="flat",
                      showvalue=False, command=on, length=200)
        sc.set(cur); val_lbl.config(text=fmt.format(cur)); sc.pack(side="right", padx=4)
        return sc

    def _toggle(self, p, label, key):
        var = tk.BooleanVar(value=self.cfg.get_bool(key))
        row = tk.Frame(p, bg=C_CARD); row.pack(fill="x", pady=3)
        self._lbl(row, label).pack(side="left")
        tk.Checkbutton(row, variable=var,
                       command=lambda k=key, v=var: self.cfg.set(k, "true" if v.get() else "false"),
                       bg=C_CARD, fg=C_TEXT, selectcolor=C_ACCENT,
                       activebackground=C_CARD, relief="flat").pack(side="right")
        return var

    def _scroll_table(self, parent):
        """Return (canvas, rows_frame) scrollable container."""
        c = tk.Canvas(parent, bg=C_CARD, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=c.yview)
        c.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        c.pack(fill="both", expand=True)
        f = tk.Frame(c, bg=C_CARD)
        c.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
        return c, f

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _dashboard(self):
        self._title("📊 Dashboard")
        # Stat cards
        row = tk.Frame(self._content, bg=C_BG); row.pack(fill="x", pady=(0, 12))
        for label, val, color in [
            ("👥 Total Users",   str(self.db.get_user_count()), C_ACCENT),
            ("🟢 Active (24h)",  str(self.db.get_active_user_count()), C_SUCCESS),
            ("📋 Log Events",    str(len(self.db.get_audit_log(limit=9999))), C_WARNING),
            ("🔒 Watermark",
             "ON" if self.cfg.watermark_enabled else "OFF",
             C_SUCCESS if self.cfg.watermark_enabled else C_DANGER),
        ]:
            card = tk.Frame(row, bg=C_CARD, padx=18, pady=14)
            card.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(card, text=val, font=("Arial", 24, "bold"),
                     bg=C_CARD, fg=color).pack()
            tk.Label(card, text=label, font=("Arial", 10),
                     bg=C_CARD, fg=C_MUTED).pack()

        # Current text
        pc = self._card("📌 Current Watermark Text")
        tk.Label(pc, text=self.cfg.watermark_text, font=("Arial", 11, "italic"),
                 bg=C_CARD, fg=C_ACCENT, wraplength=560).pack(anchor="w", pady=3)

        # DB info
        dc = self._card("🐘 PostgreSQL Connection")
        try:
            from shared.config_file import get_db_kwargs
            kw = get_db_kwargs()
            for k, v in [("Host", f"{kw['host']}:{kw['port']}"),
                         ("Database", kw["dbname"]),
                         ("User", kw["user"])]:
                r = tk.Frame(dc, bg=C_CARD); r.pack(fill="x", pady=1)
                tk.Label(r, text=f"{k}:", width=10, anchor="w",
                         bg=C_CARD, fg=C_MUTED, font=("Arial", 10)).pack(side="left")
                tk.Label(r, text=v, anchor="w",
                         bg=C_CARD, fg=C_TEXT, font=("Arial", 10)).pack(side="left")
        except Exception as e:
            tk.Label(dc, text=str(e), bg=C_CARD, fg=C_DANGER).pack()

        # Recent events
        rc = self._card("🕐 Recent Activity")
        for ev in self.db.get_audit_log(limit=6):
            r = tk.Frame(rc, bg=C_CARD); r.pack(fill="x", pady=1)
            col = SEV_COLORS.get(ev.get("severity","INFO"), C_TEXT)
            ts  = str(ev.get("created_at",""))[:16]
            tk.Label(r, text=ts,                       width=16, bg=C_CARD, fg=C_MUTED, font=("Arial",9)).pack(side="left")
            tk.Label(r, text=ev.get("event_type",""),  width=22, bg=C_CARD, fg=col,    font=("Arial",9,"bold")).pack(side="left")
            tk.Label(r, text=str(ev.get("details",""))[:55],     bg=C_CARD, fg=C_TEXT,  font=("Arial",9)).pack(side="left")

    # ── Appearance ────────────────────────────────────────────────────────────

    def _appearance(self):
        self._title("🎨 Appearance")
        cols = tk.Frame(self._content, bg=C_BG); cols.pack(fill="both", expand=True)
        L = tk.Frame(cols, bg=C_BG); L.pack(side="left", fill="both", expand=True, padx=(0,8))
        R = tk.Frame(cols, bg=C_BG); R.pack(side="left", fill="both", expand=True)

        # Typography
        tc = self._card_in(L, "🔤 Typography")
        self._slider(tc, "Font Size",   "font_size",  8,  64, 1)
        self._toggle(tc, "Bold Text",   "font_bold")
        fr = tk.Frame(tc, bg=C_CARD); fr.pack(fill="x", pady=3)
        self._lbl(fr, "Font Family").pack(side="left", padx=(0,8))
        ff_var = tk.StringVar(value=self.cfg.get_str("font_family","Arial"))
        om = tk.OptionMenu(fr, ff_var,
                           "Arial","Calibri","Helvetica","Tahoma","Verdana",
                           "Times New Roman","Courier New","Segoe UI",
                           command=lambda v: self.cfg.set("font_family", v))
        om.config(bg=C_PANEL, fg=C_TEXT, highlightthickness=0, relief="flat")
        om.pack(side="right")

        # Layout
        lc = self._card_in(L, "📐 Layout")
        self._slider(lc, "H Spacing", "spacing_x", 80,  500, 10)
        self._slider(lc, "V Spacing", "spacing_y", 60,  400, 10)
        self._slider(lc, "Rotation",  "rotation",  -90, 0,   5)

        # Visibility
        vc = self._card_in(R, "👁 Opacity")
        self._slider(vc, "Opacity", "opacity", 0.03, 0.80, 0.01, fmt="{:.0%}")

        # Colour
        cc = self._card_in(R, "🎨 Colour")
        swatch = tk.Label(cc, bg=self.cfg.watermark_color, width=5, relief="flat")
        swatch.pack(side="left", ipady=10, padx=(0,10))
        val_l  = tk.Label(cc, text=self.cfg.watermark_color,
                          bg=C_CARD, fg=C_TEXT, font=("Courier",11))
        val_l.pack(side="left")

        def pick():
            res = colorchooser.askcolor(color=self.cfg.watermark_color,
                                        title="Watermark Colour")
            if res[1]:
                self.cfg.set("color", res[1])
                swatch.config(bg=res[1]); val_l.config(text=res[1])

        self._btn(cc, "🎨 Pick", pick).pack(pady=(8,0))
        self._btn(cc, "↺ Auto", lambda: (self.cfg.set("color",""),
                                          val_l.config(text="Auto")),
                  color=C_MUTED).pack(pady=3)

        # Preview
        pv = self._card_in(R, "👀 Preview")
        cv = tk.Canvas(pv, bg="#111", width=260, height=140, highlightthickness=0)
        cv.pack()
        def refresh_pv(*_):
            cv.delete("all")
            col  = self.cfg.watermark_color
            size = max(8, self.cfg.font_size // 2)
            for x in range(0, 300, 110):
                for y in range(0, 180, 65):
                    cv.create_text(x, y, text=self.cfg.watermark_text[:25],
                                   fill=col, font=("Arial", size),
                                   angle=self.cfg.rotation)
        refresh_pv()
        self._btn(pv, "🔄 Refresh", refresh_pv).pack(pady=3)
        self.cfg.add_observer(refresh_pv)

    def _card_in(self, parent, title="") -> tk.Frame:
        """Card that packs inside a given frame, not self._content."""
        outer = tk.Frame(parent, bg=C_CARD)
        outer.pack(fill="x", pady=(0,10))
        if title:
            tk.Label(outer, text=title, font=("Arial",11,"bold"),
                     bg=C_CARD, fg=C_ACCENT).pack(anchor="w", padx=14, pady=(8,2))
        inner = tk.Frame(outer, bg=C_CARD)
        inner.pack(fill="both", expand=True, padx=14, pady=(2,12))
        return inner

    # ── Content ───────────────────────────────────────────────────────────────

    def _content_tab(self):
        self._title("📝 Content")
        tc = self._card("✏ Watermark Text Template")
        self._lbl(tc,
                  "Variables: {username} {hostname} {date} {time} {datetime} "
                  "{classification} {department} {organization} {ip}", muted=True).pack(anchor="w")
        tv = tk.StringVar(value=self.cfg.get_str("watermark_text"))
        e = tk.Entry(tc, textvariable=tv, font=("Arial",11), width=58,
                     bg=C_PANEL, fg=C_TEXT, insertbackground=C_TEXT,
                     relief="flat", bd=5)
        e.pack(fill="x", pady=4)
        self._btn(tc, "💾 Save Template",
                  lambda: (self.cfg.set("watermark_text", tv.get()),
                           self.db.log("SETTINGS_CHANGED","watermark_text updated",
                                       "INFO",getpass.getuser(),""))).pack(anchor="w")

        # Classification
        from shared.models import CLASSIFICATION_COLORS
        cc = self._card("🔐 Classification")
        cr = tk.Frame(cc, bg=C_CARD); cr.pack(fill="x", pady=4)
        self._lbl(cr, "Level:").pack(side="left", padx=(0,8))
        cls_var = tk.StringVar(value=self.cfg.get_str("classification","CONFIDENTIAL"))
        sw = tk.Label(cr, bg=CLASSIFICATION_COLORS.get(cls_var.get(),"#AAAAAA"),
                      width=4, relief="flat")
        sw.pack(side="left", ipady=8, padx=(0,8))
        def on_cls(v):
            self.cfg.set("classification", v)
            self.cfg.set("color","")
            sw.config(bg=CLASSIFICATION_COLORS.get(v,"#AAAAAA"))
        tk.OptionMenu(cr, cls_var, *list(CLASSIFICATION_COLORS.keys()),
                      command=on_cls).pack(side="left")

        # Org meta
        mc = self._card("🏢 Organisation")
        for lbl, key in [("Org Name","organization_name"),
                          ("Department","department"),
                          ("Custom Note","custom_text")]:
            r = tk.Frame(mc, bg=C_CARD); r.pack(fill="x", pady=3)
            tk.Label(r, text=f"{lbl}:", width=14, anchor="w",
                     bg=C_CARD, fg=C_TEXT, font=("Arial",10)).pack(side="left")
            v = tk.StringVar(value=self.cfg.get_str(key))
            e2 = tk.Entry(r, textvariable=v, font=("Arial",10), width=30,
                          bg=C_PANEL, fg=C_TEXT, insertbackground=C_TEXT,
                          relief="flat", bd=4)
            e2.pack(side="left")
            e2.bind("<FocusOut>", lambda ev, k=key, vr=v: self.cfg.set(k, vr.get()))

        elc = self._card("🔧 Elements")
        for lbl, key in [("Show Username","show_username"),("Show Hostname","show_hostname"),
                          ("Show Date/Time","show_datetime"),("Show Classification","show_classification")]:
            self._toggle(elc, lbl, key)

    # ── Exclusions ────────────────────────────────────────────────────────────

    def _exclusions(self):
        self._title("🚫 Application Exclusions")
        top = tk.Frame(self._content, bg=C_BG); top.pack(fill="x", pady=(0,8))
        av = tk.StringVar()
        ae = tk.Entry(top, textvariable=av, font=("Arial",11), width=24,
                      bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=5)
        ae.pack(side="left", padx=(0,6)); ae.insert(0,"e.g. notepad.exe")
        ae.bind("<FocusIn>", lambda e: ae.delete(0,"end") if av.get().startswith("e.g") else None)

        def add_app():
            n = av.get().strip()
            if n and not n.startswith("e.g"):
                if self.db.add_excluded_app(n, n.replace(".exe","").title()):
                    self.db.log("EXCLUSION_ADDED",f"Added: {n}","INFO",getpass.getuser(),"")
                    av.set(""); refresh()
                else:
                    messagebox.showinfo("Exists", f"{n} already excluded.")

        self._btn(top, "+ Add", add_app).pack(side="left")

        def pick_running():
            try:
                import psutil
                names = sorted({(p.info.get("name") or "") for p in psutil.process_iter(["name"])
                                if p.info.get("name")})
            except Exception:
                names = []
            win = tk.Toplevel(self); win.title("Running Apps")
            win.configure(bg=C_BG); win.geometry("340x460")
            lb = tk.Listbox(win, bg=C_CARD, fg=C_TEXT, font=("Arial",10),
                            selectbackground=C_ACCENT, relief="flat")
            lb.pack(fill="both", expand=True, padx=10, pady=10)
            for n in names: lb.insert("end", n)
            def sel():
                s = lb.curselection()
                if s: av.set(lb.get(s[0])); win.destroy()
            self._btn(win, "✔ Select", sel).pack(pady=6)

        self._btn(top, "📋 Pick Running App", pick_running, color=C_MUTED).pack(side="left", padx=6)

        # Table
        tf = tk.Frame(self._content, bg=C_CARD); tf.pack(fill="both", expand=True)
        hf = tk.Frame(tf, bg=C_CARD); hf.pack(fill="x", padx=8, pady=(8,0))
        for h, w in [("Process Name",22),("Display Name",22),("Added By",12),("Date",14)]:
            tk.Label(hf, text=h, width=w, anchor="w",
                     bg=C_CARD, fg=C_ACCENT, font=("Arial",10,"bold")).pack(side="left")
        tk.Label(hf, text="", width=6, bg=C_CARD).pack(side="left")
        tk.Frame(tf, bg=C_PANEL, height=1).pack(fill="x", padx=8, pady=3)
        _, rf = self._scroll_table(tf)

        def refresh():
            for w in rf.winfo_children(): w.destroy()
            for app in self.db.get_excluded_apps():
                r = tk.Frame(rf, bg=C_CARD); r.pack(fill="x", padx=8, pady=1)
                for val, w in [(app["process_name"],22),(app.get("display_name","—"),22),
                               (app.get("added_by","—"),12),(str(app.get("added_at",""))[:10],14)]:
                    tk.Label(r, text=val, width=w, anchor="w",
                             bg=C_CARD, fg=C_TEXT, font=("Arial",10)).pack(side="left")
                def rm(aid=app["id"]):
                    if messagebox.askyesno("Remove","Remove this exclusion?"):
                        self.db.remove_excluded_app(aid)
                        self.db.log("EXCLUSION_REMOVED",f"ID {aid}","INFO",getpass.getuser(),"")
                        refresh()
                self._btn(r,"✕",rm,color=C_DANGER).pack(side="left")
        refresh()

    # ── Users ─────────────────────────────────────────────────────────────────

    def _users(self):
        self._title("👥 Organisation Users")
        top = tk.Frame(self._content, bg=C_BG); top.pack(fill="x", pady=(0,8))
        sv = tk.StringVar()
        tk.Label(top, text="🔍", bg=C_BG, fg=C_MUTED, font=("Arial",12)).pack(side="left",padx=(0,4))
        se = tk.Entry(top, textvariable=sv, font=("Arial",10), width=22,
                      bg=C_CARD, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=5)
        se.pack(side="left")

        def export():
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV","*.csv")],
                                                initialfile="watermark_users.csv")
            if path:
                users = self.db.get_org_users()
                with open(path,"w",newline="",encoding="utf-8") as f:
                    if users:
                        w = csv.DictWriter(f, fieldnames=users[0].keys())
                        w.writeheader(); w.writerows(users)
                messagebox.showinfo("Exported",f"{len(users)} users saved.")

        self._btn(top,"📥 Export CSV", export, color=C_MUTED).pack(side="left", padx=8)

        tf = tk.Frame(self._content, bg=C_CARD); tf.pack(fill="both", expand=True)
        cols = [("Username",14),("Hostname",14),("Dept",12),("IP",13),
                ("Version",9),("OS",18),("Last Seen",18)]
        hf = tk.Frame(tf, bg=C_CARD); hf.pack(fill="x", padx=8, pady=(8,0))
        for h,w in cols:
            tk.Label(hf, text=h, width=w, anchor="w",
                     bg=C_CARD, fg=C_ACCENT, font=("Arial",10,"bold")).pack(side="left")
        tk.Frame(tf, bg=C_PANEL, height=1).pack(fill="x", padx=8, pady=3)
        _, rf = self._scroll_table(tf)

        def reload(q=""):
            for w in rf.winfo_children(): w.destroy()
            for u in self.db.get_org_users():
                if q and q.lower() not in str(u).lower(): continue
                r = tk.Frame(rf, bg=C_CARD); r.pack(fill="x", padx=8, pady=1)
                me = (u["hostname"].lower()==socket.gethostname().lower() and
                      u["username"].lower()==getpass.getuser().lower())
                fg = C_ACCENT if me else C_TEXT
                for val, w in [(u["username"],14),(u["hostname"],14),(u.get("department","—"),12),
                               (u.get("ip_address","—"),13),(u.get("app_version","?"),9),
                               ((u.get("os_info","")or"—")[:18],18),(str(u.get("last_seen",""))[:16],18)]:
                    tk.Label(r, text=str(val), width=w, anchor="w",
                             bg=C_CARD, fg=fg, font=("Arial",10)).pack(side="left")

        reload()
        sv.trace_add("write", lambda *_: reload(sv.get()))

    # ── Logs ─────────────────────────────────────────────────────────────────

    def _logs(self):
        self._title("📋 Audit Log")
        top = tk.Frame(self._content, bg=C_BG); top.pack(fill="x", pady=(0,8))
        sev_var = tk.StringVar(value="ALL")
        tk.OptionMenu(top, sev_var, "ALL","INFO","WARNING","ERROR","SECURITY",
                      command=lambda v: reload(v)).pack(side="left")

        def export():
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV","*.csv")],
                                                initialfile="audit_log.csv")
            if path:
                n = self.db.export_audit_csv(Path(path))
                messagebox.showinfo("Exported",f"{n} entries saved.")

        def clear():
            if messagebox.askyesno("Clear","Delete all audit log entries?"):
                self.db.clear_audit_log()
                self.db.log("AUDIT_LOG_CLEARED","","WARNING",getpass.getuser(),"")
                reload("ALL")

        self._btn(top,"📥 Export",export,color=C_MUTED).pack(side="left",padx=6)
        self._btn(top,"🗑 Clear",  clear, color=C_DANGER).pack(side="left")

        tf = tk.Frame(self._content, bg=C_CARD); tf.pack(fill="both", expand=True)
        hf = tk.Frame(tf, bg=C_CARD); hf.pack(fill="x", padx=8, pady=(8,0))
        for h,w in [("Timestamp",16),("Type",22),("User",12),
                    ("Host",12),("Sev",10),("Details",35)]:
            tk.Label(hf, text=h, width=w, anchor="w",
                     bg=C_CARD, fg=C_ACCENT, font=("Arial",10,"bold")).pack(side="left")
        tk.Frame(tf, bg=C_PANEL, height=1).pack(fill="x", padx=8, pady=3)
        _, rf = self._scroll_table(tf)

        def reload(sev="ALL"):
            for w in rf.winfo_children(): w.destroy()
            sv = None if sev == "ALL" else sev
            for ev in self.db.get_audit_log(limit=300, severity=sv):
                r = tk.Frame(rf, bg=C_CARD); r.pack(fill="x", padx=8, pady=1)
                s = ev.get("severity","INFO"); col = SEV_COLORS.get(s,C_TEXT)
                ts = str(ev.get("created_at",""))[:16]
                for val, w in [(ts,16),(ev.get("event_type",""),22),
                               (ev.get("username",""),12),(ev.get("hostname",""),12),
                               (s,10),(str(ev.get("details",""))[:50],35)]:
                    tk.Label(r, text=str(val), width=w, anchor="w",
                             bg=C_CARD, fg=col, font=("Arial",9)).pack(side="left")
        reload()

    # ── Settings ─────────────────────────────────────────────────────────────

    def _settings(self):
        self._title("⚙ Settings")

        # Auto-start
        ac = self._card("🚀 Auto-Start (Task Scheduler)")
        auto_v = tk.BooleanVar(value=self.autostart.is_autostart_enabled())
        def tog_auto():
            if auto_v.get():
                self.autostart.enable_autostart()
                self.db.log("AUTOSTART_ENABLED","","INFO",getpass.getuser(),"")
            else:
                self.autostart.disable_autostart()
                self.db.log("AUTOSTART_DISABLED","","INFO",getpass.getuser(),"")
        tk.Checkbutton(ac, text="Launch WatermarkPro at user logon (Task Scheduler — no terminal)",
                       variable=auto_v, command=tog_auto,
                       bg=C_CARD, fg=C_TEXT, selectcolor=C_ACCENT,
                       activebackground=C_CARD, font=("Arial",10)).pack(anchor="w")

        # Schedule
        sc_c = self._card("🕐 Schedule")
        self._toggle(sc_c,"Enable work-hours schedule","schedule_enabled")
        tr = tk.Frame(sc_c, bg=C_CARD); tr.pack(fill="x", pady=4)
        for lbl, key in [("Start:","schedule_start"),("End:","schedule_end")]:
            tk.Label(tr, text=lbl, bg=C_CARD, fg=C_TEXT, font=("Arial",10)).pack(side="left",padx=(0,4))
            v = tk.StringVar(value=self.cfg.get_str(key,"08:00"))
            e = tk.Entry(tr, textvariable=v, width=7, bg=C_PANEL, fg=C_TEXT,
                         insertbackground=C_TEXT, font=("Arial",10), relief="flat", bd=4)
            e.pack(side="left", padx=(0,16))
            e.bind("<FocusOut>", lambda ev, k=key, vr=v: self.cfg.set(k, vr.get()))

        # Password change
        pw_c = self._card("🔑 Change Admin Password")
        pw_r = tk.Frame(pw_c, bg=C_CARD); pw_r.pack(fill="x", pady=3)
        tk.Label(pw_r, text="New Password:", width=14, anchor="w",
                 bg=C_CARD, fg=C_TEXT, font=("Arial",10)).pack(side="left")
        pv = tk.StringVar()
        tk.Entry(pw_r, textvariable=pv, show="•", font=("Arial",10), width=22,
                 bg=C_PANEL, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=4).pack(side="left")
        cv = tk.StringVar()
        cr2 = tk.Frame(pw_c, bg=C_CARD); cr2.pack(fill="x", pady=3)
        tk.Label(cr2, text="Confirm:", width=14, anchor="w",
                 bg=C_CARD, fg=C_TEXT, font=("Arial",10)).pack(side="left")
        tk.Entry(cr2, textvariable=cv, show="•", font=("Arial",10), width=22,
                 bg=C_PANEL, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=4).pack(side="left")
        def change_pw():
            p1, p2 = pv.get(), cv.get()
            if len(p1) < 6:
                messagebox.showerror("Error","Minimum 6 characters."); return
            if p1 != p2:
                messagebox.showerror("Error","Passwords do not match."); return
            self.db.set_password(p1)
            self.db.log("PASSWORD_CHANGED","","SECURITY",getpass.getuser(),"")
            pv.set(""); cv.set("")
            messagebox.showinfo("Done","Password changed.")
        self._btn(pw_c,"🔒 Change Password",change_pw,color=C_ACCENT2).pack(anchor="w",pady=4)

        # DB backup
        bc = self._card("📦 Backup")
        def bk():
            path = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON","*.json")],
                                                initialfile="watermark_backup.json")
            if path:
                self.db.export_json(Path(path))
                messagebox.showinfo("Done",f"Backup saved: {path}")
        self._btn(bc,"💾 Export JSON Backup", bk).pack(anchor="w")

        # About
        ab = self._card("ℹ About")
        for t, f, c in [("WatermarkPro v2",("Arial",14,"bold"),C_ACCENT),
                         ("Enterprise Screen Watermark — PostgreSQL Edition",("Arial",10),C_TEXT),
                         ("Separate User & Admin EXEs · Windows Service Guardian",("Arial",10),C_MUTED)]:
            tk.Label(ab, text=t, font=f, bg=C_CARD, fg=c).pack(anchor="w")
