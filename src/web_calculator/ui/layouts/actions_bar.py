import tkinter as tk
from tkinter import ttk


class ActionsBar(ttk.Frame):
    """
    Spodná lišta s akčnými tlačidlami.
    """

    def __init__(self, master: tk.Misc, on_reset, on_save, on_load, on_pdf, on_help, on_preview, on_search):
        super().__init__(master, padding=8)
        self.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Button(self, text="Reset vyberu", command=on_reset).pack(side="left", padx=(0, 6))
        self.save_btn = ttk.Button(self, text="Uloz klienta", command=on_save)
        self.save_btn.pack(side="left", padx=(0, 6))
        ttk.Button(self, text="Nacitaj klienta", command=on_load).pack(side="left", padx=(0, 6))
        self.pdf_btn = ttk.Button(self, text="Export PDF", command=on_pdf)
        self.pdf_btn.pack(side="right")
        ttk.Button(self, text="Vyhladat", command=on_search).pack(side="right", padx=(0, 6))
        ttk.Button(self, text="Nahľad", command=on_preview).pack(side="right", padx=(0, 6))
        ttk.Button(self, text="Nápoveda", command=on_help).pack(side="right", padx=(0, 6))

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.save_btn.state(["!disabled"])
            self.pdf_btn.state(["!disabled"])
        else:
            self.save_btn.state(["disabled"])
            self.pdf_btn.state(["disabled"])
