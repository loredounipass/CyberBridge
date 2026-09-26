"""
CyberBridge - Server Entry Point
Dual mode: App Tkinter o Web Liquid Glass
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import argparse
import webbrowser
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, _ROOT)

from server.ui.dashboard import Dashboard

def _parse_mode():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode', choices=['web','app'], default=None)
    args, _ = parser.parse_known_args()
    return args.mode

def _prompt_mode():
    print("\nCyberBridge v1.0 - Selecciona modo de ejecución")
    print("1) Modo Web  - Navegador Liquid Glass")
    print("2) Modo App  - Ventana de escritorio Tkinter")
    while True:
        choice = input("Elige 1 o 2: ").strip()
        if choice in ('1','web','w'):
            return 'web'
        if choice in ('2','app','a'):
            return 'app'
        print("Opción no válida")

def start_app():
    app = Dashboard()
    app.run()

def start_web():
    from server.web_server import WebServer
    from server.config import SERVER_BIND_HOST
    # Port defaults to env via WebServer.__init__
    server = WebServer()
    def open_browser():
        import time
        time.sleep(1.5)
        host = SERVER_BIND_HOST if SERVER_BIND_HOST != '0.0.0.0' else 'localhost'
        webbrowser.open(f'http://{host}:{server.port}')
    threading.Thread(target=open_browser, daemon=True).start()
    server.run()

def main():
    mode = _parse_mode()
    if not mode:
        mode = _prompt_mode()
    if mode == 'web':
        start_web()
    else:
        start_app()

if __name__ == "__main__":
    main()
