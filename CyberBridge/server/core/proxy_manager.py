"""
CyberBridge - Proxy & Tunnel Manager
Handles the execution and monitoring of reverse proxies like Cloudflare Tunnels (cloudflared) and Ngrok.
"""

import subprocess
import threading
import logging
import re
import os

logger = logging.getLogger("cyberbridge.proxy")

class ProxyManager:
    """Manages background proxy processes to expose the local server."""
    
    def __init__(self):
        self._process = None
        self._current_url = None
        self.current_proxy = "Local (Ninguno)"
        
    def start_proxy(self, proxy_type: str, port: int, on_url_found=None, on_error=None, on_log=None):
        """Starts the selected proxy pointing to the local port."""
        self.stop_proxy()
        self.current_proxy = proxy_type
        
        if proxy_type == "Local (Ninguno)":
            if on_url_found:
                on_url_found(f"http://localhost:{port}")
            return
            
        def _run():
            cmd = []
            if proxy_type == "Cloudflare Tunnels":
                exe_path = "cloudflared"
                if os.name == 'nt':
                    paths = [
                        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
                        r"C:\Program Files\cloudflared\cloudflared.exe",
                        r"C:\Users\erick\Downloads\cloudflared-tunels\cloudflared-windows-386.exe"
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            exe_path = p
                            break
                cmd = [exe_path, "tunnel", "--url", f"http://localhost:{port}"]
            elif proxy_type == "Ngrok":
                cmd = [
                    "ngrok", "http", str(port), 
                    "--url", "https://marquis-prorefugee-lala.ngrok-free.app", 
                    "--log=stdout"
                ]
            else:
                return

            try:
                creation_flags = 0
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NO_WINDOW
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=creation_flags
                )

                # Stream logs to UI
                def _reader():
                    try:
                        for line in self._process.stdout:
                            line = line.rstrip()
                            if on_log:
                                on_log(line)
                            # Detect URL from ngrok log
                            if proxy_type == "Ngrok" and "started tunnel" in line:
                                m = re.search(r'url=([^\s]+)', line)
                                if m and on_url_found:
                                    url = m.group(1)
                                    on_url_found(url)
                    except Exception as e:
                        logger.warning(f"Proxy log reader error: {e}")

                threading.Thread(target=_reader, daemon=True).start()

                if proxy_type == "Ngrok" and on_url_found:
                    # Fallback immediate URL
                    on_url_found("https://marquis-prorefugee-lala.ngrok-free.app")
                        
            except FileNotFoundError:
                msg = f"No se encontró el ejecutable de {proxy_type}. Asegúrate de que esté instalado y agregado al PATH."
                logger.error(msg)
                if on_error:
                    on_error(msg)
            except Exception as e:
                msg = f"Error al iniciar {proxy_type}: {e}"
                logger.error(msg)
                if on_error:
                    on_error(msg)

        threading.Thread(target=_run, daemon=True).start()
        
    def stop_proxy(self):
        """Terminates the running proxy process."""
        if self._process:
            try:
                self._process.terminate()
            except:
                pass
            self._process = None
        self._current_url = None
        self.current_proxy = "Local (Ninguno)"
