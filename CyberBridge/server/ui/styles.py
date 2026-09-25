"""
CyberBridge - UI Style Constants
Professional "Liquid Glass" Matrix aesthetic.
Uses subtle dark-green tinted backgrounds and crisp neon accents to simulate a glossy, deep interface.
"""

# ─── Color Palette (Liquid Glass Theme) ───────────────────────────────────────

BG_DEEP      = "#050806"      # Deepest background (gives depth to the glass)
BG_PANEL     = "#0a130c"      # Panels: slightly elevated green-black tint
BG_CARD      = "#101d13"      # Cards: closer to the user, slightly brighter
BG_INPUT     = "#070e09"      # Input fields: recessed dark glass

FG_PRIMARY   = "#00ff41"      # Bright matrix green (primary text/neon glow)
FG_SECONDARY = "#2ce55b"      # Softer neon green for secondary elements
FG_DIM       = "#1e4d29"      # Dim glass borders/placeholders
FG_WHITE     = "#e0ffe0"      # Crisp off-white for primary readability
FG_RED       = "#ff3333"      # Alerts / errors (neon red)
FG_YELLOW    = "#e6ff00"      # Warnings / highlights
FG_CYAN      = "#00ffe5"      # Accent / online status

BORDER_COLOR = "#193d22"      # Edges that catch the "light" (subtle glass borders)
SEP_COLOR    = "#0a170d"      # Separator lines

SCROLLBAR_BG = "#0a130c"
SCROLLBAR_FG = "#1a4023"

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

# Base frames (simulating tinted glass panels)
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

# Buttons (designed to look like raised glassy elements with neon active states)
STYLE_BUTTON = {
    "bg": BG_CARD,
    "fg": FG_PRIMARY,
    "font": FONT_BUTTON,
    "activebackground": "#122a18",
    "activeforeground": FG_CYAN,
    "relief": "flat",
    "cursor": "hand2",
    "bd": 1,
    "highlightbackground": BORDER_COLOR,
    "highlightthickness": 1,
    "padx": 8,
    "pady": 4,
}

STYLE_BUTTON_DANGER = {
    **STYLE_BUTTON,
    "fg": FG_RED,
    "activeforeground": "#ff8080",
    "highlightbackground": "#591c1c",
}

STYLE_ENTRY = {
    "bg": BG_INPUT,
    "fg": FG_PRIMARY,
    "insertbackground": FG_PRIMARY,
    "relief": "flat",
    "font": FONT_MONO,
    "highlightbackground": BORDER_COLOR,
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
    "selectbackground": "#17361e",
    "selectforeground": FG_CYAN,
    "activestyle": "none",
    "highlightbackground": BORDER_COLOR,
    "highlightthickness": 1,
}
