import tkinter as tk
import customtkinter as ctk


class FilterControls(ctk.CTkFrame):
    """
    Horný panel s tlačidlom reset filtrov a späť.
    """

    def __init__(self, master: tk.Misc, on_reset_filters, on_back):
        super().__init__(master, fg_color="transparent")
        self.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.back_btn = ctk.CTkButton(self, text="Spat", command=on_back)
        self.back_btn.pack(side="left")
        self.reset_btn = ctk.CTkButton(self, text="Reset filtrov", command=on_reset_filters)
        self.reset_btn.pack(side="right", padx=(4, 0))

    def set_back_enabled(self, enabled: bool) -> None:
        self.back_btn.configure(state="normal" if enabled else "disabled")
