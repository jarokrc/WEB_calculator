import tkinter as tk
from tkinter import ttk


def apply_theme(root: tk.Misc) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Treeview", rowheight=24)
    style.configure("TFrame", background="#f5f6fa")
    style.configure("TLabel", background="#f5f6fa")
