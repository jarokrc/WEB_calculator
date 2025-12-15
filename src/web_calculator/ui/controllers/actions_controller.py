from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox

from web_calculator.core.services.invoice import build_invoice_payload
from web_calculator.core.services.catalog import save_packages, save_catalog
from web_calculator.utils.pdf import export_simple_pdf


class ActionsController:
    """
    Obsluhuje akcie ulozit/nacitat klienta, export PDF a reset stavu.
    Drzi referenciu na hlavne okno, aby nemusel duplicovat stav.
    """

    def __init__(self, window) -> None:
        self.w = window

    # --- UI helpers ---
    def update_save_buttons(self) -> None:
        if not hasattr(self.w, "client_form") or not hasattr(self.w, "actions"):
            return
        has_data = self.w.client_form.has_data()
        self.w.actions.set_enabled(has_data)

    # --- Actions ---
    def save_client(self) -> None:
        client = self.w.client_form.data()
        if not self.w.client_form.has_data():
            messagebox.showwarning("Ulozit klienta", "Vypln aspon jeden udaj o klientovi alebo firme.")
            return
        path = filedialog.asksaveasfile(
            mode="w",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            title="Uloz klienta",
        )
        if not path:
            return
        data = {
            "package": self.w._current_package.code if self.w._current_package else None,
            "services": list(self.w._selected_services),
            "quantities": self.w._service_qty,
            "client": client,
            "discount_pct": self.w._discount_pct,
        }
        path.write(json.dumps(data, ensure_ascii=False, indent=2))
        path.close()

    def load_client(self) -> None:
        path = filedialog.askopenfile(
            mode="r",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            title="Nacitaj klienta",
        )
        if not path:
            return
        try:
            data = json.load(path)
        finally:
            path.close()
        pkg_code = data.get("package")
        self.w.package_selector.select_package(pkg_code)
        self.w._selected_services = set(data.get("services", []))
        self.w._service_qty = data.get("quantities", {code: 1 for code in self.w._selected_services})
        self.w._discount_pct = float(data.get("discount_pct", 0.0) or 0.0)
        self.w.client_form.set_data(data.get("client", {}))
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.w._services.update_summary()
        self.update_save_buttons()

    def export_pdf(self) -> None:
        if not self.w.client_form.has_data():
            messagebox.showwarning("Export PDF", "Vypln aspon jeden udaj o klientovi alebo firme.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
            title="Export do PDF",
        )
        if not path:
            return

        selections = [
            (self.w._services.with_effective_price(s), self.w._service_qty.get(s.code, 1))
            for s in self.w._catalog.services
            if s.code in self.w._selected_services
        ]
        payload = build_invoice_payload(
            self.w._current_package,
            selections,
            self.w.client_form.data(),
            self.w._pricing,
            discount_pct=self.w._discount_pct,
        )
        export_simple_pdf(Path(path), payload)

    def reset_selection(self) -> None:
        self.w._selected_services.clear()
        self.w._current_package = None
        self.w._current_package_raw = None
        self.w._service_qty = {s.code: 1 for s in self.w._catalog.services}
        self.w.client_form.reset()
        self.w._discount_pct = 0.0
        self.w.package_selector.select_none()
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.w._update_summary()
        self.update_save_buttons()
