from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, simpledialog
from typing import Iterable, Set

from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service
from web_calculator.core.services.catalog import save_catalog, save_packages
from web_calculator.core.services.invoice import build_invoice_payload
from web_calculator.ui.components.preview_dialog import PreviewDialog
from web_calculator.ui.components.search_dialog import SearchDialog


class ServiceController:
    """
    Riadi logiku balikov a sluzieb: vyber balika, ceny, filtre, zahrnute sluzby.
    """

    def __init__(self, window) -> None:
        self.w = window

    # -------- Package handling --------
    def on_package_select(self, package: Package | None) -> None:
        self.set_package(package)

    def on_price_mode_change(self, mode: str) -> None:
        self.w._price_mode = mode
        if self.w._current_package_raw:
            self.set_package(self.w._current_package_raw)

    def set_package(self, package: Package | None) -> None:
        self.w._current_package_raw = package
        effective = self._package_with_price(package)
        self.w._pricing.update_package(effective)
        self.w._current_package = effective
        self.apply_included_services(effective)
        self.refresh_service_tables(effective)
        self.update_summary()

    def _package_with_price(self, package: Package | None) -> Package | None:
        if not package:
            return None
        price = package.base_price
        if self.w._price_mode == "promo" and package.promo_price is not None:
            price = package.promo_price
        elif self.w._price_mode == "intra" and package.intra_price is not None:
            price = package.intra_price
        return replace(package, base_price=price)

    # -------- Service handling --------
    def refresh_service_tables(self, package: Package | None) -> None:
        all_services: list[Service] = [
            s for s in self.w._catalog.services if self._matches_filters(s) and s.code not in self.w._hidden_service_codes
        ]
        primary = [s for s in all_services if (s.source or "").upper() == "PRIMARY"]
        eshop = [s for s in all_services if (s.source or "").upper().startswith("ESHOP")]
        backend = [s for s in all_services if (s.source or "").upper() == "WEB"]

        primary_sorted = self._apply_sort(primary)
        eshop_sorted = self._apply_sort(eshop)
        backend_sorted = self._apply_sort(backend)

        self.w.service_area.set_services(
            primary_sorted, eshop_sorted, backend_sorted, self.w._selected_services, self.w._service_qty
        )
        self.w.service_area._apply_expand_layout()

    def on_service_toggle(self, service: Service, selected: bool) -> None:
        if selected:
            self.w._selected_services.add(service.code)
            self.w._service_qty.setdefault(service.code, 1)
        else:
            self.w._selected_services.discard(service.code)
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.update_summary()

    def on_filter_header(self, field: str) -> None:
        tags = {s.tag for s in self.w._catalog.services if s.tag}
        from web_calculator.ui.components.filter_dialog import FilterDialog

        FilterDialog(
            self.w.service_area,
            tags=tags,
            sources=set(),
            selected_tags=self.w._filter_tags,
            selected_sources=set(),
            on_apply=self.on_filter_change,
        )

    def on_filter_change(self, tags: Set[str], sources: Set[str]) -> None:
        self.w._filter_tags = tags
        self.refresh_service_tables(self.w._current_package)

    def reset_filters(self) -> None:
        self.w._filter_tags.clear()
        self.w._sort_field = None
        self.w._sort_dir = "asc"
        self.refresh_service_tables(self.w._current_package)

    def on_sort(self, field: str) -> None:
        if self.w._sort_field == field:
            self.w._sort_dir = "desc" if self.w._sort_dir == "asc" else "asc"
        else:
            self.w._sort_field = field
            self.w._sort_dir = "asc"
        self.refresh_service_tables(self.w._current_package)

    def _apply_sort(self, services: list[Service]) -> list[Service]:
        if not self.w._sort_field:
            return services
        reverse = self.w._sort_dir == "desc"
        if self.w._sort_field == "price":
            return sorted(services, key=lambda s: s.price, reverse=reverse)
        if self.w._sort_field == "label":
            return sorted(services, key=lambda s: (s.label or "").lower(), reverse=reverse)
        return services

    def edit_service_price(self, service: Service) -> None:
        value = simpledialog.askstring(
            "Upravit cenu",
            f"Nova cena pre:\n{service.label}",
            initialvalue=f"{service.price:.2f}",
            parent=self.w,
        )
        if value is None:
            return
        try:
            price = float(value.replace(",", "."))
        except ValueError:
            messagebox.showerror("Chyba", "Zadaj platne cislo.")
            return
        service.price = price
        _, alt = self.w._base_prices.get(service.code, (price, service.price2))
        self.w._base_prices[service.code] = (price, alt)
        save_catalog(self.w._catalog)
        self.refresh_service_tables(self.w._current_package)
        self.update_summary()

    def edit_service_qty(self, _section: str, service: Service) -> None:
        current = self.w._service_qty.get(service.code, 1)
        value = simpledialog.askstring(
            "Upravit mnozstvo",
            f"Nova hodnota pre:\n{service.label}",
            initialvalue=str(current),
            parent=self.w,
        )
        if value is None:
            return
        try:
            qty = int(value.strip())
        except ValueError:
            messagebox.showerror("Chyba", "Zadaj cele cislo.")
            return
        if qty <= 0:
            messagebox.showerror("Chyba", "Mnozstvo musi byt vacsie ako 0.")
            return
        self.w._service_qty[service.code] = qty
        self.w._selected_services.add(service.code)
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.update_summary()

    def show_service_info(self, service: Service) -> None:
        info = service.info or "(bez popisu)"
        messagebox.showinfo("Info sluzby", f"{service.label}\n\n{info}")

    def show_selected_service_info(self) -> None:
        selected = list(self.w._selected_services)
        if not selected:
            messagebox.showinfo("Info sluzby", "Nie je zvolena ziadna sluzba.")
            return
        code = selected[0]
        svc = next((s for s in self.w._catalog.services if s.code == code), None)
        if svc:
            self.show_service_info(svc)

    def show_preview(self) -> None:
        services = [
            (self.with_effective_price(s), self.w._service_qty.get(s.code, 1))
            for s in self.w._catalog.services
            if s.code in self.w._selected_services
        ]
        if not services and not self.w._current_package:
            messagebox.showinfo("Nahlad", "Vyber aspon balicek alebo jednu sluzbu.")
            return
        client = self.w.client_form.data()
        breakdown = self.w._pricing.summarize(services)
        PreviewDialog(self.w, self.w._current_package, services, breakdown, self.w._discount_pct, self.w._pricing)

    def open_search(self) -> None:
        SearchDialog(self.w, self.w._catalog.services, self.select_service_by_code)

    def select_service_by_code(self, code: str) -> None:
        svc = next((s for s in self.w._catalog.services if s.code == code), None)
        if not svc:
            return
        self.w._selected_services.add(code)
        self.w._service_qty.setdefault(code, 1)
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.update_summary()

    # -------- Pricing helpers --------
    def update_summary(self) -> None:
        services = [
            (self.with_effective_price(s), self.w._service_qty.get(s.code, 1))
            for s in self.w._catalog.services
            if s.code in self.w._selected_services
        ]
        breakdown = self.w._pricing.summarize(services)
        self.w.summary.update_values(breakdown, self.w._discount_pct)

    def set_discount(self, value: float) -> None:
        self.w._discount_pct = min(100.0, max(0.0, value))
        self.update_summary()

    def with_effective_price(self, service: Service) -> Service:
        price = self.effective_price(service)
        return replace(service, price=price)

    def effective_price(self, service: Service) -> float:
        base_price, alt_price = self.w._base_prices.get(service.code, (service.price, service.price2))
        qty = self.w._service_qty.get(service.code, 1)
        if not self.w._current_package:
            return base_price

        pkg_code = (self.w._current_package.code or "").upper()
        included_set = self.included_services_for(self.w._current_package)
        included_qty = self._included_qty_map().get(service.code, 0)
        if included_qty > 0 and qty > 0 and service.code in included_set:
            paid_qty = max(0, qty - included_qty)
            total_cost = paid_qty * base_price
            return total_cost / qty if qty > 0 else base_price

        bundle_match = (service.bundle or "NONE").upper()
        if bundle_match != "NONE" and pkg_code.startswith(bundle_match) and service.code in included_set:
            return alt_price if alt_price is not None else 0.0

        if pkg_code.startswith("ESHOP-P"):
            included_set |= set(self.w._eshop_advanced_included)
        elif pkg_code.startswith("ESHOP-Z"):
            included_set |= set(self.w._eshop_basic_included)
        if service.code in included_set:
            return 0.0
        return base_price

    def _matches_filters(self, service: Service) -> bool:
        if self.w._filter_tags and (service.tag or "") not in self.w._filter_tags:
            return False
        return True

    def included_services_for(self, package: Package | None) -> Set[str]:
        if not package:
            return set()
        code = (package.code or "").upper()
        return set(package.included_services or [])

    def apply_included_services(self, package: Package | None) -> None:
        included = self.included_services_for(package)
        for code in list(self.w._auto_selected):
            self.w._selected_services.discard(code)
        self.w._auto_selected.clear()

        if not included:
            return
        qty_map = self._included_qty_map()
        for code in included:
            self.w._selected_services.add(code)
            min_qty = qty_map.get(code, 1)
            current = self.w._service_qty.get(code, 0)
            self.w._service_qty[code] = max(current, min_qty)
        self.w._auto_selected = set(included)

    def _included_qty_map(self) -> dict[str, int]:
        if not self.w._current_package:
            return {}
        return self.w._current_package.included_quantities or {}

    def show_help(self) -> None:
        messagebox.showinfo(
            "Nápoveda",
            "Dvojklik na službu zobrazí detail.\nDvojklik na množstvo/cenu umožní úpravu.\nFiltrovanie a triedenie je dostupné v hlavičkách tabuliek.",
        )

    def export_state(self, path: Path) -> None:
        """
        Helper na ulozenie stavu sluzieb (na debug). Nepouzite v UI.
        """
        payload = {
            "selected_services": list(self.w._selected_services),
            "quantities": self.w._service_qty,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
