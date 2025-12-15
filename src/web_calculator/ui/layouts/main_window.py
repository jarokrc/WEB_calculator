import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import List, Set

from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service
from web_calculator.core.services.catalog import Catalog, save_catalog, save_packages
from web_calculator.ui.layouts.service_area import ServiceArea
from web_calculator.ui.layouts.client_form import ClientForm
from web_calculator.ui.layouts.actions_bar import ActionsBar
from web_calculator.ui.components.package_selector import PackageSelector
from web_calculator.ui.components.summary_panel import SummaryPanel
from web_calculator.ui.styles.theme import apply_theme
from web_calculator.ui.controllers.actions_controller import ActionsController
from web_calculator.ui.controllers.service_controller import ServiceController


class MainWindow(tk.Tk):
    def __init__(self, catalog: Catalog):
        super().__init__()
        apply_theme(self)
        self.title("WEB kalkulacka")
        self.geometry("1024x780")
        self.minsize(900, 650)
        self._catalog = catalog
        self._pricing = PricingEngine()
        self._selected_services: Set[str] = set()
        self._service_qty: dict[str, int] = {s.code: 1 for s in catalog.services}
        self._filter_tags: Set[str] = set()
        self._sort_field: str | None = None
        self._sort_dir: str = "asc"
        self._current_package: Package | None = None
        self._current_package_raw: Package | None = None
        self._price_mode: str = "base"
        self._discount_pct: float = 0.0
        self._base_prices: dict[str, tuple[float, float]] = {s.code: (s.price, s.price2) for s in catalog.services}
        self._auto_selected: Set[str] = set()
        self._hidden_service_codes: Set[str] = {"ESHOP-E-SHOP-MODUL-ZAKLAD"}

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._services = ServiceController(self)
        self._actions = ActionsController(self)
        self.package_selector = PackageSelector(
            self,
            self._catalog.packages,
            self._services.on_package_select,
            on_price_mode_change=self._services.on_price_mode_change,
            on_edit_package=self._open_package_edit_dialog,
        )
        self.package_selector.grid(row=0, column=0, sticky="nsw")

        self.service_area = ServiceArea(
            self,
            self._services.on_service_toggle,
            self._services.on_sort,
            self._services.on_filter_header,
            self._services.show_service_info,
            self._services.edit_service_price,
            self._services.edit_service_qty,
            price_provider=self._services.effective_price,
        )

        self.summary = SummaryPanel(self, self._pricing, on_discount_change=self._services.set_discount)
        self.summary.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.client_form = ClientForm(self, on_change=self._update_save_buttons, row=2)

        self.actions = ActionsBar(
            self,
            on_reset=self._actions.reset_selection,
            on_save=self._actions.save_client,
            on_load=self._actions.load_client,
            on_pdf=self._actions.export_pdf,
            on_help=self._services.show_help,
            on_preview=self._services.show_preview,
            on_search=self._open_search,
        )

        # Default to "no package" so doplnky mozno pouzit samostatne.
        self.package_selector.select_none()
        self._update_save_buttons()

    def _open_package_edit_dialog(self, package: Package) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(f"Upravit sluzby balika {package.code}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("720x520")
        dialog.minsize(600, 400)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Balik {package.code}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Vyber sluzby, ktore maju byt automaticky zahrnute v baliku.").pack(anchor="w", pady=(0, 6))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, activestyle="dotbox")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        service_rows = [
            (svc.code, svc.label, svc.tag, svc.bundle)
            for svc in self._catalog.services
        ]
        for idx, (code, label, tag, bundle) in enumerate(service_rows):
            tag_txt = f" [{tag}]" if tag else ""
            bundle_txt = f" (bundle: {bundle})" if bundle and bundle != "NONE" else ""
            listbox.insert(tk.END, f"{code} - {label}{tag_txt}{bundle_txt}")
            if code in (package.included_services or []):
                listbox.selection_set(idx)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))

        def save_and_close() -> None:
            prev_included = set(package.included_services or [])
            sel_indices = listbox.curselection()
            selected_codes = [service_rows[i][0] for i in sel_indices]
            package.included_services = selected_codes
            # Update bundle flag on services: added -> set bundle to package; removed -> NONE if previously linked.
            for svc in self._catalog.services:
                if svc.code in selected_codes:
                    svc.bundle = package.code
                elif (svc.bundle or "").upper() == (package.code or "").upper():
                    svc.bundle = "NONE"
            # Keep included quantities in sync: remove dropped codes, ensure new ones at least 1.
            qty_map = dict(package.included_quantities or {})
            for code in list(qty_map.keys()):
                if code not in selected_codes:
                    qty_map.pop(code, None)
            for code in selected_codes:
                qty_map.setdefault(code, 1)
            package.included_quantities = qty_map
            # Persist both split packages.json and combined catalog.json for konzistentnost.
            save_packages(self._catalog)
            save_catalog(self._catalog)
            if self._current_package_raw and self._current_package_raw.code == package.code:
                self._services.set_package(self._current_package_raw)
                self.service_area.refresh_selection(self._selected_services, self._service_qty)
            dialog.destroy()

        ttk.Button(buttons, text="Zrusit", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Ulozit", command=save_and_close).pack(side="right")



    # -------- Client & actions --------
    def _update_save_buttons(self) -> None:
        if hasattr(self, "_actions"):
            self._actions.update_save_buttons()

    def _open_search(self) -> None:
        self._services.open_search()
