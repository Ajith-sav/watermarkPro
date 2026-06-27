"""
WatermarkPro v2 — Watermark Overlay (user_app/overlay.py)
Transparent, click-through, always-on-top Tkinter windows — one per monitor.
"""

import ctypes
import logging
import sys
import tkinter as tk
from typing import List, Optional

logger = logging.getLogger(__name__)

_TRANSPARENT_COLOR = "#010203"   # Must not appear in watermark text colour


class MonitorOverlay(tk.Toplevel):
    def __init__(self, master, x, y, w, h, cfg):
        super().__init__(master)
        self._cfg = cfg
        self._x, self._y, self._mon_w, self._mon_h = x, y, w, h
        self._visible = True

        # ── Window chrome ───────────────────────────────────────────────────
        self.overrideredirect(True)              # No title bar / borders
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.attributes("-topmost", True)        # Full alpha — transparency via colour key
        self.configure(bg=_TRANSPARENT_COLOR)
        self.lift()
        self.wm_attributes("-transparentcolor", _TRANSPARENT_COLOR)

        # ── Canvas ──────────────────────────────────────────────────────────
        self._canvas = tk.Canvas(
            self, bg=_TRANSPARENT_COLOR, highlightthickness=0, bd=0, width=w, height=h,
        )
        self._canvas.pack(fill="both", expand=True)

        # ── Make click-through (Windows only) ───────────────────────────────
        if sys.platform == "win32":
            self.after(120, self._click_through)

        # ── Draw and schedule updates ────────────────────────────────────────
        self.after(250, self._draw)
            
    # ── Windows API click-through ─────────────────────────────────────────────
    def _click_through(self):
        try:
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x80000
            WS_EX_TRANSPARENT = 0x20
            WS_EX_NOACTIVATE  = 0x08000000
            hwnd = self._hwnd()
            if hwnd:
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE,
                    style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE,
                )
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE
                )
        except Exception as e:
            logger.debug("click-through: %s", e)

    def _hwnd(self):
        try:
            return int(self.frame(), 16)
        except Exception:
            return ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _draw(self):
        if not self._visible:
            self.after(self._cfg.update_interval_ms, self._draw)
            return

        self._canvas.delete("all")
        c   = self._cfg
        sx     = c.spacing_x
        sy     = c.spacing_y
        font = (c.font_family, c.font_size, "bold") if c.font_bold else (c.font_family, c.font_size)
 
    #    # Tile across the full monitor with generous overflow
    #     for x in range(-self._w, self._w * 2, c.spacing_x):
    #         for y in range(-self._h, self._h * 2, c.spacing_y):
    #             self._canvas.create_text(
    #                 x, y, text=c.watermark_text,
    #                 fill=c.watermark_color, font=font, angle=c.rotation, anchor="center",
    #             )

        # Tile across the full monitor with generous overflow
        xs = range(-self._mon_w, self._mon_w * 2, sx)
        ys = range(-self._mon_h, self._mon_h * 2, sy)
        for x in xs:
            for y in ys:
                self._canvas.create_text(
                    x, y,
                    text=c.watermark_text,
                    fill=c.watermark_color,
                    font=font,
                    angle=c.rotation,
                    anchor="center",
                )

        if sys.platform == "win32":
            self.after(60, self._click_through)

        self.after(c.update_interval_ms, self._draw)

    def refresh(self):
        self._canvas.delete("all")
        self._draw()

    # ── Visibility ────────────────────────────────────────────────────────────
    def show(self):
        if not self._visible:
            self._visible = True
            self.deiconify()
            if sys.platform == "win32":
                self.after(60, self._click_through)

    def hide(self):
        if self._visible:
            self._visible = False
            self.withdraw()


class WatermarkManager:
    def __init__(self, cfg):
        self._cfg = cfg
        self._root: Optional[tk.Tk] = None
        self._overlays: List[MonitorOverlay] = []

    def start(self, root: tk.Tk):
        self._root = root
        monitors = self._get_monitors()
        logger.info("Creating overlays for %d monitor(s)", len(monitors))
        for (x, y, w, h) in monitors:
            # self._overlays.append(MonitorOverlay(root, x, y, w, h, self._cfg))
            ov = MonitorOverlay(root, x, y, w, h, self._cfg)
            self._overlays.append(ov)
        
        # Register for config changes
        self._cfg.add_observer(self.refresh_all)

    def _get_monitors(self):
        monitors = []
        if sys.platform == "win32":
            try:
                import ctypes, ctypes.wintypes as wt
                MonitorEnumProc = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
                    ctypes.POINTER(wt.RECT), ctypes.c_double,
                )
                def cb(hMon, hdcMon, lprc, dw):
                    r = lprc.contents
                    # monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
                    monitors.append((
                        int(r.left), 
                        int(r.top), 
                        int(r.right - r.left), 
                        int(r.bottom - r.top)
                    ))
                    return True
                ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(cb), 0)
            except Exception as e:
                logger.warning("Monitor enum failed: %s", e)

        if not monitors and self._root:
            monitors = [(0, 0, self._root.winfo_screenwidth(), self._root.winfo_screenheight())]
        return monitors or [(0, 0, 1920, 1080)]

    def show_all(self):
        for o in self._overlays: o.show()

    def hide_all(self):
        for o in self._overlays: o.hide()

    def refresh_all(self):
        for o in self._overlays:
            try: o.refresh()
            except Exception: pass

    def is_visible(self):
        return any(o._visible for o in self._overlays)
