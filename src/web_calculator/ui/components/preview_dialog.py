import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from typing import Iterable

from web_calculator.core.calculations.pricing_engine import PricingBreakdown, PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service
from web_calculator.ui.styles import theme


class PreviewDialog(ctk.CTkToplevel):
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

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=12)
        main.columnconfigure(1, weight=1)

        ctk.CTkLabel(main, text="Balik", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(main, text=package.code if package else "Bez balika").grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(main, text="Zlava (%)").grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(main, text=f"{discount_pct:.2f} %").grid(row=1, column=1, sticky="w")

        separator = ctk.CTkFrame(main, height=2, fg_color=theme.PALETTE["border"])
        separator.grid(row=2, column=0, columnspan=2, sticky="we", pady=6)

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

        summary = ctk.CTkFrame(main, fg_color="transparent")
        summary.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ctk.CTkLabel(summary, text="Bez DPH:").grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(summary, text=f"{subtotal:.2f} EUR").grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(summary, text=f"Zlava {discount_pct:.2f}%:").grid(row=1, column=0, sticky="e")
        ctk.CTkLabel(summary, text=f"-{discount_amount:.2f} EUR").grid(row=1, column=1, sticky="e")
        ctk.CTkLabel(summary, text="DPH 23%:").grid(row=2, column=0, sticky="e")
        ctk.CTkLabel(summary, text=f"{vat:.2f} EUR").grid(row=2, column=1, sticky="e")
        ctk.CTkLabel(summary, text="Spolu s DPH:", font=("Segoe UI", 11, "bold")).grid(row=3, column=0, sticky="e", pady=(4, 0))
        ctk.CTkLabel(summary, text=f"{total_with_vat:.2f} EUR", font=("Segoe UI", 11, "bold")).grid(row=3, column=1, sticky="e", pady=(4, 0))

        ctk.CTkButton(main, text="Zavriet", command=self.destroy).grid(row=5, column=0, columnspan=2, pady=10)
