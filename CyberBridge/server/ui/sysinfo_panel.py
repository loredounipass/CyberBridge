"""
CyberBridge - System Info Panel
Displays live hardware metrics for the selected client.
"""

import tkinter as tk
import threading
import time
import datetime

from .styles import *


class SystemInfoPanel(tk.Frame):
    """Shows CPU, RAM, disk, hostname, and uptime for the active client."""

    _REFRESH_SEC = 5

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)
        self._session = None
        self._running = False
        self._build()

    def _build(self):
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")
        tk.Label(tb, text="◆ SYSTEM MONITOR", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)

        self._refresh_btn = tk.Button(tb, text="↺ REFRESH",
                                      command=self._force_refresh,
                                      **STYLE_BUTTON)
        self._refresh_btn.pack(side="right", padx=4)

        # ── Grid of metrics ────────────────────────────────────────────────────
        mf = tk.Frame(self, bg=BG_PANEL)
        mf.pack(fill="both", expand=True, padx=8, pady=8)

        self._metrics = {}
        fields = [
            ("hostname",  "HOSTNAME"),
            ("ip",        "IP ADDRESS"),
            ("platform",  "PLATFORM"),
            ("processor", "PROCESSOR"),
            ("cpu_pct",   "CPU USAGE"),
            ("ram_pct",   "RAM USAGE"),
            ("ram_used",  "RAM USED"),
            ("ram_total", "RAM TOTAL"),
            ("disk_used", "DISK USED"),
            ("disk_total","DISK TOTAL"),
            ("uptime",    "UPTIME"),
            ("python",    "PYTHON"),
        ]

        for i, (key, label) in enumerate(fields):
            row = i % 6
            col = (i // 6) * 2

            lbl_frame = tk.Frame(mf, bg=BG_CARD,
                                 highlightbackground=BORDER_COLOR,
                                 highlightthickness=1)
            lbl_frame.grid(row=row, column=col, sticky="nsew",
                           padx=3, pady=3, ipadx=6, ipady=4)

            tk.Label(lbl_frame, text=label, **STYLE_LABEL).pack(anchor="w")
            val = tk.Label(lbl_frame, text="—", bg=BG_CARD,
                           fg=FG_PRIMARY, font=FONT_MONO_LG, anchor="w")
            val.pack(anchor="w", fill="x")
            self._metrics[key] = val

        mf.columnconfigure(0, weight=1)
        mf.columnconfigure(1, weight=0, minsize=10)
        mf.columnconfigure(2, weight=1)

        # ── Bar widgets ────────────────────────────────────────────────────────
        bf = tk.Frame(self, bg=BG_PANEL)
        bf.pack(fill="x", padx=8, pady=4)

        tk.Label(bf, text="CPU", **STYLE_LABEL).grid(row=0, column=0, sticky="w", padx=4)
        self._cpu_bar = self._make_bar(bf, row=0)

        tk.Label(bf, text="RAM", **STYLE_LABEL).grid(row=1, column=0, sticky="w", padx=4)
        self._ram_bar = self._make_bar(bf, row=1)

        bf.columnconfigure(1, weight=1)

        # ── Timestamp ─────────────────────────────────────────────────────────
        self._ts_lbl = tk.Label(self, text="", bg=BG_PANEL,
                                fg=FG_DIM, font=FONT_STATUS)
        self._ts_lbl.pack(anchor="w", padx=8, pady=(0, 4))

    def _make_bar(self, parent, row: int):
        canvas = tk.Canvas(parent, height=12, bg=BG_DEEP,
                           bd=0, highlightthickness=1,
                           highlightbackground=FG_DIM)
        canvas.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        bar = canvas.create_rectangle(0, 0, 0, 12, fill=FG_PRIMARY, outline="")
        return (canvas, bar)

    def _update_bar(self, bar_tuple, pct: float):
        canvas, bar = bar_tuple
        w = canvas.winfo_width()
        fill_w = int(w * max(0, min(pct, 100)) / 100)
        color = FG_PRIMARY if pct < 70 else FG_YELLOW if pct < 90 else FG_RED
        canvas.coords(bar, 0, 0, fill_w, 12)
        canvas.itemconfig(bar, fill=color)

    def set_session(self, session):
        self._session = session
        self._running = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def clear_session(self):
        self._running = False
        self._session = None
        for v in self._metrics.values():
            v.config(text="—")

    def _force_refresh(self):
        if self._session:
            threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _poll_loop(self):
        while self._running and self._session:
            self._fetch_and_update()
            time.sleep(self._REFRESH_SEC)

    def _fetch_and_update(self):
        try:
            if not self._session.ensure_connected():
                return
            info = self._session.get_system_info()
            self._apply_info(info)
        except Exception as e:
            pass

    def _apply_info(self, info: dict):
        def _fmt_bytes(b):
            gb = b / (1024 ** 3)
            return f"{gb:.1f} GB"

        def _fmt_uptime(s):
            h, m = divmod(int(s) // 60, 60)
            d, h = divmod(h, 24)
            return f"{d}d {h:02d}h {m:02d}m"

        mapping = {
            "hostname":  info.get("hostname", "—"),
            "ip":        info.get("ip", "—"),
            "platform":  f"{info.get('platform','')} {info.get('release','')}",
            "processor": info.get("processor", "—")[:40],
            "cpu_pct":   f"{info.get('cpu_pct', 0):.1f} %",
            "ram_pct":   f"{info.get('ram_pct', 0):.1f} %",
            "ram_used":  _fmt_bytes(info.get("ram_used", 0)),
            "ram_total": _fmt_bytes(info.get("ram_total", 0)),
            "disk_used": _fmt_bytes(info.get("disk_used", 0)),
            "disk_total":_fmt_bytes(info.get("disk_total", 0)),
            "uptime":    _fmt_uptime(info.get("uptime", 0)),
            "python":    info.get("python", "—"),
        }

        for key, val in mapping.items():
            if key in self._metrics:
                self._metrics[key].config(text=val)

        self._update_bar(self._cpu_bar, info.get("cpu_pct", 0))
        self._update_bar(self._ram_bar, info.get("ram_pct", 0))

        ts = datetime.datetime.now().strftime("Last updated: %H:%M:%S")
        self._ts_lbl.config(text=ts)
