"""
CyberBridge - Screenshot / Live Screen Panel
- CAPTURE: single full-quality screenshot
- LIVE: continuous real-time screen stream (like remote desktop)
- SAVE: save last frame to Desktop
"""

import tkinter as tk
import tkinter.ttk as ttk
import threading
import io
import time
import datetime
import os

from .styles import *

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


class ScreenshotPanel(tk.Frame):
    """
    Dual-mode remote screen viewer:
      • CAPTURE — one-shot full screenshot
      • LIVE    — continuous compressed stream (~3 FPS)
    """

    LIVE_FPS     = 3          # target frames per second for live mode
    LIVE_QUALITY = 45         # JPEG quality for streaming
    LIVE_SCALE   = 0.65       # capture scale (65% of original resolution)

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._session    = None
        self._img_ref    = None
        self._last_bytes = b""
        self._live       = False
        self._auto       = False
        self._fps_lbl    = None
        self._frame_t    = 0.0
        self._frame_count = 0
        self._build()

    # ─── UI ───────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")

        tk.Label(tb, text="🖥 SCREEN", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)

        self._status = tk.Label(tb, text="IDLE", font=FONT_MONO_SM,
                                bg=BG_CARD, fg=FG_DIM)
        self._status.pack(side="right", padx=8)

        self._fps_lbl = tk.Label(tb, text="", font=FONT_MONO_SM,
                                 bg=BG_CARD, fg=FG_CYAN)
        self._fps_lbl.pack(side="right", padx=4)

        # ── Quality slider (live mode) ────────────────────────────────────
        qf = tk.Frame(self, bg=BG_PANEL)
        qf.pack(fill="x", padx=6, pady=(4, 0))

        tk.Label(qf, text="QUALITY", **STYLE_LABEL).pack(side="left", padx=4)
        self._quality_var = tk.IntVar(value=self.LIVE_QUALITY)
        ttk.Scale(qf, from_=20, to=85, orient="horizontal",
                  variable=self._quality_var, length=120).pack(side="left")
        tk.Label(qf, textvariable=self._quality_var, **STYLE_LABEL).pack(side="left", padx=2)

        tk.Label(qf, text="  SCALE", **STYLE_LABEL).pack(side="left", padx=(12, 4))
        self._scale_var = tk.DoubleVar(value=self.LIVE_SCALE)
        ttk.Scale(qf, from_=0.3, to=1.0, orient="horizontal",
                  variable=self._scale_var, length=100).pack(side="left")

        self._res_lbl = tk.Label(qf, text="", **STYLE_LABEL)
        self._res_lbl.pack(side="left", padx=4)

        # ── Canvas ────────────────────────────────────────────────────────
        self._canvas = tk.Canvas(self, bg=BG_DEEP, bd=0, highlightthickness=0,
                                 cursor="crosshair")
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._placeholder = self._canvas.create_text(
            300, 200,
            text="[ No Signal ]\nClick CAPTURE or LIVE to start",
            fill=FG_DIM, font=FONT_MONO_LG, justify="center",
        )

        # ── Controls ──────────────────────────────────────────────────────
        cf = tk.Frame(self, bg=BG_PANEL)
        cf.pack(fill="x", padx=4, pady=(0, 6))

        tk.Button(cf, text="📷 CAPTURE",
                  command=self._capture, **STYLE_BUTTON).pack(side="left", padx=4)

        self._live_btn = tk.Button(cf, text="▶ LIVE",
                                   command=self._toggle_live, **STYLE_BUTTON)
        self._live_btn.pack(side="left", padx=4)

        tk.Button(cf, text="💾 GUARDAR CAPTURA",
                  command=self._save, **STYLE_BUTTON).pack(side="left", padx=4)

        self._auto_var = tk.BooleanVar(value=False)
        tk.Checkbutton(cf, text="AUTO-SNAP (10s)", variable=self._auto_var,
                       bg=BG_PANEL, fg=FG_SECONDARY, font=FONT_LABEL,
                       selectcolor=BG_CARD, activebackground=BG_PANEL,
                       activeforeground=FG_PRIMARY,
                       command=self._toggle_auto).pack(side="left", padx=8)

        self._ts_lbl = tk.Label(cf, text="", bg=BG_PANEL,
                                fg=FG_DIM, font=FONT_STATUS)
        self._ts_lbl.pack(side="right", padx=8)

    # ─── Session ──────────────────────────────────────────────────────────────

    def set_session(self, session):
        self._stop_live()
        self._session = session
        self._status.config(text=f"READY — {session.hostname}", fg=FG_SECONDARY)

    def clear_session(self):
        self._stop_live()
        self._session = None
        self._auto = False
        self._status.config(text="IDLE", fg=FG_DIM)

    # ─── One-shot capture ─────────────────────────────────────────────────────

    def _capture(self):
        if not self._session:
            return
        threading.Thread(target=self._do_capture, daemon=True).start()

    def _do_capture(self):
        try:
            self.after(0, lambda: self._status.config(
                text="● CAPTURING…", fg=FG_YELLOW))
            if not self._session.ensure_connected():
                self.after(0, lambda: self._status.config(
                    text="✗ Connect failed", fg=FG_RED))
                return
            data = self._session.screenshot()
            if data:
                self._last_bytes = data
                self._show_frame(data)
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.after(0, lambda: self._ts_lbl.config(text=f"Captured {ts}"))
                self.after(0, lambda: self._status.config(
                    text="✓ OK", fg=FG_CYAN))
        except Exception as e:
            self.after(0, lambda: self._status.config(
                text=f"✗ {e}", fg=FG_RED))

    # ─── Live stream ──────────────────────────────────────────────────────────

    def _toggle_live(self):
        if self._live:
            self._stop_live()
        else:
            self._start_live()

    def _start_live(self):
        if not self._session or self._live:
            return
        self._live = True
        self._frame_count = 0
        self._frame_t = time.time()
        self._live_btn.config(text="■ STOP LIVE", bg=FG_RED, fg=BG_DEEP)
        self._status.config(text="● LIVE", fg=FG_CYAN)
        threading.Thread(target=self._live_loop, daemon=True).start()

    def _stop_live(self):
        self._live = False
        self.after(0, lambda: self._live_btn.config(
            text="▶ LIVE", **STYLE_BUTTON))
        self.after(0, lambda: self._fps_lbl.config(text=""))
        self.after(0, lambda: self._status.config(
            text="■ STOPPED", fg=FG_DIM))

    def _live_loop(self):
        interval = 1.0 / self.LIVE_FPS
        while self._live and self._session:
            t0 = time.time()
            try:
                if not self._live:
                    break
                quality = self._quality_var.get()
                scale   = round(self._scale_var.get(), 2)
                data = self._session.screen_frame(quality, scale)
                if data:
                    self._last_bytes = data
                    self._show_frame(data)
                    self._frame_count += 1
                    elapsed = time.time() - self._frame_t
                    if elapsed >= 2.0:
                        fps = self._frame_count / elapsed
                        self._frame_count = 0
                        self._frame_t = time.time()
                        self.after(0, lambda f=fps: self._fps_lbl.config(
                            text=f"{f:.1f} FPS"))
            except Exception as e:
                self.after(0, lambda: self._status.config(
                    text=f"Stream error", fg=FG_RED))
                break
            # Throttle to target FPS
            sleep = interval - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)

        self._live = False
        self.after(0, lambda: self._live_btn.config(
            text="▶ LIVE", **STYLE_BUTTON))
        self.after(0, lambda: self._fps_lbl.config(text=""))
        self.after(0, lambda: self._status.config(
            text="■ STOPPED", fg=FG_DIM))

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _show_frame(self, data: bytes):
        """Decode JPEG and display on canvas (called from any thread safely)."""
        if not _PIL_OK or not data:
            return
        try:
            img = Image.open(io.BytesIO(data))
            cw  = max(self._canvas.winfo_width(),  400)
            ch  = max(self._canvas.winfo_height(), 300)
            img.thumbnail((cw, ch), Image.LANCZOS)
            # Update resolution label
            rw, rh = img.size
            self.after(0, lambda: self._res_lbl.config(
                text=f"{rw}×{rh}"))
            photo = ImageTk.PhotoImage(img)
            def _draw(p=photo):
                self._canvas.delete("all")
                self._canvas.create_image(cw // 2, ch // 2,
                                           image=p, anchor="center")
                self._img_ref = p
            self.after(0, _draw)
        except Exception:
            pass

    def _save(self):
        if not self._last_bytes:
            return
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        save_dir = os.path.join(base_dir, "capturas")
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"cb_screen_{ts}.jpg")
        with open(path, "wb") as f:
            f.write(self._last_bytes)
        self.after(0, lambda: self._status.config(
            text=f"Saved → {path}", fg=FG_CYAN))

    def _toggle_auto(self):
        self._auto = self._auto_var.get()
        if self._auto:
            threading.Thread(target=self._auto_loop, daemon=True).start()

    def _auto_loop(self):
        while self._auto and self._session:
            self._do_capture()
            time.sleep(10)
