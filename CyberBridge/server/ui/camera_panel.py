"""
CyberBridge - Camera Panel
Displays live JPEG frames from the remote machine's webcam.
"""

import tkinter as tk
import threading
import io
import time

from .styles import *

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


class CameraPanel(tk.Frame):
    """Shows a live camera feed from the selected client."""

    _REFRESH_MS = 150   # ~6-7 FPS

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._session  = None
        self._running  = False
        self._img_ref  = None
        self._build()

    def _build(self):
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")
        tk.Label(tb, text="◉ CAMERA FEED", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)

        self._status = tk.Label(tb, text="IDLE", font=FONT_MONO_SM,
                                bg=BG_CARD, fg=FG_DIM)
        self._status.pack(side="right", padx=8)

        self._canvas = tk.Canvas(self, bg=BG_DEEP, bd=0,
                                 highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)

        self._no_feed_text = self._canvas.create_text(
            300, 200,
            text="[ NO FEED ]\nSelect a client to view camera",
            fill=FG_DIM, font=FONT_MONO_LG, justify="center",
        )

        # Control bar
        cf = tk.Frame(self, bg=BG_PANEL)
        cf.pack(fill="x", padx=4, pady=(0, 4))
        tk.Button(cf, text="▶ START", command=self.start_feed,
                  **STYLE_BUTTON).pack(side="left", padx=4)
        tk.Button(cf, text="■ STOP",  command=self.stop_feed,
                  **STYLE_BUTTON_DANGER).pack(side="left", padx=4)

    def set_session(self, session):
        self.stop_feed()
        self._session = session
        self._status.config(text=f"READY — {session.hostname}", fg=FG_SECONDARY)

    def clear_session(self):
        self.stop_feed()
        self._session = None
        self._status.config(text="IDLE", fg=FG_DIM)

    def start_feed(self):
        if self._session is None or self._running:
            return
        self._running = True
        self._status.config(text="● LIVE", fg=FG_CYAN)
        threading.Thread(target=self._feed_loop, daemon=True).start()

    def stop_feed(self):
        self._running = False
        self._status.config(text="■ STOPPED", fg=FG_DIM)

    def _feed_loop(self):
        while self._running and self._session:
            try:
                if not self._session.ensure_connected():
                    time.sleep(1)
                    continue
                frame_bytes = self._session.get_camera_frame()
                if frame_bytes and _PIL_OK:
                    img = Image.open(io.BytesIO(frame_bytes))
                    # Fit to canvas
                    cw = max(self._canvas.winfo_width(),  320)
                    ch = max(self._canvas.winfo_height(), 240)
                    img.thumbnail((cw, ch), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self._canvas.delete("all")
                    self._canvas.create_image(
                        cw // 2, ch // 2,
                        image=photo, anchor="center",
                    )
                    self._img_ref = photo
            except Exception:
                pass
            time.sleep(self._REFRESH_MS / 1000)
