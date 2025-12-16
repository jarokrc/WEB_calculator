import tkinter as tk
from tkinter import ttk
from typing import Dict

# Theme definitions
THEMES: Dict[str, dict] = {
    "light": {
        "bg": "#f5f6fa",
        "surface": "#ffffff",
        "panel": "#eef1f7",
        "muted": "#4b5563",
        "text": "#0f172a",
        "accent": "#3b82f6",
        "accent_dim": "#2563eb",
        "border": "#d5d8e0",
        "highlight": "#e5e7eb",
    },
    "dark_futuristic": {
        "bg": "#0d1119",
        "surface": "#131a26",
        "panel": "#1a2333",
        "muted": "#9ca3af",
        "text": "#e5e7eb",
        "accent": "#22d3ee",
        "accent_dim": "#0ea5e9",
        "border": "#1f2a3c",
        "highlight": "#0b1624",
    },
    "soft_neon": {
        "bg": "#0f1624",
        "surface": "#131b2c",
        "panel": "#162033",
        "muted": "#cbd5e1",
        "text": "#f8fafc",
        "accent": "#f472b6",  # neon pink
        "accent_dim": "#fb7185",  # coral
        "border": "#1f2937",
        "highlight": "#1d2538",
    },
}

ACTIVE_THEME = "dark_futuristic"
PALETTE = THEMES[ACTIVE_THEME]


def apply_theme(root: tk.Misc, name: str = "dark_futuristic") -> dict:
    global ACTIVE_THEME, PALETTE
    if name not in THEMES:
        name = "dark_futuristic"
    ACTIVE_THEME = name
    PALETTE = THEMES[name]

    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=PALETTE["bg"])

    style.configure("TFrame", background=PALETTE["bg"])
    style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"])

    style.configure(
        "TButton",
        background=PALETTE["panel"],
        foreground=PALETTE["text"],
        borderwidth=0,
        padding=6,
    )
    style.map(
        "TButton",
        background=[("active", PALETTE["accent_dim"]), ("pressed", PALETTE["accent"])],
        foreground=[("active", PALETTE["text"]), ("pressed", PALETTE["text"])],
    )

    style.configure(
        "Accent.TButton",
        background=PALETTE["accent"],
        foreground="#0b1220",
        padding=7,
        borderwidth=0,
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", PALETTE["accent_dim"]), ("pressed", PALETTE["accent_dim"])],
        foreground=[("active", "#0b1220"), ("pressed", "#0b1220")],
    )

    style.configure(
        "TEntry",
        fieldbackground=PALETTE["panel"],
        background=PALETTE["panel"],
        foreground=PALETTE["text"],
        insertcolor=PALETTE["accent"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
    )

    style.configure(
        "Treeview",
        background=PALETTE["panel"],
        fieldbackground=PALETTE["panel"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        rowheight=24,
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["accent_dim"])],
        foreground=[("selected", PALETTE["text"])],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", PALETTE["highlight"])])

    style.configure("TSeparator", background=PALETTE["border"])
    return PALETTE


def style_listbox(listbox: tk.Listbox, palette: dict) -> None:
    listbox.configure(
        bg=palette["panel"],
        fg=palette["text"],
        selectbackground=palette["accent_dim"],
        highlightbackground=palette["border"],
        highlightcolor=palette["accent"],
        relief="flat",
    )
