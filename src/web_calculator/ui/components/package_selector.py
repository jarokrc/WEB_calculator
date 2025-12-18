import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional

from web_calculator.core.models.package import Package
from web_calculator.ui.styles import theme


class PackageSelector(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        packages: list[Package],
        on_select: Callable[[Package | None], None],
        on_price_mode_change: Callable[[str], None] | None = None,
        on_edit_package: Callable[[Package], None] | None = None,
    ):
        super().__init__(master, fg_color="transparent")
        self._packages = packages
        self._on_select = on_select
        self._on_price_mode_change = on_price_mode_change or (lambda _mode: None)
        self._on_edit_package = on_edit_package or (lambda _pkg: None)
        self._desc_var = tk.StringVar(value="")
        self._items: list[Package | None] = [None] + list(packages)
        self._price_mode = "base"

        ctk.CTkLabel(self, text="Baliky", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 4), padx=8)
        ctk.CTkLabel(mode_frame, text="Cenova uroven:").pack(side="left")
        self._mode_var = tk.StringVar(value=self._price_mode)
        self._mode_combo = ctk.CTkComboBox(
            mode_frame,
            values=["base", "promo", "intra"],
            variable=self._mode_var,
            command=lambda _val: self._change_mode(self._mode_var.get()),
            state="readonly",
            width=120,
        )
        self._mode_combo.pack(side="left", padx=(6, 0))
        theme.style_combo_box(self._mode_combo, theme.PALETTE)
        self._mode_combo.set(self._mode_var.get())

        self._list = tk.Listbox(self, height=max(1, min(8, len(self._items))), activestyle="dotbox")
        theme.style_listbox(self._list, theme.PALETTE)
        self._list.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self._refresh_list()
        self._list.bind("<<ListboxSelect>>", self._handle_select)
        self._list.bind("<Double-Button-1>", self._handle_edit)
        ctk.CTkLabel(self, textvariable=self._desc_var, wraplength=260, justify="left").pack(fill="x", padx=8, pady=(6, 8))

    def select_package(self, code: Optional[str]) -> None:
        """
        Vyberie balik podla kodu; ak code je None alebo '', zvoli rezim bez balika.
        """
        if not code:
            self.select_none()
            return
        for idx, pkg in enumerate(self._packages, start=1):  # offset o "bez balika"
            if pkg.code == code:
                self._list.selection_clear(0, tk.END)
                self._list.selection_set(idx)
                self._list.see(idx)
                self._on_select_internal()
                break

    def select_none(self) -> None:
        self._list.selection_clear(0, tk.END)
        self._list.selection_set(0)
        self._list.see(0)
        self._on_select_internal()

    def _on_select_internal(self) -> None:
        pkg = self._selected_package()
        if pkg is None and self._list.curselection() == ():
            return
        if pkg:
            self._desc_var.set(pkg.description or "")
        else:
            self._desc_var.set("Vyber tuto moznost, ak chces len doplnky k existujucej stranke.")
        self._on_select(pkg)

    def _handle_select(self, _event: tk.Event) -> None:
        self._on_select_internal()

    def _refresh_list(self) -> None:
        selection = self._list.curselection()
        selected_idx = selection[0] if selection else 0
        self._list.delete(0, tk.END)
        self._list.insert(tk.END, "Bez balika (len doplnky)")
        for pkg in self._packages:
            price = self._current_price(pkg)
            self._list.insert(tk.END, f"{pkg.code} - {price:.0f} EUR")
        selected_idx = min(selected_idx, self._list.size() - 1)
        self._list.selection_set(selected_idx)
        self._list.see(selected_idx)

    def refresh_packages(self) -> None:
        self._refresh_list()

    def _change_mode(self, mode: str) -> None:
        if mode not in {"base", "promo", "intra"}:
            return
        self._price_mode = mode
        self._refresh_list()
        self._on_price_mode_change(mode)
        self._on_select_internal()

    def set_price_mode(self, mode: str) -> None:
        """
        Programmatically choose a price mode and keep the UI in sync.
        """
        target = mode if mode in {"base", "promo", "intra"} else "base"
        if self._mode_var.get() == target:
            return
        self._mode_var.set(target)
        if hasattr(self, "_mode_combo"):
            self._mode_combo.set(target)
        self._change_mode(target)

    def _current_price(self, pkg: Package) -> float:
        if self._price_mode == "promo" and pkg.promo_price is not None:
            return pkg.promo_price
        if self._price_mode == "intra" and pkg.intra_price is not None:
            return pkg.intra_price
        return pkg.base_price

    def update_theme(self, palette: dict) -> None:
        theme.style_listbox(self._list, palette)
        if hasattr(self, "_mode_combo"):
            theme.style_combo_box(self._mode_combo, palette)

    def _selected_package(self) -> Package | None:
        selection = self._list.curselection()
        if not selection:
            return None
        return self._items[selection[0]]

    def _handle_edit(self, _event: tk.Event) -> None:
        pkg = self._selected_package()
        if pkg:
            self._on_edit_package(pkg)
