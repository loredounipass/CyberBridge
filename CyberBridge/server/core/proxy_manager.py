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
            if proxy_type == "Cloudflare Tunnels":
                # Cloudflared uses stderr for logging and generates a .trycloudflare.com URL
                cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
            elif proxy_type == "Ngrok":
                cmd = ["ngrok", "http", str(port)]
            else:
                return

            try:
                # Hide the console window on Windows
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                # Combine stdout and stderr since cloudflared outputs to stderr
                self._process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    startupinfo=startupinfo
                )
                
                # Regex to catch URLs from both Cloudflare and Ngrok
                url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.(trycloudflare\.com|ngrok\.io|ngrok-free\.app)')
                
                for line in self._process.stdout:
                    match = url_pattern.search(line)
                    if match and not self._current_url:
                        self._current_url = match.group(0)
                        logger.info(f"[{proxy_type}] Tunnel URL found: {self._current_url}")
                        if on_url_found:
                            on_url_found(self._current_url)
                            
            except FileNotFoundError:
                msg = f"No se encontró el ejecutable de {proxy_type}. Asegúrate de que esté instalado y agregado al PATH del sistema."
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
