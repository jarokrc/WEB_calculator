import tkinter as tk
from tkinter import ttk


class ActionsBar(ttk.Frame):
    """
    Bottom action bar with key buttons.
    """

    def __init__(self, master: tk.Misc, on_reset, on_save, on_load, on_pdf, on_help, on_preview, on_search, on_theme_change=None, theme_names=None):
        super().__init__(master, padding=8)
        self.grid(row=3, column=0, columnspan=2, sticky="ew")

        ttk.Button(self, text="Reset vyberu", command=on_reset).pack(side="left", padx=(0, 6))

        self.save_btn = ttk.Button(self, text="Uloz klienta", command=on_save, style="Accent.TButton")
        self.save_btn.pack(side="left", padx=(0, 6))

        ttk.Button(self, text="Nacitaj klienta", command=on_load).pack(side="left", padx=(0, 6))

        self.pdf_btn = ttk.Button(self, text="Export PDF", command=on_pdf, style="Accent.TButton")
        self.pdf_btn.pack(side="right")

        ttk.Button(self, text="Vyhladat", command=on_search).pack(side="right", padx=(0, 6))
        ttk.Button(self, text="Nahlad", command=on_preview).pack(side="right", padx=(0, 6))
        ttk.Button(self, text="Napoveda", command=on_help).pack(side="right", padx=(0, 6))

        if on_theme_change and theme_names:
            theme_frame = ttk.Frame(self)
            theme_frame.pack(side="right", padx=(10, 0))
            ttk.Label(theme_frame, text="Tema:").pack(side="left")
            self._theme_var = tk.StringVar(value=theme_names[0])
            combo = ttk.Combobox(theme_frame, state="readonly", width=12, values=theme_names, textvariable=self._theme_var)
            combo.pack(side="left", padx=(4, 0))
            combo.bind("<<ComboboxSelected>>", lambda _e: on_theme_change(self._theme_var.get()))

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.save_btn.state(["!disabled"])
            self.pdf_btn.state(["!disabled"])
        else:
            self.save_btn.state(["disabled"])
            self.pdf_btn.state(["disabled"])
