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
        
    def start_proxy(self, proxy_type: str, port: int, on_url_found=None, on_error=None):
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
                # Find cloudflared executable (check common absolute paths if not in PATH)
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
                # User's specific ngrok static URL. We add --log=stdout to prevent interactive TUI from hanging the subprocess.
                cmd = [
                    "ngrok", "http", str(port), 
                    "--url", "https://marquis-prorefugee-lala.ngrok-free.app", 
                    "--log=stdout"
                ]
            else:
                return

            try:
                # To open a visible CMD window, we use 'start cmd /k' on Windows
                if os.name == 'nt':
                    # We safely convert the command list to a string handling spaces in paths
                    cmd_str = subprocess.list2cmdline(cmd)
                    # We launch it in a new visible console
                    self._process = subprocess.Popen(f'start "CyberBridge Proxy" cmd /k "{cmd_str}"', shell=True)
                else:
                    self._process = subprocess.Popen(cmd)

                # Since we are opening a separate CMD window, we can't easily capture its stdout in real-time.
                # So we update the UI directly based on the proxy type.
                if proxy_type == "Ngrok":
                    if on_url_found:
                        on_url_found("https://marquis-prorefugee-lala.ngrok-free.app")
                elif proxy_type == "Cloudflare Tunnels":
                    if on_url_found:
                        on_url_found("(Revisa la ventana de CMD para copiar tu enlace .trycloudflare.com)")
                            
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
