import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Set

from web_calculator.core.models.service import Service
from web_calculator.ui.components.service_table import ServiceTable


class ServiceArea(ttk.Frame):
    """
    Pravá sekcia s tabuľkami služieb, vrátane expand/collapse logiky.
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

        self._row_minsize = row_minsize
        self._expanded: str | None = None

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.back_btn = ttk.Button(controls, text="Spat", command=self.collapse)
        self.back_btn.pack(side="left")
        self.back_btn.state(["disabled"])
        self.reset_filters_btn = ttk.Button(controls, text="Reset filtrov")
        self.reset_filters_btn.pack(side="right", padx=(4, 0))

        self.primary_table = ServiceTable(
            self,
            "primary",
            "Primarne doplnky",
            on_toggle,
            on_sort,
            on_filter,
            on_info,
            on_expand=self._expand_table,
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
            on_expand=self._expand_table,
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
            on_expand=self._expand_table,
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
        self._apply_expand_layout()

    def refresh_selection(self, selected: Set[str], quantities: dict[str, float]) -> None:
        self.primary_table.refresh_selection(selected, quantities)
        self.eshop_table.refresh_selection(selected, quantities)
        self.backend_table.refresh_selection(selected, quantities)

    def _expand_table(self, name: str) -> None:
        self._expanded = name
        self._apply_expand_layout()

    def collapse(self) -> None:
        self._expanded = None
        self._apply_expand_layout()

    def _apply_expand_layout(self) -> None:
        tables: Dict[str, ttk.Frame] = {
            "primary": self.primary_table,
            "eshop": self.eshop_table,
            "backend": self.backend_table,
        }
        for table in tables.values():
            table.grid_remove()
        if self._expanded:
            table = tables.get(self._expanded)
            if table:
                table.grid(row=1, column=0, rowspan=3, sticky="nsew")
            self.back_btn.state(["!disabled"])
            self.rowconfigure(1, minsize=self._row_minsize * 3, weight=1, uniform="tables")
            self.rowconfigure(2, minsize=0, weight=0)
            self.rowconfigure(3, minsize=0, weight=0)
        else:
            self.primary_table.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
            self.eshop_table.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
            self.backend_table.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
            self.back_btn.state(["disabled"])
            self.rowconfigure(1, minsize=self._row_minsize, weight=1, uniform="tables")
            self.rowconfigure(2, minsize=self._row_minsize, weight=1, uniform="tables")
            self.rowconfigure(3, minsize=self._row_minsize, weight=1, uniform="tables")
