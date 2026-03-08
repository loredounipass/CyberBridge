"""
CyberBridge - Client Watchdog
Self-monitoring process spawner.
"""

import sys
import os
import time
import subprocess
import logging
import threading

logger = logging.getLogger("cyberbridge.watchdog")

_WATCHDOG_FLAG = "--cb-watchdog"


def run_watchdog_if_requested() -> bool:
    """
    Checks if this process was launched as a watchdog.
    If so, it monitors the parent process and restarts it if it dies.
    Returns True if this is the watchdog process (should not run main app logic).
    """
    if _WATCHDOG_FLAG not in sys.argv:
        return False

    # This is the watchdog process
    try:
        idx = sys.argv.index(_WATCHDOG_FLAG)
        parent_pid = int(sys.argv[idx + 1])
    except Exception:
        return True  # Invalid args, but still watchdog mode -> exit silently

    logger.info("Watchdog active. Monitoring PID %d...", parent_pid)
    
    # Wait for parent to exit
    try:
        # psutil is better but optional
        import psutil
        while psutil.pid_exists(parent_pid):
            time.sleep(2)
    except ImportError:
        # Fallback to polling via tasklist or just waiting on handle if possible
        # Simple polling: check if process is still running via tasklist
        while True:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {parent_pid}"],
                capture_output=True, text=True
            )
            if str(parent_pid) not in (res.stdout or ""):
                break
            time.sleep(2)

    logger.info("Parent process died. Restarting...")
    
    # Relaunch the main application (without watchdog flag)
    # The new main app will then spawn a new watchdog
    exe = sys.executable
    script = sys.argv[0]
    
    if getattr(sys, 'frozen', False):
        cmd = [exe]
    else:
        cmd = [exe, script]
    
    # Pass along other arguments
    cmd += sys.argv[1:idx] + sys.argv[idx + 2:]
    
    # Detached creation flags
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(cmd, close_fds=True, creationflags=creationflags)
    return True


def start_watchdog():
    """
    Spawns a copy of this process in watchdog mode to monitor us.
    """
    exe = sys.executable
    script = sys.argv[0]
    pid = os.getpid()
    
    if getattr(sys, 'frozen', False):
        cmd = [exe, _WATCHDOG_FLAG, str(pid)]
    else:
        cmd = [exe, script, _WATCHDOG_FLAG, str(pid)]
    
    # Pass along other arguments
    cmd += sys.argv[1:]
    
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.Popen(
            cmd,
            close_fds=True,
            creationflags=creationflags
        )
        logger.info("Spawned watchdog process.")
    except Exception as e:
        logger.warning("Failed to spawn watchdog: %s", e)
