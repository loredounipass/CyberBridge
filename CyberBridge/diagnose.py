"""
CyberBridge - Diagnostics Script
Run this to check why client beacons are not reaching the server.
Usage: python diagnose.py
"""

import socket
import json
import subprocess
import sys
import os
import time
import threading

SERVER_HOST      = "127.0.0.1"
BEACON_PORT      = 18812
CLIENT_RPC_PORT  = 18813

SEP = "─" * 60

def ok(msg):   print(f"  ✅  {msg}")
def fail(msg): print(f"  ❌  {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def info(msg): print(f"  ℹ️  {msg}")


# ─── 1. Check server process ──────────────────────────────────────────────────
def check_server_running():
    print(f"\n{SEP}")
    print("1. ¿Está corriendo el servidor? (python server/main.py)")
    print(SEP)
    # Try to open a UDP socket and see if port 18812 is being listened on
    try:
        # Try binding to it — if it fails, someone else owns it (= server listening)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", BEACON_PORT))
        s.close()
        fail(f"Puerto UDP {BEACON_PORT} NO está en uso → el servidor no está corriendo o no escucha beacons.")
        info("→ Inicia el servidor: python server/main.py")
        return False
    except OSError:
        ok(f"Puerto UDP {BEACON_PORT} está en uso → servidor escuchando beacons ✓")
        return True


# ─── 2. Send a test beacon ────────────────────────────────────────────────────
def send_test_beacon():
    print(f"\n{SEP}")
    print(f"2. Enviando beacon de prueba a {SERVER_HOST}:{BEACON_PORT} …")
    print(SEP)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hostname = socket.gethostname()
        payload = json.dumps({
            "type":     "register",
            "hostname": hostname + "_DIAG",
            "ip":       socket.gethostbyname(hostname),
            "port":     CLIENT_RPC_PORT,
        }).encode()
        sock.sendto(payload, (SERVER_HOST, BEACON_PORT))
        sock.close()
        ok(f"Beacon enviado: hostname={hostname}_DIAG, ip={socket.gethostbyname(hostname)}, port={CLIENT_RPC_PORT}")
        info("→ Revisa el panel CONNECTIONS del servidor — debería aparecer '_DIAG'")
    except Exception as e:
        fail(f"Error enviando beacon: {e}")


# ─── 3. Check service status ──────────────────────────────────────────────────
def check_service():
    print(f"\n{SEP}")
    print("3. Estado del servicio CyberBridgeSvc")
    print(SEP)
    try:
        result = subprocess.run(
            ["sc", "query", "CyberBridgeSvc"],
            capture_output=True, text=True, timeout=5
        )
        if "RUNNING" in result.stdout:
            ok("Servicio CyberBridgeSvc: RUNNING")
        elif "STOPPED" in result.stdout:
            fail("Servicio CyberBridgeSvc: STOPPED")
            info("→ Inícialo: dist\\CyberBridgeSvc.exe start  (como Admin)")
        elif "1060" in result.stderr or "does not exist" in result.stdout.lower():
            warn("Servicio CyberBridgeSvc: NO INSTALADO")
            info("→ Instálalo: dist\\CyberBridgeSvc.exe install  (como Admin)")
        else:
            info(f"Salida sc query:\n{result.stdout}")
    except Exception as e:
        warn(f"No se pudo consultar el servicio: {e}")


# ─── 4. Check RPC port ────────────────────────────────────────────────────────
def check_rpc_port():
    print(f"\n{SEP}")
    print(f"4. ¿Puerto RPC del cliente {CLIENT_RPC_PORT} está abierto?")
    print(SEP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", CLIENT_RPC_PORT))
        s.close()
        if result == 0:
            ok(f"Puerto TCP {CLIENT_RPC_PORT} está ABIERTO → cliente RPC escuchando")
        else:
            fail(f"Puerto TCP {CLIENT_RPC_PORT} CERRADO → cliente RPC no está corriendo")
            info("→ El servicio debe estar corriendo para abrir este puerto")
    except Exception as e:
        fail(f"Error verificando puerto: {e}")


# ─── 5. Check log file ────────────────────────────────────────────────────────
def check_log():
    print(f"\n{SEP}")
    print("5. Últimas líneas del log del cliente")
    print(SEP)
    log_path = os.path.join(
        os.environ.get("APPDATA", ""), "Microsoft", "Logs", "cbsvc.log"
    )
    if os.path.exists(log_path):
        ok(f"Log encontrado: {log_path}")
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        last = lines[-20:] if len(lines) > 20 else lines
        for line in last:
            print(f"    {line}", end="")
    else:
        warn(f"Log no encontrado en {log_path}")
        info("→ El servicio quizás nunca arrancó correctamente")


# ─── 6. Firewall check ────────────────────────────────────────────────────────
def check_firewall():
    print(f"\n{SEP}")
    print("6. Verificando reglas de firewall para puerto UDP 18812")
    print(SEP)
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule",
             f"localport={BEACON_PORT}", "protocol=UDP"],
            capture_output=True, text=True, timeout=5
        )
        if "No rules match" in result.stdout or not result.stdout.strip():
            warn(f"No hay regla de firewall para UDP {BEACON_PORT}")
            info("→ Windows Firewall podría bloquear los beacons")
            info(f"→ Agrégala: netsh advfirewall firewall add rule name=\"CyberBridge\" protocol=UDP dir=in localport={BEACON_PORT} action=allow")
        else:
            ok(f"Regla de firewall encontrada para UDP {BEACON_PORT}")
            print(result.stdout[:400])
    except Exception as e:
        warn(f"No se pudo verificar firewall: {e}")


# ─── 7. SERVER_HOST mismatch ─────────────────────────────────────────────────
def check_config():
    print(f"\n{SEP}")
    print("7. Verificación de configuración de red")
    print(SEP)
    hostname  = socket.gethostname()
    local_ip  = socket.gethostbyname(hostname)
    info(f"IP local de esta máquina: {local_ip}")
    info(f"SERVER_HOST en config.py:  {SERVER_HOST}")

    if SERVER_HOST == "127.0.0.1":
        ok("127.0.0.1 es correcto para pruebas en la MISMA máquina")
    elif SERVER_HOST == local_ip:
        ok(f"SERVER_HOST coincide con la IP local ({local_ip}) ✓")
    else:
        warn(f"SERVER_HOST ({SERVER_HOST}) ≠ IP local ({local_ip})")
        info("→ Si el cliente y servidor están en distinta máquina, esto es normal")
        info(f"→ Si están en la misma, cambia SERVER_HOST a {local_ip} o 127.0.0.1")


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   CYBERBRIDGE — DIAGNÓSTICO DE CONEXIÓN")
    print("=" * 60)

    check_config()
    srv_running = check_server_running()
    check_service()
    check_rpc_port()
    check_firewall()
    check_log()

    if srv_running:
        send_test_beacon()

    print(f"\n{SEP}")
    print("Diagnóstico completo. Revisa los ❌ y ⚠️ arriba.")
    print(SEP)
