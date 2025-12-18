import tkinter as tk
import customtkinter as ctk

from web_calculator.ui.layouts.client_form import ClientForm
from web_calculator.ui.styles import theme


class ClientDialog(ctk.CTkToplevel):
    def __init__(self, master: tk.Misc, data: dict, on_save):
        super().__init__(master)
        self.title("Klient")
        self.transient(master)
        self.grab_set()
        self.geometry("520x460")
        self.minsize(480, 400)
        self._on_save = on_save

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)

        self._form = ClientForm(body, on_change=lambda: None, row=None, use_grid=False)
        self._form.pack(fill="both", expand=True)
        self._form.set_data(data or {})
        self._form.update_theme(theme.PALETTE)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(btns, text="Zrusit", command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            btns,
            text="Ulozit",
            command=self._handle_save,
            fg_color=theme.PALETTE["accent"],
            hover_color=theme.PALETTE["accent_dim"],
            text_color="#ffffff",
        ).pack(side="right")

    def _handle_save(self) -> None:
        self._on_save(self._form.data())
        self.destroy()
