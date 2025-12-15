import tkinter as tk
from tkinter import ttk
from typing import Iterable

from web_calculator.core.calculations.pricing_engine import PricingBreakdown, PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service


class PreviewDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        package: Package | None,
        services: Iterable[tuple[Service, int]],
        breakdown: PricingBreakdown,
        discount_pct: float,
        pricing: PricingEngine,
    ):
        super().__init__(master)
        self.title("Nahľad objednavky")
        self.transient(master)
        self.grab_set()
        self.geometry("600x500")
        self.minsize(520, 420)
        self.resizable(True, True)

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="Balik", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(main, text=package.code if package else "Bez balika").grid(row=0, column=1, sticky="w")

        ttk.Label(main, text="Zlava (%)").grid(row=1, column=0, sticky="w")
        ttk.Label(main, text=f"{discount_pct:.2f} %").grid(row=1, column=1, sticky="w")

        ttk.Separator(main, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="we", pady=6)

        tree = ttk.Treeview(main, columns=("name", "qty", "price", "total"), show="headings", height=12)
        tree.heading("name", text="Sluzba")
        tree.heading("qty", text="Mnozstvo")
        tree.heading("price", text="Cena/ks")
        tree.heading("total", text="Spolu")
        tree.column("name", width=260)
        tree.column("qty", width=70, anchor="center")
        tree.column("price", width=100, anchor="e")
        tree.column("total", width=110, anchor="e")
        tree.grid(row=3, column=0, columnspan=2, sticky="nsew")

        total_no_vat = breakdown.total
        discount_amount = total_no_vat * (discount_pct / 100.0)
        subtotal = max(0.0, total_no_vat - discount_amount)
        vat = subtotal * 0.23
        total_with_vat = subtotal + vat

        for svc, qty in services:
            line_total = svc.price * qty
            tree.insert(
                "",
                tk.END,
                values=(svc.label, qty, f"{svc.price:.2f} EUR", f"{line_total:.2f} EUR"),
            )

        summary = ttk.Frame(main)
        summary.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Label(summary, text="Bez DPH:").grid(row=0, column=0, sticky="e")
        ttk.Label(summary, text=f"{subtotal:.2f} EUR").grid(row=0, column=1, sticky="e")
        ttk.Label(summary, text=f"Zlava {discount_pct:.2f}%:").grid(row=1, column=0, sticky="e")
        ttk.Label(summary, text=f"-{discount_amount:.2f} EUR").grid(row=1, column=1, sticky="e")
        ttk.Label(summary, text="DPH 23%:").grid(row=2, column=0, sticky="e")
        ttk.Label(summary, text=f"{vat:.2f} EUR").grid(row=2, column=1, sticky="e")
        ttk.Label(summary, text="Spolu s DPH:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="e", pady=(4, 0))
        ttk.Label(summary, text=f"{total_with_vat:.2f} EUR", font=("Segoe UI", 10, "bold")).grid(row=3, column=1, sticky="e", pady=(4, 0))

        ttk.Button(main, text="Zavriet", command=self.destroy).grid(row=5, column=0, columnspan=2, pady=10)
