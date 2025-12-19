import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk
from typing import Set

from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service
from web_calculator.core.services.catalog import Catalog, save_catalog, save_packages
from web_calculator.core.services.supplier import load_supplier, save_supplier
from web_calculator.ui.layouts.service_area import ServiceArea
from web_calculator.ui.components.client_dialog import ClientDialog
from web_calculator.ui.layouts.actions_bar import ActionsBar
from web_calculator.ui.components.package_selector import PackageSelector
from web_calculator.ui.components.summary_panel import SummaryPanel
from web_calculator.ui.styles import theme
from web_calculator.ui.controllers.actions_controller import ActionsController
from web_calculator.ui.controllers.service_controller import ServiceController


class MainWindow(ctk.CTk):
    def __init__(self, catalog: Catalog):
        super().__init__()
        self._theme_name = "dark_futuristic"
        self._palette = theme.apply_theme(self, self._theme_name)
        self.title("WEB kalkulacka")
        # Minimalne rozmery, na ktore mozno zmensit okno (pri presunoch/resize),
        # nasledne sa aj tak po 3s maximalizuje na aktualny monitor.
        self._base_min_w, self._base_min_h = 800, 600
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        min_w, min_h = min(self._base_min_w, screen_w), min(self._base_min_h, screen_h)
        self.geometry(f"{min_w}x{min_h}+0+0")
        self.minsize(min_w, min_h)
        # Povolit resize, ale po pauze sa okno samo maximalizuje na dany monitor.
        self.resizable(True, True)
        self._current_monitor = None
        self._fit_after_id: str | None = None
        self._last_full_size: tuple[int, int] | None = None
        self._shrunk_on_normal = False
        self._suppress_fit = False
        # Spusti okno maximalizovane, aby sa zobrazili vsetky ovladace a mali priestor.
        self.after(0, self._maximize_window)
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
        self._vat_rate: float = 0.23
        self._vat_mode: str = "add"  # add = ceny bez DPH, included = ceny s DPH
        self._base_prices: dict[str, tuple[float, float]] = {s.code: (s.price, s.price2) for s in catalog.services}
        self._auto_selected: Set[str] = set()
        self._hidden_service_codes: Set[str] = {"ESHOP-E-SHOP-MODUL-ZAKLAD"}
        self._service_editor_windows: dict[str, tk.Toplevel] = {}
        self._client_data: dict[str, str] = {}
        self._supplier_data: dict[str, str] = load_supplier()
        self._title_base = "WEB kalkulacka"

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
            self._services.open_section_window,
            self._services.reset_filters,
            self._open_client_dialog,
            price_provider=self._services.effective_price,
        )
        self.service_area.set_client_name(self._client_display_name())

        self.summary = SummaryPanel(
            self,
            self._pricing,
            vat_rate=self._vat_rate,
            vat_mode=self._vat_mode,
            on_discount_change=self._services.set_discount,
            on_vat_change=self._set_vat_rate,
            on_vat_mode_change=self._set_vat_mode,
        )
        self.summary.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.actions = ActionsBar(
            self,
            on_reset=self._actions.reset_selection,
            on_save=self._actions.save_client,
            on_load=self._actions.load_client,
            on_pdf=self._actions.export_pdf,
            on_help=self._services.show_help,
            on_preview=self._services.show_preview,
            on_search=self._open_search,
            on_edit_supplier=self._open_supplier_dialog,
            on_theme_change=self._set_theme,
            theme_names=list(theme.THEMES.keys()),
            row=2,
        )

        # Default to "no package" so doplnky mozno pouzit samostatne.
        self.package_selector.select_none()
        self._update_save_buttons()
        self._update_title()

    def _maximize_window(self) -> None:
        """Try to maximize; fallback to full screen size if zoomed is unsupported."""
        try:
            self.state("zoomed")
        except Exception:
            try:
                w, h = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f"{w}x{h}+0+0")
            except Exception:
                pass
        # Bind to monitor changes (window moves) to refit to the target display.
        self.bind("<Configure>", self._on_configure_monitor, add="+")
        self._fit_to_monitor_fullscreen(force=True)

    def _open_package_edit_dialog(self, package: Package) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Upravit sluzby balika {package.code} - {self._supplier_display_name()}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("720x520")
        dialog.minsize(600, 400)

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(frame, text=f"Balik {package.code}", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text="Vyber sluzby, ktore maju byt automaticky zahrnute v baliku.").pack(anchor="w", pady=(0, 6))

        base_var = tk.StringVar(value=f"{float(package.base_price):.2f}")
        promo_var = tk.StringVar(value=f"{float(package.promo_price):.2f}" if package.promo_price is not None else "")
        intra_var = tk.StringVar(value=f"{float(package.intra_price):.2f}" if package.intra_price is not None else "")

        price_frame = ctk.CTkFrame(frame)
        price_frame.pack(fill="x", pady=(0, 10))
        price_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(price_frame, text="Ceny balika", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )
        ctk.CTkLabel(price_frame, text="Base").grid(row=1, column=0, sticky="w", padx=(8, 6), pady=(4, 0))
        ctk.CTkEntry(price_frame, textvariable=base_var, width=120, justify="right").grid(row=1, column=1, sticky="w", pady=(4, 0))
        ctk.CTkLabel(price_frame, text="Promo").grid(row=2, column=0, sticky="w", padx=(8, 6), pady=(4, 0))
        ctk.CTkEntry(price_frame, textvariable=promo_var, width=120, justify="right").grid(row=2, column=1, sticky="w", pady=(4, 0))
        ctk.CTkLabel(price_frame, text="Intra").grid(row=3, column=0, sticky="w", padx=(8, 6), pady=(4, 6))
        ctk.CTkEntry(price_frame, textvariable=intra_var, width=120, justify="right").grid(row=3, column=1, sticky="w", pady=(4, 6))

        filter_frame = ctk.CTkFrame(frame, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(filter_frame, text="Zdroj").pack(side="left")
        source_var = tk.StringVar(value="Vsetko")
        source_box = ctk.CTkComboBox(
            filter_frame,
            values=["Vsetko", "PRIMARY", "ESHOP", "WEB"],
            variable=source_var,
            command=lambda _val: refresh_list(),
            state="readonly",
            width=120,
        )
        source_box.pack(side="left", padx=(6, 12))
        theme.style_combo_box(source_box, self._palette)
        ctk.CTkLabel(filter_frame, text="Hladat").pack(side="left")
        query_var = tk.StringVar()
        query_entry = ctk.CTkEntry(filter_frame, textvariable=query_var)
        query_entry.pack(side="left", fill="x", expand=True)

        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True)
        listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, activestyle="dotbox", exportselection=False)
        theme.style_listbox(listbox, self._palette)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        services = list(self._catalog.services)
        selected_codes = set(package.included_services or [])
        qty_map = dict(package.included_quantities or {})
        visible_codes: list[str] = []
        updating = False

        def score(svc: Service, query: str) -> int:
            label = (svc.label or "").lower()
            code = (svc.code or "").lower()
            if not query:
                return 0
            if label.startswith(query) or code.startswith(query):
                return 0
            idx = label.find(query)
            if idx == -1:
                idx = code.find(query)
            return idx if idx >= 0 else 999

        def matches_source(svc: Service, source_filter: str) -> bool:
            source = (svc.source or "").upper()
            if source_filter == "PRIMARY":
                return source == "PRIMARY"
            if source_filter == "ESHOP":
                return source.startswith("ESHOP")
            if source_filter == "WEB":
                return source == "WEB"
            return True

        def refresh_list() -> None:
            nonlocal visible_codes, updating
            updating = True
            try:
                listbox.delete(0, tk.END)
                visible_codes = []
                query = (query_var.get() or "").strip().lower()
                source_filter = source_var.get() or "Vsetko"
                matches = []
                for svc in services:
                    if not matches_source(svc, source_filter):
                        continue
                    label = (svc.label or "").lower()
                    code = (svc.code or "").lower()
                    if query and query not in label and query not in code:
                        continue
                    matches.append((score(svc, query), svc))
                matches.sort(key=lambda item: (item[0], (item[1].label or "").lower()))
                for idx, (_score, svc) in enumerate(matches):
                    tag_txt = f" [{svc.tag}]" if svc.tag else ""
                    bundle_txt = f" (bundle: {svc.bundle})" if svc.bundle and svc.bundle != "NONE" else ""
                    qty_txt = ""
                    if svc.code in selected_codes:
                        qty_txt = f" (qty: {qty_map.get(svc.code, 1)})"
                    listbox.insert(tk.END, f"{svc.code} - {svc.label}{tag_txt}{bundle_txt}{qty_txt}")
                    visible_codes.append(svc.code)
                    if svc.code in selected_codes:
                        listbox.selection_set(idx)
            finally:
                updating = False

        def sync_selection_from_listbox() -> None:
            nonlocal selected_codes
            if updating:
                return
            prev_selected = set(selected_codes)
            visible_set = set(visible_codes)
            selected_visible = {visible_codes[i] for i in listbox.curselection()}
            selected_codes = (selected_codes - visible_set) | selected_visible
            for code in selected_codes - prev_selected:
                qty_map.setdefault(code, 1)

        def edit_quantity(event: tk.Event) -> None:
            idx = listbox.nearest(event.y)
            if idx < 0 or idx >= len(visible_codes):
                return
            code = visible_codes[idx]
            svc = next((s for s in services if s.code == code), None)
            if svc is None:
                return
            selected_codes.add(code)
            qty_map.setdefault(code, 1)
            current = qty_map.get(code, 1)
            value = simpledialog.askstring(
                "Mnozstvo v baliku",
                f"Mnozstvo pre:\n{svc.label}",
                initialvalue=str(current),
                parent=dialog,
            )
            if value is None:
                return
            try:
                qty = int(value.strip())
            except ValueError:
                messagebox.showerror("Chyba", "Zadaj cele cislo.", parent=dialog)
                return
            if qty <= 0:
                messagebox.showerror("Chyba", "Mnozstvo musi byt vacsie ako 0.", parent=dialog)
                return
            qty_map[code] = qty
            refresh_list()

        listbox.bind("<<ListboxSelect>>", lambda _e: sync_selection_from_listbox())
        listbox.bind("<Double-Button-1>", edit_quantity)
        query_entry.bind("<KeyRelease>", lambda _e: refresh_list())
        refresh_list()
        query_entry.focus_set()

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))

        def parse_price(raw: str, allow_empty: bool) -> float | None:
            text = (raw or "").strip()
            if text == "":
                if allow_empty:
                    return None
                raise ValueError("required")
            value = float(text.replace(",", "."))
            if value < 0:
                raise ValueError("negative")
            return value

        def save_and_close() -> None:
            try:
                base_price = parse_price(base_var.get(), allow_empty=False)
                promo_price = parse_price(promo_var.get(), allow_empty=True)
                intra_price = parse_price(intra_var.get(), allow_empty=True)
            except ValueError:
                messagebox.showerror("Chyba", "Zadaj platne cislo pre ceny balika.", parent=dialog)
                return

            package.base_price = float(base_price)
            package.promo_price = promo_price
            package.intra_price = intra_price

            package.included_services = [svc.code for svc in services if svc.code in selected_codes]
            # Update bundle flag on services: added -> set bundle to package; removed -> NONE if previously linked.
            for svc in self._catalog.services:
                if svc.code in selected_codes:
                    svc.bundle = package.code
                elif (svc.bundle or "").upper() == (package.code or "").upper():
                    svc.bundle = "NONE"
            # Keep included quantities in sync: remove dropped codes, ensure new ones at least 1.
            for code in list(qty_map.keys()):
                if code not in selected_codes:
                    qty_map.pop(code, None)
            for code in selected_codes:
                qty_map.setdefault(code, 1)
            package.included_quantities = qty_map
            # Persist both split packages.json and combined catalog.json for konzistentnost.
            save_packages(self._catalog)
            save_catalog(self._catalog)
            self.package_selector.refresh_packages()
            if self._current_package_raw and self._current_package_raw.code == package.code:
                self._services.set_package(self._current_package_raw)
                self.service_area.refresh_selection(self._selected_services, self._service_qty)
            dialog.destroy()

        ctk.CTkButton(buttons, text="Zrusit", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            buttons,
            text="Ulozit",
            command=save_and_close,
            fg_color=self._palette["accent"],
            hover_color=self._palette["accent_dim"],
            text_color="#ffffff",
        ).pack(side="right")



    # -------- Client & actions --------
    def _update_save_buttons(self) -> None:
        if hasattr(self, "_actions"):
            self._actions.update_save_buttons()

    def _open_search(self) -> None:
        self._services.open_search()

    def _open_client_dialog(self) -> None:
        ClientDialog(self, self.client_data(), self.set_client_data, firm_name=self._supplier_display_name())

    def _open_supplier_dialog(self) -> None:
        from web_calculator.ui.components.supplier_dialog import SupplierDialog

        SupplierDialog(self, self._supplier_data, self.set_supplier_data, firm_name=self._supplier_display_name())

    def _set_vat_rate(self, value: float) -> None:
        self._vat_rate = max(0.0, value)
        self._services.update_summary()

    def _set_vat_mode(self, mode: str) -> None:
        mode_norm = (mode or "add").lower()
        if "inc" in mode_norm or "cene" in mode_norm:
            self._vat_mode = "included"
        else:
            self._vat_mode = "add"
        self._services.update_summary()

    def _set_theme(self, name: str) -> None:
        self._theme_name = name
        self._palette = theme.apply_theme(self, name)
        self.package_selector.update_theme(self._palette)
        if hasattr(self, "actions"):
            self.actions.update_theme(self._palette)

    def _client_display_name(self) -> str:
        name = (self._client_data.get("name") or self._client_data.get("company") or "").strip()
        return name or "-"

    def client_data(self) -> dict:
        return dict(self._client_data)

    def set_client_data(self, data: dict) -> None:
        self._client_data = dict(data or {})
        self.service_area.set_client_name(self._client_display_name())
        self._update_save_buttons()

    def reset_client_data(self) -> None:
        self._client_data = {}
        self.service_area.set_client_name(self._client_display_name())
        self._update_save_buttons()

    def has_client_data(self) -> bool:
        keys = ["name", "company", "ico", "dic", "icdph", "email", "address"]
        return any((self._client_data.get(k) or "").strip() for k in keys)

    def supplier_data(self) -> dict:
        # Return flattened mapping of active profile for PDF consumption
        active_id = self._supplier_data.get("active")
        profiles = self._supplier_data.get("profiles", [])
        prof = next((p for p in profiles if p.get("id") == active_id), profiles[0] if profiles else {"fields": []})
        mapping: dict[str, str] = {}
        for item in prof.get("fields", []):
            code = (item.get("code") or item.get("label") or "").strip()
            val = (item.get("value") or "").strip()
            if not code and not val:
                continue
            key = code or f"field_{len(mapping)+1}"
            mapping[key] = val
        return mapping

    def supplier_fields(self) -> list[dict]:
        active_id = self._supplier_data.get("active")
        profiles = self._supplier_data.get("profiles", [])
        prof = next((p for p in profiles if p.get("id") == active_id), profiles[0] if profiles else {"fields": []})
        return list(prof.get("fields", []))

    def set_supplier_data(self, data: dict) -> None:
        self._supplier_data = dict(data or {})
        save_supplier(self._supplier_data)
        self._update_title()

    def _supplier_display_name(self) -> str:
        profiles = self._supplier_data.get("profiles", [])
        active_id = self._supplier_data.get("active")
        prof = next((p for p in profiles if p.get("id") == active_id), profiles[0] if profiles else None)
        name = (prof.get("name") or prof.get("id")) if prof else ""
        return name.strip() if name else "NASTAV FIRMU"

    def _update_title(self) -> None:
        self.title(f"{self._title_base} - {self._supplier_display_name()}")

    # --- Monitor-aware sizing ---
    def _on_configure_monitor(self, _event=None) -> None:
        if self._suppress_fit:
            return
        # Debounce auto-fit; po 3s nečinnosti sa prispôsobí aktuálnemu monitoru a maximalizuje sa.
        if self.state() == "normal" and not self._shrunk_on_normal:
            info = self._get_monitor_info()
            work_w = info[3] if info else self.winfo_screenwidth()
            work_h = info[4] if info else self.winfo_screenheight()
            base_w = self._last_full_size[0] if self._last_full_size else self.winfo_width()
            base_h = self._last_full_size[1] if self._last_full_size else self.winfo_height()
            shrink_w = max(self._base_min_w, min(work_w, max(1, base_w // 2)))
            shrink_h = max(self._base_min_h, min(work_h, max(1, base_h // 2)))
            try:
                cur_x, cur_y = self.winfo_rootx(), self.winfo_rooty()
                self.geometry(f"{shrink_w}x{shrink_h}+{cur_x}+{cur_y}")
            except Exception:
                self.geometry(f"{shrink_w}x{shrink_h}")
            self._shrunk_on_normal = True

        if self._fit_after_id:
            self.after_cancel(self._fit_after_id)
        self._fit_after_id = self.after(3000, lambda: self._fit_to_monitor_fullscreen(force=True))

    def _fit_to_monitor_fullscreen(self, force: bool = False) -> None:
        """Fit window to current monitor's work area. Uses full work area and updates minsize."""
        self._fit_after_id = None
        info = self._get_monitor_info()
        if not info:
            return
        hmon, left, top, work_w, work_h = info
        if not force and hmon == getattr(self, "_current_monitor", None):
            return
        self._current_monitor = hmon
        min_w = min(self._base_min_w, work_w)
        min_h = min(self._base_min_h, work_h)
        self.minsize(min_w, min_h)
        self._shrunk_on_normal = False
        # Account for window decorations (title bar/borders) so obsah neprekrýva taskbar.
        self.update_idletasks()
        border = max(0, self.winfo_rootx() - self.winfo_x())
        title = max(0, self.winfo_rooty() - self.winfo_y())
        extra_w = border * 2
        extra_h = title + border  # aproximácia pre spodný okraj
        adj_w = max(min_w, work_w - extra_w)
        adj_h = max(min_h, work_h - extra_h)
        self._suppress_fit = True
        try:
            self.geometry(f"{adj_w}x{adj_h}+{left}+{top}")
            try:
                self.state("zoomed")
            except Exception:
                pass
        finally:
            self._suppress_fit = False
        self._last_full_size = (adj_w, adj_h)

    def _get_monitor_info(self):
        """Return (handle, left, top, work_w, work_h) for the monitor under the window center (Windows only)."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            MONITOR_DEFAULTTONEAREST = 2

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

            x = self.winfo_rootx() + self.winfo_width() // 2
            y = self.winfo_rooty() + self.winfo_height() // 2
            hmon = user32.MonitorFromPoint(wintypes.POINT(x, y), MONITOR_DEFAULTTONEAREST)
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                return None
            work_w = mi.rcWork.right - mi.rcWork.left
            work_h = mi.rcWork.bottom - mi.rcWork.top
            return hmon, mi.rcWork.left, mi.rcWork.top, work_w, work_h
        except Exception:
            return None
