"""
CyberBridge - Server Configuration
"""

# ─── Network ──────────────────────────────────────────────────────────────────

# IP address this server listens on (0.0.0.0 = all interfaces)
SERVER_BIND_HOST = "0.0.0.0"

# HTTP port for client communication (expose this via ngrok)
HTTP_PORT = 18812

# ─── Timeouts ─────────────────────────────────────────────────────────────────

# Seconds before a client is considered IDLE (no poll received)
IDLE_TIMEOUT = 20

# Seconds before a client is considered OFFLINE
OFFLINE_TIMEOUT = 60

# Command timeout (seconds)
CMD_TIMEOUT = 60

# ─── UI ───────────────────────────────────────────────────────────────────────

# Dashboard window title
WINDOW_TITLE = "CyberBridge  v1.0  ▮  Remote Monitoring Station"

# Camera refresh rate in milliseconds (~6 FPS at 150ms)
CAMERA_REFRESH_MS = 150

# System info auto-refresh interval in seconds
SYSINFO_REFRESH_SEC = 5
