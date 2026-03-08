"""
CyberBridge - Audio Panel
Play or record live audio from the remote machine's microphone.
"""

import tkinter as tk
import threading
import time
import datetime
import os

from .styles import *

try:
    import pyaudio
    _PA_OK = True
except ImportError:
    _PA_OK = False


class AudioPanel(tk.Frame):
    """Streams remote microphone audio and optionally records it to a WAV."""

    SAMPLE_RATE = 16000
    CHANNELS    = 1
    FORMAT_STR  = "16-bit PCM"

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PANEL, **kwargs)
        self._session    = None
        self._streaming  = False
        self._recording  = False
        self._build()

    def _build(self):
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")
        tk.Label(tb, text="🎙 MICROPHONE", font=FONT_MONO_XL,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)
        self._status = tk.Label(tb, text="IDLE", font=FONT_MONO_SM,
                                bg=BG_CARD, fg=FG_DIM)
        self._status.pack(side="right", padx=8)

        # Volume bar
        vf = tk.Frame(self, bg=BG_PANEL)
        vf.pack(fill="x", padx=8, pady=8)
        tk.Label(vf, text="LEVEL", **STYLE_LABEL).pack(side="left", padx=4)
        self._vol_canvas = tk.Canvas(vf, height=20, bg=BG_DEEP,
                                     highlightthickness=1,
                                     highlightbackground=FG_DIM)
        self._vol_canvas.pack(fill="x", expand=True, side="left", padx=4)
        self._vol_bar = self._vol_canvas.create_rectangle(
            0, 0, 0, 20, fill=FG_PRIMARY, outline=""
        )

        # Log
        lf = tk.Frame(self, bg=BG_DEEP)
        lf.pack(fill="both", expand=True, padx=8, pady=4)
        self._log = tk.Text(lf, height=8, state="disabled", **STYLE_TEXT)
        self._log.pack(fill="both", expand=True)
        self._log.tag_config("info", foreground=FG_SECONDARY)
        self._log.tag_config("warn", foreground=FG_YELLOW)
        self._log.tag_config("ok",   foreground=FG_CYAN)

        # Controls
        cf = tk.Frame(self, bg=BG_PANEL)
        cf.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(cf, text="▶ LISTEN",    command=self._start_stream, **STYLE_BUTTON).pack(side="left", padx=4)
        tk.Button(cf, text="■ STOP",      command=self._stop_stream,  **STYLE_BUTTON_DANGER).pack(side="left", padx=4)
        tk.Button(cf, text="⏺ RECORD",   command=self._start_record, **STYLE_BUTTON).pack(side="left", padx=4)

    def set_session(self, session):
        self._stop_stream()
        self._session = session
        self._append("Session set: " + session.hostname + " (" + session.ip + ")", "info")

    def clear_session(self):
        self._stop_stream()
        self._session = None

    def _append(self, text: str, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.config(state="normal")
        self._log.insert(tk.END, f"[{ts}] {text}\n", tag)
        self._log.see(tk.END)
        self._log.config(state="disabled")

    def _start_stream(self):
        if not self._session or self._streaming:
            return
        # Run connection + audio init in background to avoid blocking the UI
        threading.Thread(target=self._do_start_stream, daemon=True).start()

    def _do_start_stream(self):
        """Background thread: connects and starts audio without blocking the UI."""
        try:
            if not self._session.ensure_connected():
                self.after(0, lambda: self._append("Cannot connect to client", "warn"))
                return
            ok = self._session.start_audio()
            if not ok:
                self.after(0, lambda: self._append("Remote: PyAudio not available (no mic?)", "warn"))
                return
            self._streaming = True
            self.after(0, lambda: self._status.config(text="● LIVE", fg=FG_CYAN))
            self.after(0, lambda: self._append("Audio stream started — waiting for mic data…", "ok"))

            # Wait 1.5s then check if audio is actually capturing
            time.sleep(1.5)
            try:
                # In HTTP mode we check via ping instead of audio_status
                ok = self._session.ping()
                if not ok:
                    self.after(0, lambda: self._append(
                        "Client not responding — check connection", "warn"))
                else:
                    self.after(0, lambda: self._append(
                        "Audio capturing on client ✓", "ok"))
            except Exception:
                pass

            self._stream_loop()
        except Exception as e:
            self.after(0, lambda: self._append(f"Audio error: {e}", "warn"))
            self._streaming = False

    def _stop_stream(self):
        if not self._streaming and not self._recording:
            return
        was_streaming = self._streaming
        was_recording = self._recording
        self._streaming = False
        self._recording = False

        def _do_stop():
            try:
                if self._session and self._session.connected:
                    if was_streaming:
                        self._session.stop_audio()
                    if was_recording:
                        audio = self._session.stop_audio_record()
                        if audio:
                            path = self._save_recording(audio)
                            self.after(0, lambda: self._append(f"Saved → {path}", "ok"))
                        else:
                            self.after(0, lambda: self._append("No recording received", "warn"))
            except Exception as e:
                self.after(0, lambda: self._append(f"Audio stop error: {e}", "warn"))
            self.after(0, lambda: self._status.config(text="■ STOPPED", fg=FG_DIM))

        threading.Thread(target=_do_stop, daemon=True).start()

    def _start_record(self):
        if not self._session or self._recording:
            return
        self._recording = True

        def _do_start():
            try:
                if not self._session.ensure_connected():
                    self.after(0, lambda: self._append("Cannot connect to client", "warn"))
                    self._recording = False
                    return
                if self._streaming:
                    try:
                        self._session.stop_audio()
                    except Exception:
                        pass
                    self._streaming = False
                ok = self._session.start_audio_record()
                if not ok:
                    self.after(0, lambda: self._append("Remote: PyAudio not available (no mic?)", "warn"))
                    self._recording = False
                    return
                self.after(0, lambda: self._status.config(text="● REC", fg=FG_YELLOW))
                self.after(0, lambda: self._append("Recording on client…", "ok"))
            except Exception as e:
                self._recording = False
                self.after(0, lambda: self._append(f"Record error: {e}", "warn"))

        threading.Thread(target=_do_start, daemon=True).start()

    def _save_recording(self, data: bytes) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        save_dir = os.path.join(base_dir, "audios")
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"cb_audio_{ts}.wav")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _stream_loop(self):
        """Audio poll loop — runs in background thread, never on the UI thread."""
        pa = None
        out_stream = None
        if _PA_OK:
            try:
                pa = pyaudio.PyAudio()
                out_stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=self.CHANNELS,
                    rate=self.SAMPLE_RATE,
                    output=True,
                )
            except Exception:
                pa = None

        empty_count = 0
        while self._streaming and self._session:
            try:
                if not self._streaming:
                    break
                chunk = self._session.get_audio_chunk()
                if chunk:
                    empty_count = 0
                    if out_stream:
                        try:
                            out_stream.write(chunk)
                        except Exception:
                            pass
                    # Volume level — update on UI thread
                    try:
                        import audioop
                        rms = audioop.rms(chunk, 2)
                        pct = min(rms / 3000 * 100, 100)
                        def _upd(p=pct):
                            w = self._vol_canvas.winfo_width()
                            self._vol_canvas.coords(self._vol_bar,
                                                    0, 0, int(w * p / 100), 20)
                        self.after(0, _upd)
                    except Exception:
                        pass
                else:
                    empty_count += 1
                    # After 10 empty polls (~1.5s), warn that mic isn't sending data
                    if empty_count == 10:
                        self.after(0, lambda: self._append(
                            "⚠ No mic data arriving — check if client has a microphone", "warn"))
            except Exception as e:
                self.after(0, lambda err=e: self._append(f"Stream error: {err}", "warn"))
                break
            time.sleep(0.15)


        # Cleanup
        self._streaming = False
        self.after(0, lambda: self._status.config(text="■ STOPPED", fg=FG_DIM))
        for obj, method in [(out_stream, "stop_stream"), (out_stream, "close"), (pa, "terminate")]:
            if obj:
                try:
                    getattr(obj, method)()
                except Exception:
                    pass

