#!/usr/bin/env python3
"""
CyberBridge Client Builder
- Builds Windows .exe with PyInstaller
- Builds Linux binary with PyInstaller
- Builds Android APK with Buildozer if available
Usage: python build_client.py
"""
import os
import sys
import platform
import subprocess
import shutil

ROOT = os.path.abspath(os.path.dirname(__file__))
MAIN = os.path.join(ROOT, "main.py")
CONFIG = os.path.join(ROOT, "config.py")

def run(cmd, cwd=None):
    print(f"[BUILD] $ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd or ROOT)

def build_windows_exe():
    print("[BUILD] Windows EXE")
    run([sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"])
    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "CyberBridgeClient",
        "--add-data", f"{CONFIG};.",
        MAIN
    ])
    dst = os.path.join(ROOT, "dist", "CyberBridgeClient.exe")
    if os.path.exists(dst):
        print(f"[OK] Windows EXE: {dst}")

def build_linux_bin():
    print("[BUILD] Linux binary")
    run([sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"])
    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "CyberBridgeClient",
        "--add-data", f"{CONFIG}:.",
        MAIN
    ])
    dst = os.path.join(ROOT, "dist", "CyberBridgeClient")
    if os.path.exists(dst):
        print(f"[OK] Linux binary: {dst}")

def build_apk():
    print("[BUILD] Android APK")
    try:
        import buildozer
    except Exception:
        print("[WARN] buildozer not installed. Skipping APK.")
        return
    build_dir = os.path.join(ROOT, "build_android")
    os.makedirs(build_dir, exist_ok=True)
    # copy sources
    shutil.copy2(MAIN, build_dir)
    shutil.copy2(CONFIG, build_dir)
    spec = os.path.join(build_dir, "buildozer.spec")
    if not os.path.exists(spec):
        with open(spec, "w") as f:
            f.write("""[app]
title = CyberBridge Client
package.name = cyberbridgeclient
package.domain = org.cyberbridge
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,requests,Pillow,mss,psutil
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
""")
    run(["buildozer", "android", "debug"], cwd=build_dir)
    print("[OK] APK built in build_android/bin")

if __name__ == "__main__":
    # Always build Windows exe
    build_windows_exe()
    # Build Linux if not Windows
    if platform.system() != "Windows":
        build_linux_bin()
    else:
        # On Windows we can still build Linux binary with cross-compile? Skip
        print("[INFO] Linux binary skipped on Windows host")
    # Try APK
    build_apk()
    print("[DONE] Build complete")
