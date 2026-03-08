"""
CyberBridge - UI Style Constants
Green-on-black hacker aesthetic with subtle neon accents.
"""

# ─── Color Palette ────────────────────────────────────────────────────────────

BG_DEEP      = "#0a0f0a"      # Near-black background
BG_PANEL     = "#0d1410"      # Slightly lighter panels
BG_CARD      = "#111a12"      # Cards / session tiles
BG_INPUT     = "#0c1509"      # Input field background

FG_PRIMARY   = "#00ff41"      # Bright matrix green (primary text)
FG_SECONDARY = "#00c030"      # Dimmed green (labels)
FG_DIM       = "#3a6640"      # Very dim green (borders, placeholders)
FG_WHITE     = "#e0ffe0"      # Off-white for readability
FG_RED       = "#ff4040"      # Alerts / errors
FG_YELLOW    = "#d4ff00"      # Warnings / highlights
FG_CYAN      = "#00ffcc"      # Accent / online status

BORDER_COLOR = "#1a3a1e"      # Panel borders
SEP_COLOR    = "#0f2212"      # Separator lines

SCROLLBAR_BG = "#0d1410"
SCROLLBAR_FG = "#1f5c25"

# ─── Font Definitions ─────────────────────────────────────────────────────────

FONT_MONO    = ("Consolas",    10)
FONT_MONO_SM = ("Consolas",     9)
FONT_MONO_LG = ("Consolas",    12)
FONT_MONO_XL = ("Consolas",    14, "bold")
FONT_TITLE   = ("Consolas",    16, "bold")
FONT_LABEL   = ("Consolas",     9)
FONT_STATUS  = ("Consolas",     8)
FONT_BUTTON  = ("Consolas",    10, "bold")

# ─── Widget Style Presets ─────────────────────────────────────────────────────

STYLE_FRAME = {
    "bg": BG_PANEL,
    "highlightbackground": BORDER_COLOR,
    "highlightthickness": 1,
}

STYLE_LABEL = {
    "bg": BG_PANEL,
    "fg": FG_SECONDARY,
    "font": FONT_LABEL,
}

STYLE_LABEL_PRIMARY = {
    "bg": BG_PANEL,
    "fg": FG_PRIMARY,
    "font": FONT_MONO,
}

STYLE_BUTTON = {
    "bg": BG_CARD,
    "fg": FG_PRIMARY,
    "font": FONT_BUTTON,
    "activebackground": "#1a3a1e",
    "activeforeground": FG_CYAN,
    "relief": "flat",
    "cursor": "hand2",
    "bd": 1,
    "highlightbackground": FG_DIM,
    "highlightthickness": 1,
    "padx": 8,
    "pady": 4,
}

STYLE_BUTTON_DANGER = {
    **STYLE_BUTTON,
    "fg": FG_RED,
    "activeforeground": "#ff8080",
    "highlightbackground": FG_RED,
}

STYLE_ENTRY = {
    "bg": BG_INPUT,
    "fg": FG_PRIMARY,
    "insertbackground": FG_PRIMARY,
    "relief": "flat",
    "font": FONT_MONO,
    "highlightbackground": FG_DIM,
    "highlightthickness": 1,
}

STYLE_TEXT = {
    "bg": BG_DEEP,
    "fg": FG_PRIMARY,
    "insertbackground": FG_PRIMARY,
    "font": FONT_MONO,
    "relief": "flat",
    "selectbackground": "#1a3a1e",
    "selectforeground": FG_CYAN,
    "wrap": "word",
}

STYLE_LISTBOX = {
    "bg": BG_DEEP,
    "fg": FG_PRIMARY,
    "font": FONT_MONO_SM,
    "relief": "flat",
    "selectbackground": "#1a3a1e",
    "selectforeground": FG_CYAN,
    "activestyle": "none",
    "highlightbackground": BORDER_COLOR,
    "highlightthickness": 1,
}
