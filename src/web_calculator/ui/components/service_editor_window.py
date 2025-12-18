import tkinter as tk
import customtkinter as ctk
from typing import Callable, Iterable

from web_calculator.core.models.service import Service
from web_calculator.ui.components.service_table import ServiceTable


class ServiceEditorWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master: tk.Misc,
        section_id: str,
        title: str,
        services: Iterable[Service],
        selected: set[str],
        quantities: dict[str, float],
        on_toggle,
        on_edit_qty,
        on_edit_price,
        on_edit_details,
        price_provider,
        on_close: Callable[[str], None],
    ):
        super().__init__(master)
        self._section_id = section_id
        self._on_close = on_close

        self.title(title)
        self.transient(master)
        self.geometry("980x640")
        self.minsize(780, 520)

        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Zavriet", command=self._handle_close).pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        # In this window, double-click on a row opens the full editor (name/info/prices).
        self._table = ServiceTable(
            body,
            table_id=section_id,
            title=title,
            on_toggle=on_toggle,
            on_sort=lambda _field: None,
            on_filter=lambda _field: None,
            on_info=on_edit_details,
            on_expand=lambda _name: None,
            on_edit_price=on_edit_price,
            on_edit_qty=on_edit_qty,
            price_provider=price_provider,
        )
        self._table.grid(row=0, column=0, sticky="nsew")
        self.refresh(services, selected, quantities)

    def refresh(self, services: Iterable[Service], selected: set[str], quantities: dict[str, float]) -> None:
        self._table.set_services(services, selected, quantities)
        self._table.focus_tree()

    def _handle_close(self) -> None:
        self._on_close(self._section_id)
        self.destroy()
