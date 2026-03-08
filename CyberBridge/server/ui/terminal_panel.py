"""
CyberBridge - Terminal Panel
Interactive remote shell panel for a connected client session.
"""

import tkinter as tk
import threading
import time
import datetime

from .styles import *


class TerminalPanel(tk.Frame):
    """Remote terminal — send commands, see output in a scrolling console."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._session     = None
        self._history     = []
        self._hist_idx    = -1
        self._build()

    # ─── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Title bar ─────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")
        tk.Label(tb, text="▶ REMOTE TERMINAL", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)
        tk.Button(tb, text="CLEAR", command=self._clear_output,
                  **STYLE_BUTTON).pack(side="right", padx=4)

        # ── Output area ───────────────────────────────────────────────────────
        of = tk.Frame(self, bg=BG_DEEP)
        of.pack(fill="both", expand=True, padx=4, pady=4)

        sb = tk.Scrollbar(of, orient="vertical",
                          bg=SCROLLBAR_BG, troughcolor=BG_DEEP,
                          activebackground=SCROLLBAR_FG, width=8)
        sb.pack(side="right", fill="y")

        self._output = tk.Text(of, yscrollcommand=sb.set,
                               state="disabled", **STYLE_TEXT)
        self._output.pack(fill="both", expand=True)
        sb.config(command=self._output.yview)

        # Color tags
        self._output.tag_config("cmd",    foreground=FG_CYAN)
        self._output.tag_config("out",    foreground=FG_PRIMARY)
        self._output.tag_config("err",    foreground=FG_RED)
        self._output.tag_config("ts",     foreground=FG_DIM)
        self._output.tag_config("banner", foreground=FG_SECONDARY)

        # ── Input bar ─────────────────────────────────────────────────────────
        inf = tk.Frame(self, bg=BG_PANEL,
                       highlightbackground=BORDER_COLOR, highlightthickness=1)
        inf.pack(fill="x", padx=4, pady=(0, 4))

        self._prompt_lbl = tk.Label(inf, text="C:\\> ", font=FONT_MONO_LG,
                                    bg=BG_PANEL, fg=FG_CYAN)
        self._prompt_lbl.pack(side="left", padx=4)

        self._cmd_var = tk.StringVar()
        self._entry   = tk.Entry(inf, textvariable=self._cmd_var,
                                 **STYLE_ENTRY)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=4)
        self._entry.bind("<Return>",   self._on_enter)
        self._entry.bind("<Up>",       self._hist_up)
        self._entry.bind("<Down>",     self._hist_down)

        tk.Button(inf, text="► EXEC", command=self._on_enter,
                  **STYLE_BUTTON).pack(side="right", padx=4, pady=4)

    # ─── Session ──────────────────────────────────────────────────────────────

    def set_session(self, session):
        self._session = session
        self._clear_output()
        self._append_banner(f"Connected to {session.hostname} ({session.ip})")
        self._append_banner("Type commands and press ENTER or ► EXEC")
        self._prompt_lbl.config(text=f"{session.hostname}> ")

    def clear_session(self):
        self._session = None
        self._clear_output()
        self._prompt_lbl.config(text="C:\\> ")

    # ─── Display ──────────────────────────────────────────────────────────────

    def _append_banner(self, text: str):
        self._write(f"{'─'*60}\n{text}\n{'─'*60}\n", "banner")

    def _append_cmd(self, cmd: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._write(f"[{ts}] ", "ts")
        self._write(f"$ {cmd}\n", "cmd")

    def _append_output(self, text: str, is_err: bool = False):
        tag = "err" if is_err else "out"
        if text:
            self._write(text if text.endswith("\n") else text + "\n", tag)

    def _write(self, text: str, tag: str = "out"):
        self._output.config(state="normal")
        self._output.insert(tk.END, text, tag)
        self._output.see(tk.END)
        self._output.config(state="disabled")

    def _clear_output(self):
        self._output.config(state="normal")
        self._output.delete("1.0", tk.END)
        self._output.config(state="disabled")

    # ─── Commands ─────────────────────────────────────────────────────────────

    def _on_enter(self, event=None):
        cmd = self._cmd_var.get().strip()
        if not cmd:
            return
        self._cmd_var.set("")
        self._history.append(cmd)
        self._hist_idx = len(self._history)

        if self._session is None:
            self._append_output("No session selected.\n", is_err=True)
            return

        self._append_cmd(cmd)
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _run_cmd(self, cmd: str):
        try:
            if not self._session.ensure_connected():
                self._append_output("Cannot connect to client.\n", is_err=True)
                return
            result = self._session.execute_command(cmd)
            # Update prompt with current working directory if provided
            cwd = result.get("cwd")
            if cwd:
                self._prompt_lbl.config(text=f"{cwd}> ")
            self._append_output(result.get("stdout", ""))
            if result.get("stderr"):
                self._append_output(result["stderr"], is_err=True)
            rc = result.get("returncode", 0)
            if rc != 0:
                self._write(f"[exit {rc}]\n", "err")
        except Exception as e:
            self._append_output(f"Error: {e}\n", is_err=True)

    def _hist_up(self, event):
        if self._history and self._hist_idx > 0:
            self._hist_idx -= 1
            self._cmd_var.set(self._history[self._hist_idx])

    def _hist_down(self, event):
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._cmd_var.set(self._history[self._hist_idx])
        else:
            self._hist_idx = len(self._history)
            self._cmd_var.set("")
