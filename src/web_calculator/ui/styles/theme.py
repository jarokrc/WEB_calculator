import tkinter as tk
from tkinter import ttk
from typing import Dict

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional dependency fallback
    ctk = None  # type: ignore[assignment]

# Theme definitions
THEMES: Dict[str, dict] = {
    "light": {
        "bg": "#f8f9fc",
        "surface": "#ffffff",
        "panel": "#f2f5f9",
        "muted": "#475467",
        "text": "#0f172a",
        "accent": "#3b82f6",
        "accent_dim": "#2563eb",
        "border": "#d7dde7",
        "highlight": "#e9eef6",
    },
    "dark_futuristic": {
        "bg": "#0b111a",
        "surface": "#121a26",
        "panel": "#1b2433",
        "muted": "#9aa3b2",
        "text": "#f2f5f9",
        "accent": "#3dd9c0",
        "accent_dim": "#2bb8a3",
        "border": "#243040",
        "highlight": "#1a2230",
    },
    "soft_neon": {
        "bg": "#0f141f",
        "surface": "#151b29",
        "panel": "#1c2434",
        "muted": "#c3cad6",
        "text": "#f8fafc",
        "accent": "#ffb454",
        "accent_dim": "#ff9f1c",
        "border": "#273246",
        "highlight": "#1a2131",
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

    if ctk is not None:
        appearance = "Light" if name == "light" else "Dark"
        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme("blue" if appearance == "Light" else "dark-blue")
        try:
            root.configure(fg_color=PALETTE["bg"])  # type: ignore[arg-type]
        except Exception:
            root.configure(bg=PALETTE["bg"])
    else:
        root.configure(bg=PALETTE["bg"])

    style = ttk.Style(root)
    style.theme_use("clam")

    base_font = ("Segoe UI", 10)
    style.configure("TFrame", background=PALETTE["bg"])
    style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"], font=base_font)

    style.configure(
        "TButton",
        background=PALETTE["panel"],
        foreground=PALETTE["text"],
        borderwidth=0,
        padding=7,
        font=base_font,
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
        font=base_font,
    )

    style.configure(
        "Treeview",
        background=PALETTE["panel"],
        fieldbackground=PALETTE["panel"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        rowheight=26,
        font=base_font,
    )
    selected_fg = "#ffffff" if name == "light" else PALETTE["text"]
    style.map(
        "Treeview",
        background=[("selected", PALETTE["accent_dim"])],
        foreground=[("selected", selected_fg)],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        relief="flat",
        font=("Segoe UI", 10, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", PALETTE["highlight"])])

    style.configure("TSeparator", background=PALETTE["border"])
    return PALETTE


def style_listbox(listbox: tk.Listbox, palette: dict) -> None:
    selected_fg = "#ffffff" if ACTIVE_THEME == "light" else palette["text"]
    listbox.configure(
        bg=palette["panel"],
        fg=palette["text"],
        selectbackground=palette["accent_dim"],
        selectforeground=selected_fg,
        highlightbackground=palette["border"],
        highlightcolor=palette["accent"],
        font=("Segoe UI", 10),
        relief="flat",
    )


def style_option_menu(menu: object, palette: dict) -> None:
    """
    Apply palette to CustomTkinter option menus for readable light theme.
    """
    if ctk is None:
        return
    try:
        menu.configure(
            fg_color=palette["surface"],
            button_color=palette["accent"],
            button_hover_color=palette["accent_dim"],
            text_color=palette["text"],
            dropdown_fg_color=palette["surface"],
            dropdown_text_color=palette["text"],
            dropdown_hover_color=palette["highlight"],
        )
    except Exception:
        return


def style_combo_box(combo: object, palette: dict) -> None:
    """
    Apply palette to CustomTkinter combo boxes for readable light theme.
    """
    if ctk is None:
        return
    try:
        combo.configure(
            fg_color=palette["surface"],
            border_color=palette["border"],
            button_color=palette["accent"],
            button_hover_color=palette["accent_dim"],
            text_color=palette["text"],
            dropdown_fg_color=palette["surface"],
            dropdown_text_color=palette["text"],
            dropdown_hover_color=palette["highlight"],
            corner_radius=10,
            border_width=1,
        )
    except Exception:
        return
