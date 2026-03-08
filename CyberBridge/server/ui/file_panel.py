"""
CyberBridge - File Transfer Panel
Allows uploading and downloading files between server and client.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import datetime

from .styles import *

class FilePanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, **kwargs)
        self._session = None
        self._build_ui()

    def _build_ui(self):
        # ── Title bar ─────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        tb.pack(fill="x")
        tk.Label(tb, text="📂 FILE TRANSFER", font=FONT_TITLE,
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=10, pady=6)
        
        # ── Main Content ──────────────────────────────────────────────────────
        content = tk.Frame(self, bg=BG_DEEP)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # ─── Upload Section ───────────────────────────────────────────────────
        up_frame = tk.LabelFrame(content, text=" UPLOAD (Server → Client) ",
                                 bg=BG_DEEP, fg=FG_SECONDARY, font=FONT_MONO_LG,
                                 bd=1, relief="solid")
        up_frame.pack(fill="x", pady=(0, 20), ipady=10)

        # Row 1: Local File
        f1 = tk.Frame(up_frame, bg=BG_DEEP)
        f1.pack(fill="x", padx=10, pady=5)
        tk.Label(f1, text="Local File: ", width=15, anchor="e", **STYLE_LABEL).pack(side="left")
        
        self._up_local_var = tk.StringVar()
        tk.Entry(f1, textvariable=self._up_local_var, **STYLE_ENTRY).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f1, text="Browse...", command=self._browse_upload_file, **STYLE_BUTTON).pack(side="left")

        # Row 2: Remote Path
        f2 = tk.Frame(up_frame, bg=BG_DEEP)
        f2.pack(fill="x", padx=10, pady=5)
        tk.Label(f2, text="Remote Path:", width=15, anchor="e", **STYLE_LABEL).pack(side="left")
        
        self._up_remote_var = tk.StringVar(value="C:\\Windows\\Temp\\")
        tk.Entry(f2, textvariable=self._up_remote_var, **STYLE_ENTRY).pack(side="left", fill="x", expand=True, padx=5)
        
        # Row 3: Action
        f3 = tk.Frame(up_frame, bg=BG_DEEP)
        f3.pack(fill="x", padx=10, pady=5)
        tk.Button(f3, text="⬆ UPLOAD TO CLIENT", command=self._start_upload, **STYLE_BUTTON).pack(side="right")


        # ─── Download Section ─────────────────────────────────────────────────
        down_frame = tk.LabelFrame(content, text=" DOWNLOAD (Client → Server) ",
                                   bg=BG_DEEP, fg=FG_SECONDARY, font=FONT_MONO_LG,
                                   bd=1, relief="solid")
        down_frame.pack(fill="x", pady=(0, 20), ipady=10)

        # Row 1: Remote File
        f4 = tk.Frame(down_frame, bg=BG_DEEP)
        f4.pack(fill="x", padx=10, pady=5)
        tk.Label(f4, text="Remote File:", width=15, anchor="e", **STYLE_LABEL).pack(side="left")
        
        self._down_remote_var = tk.StringVar()
        tk.Entry(f4, textvariable=self._down_remote_var, **STYLE_ENTRY).pack(side="left", fill="x", expand=True, padx=5)

        # Row 2: Local Path
        f5 = tk.Frame(down_frame, bg=BG_DEEP)
        f5.pack(fill="x", padx=10, pady=5)
        tk.Label(f5, text="Local Dest: ", width=15, anchor="e", **STYLE_LABEL).pack(side="left")
        
        self._down_local_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        tk.Entry(f5, textvariable=self._down_local_var, **STYLE_ENTRY).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f5, text="Browse...", command=self._browse_download_dest, **STYLE_BUTTON).pack(side="left")

        # Row 3: Action
        f6 = tk.Frame(down_frame, bg=BG_DEEP)
        f6.pack(fill="x", padx=10, pady=5)
        tk.Button(f6, text="⬇ DOWNLOAD FROM CLIENT", command=self._start_download, **STYLE_BUTTON).pack(side="right")


        # ─── Log Area ─────────────────────────────────────────────────────────
        tk.Label(content, text="Transfer Log", **STYLE_LABEL).pack(anchor="w")
        
        sb = tk.Scrollbar(content, orient="vertical",
                          bg=SCROLLBAR_BG, troughcolor=BG_DEEP,
                          activebackground=SCROLLBAR_FG)
        sb.pack(side="right", fill="y")
        
        self._log_text = tk.Text(content, height=8, yscrollcommand=sb.set, **STYLE_TEXT)
        self._log_text.pack(fill="both", expand=True)
        sb.config(command=self._log_text.yview)

        # Tags
        self._log_text.tag_config("info", foreground=FG_DIM)
        self._log_text.tag_config("success", foreground=FG_CYAN)
        self._log_text.tag_config("error", foreground=FG_RED)


    # ─── Logic ────────────────────────────────────────────────────────────────

    def set_session(self, session):
        self._session = session
        self._log(f"Session selected: {session.hostname} ({session.ip})", "info")

    def clear_session(self):
        self._session = None
        self._log("Session cleared", "info")

    def _browse_upload_file(self):
        path = filedialog.askopenfilename()
        if path:
            self._up_local_var.set(path)
            # Suggest remote path
            current_remote = self._up_remote_var.get()
            basename = os.path.basename(path)
            if current_remote.endswith("\\") or current_remote.endswith("/"):
                self._up_remote_var.set(current_remote + basename)
            elif os.path.isdir(current_remote) or (not "." in os.path.basename(current_remote)):
                 self._up_remote_var.set(os.path.join(current_remote, basename))

    def _browse_download_dest(self):
        path = filedialog.askdirectory()
        if path:
            self._down_local_var.set(path)

    def _log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] {msg}\n", tag)
        self._log_text.see("end")

    def _start_upload(self):
        if not self._session:
            self._log("Error: No session selected", "error")
            return

        local = self._up_local_var.get()
        remote = self._up_remote_var.get()

        if not local or not os.path.exists(local):
            self._log("Error: Invalid local file", "error")
            return
        if not remote:
            self._log("Error: Invalid remote path", "error")
            return

        self._log(f"Uploading {os.path.basename(local)} -> {remote} ...", "info")

        def _do():
            try:
                ok = self._session.upload_file(local, remote)
                if ok:
                    self._log("Upload completed successfully", "success")
                else:
                    self._log("Upload failed. (Check client version/permissions)", "error")
            except Exception as e:
                self._log(f"Upload error: {e}", "error")

        threading.Thread(target=_do, daemon=True).start()

    def _start_download(self):
        if not self._session:
            self._log("Error: No session selected", "error")
            return

        remote = self._down_remote_var.get()
        local_dir = self._down_local_var.get()

        if not remote:
            self._log("Error: Invalid remote file path", "error")
            return
        if not local_dir or not os.path.isdir(local_dir):
            self._log("Error: Invalid local destination directory", "error")
            return

        # Determine local filename
        basename = os.path.basename(remote.replace("\\", "/"))
        if not basename:
            basename = "downloaded_file.dat"
        local_path = os.path.join(local_dir, basename)

        self._log(f"Downloading {remote} -> {local_path} ...", "info")

        def _do():
            try:
                ok = self._session.download_file(remote, local_path)
                if ok:
                    self._log(f"Download completed: {local_path}", "success")
                else:
                    self._log("Download failed (Check remote path/client version)", "error")
            except Exception as e:
                self._log(f"Download error: {e}", "error")

        threading.Thread(target=_do, daemon=True).start()
