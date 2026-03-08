"""
CyberBridge - Connection Panel
Left sidebar showing all registered client sessions.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading

from .styles import *


class ConnectionPanel(tk.Frame):
    """
    Left panel — lists all discovered clients with their status.
    Clicking a session row notifies the parent to switch views.
    """

    def __init__(self, parent, on_select_session=None, on_delete_session=None, **kwargs):
        super().__init__(parent, bg=BG_PANEL,
                         highlightbackground=BORDER_COLOR,
                         highlightthickness=1, **kwargs)

        self._on_select = on_select_session
        self._on_delete = on_delete_session
        self._sessions  = []
        self._selected  = None

        self._build()
        self._start_refresh_loop()

    # ─── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_CARD,
                       highlightbackground=FG_DIM, highlightthickness=1)
        hdr.pack(fill="x", padx=4, pady=(4, 0))

        tk.Label(hdr, text="◈ CONNECTIONS", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=8, pady=6)

        self._count_lbl = tk.Label(hdr, text="0", font=FONT_MONO_LG,
                                   bg=BG_CARD, fg=FG_CYAN)
        self._count_lbl.pack(side="right", padx=8)

        # ── Filter / search ───────────────────────────────────────────────────
        sf = tk.Frame(self, bg=BG_PANEL)
        sf.pack(fill="x", padx=4, pady=4)

        tk.Label(sf, text="FILTER:", **STYLE_LABEL).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_list())
        e = tk.Entry(sf, textvariable=self._filter_var, width=14, **STYLE_ENTRY)
        e.pack(side="left", padx=4, fill="x", expand=True)

        # ── Session listbox with scrollbar ────────────────────────────────────
        lf = tk.Frame(self, bg=BG_DEEP)
        lf.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        sb = tk.Scrollbar(lf, orient="vertical",
                          bg=SCROLLBAR_BG, troughcolor=BG_DEEP,
                          activebackground=SCROLLBAR_FG, width=8)
        sb.pack(side="right", fill="y")

        self._listbox = tk.Listbox(lf, yscrollcommand=sb.set,
                                   **STYLE_LISTBOX)
        self._listbox.pack(fill="both", expand=True)
        sb.config(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        cf = tk.Frame(self, bg=BG_PANEL)
        cf.pack(fill="x", padx=4, pady=(0, 4))
        tk.Button(cf, text="🗑 ELIMINAR CONEXIÓN",
                  command=self._delete_selected, **STYLE_BUTTON_DANGER).pack(side="left", padx=2)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status_lbl = tk.Label(self, text="● Listening…",
                                    bg=BG_PANEL, fg=FG_DIM,
                                    font=FONT_STATUS, anchor="w")
        self._status_lbl.pack(fill="x", padx=6, pady=(0, 4))

    # ─── Session updates ──────────────────────────────────────────────────────

    def update_sessions(self, sessions: list):
        """Called by parent when the session list changes."""
        self._sessions = sessions
        self._refresh_list()

    def _refresh_list(self):
        flt = self._filter_var.get().lower()
        self._listbox.delete(0, tk.END)

        visible = [s for s in self._sessions
                   if flt in s.hostname.lower() or flt in s.ip.lower()]

        self._count_lbl.config(text=str(len(self._sessions)))

        for s in visible:
            age = time.time() - s.last_seen
            if age < 15:
                icon, color = "●", FG_CYAN
            elif age < 60:
                icon, color = "◉", FG_YELLOW
            else:
                icon, color = "○", FG_DIM

            line = f" {icon} {s.hostname:<18} {s.ip:<15} :{s.port}"
            self._listbox.insert(tk.END, line)

            # Color individual items
            idx = self._listbox.size() - 1
            self._listbox.itemconfig(idx, foreground=color)

        # Status
        online = sum(1 for s in self._sessions if time.time() - s.last_seen < 15)
        self._status_lbl.config(
            text=f"● {len(self._sessions)} clients  |  {online} online",
            fg=FG_SECONDARY if self._sessions else FG_DIM,
        )

    def _on_listbox_select(self, event):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx     = sel[0]
        flt     = self._filter_var.get().lower()
        visible = [s for s in self._sessions
                   if flt in s.hostname.lower() or flt in s.ip.lower()]
        if idx < len(visible):
            self._selected = visible[idx]
            if self._on_select:
                self._on_select(self._selected)

    def _delete_selected(self):
        if not self._on_delete:
            return
        flt = self._filter_var.get().lower()
        visible = [s for s in self._sessions
                   if flt in s.hostname.lower() or flt in s.ip.lower()]
        sel = self._listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(visible):
                self._on_delete(visible[idx])
                self._selected = None
                self._listbox.selection_clear(0, tk.END)
            return

        now = time.time()
        stale = [s for s in self._sessions if now - s.last_seen >= 15]
        for s in stale:
            self._on_delete(s)
        self._selected = None
        self._listbox.selection_clear(0, tk.END)

    # ─── Auto-refresh ─────────────────────────────────────────────────────────

    def _start_refresh_loop(self):
        def _loop():
            while True:
                try:
                    self._refresh_list()
                except Exception:
                    pass
                threading.Event().wait(5)

        threading.Thread(target=_loop, daemon=True).start()
