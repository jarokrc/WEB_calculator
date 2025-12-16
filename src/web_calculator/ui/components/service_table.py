import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, List, Set

from web_calculator.core.models.service import Service


class ServiceTable(ttk.Frame):
    """
    Multi-select table with checkbox-like toggles for services.
    Podporuje triedenie, filter, zobrazenie info a editaciu ceny/mnozstva na dvojklik.
    """

    def __init__(
        self,
        master: tk.Misc,
        table_id: str,
        title: str,
        on_toggle: Callable[[Service, bool], None],
        on_sort: Callable[[str], None],
        on_filter: Callable[[str], None],
        on_info: Callable[[Service], None],
        on_expand: Callable[[str], None],
        on_edit_price: Callable[[Service], None],
        on_edit_qty: Callable[[Service], None],
        price_provider: Callable[[Service], float] | None = None,
    ):
        super().__init__(master, padding=8)
        self._services: List[Service] = []
        self._selected: Set[str] = set()
        self._quantities: dict[str, float] = {}
        self._table_id = table_id
        self._on_toggle = on_toggle
        self._on_sort = on_sort
        self._on_filter = on_filter
        self._on_info = on_info
        self._on_edit_price = on_edit_price
        self._on_expand = on_expand
        self._on_edit_qty = on_edit_qty
        self._price_provider = price_provider or (lambda svc: svc.price)

        header = ttk.Label(self, text=title, font=("Segoe UI", 10, "bold"), cursor="hand2")
        header.pack(anchor="w")
        header.bind("<Button-1>", lambda _e: self._on_expand(self._table_id))

        columns = ("check", "label", "qty", "price", "total", "tag")
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, pady=(4, 0))
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="none", height=12)
        tree.heading("check", text="[ ]")
        tree.heading("label", text="Sluzba", command=lambda: self._on_sort("label"))
        tree.heading("qty", text="Mnoz.")
        tree.heading("price", text="Cena", command=lambda: self._on_sort("price"))
        tree.heading("total", text="Spolu")
        tree.heading("tag", text="Tag", command=lambda: self._on_filter("tag"))
        tree.column("check", width=36, anchor="center")
        tree.column("label", width=320)
        tree.column("qty", width=60, anchor="center")
        tree.column("price", width=90, anchor="e")
        tree.column("total", width=100, anchor="e")
        tree.column("tag", width=90, anchor="center")
        tree.tag_configure("selected", background="#0e2235")
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        self._tree = tree

        tree.bind("<ButtonRelease-1>", self._on_click)
        tree.bind("<Double-1>", self._on_double_click)

    def set_services(self, services: Iterable[Service], selected: Set[str], quantities: dict[str, float]) -> None:
        self._services = list(services)
        self._selected = set(selected)
        self._quantities = dict(quantities)
        for row in self._tree.get_children():
            self._tree.delete(row)
        for svc in self._services:
            icon = "[x]" if svc.code in self._selected else "[ ]"
            tags = ("selected",) if svc.code in self._selected else ()
            qty = self._quantities.get(svc.code, 1.0)
            price = self._price_provider(svc)
            total = price * qty if svc.code in self._selected else None
            self._tree.insert(
                "",
                tk.END,
                iid=svc.code,
                values=(
                    icon,
                    svc.label,
                    self._format_qty(qty),
                    f"{price:.2f} EUR",
                    f"{total:.2f} EUR" if total is not None else "",
                    svc.tag,
                ),
                tags=tags,
            )

    def refresh_selection(self, selected: Set[str], quantities: dict[str, float]) -> None:
        self._selected = set(selected)
        self._quantities = dict(quantities)
        for svc in self._services:
            if not self._tree.exists(svc.code):
                continue
            icon = "[x]" if svc.code in selected else "[ ]"
            values = list(self._tree.item(svc.code, "values"))
            values[0] = icon
            qty = self._quantities.get(svc.code, 1.0)
            values[2] = self._format_qty(qty)
            price = self._price_provider(svc)
            values[3] = f"{price:.2f} EUR"
            total = price * qty if svc.code in selected else None
            values[4] = f"{total:.2f} EUR" if total is not None else ""
            tags = ("selected",) if svc.code in selected else ()
            self._tree.item(svc.code, values=values, tags=tags)

    def _on_click(self, event: tk.Event) -> None:
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        svc = next((s for s in self._services if s.code == row_id), None)
        if not svc:
            return
        selected = row_id not in self._selected
        if selected:
            self._selected.add(row_id)
        else:
            self._selected.discard(row_id)
        self.refresh_selection(self._selected, self._quantities)
        self._on_toggle(svc, selected)

    def _on_double_click(self, event: tk.Event) -> None:
        row_id = self._tree.identify_row(event.y)
        column = self._tree.identify_column(event.x)
        svc = next((s for s in self._services if s.code == row_id), None)
        if not svc:
            return
        if column == "#3":  # qty column
            self._on_edit_qty(svc)
        elif column == "#4":  # price column
            self._on_edit_price(svc)
        else:
            self._on_info(svc)

    @staticmethod
    def _format_qty(qty: float) -> str:
        return f"{int(qty)}" if float(qty).is_integer() else f"{qty:.2f}"
