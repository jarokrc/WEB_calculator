import tkinter as tk
import customtkinter as ctk

from web_calculator.ui.styles import icons, theme


class ActionsBar(ctk.CTkFrame):
    """
    Bottom action bar with key buttons.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_reset,
        on_save,
        on_load,
        on_pdf,
        on_help,
        on_preview,
        on_search,
        on_theme_change=None,
        theme_names=None,
        row: int = 3,
    ):
        super().__init__(master, fg_color="transparent")
        self.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=6)

        self._icon_color = theme.PALETTE["text"]
        self._accent_icon_color = "#ffffff"
        self._icons = icons.build_icons(self._icon_color)
        self._accent_icons = icons.build_icons(self._accent_icon_color)

        self.reset_btn = ctk.CTkButton(
            self,
            text="Reset vyberu",
            command=on_reset,
            image=self._icons["reset"],
            compound="left",
        )
        self.reset_btn.pack(side="left", padx=(0, 6))

        self.save_btn = ctk.CTkButton(
            self,
            text="Uloz klienta",
            command=on_save,
            fg_color=theme.PALETTE["accent"],
            hover_color=theme.PALETTE["accent_dim"],
            text_color="#ffffff",
            image=self._accent_icons["save"],
            compound="left",
        )
        self.save_btn.pack(side="left", padx=(0, 6))

        self.load_btn = ctk.CTkButton(
            self,
            text="Nacitaj klienta",
            command=on_load,
            image=self._icons["load"],
            compound="left",
        )
        self.load_btn.pack(side="left", padx=(0, 6))

        self.pdf_btn = ctk.CTkButton(
            self,
            text="Export PDF",
            command=on_pdf,
            fg_color=theme.PALETTE["accent"],
            hover_color=theme.PALETTE["accent_dim"],
            text_color="#ffffff",
            image=self._accent_icons["pdf"],
            compound="left",
        )
        self.pdf_btn.pack(side="right")

        self.search_btn = ctk.CTkButton(
            self,
            text="Vyhladat",
            command=on_search,
            image=self._icons["search"],
            compound="left",
        )
        self.search_btn.pack(side="right", padx=(0, 6))
        self.preview_btn = ctk.CTkButton(
            self,
            text="Nahlad",
            command=on_preview,
            image=self._icons["preview"],
            compound="left",
        )
        self.preview_btn.pack(side="right", padx=(0, 6))
        self.help_btn = ctk.CTkButton(
            self,
            text="Napoveda",
            command=on_help,
            image=self._icons["help"],
            compound="left",
        )
        self.help_btn.pack(side="right", padx=(0, 6))

        if on_theme_change and theme_names:
            theme_frame = ctk.CTkFrame(self, fg_color="transparent")
            theme_frame.pack(side="right", padx=(10, 0))
            ctk.CTkLabel(theme_frame, text="Tema:").pack(side="left")
            self._theme_var = tk.StringVar(value=theme_names[0])
            self._theme_menu = ctk.CTkComboBox(
                theme_frame,
                values=list(theme_names),
                variable=self._theme_var,
                command=lambda _val: on_theme_change(self._theme_var.get()),
                state="readonly",
                width=140,
            )
            self._theme_menu.pack(side="left", padx=(4, 0))
            theme.style_combo_box(self._theme_menu, theme.PALETTE)
            self._theme_menu.set(self._theme_var.get())

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.save_btn.configure(state=state)
        self.pdf_btn.configure(state=state)

    def update_theme(self, palette: dict) -> None:
        self._icon_color = palette["text"]
        self._icons = icons.build_icons(self._icon_color)
        self._accent_icons = icons.build_icons("#ffffff")
        self.reset_btn.configure(image=self._icons["reset"])
        self.load_btn.configure(image=self._icons["load"])
        self.search_btn.configure(image=self._icons["search"])
        self.preview_btn.configure(image=self._icons["preview"])
        self.help_btn.configure(image=self._icons["help"])
        self.save_btn.configure(
            image=self._accent_icons["save"],
            fg_color=palette["accent"],
            hover_color=palette["accent_dim"],
            text_color="#ffffff",
        )
        self.pdf_btn.configure(
            image=self._accent_icons["pdf"],
            fg_color=palette["accent"],
            hover_color=palette["accent_dim"],
            text_color="#ffffff",
        )
        if hasattr(self, "_theme_menu"):
            theme.style_combo_box(self._theme_menu, palette)
