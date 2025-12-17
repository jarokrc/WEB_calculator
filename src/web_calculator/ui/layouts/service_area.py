import tkinter as tk
from tkinter import ttk
from typing import List, Set

from web_calculator.core.models.service import Service
from web_calculator.ui.components.service_table import ServiceTable


class ServiceArea(ttk.Frame):
    """
    Prava sekcia s tabulkami sluzieb (PRIMARY/ESHOP/WEB).
    Klik na nazov tabulky otvori samostatne okno s editorom sluzieb.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_toggle,
        on_sort,
        on_filter,
        on_info,
        on_edit_price,
        on_edit_qty,
        on_open_section,
        on_reset_filters,
        price_provider,
        row_minsize: int = 220,
    ):
        super().__init__(master, padding=4)
        self.grid(row=0, column=1, sticky="nsew")
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1, uniform="tables", minsize=row_minsize)
        self.rowconfigure(2, weight=1, uniform="tables", minsize=row_minsize)
        self.rowconfigure(3, weight=1, uniform="tables", minsize=row_minsize)
        self.columnconfigure(0, weight=1)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(controls, text="Reset filtrov", command=on_reset_filters).pack(side="right")

        self.primary_table = ServiceTable(
            self,
            "primary",
            "Primarne doplnky",
            on_toggle,
            on_sort,
            on_filter,
            on_info,
            on_expand=on_open_section,
            on_edit_price=on_edit_price,
            on_edit_qty=lambda svc: on_edit_qty("primary", svc),
            price_provider=price_provider,
        )
        self.primary_table.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        self.eshop_table = ServiceTable(
            self,
            "eshop",
            "E-shop doplnky",
            on_toggle,
            on_sort,
            on_filter,
            on_info,
            on_expand=on_open_section,
            on_edit_price=on_edit_price,
            on_edit_qty=lambda svc: on_edit_qty("eshop", svc),
            price_provider=price_provider,
        )
        self.eshop_table.grid(row=2, column=0, sticky="nsew", pady=(4, 0))

        self.backend_table = ServiceTable(
            self,
            "backend",
            "Backend / bezpecnost",
            on_toggle,
            on_sort,
            on_filter,
            on_info,
            on_expand=on_open_section,
            on_edit_price=on_edit_price,
            on_edit_qty=lambda svc: on_edit_qty("backend", svc),
            price_provider=price_provider,
        )
        self.backend_table.grid(row=3, column=0, sticky="nsew", pady=(4, 0))

    def set_services(
        self,
        primary: List[Service],
        eshop: List[Service],
        backend: List[Service],
        selected: Set[str],
        quantities: dict[str, float],
    ) -> None:
        self.primary_table.set_services(primary, selected, quantities)
        self.eshop_table.set_services(eshop, selected, quantities)
        self.backend_table.set_services(backend, selected, quantities)

    def refresh_selection(self, selected: Set[str], quantities: dict[str, float]) -> None:
        self.primary_table.refresh_selection(selected, quantities)
        self.eshop_table.refresh_selection(selected, quantities)
        self.backend_table.refresh_selection(selected, quantities)
