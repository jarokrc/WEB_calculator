from __future__ import annotations

import json
import tkinter as tk
import customtkinter as ctk
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, simpledialog
from typing import Iterable, Set

from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service
from web_calculator.core.services.catalog import save_catalog, save_packages
from web_calculator.core.services.invoice import build_invoice_payload
from web_calculator.ui.components.service_editor_window import ServiceEditorWindow
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
        self._refresh_service_editor_windows()

    def on_service_toggle(self, service: Service, selected: bool) -> None:
        if selected:
            self.w._selected_services.add(service.code)
            self.w._service_qty.setdefault(service.code, 1)
        else:
            self.w._selected_services.discard(service.code)
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self._refresh_service_editor_windows()
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
        self._refresh_service_editor_windows()

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
        self._refresh_service_editor_windows()
        self.update_summary()

    def show_service_info(self, service: Service) -> None:
        info = service.info or "(bez popisu)"
        messagebox.showinfo("Info sluzby", f"{service.label}\n\n{info}")

    # -------- Service editor window --------
    def open_section_window(self, section_id: str) -> None:
        existing = getattr(self.w, "_service_editor_windows", {}).get(section_id)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        title_map = {
            "primary": "Primarne doplnky",
            "eshop": "E-shop doplnky",
            "backend": "Backend / bezpecnost",
        }
        title = title_map.get(section_id, f"Sluzby: {section_id}")

        def on_close(sec: str) -> None:
            try:
                self.w._service_editor_windows.pop(sec, None)
            except Exception:
                pass

        win = ServiceEditorWindow(
            self.w,
            section_id=section_id,
            title=title,
            services=self._services_for_section(section_id),
            selected=set(self.w._selected_services),
            quantities=dict(self.w._service_qty),
            on_toggle=self.on_service_toggle,
            on_edit_qty=lambda svc: self.edit_service_qty(section_id, svc),
            on_edit_price=self.edit_service_price,
            on_edit_details=self.edit_service_details,
            price_provider=self.effective_price,
            on_close=on_close,
        )
        self.w._service_editor_windows[section_id] = win

    def _refresh_service_editor_windows(self) -> None:
        windows = getattr(self.w, "_service_editor_windows", {})
        for section_id, win in list(windows.items()):
            try:
                if not win.winfo_exists():
                    windows.pop(section_id, None)
                    continue
                refresh = getattr(win, "refresh", None)
                if callable(refresh):
                    refresh(self._services_for_section(section_id), set(self.w._selected_services), dict(self.w._service_qty))
            except Exception:
                continue

    def _services_for_section(self, section_id: str) -> list[Service]:
        all_services: list[Service] = [
            s for s in self.w._catalog.services if self._matches_filters(s) and s.code not in self.w._hidden_service_codes
        ]
        if section_id == "primary":
            services = [s for s in all_services if (s.source or "").upper() == "PRIMARY"]
        elif section_id == "eshop":
            services = [s for s in all_services if (s.source or "").upper().startswith("ESHOP")]
        elif section_id == "backend":
            services = [s for s in all_services if (s.source or "").upper() == "WEB"]
        else:
            services = all_services
        return self._apply_sort(services)

    def edit_service_details(self, service: Service) -> None:
        dialog = ctk.CTkToplevel(self.w)
        dialog.title("Upravit sluzbu")
        dialog.transient(self.w)
        dialog.grab_set()
        dialog.geometry("620x520")
        dialog.minsize(560, 460)

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)

        ctk.CTkLabel(frame, text="Kod").grid(row=0, column=0, sticky="w")
        code_var = tk.StringVar(value=service.code)
        ctk.CTkEntry(frame, textvariable=code_var, state="disabled").grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(frame, text="Nazov").grid(row=1, column=0, sticky="w", pady=(6, 0))
        label_var = tk.StringVar(value=service.label or "")
        ctk.CTkEntry(frame, textvariable=label_var).grid(row=1, column=1, sticky="ew", pady=(6, 0))

        ctk.CTkLabel(frame, text="Cena (price)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        price_var = tk.StringVar(value=f"{float(service.price):.2f}")
        ctk.CTkEntry(frame, textvariable=price_var).grid(row=2, column=1, sticky="ew", pady=(6, 0))

        ctk.CTkLabel(frame, text="Cena pri baliku (price2)").grid(row=3, column=0, sticky="w", pady=(6, 0))
        price2_var = tk.StringVar(value=f"{float(service.price2):.2f}")
        ctk.CTkEntry(frame, textvariable=price2_var).grid(row=3, column=1, sticky="ew", pady=(6, 0))

        ctk.CTkLabel(frame, text="Tag").grid(row=4, column=0, sticky="w", pady=(6, 0))
        tag_var = tk.StringVar(value=service.tag or "")
        ctk.CTkEntry(frame, textvariable=tag_var).grid(row=4, column=1, sticky="ew", pady=(6, 0))

        ctk.CTkLabel(frame, text="Info / popis").grid(row=5, column=0, sticky="w", pady=(6, 0))
        info = ctk.CTkTextbox(frame, height=160, wrap="word")
        info.grid(row=6, column=0, columnspan=2, sticky="nsew")
        info.insert("1.0", service.info or "")

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=7, column=0, columnspan=2, sticky="e", pady=(10, 0))

        def save() -> None:
            raw_label = (label_var.get() or "").strip()
            if not raw_label:
                messagebox.showerror("Chyba", "Nazov sluzby nemoze byt prazdny.", parent=dialog)
                return
            try:
                new_price = float((price_var.get() or "0").strip().replace(",", "."))
                new_price2 = float((price2_var.get() or "0").strip().replace(",", "."))
            except ValueError:
                messagebox.showerror("Chyba", "Zadaj platne cisla pre ceny.", parent=dialog)
                return

            service.label = raw_label
            service.price = new_price
            service.price2 = new_price2
            service.tag = (tag_var.get() or "").strip()
            service.info = (info.get("1.0", "end") or "").strip()

            self.w._base_prices[service.code] = (float(service.price), float(service.price2))
            save_catalog(self.w._catalog)
            self.refresh_service_tables(self.w._current_package)
            self.update_summary()
            self._refresh_service_editor_windows()
            dialog.destroy()

        ctk.CTkButton(btns, text="Zrusit", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            btns,
            text="Ulozit",
            command=save,
            fg_color=self.w._palette["accent"],
            hover_color=self.w._palette["accent_dim"],
            text_color="#ffffff",
        ).pack(side="right")

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
        client = self.w.client_data()
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

        # Services explicitly included in the selected package use the package price (`price2`).
        # If `included_quantities` defines a free quota, only the paid remainder uses base price.
        included_qty = self._included_qty_map().get(service.code, 0)
        if service.code in included_set:
            if qty <= 0:
                return base_price
            bundle_qty = included_qty if included_qty > 0 else 1
            if qty <= bundle_qty:
                return float(alt_price)
            total_cost = (bundle_qty * float(alt_price)) + ((qty - bundle_qty) * base_price)
            return total_cost / qty if qty > 0 else base_price

        # Optional bundle discount: show/apply alternative price when the service declares a bundle match.
        bundle_match = (service.bundle or "NONE").upper()
        if bundle_match != "NONE" and pkg_code.startswith(bundle_match):
            return float(alt_price)
        return base_price

    def _matches_filters(self, service: Service) -> bool:
        if self.w._filter_tags and (service.tag or "") not in self.w._filter_tags:
            return False
        return True

    def included_services_for(self, package: Package | None) -> Set[str]:
        if not package:
            return set()
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
