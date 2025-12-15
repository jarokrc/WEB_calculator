import tkinter as tk
from tkinter import ttk

from web_calculator.core.calculations.pricing_engine import PricingBreakdown, PricingEngine


class SummaryPanel(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        pricing: PricingEngine,
        vat_rate: float = 0.23,
        on_discount_change=None,
    ):
        super().__init__(master, padding=8)
        self._pricing = pricing
        self._vat_rate = vat_rate
        self._on_discount_change = on_discount_change or (lambda _val: None)
        self._updating = False

        self._base_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._extras_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._discount_var = tk.StringVar(value="0")
        self._discount_amount_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._total_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._vat_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._total_vat_var = tk.StringVar(value=self._pricing.format_currency(0))

        ttk.Label(self, text="Suhrn", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Balik").grid(row=1, column=0, sticky="w")
        ttk.Label(self, textvariable=self._base_var, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e")

        ttk.Label(self, text="Doplnky").grid(row=2, column=0, sticky="w")
        ttk.Label(self, textvariable=self._extras_var).grid(row=2, column=1, sticky="e")

        ttk.Label(self, text="Zlava (%)").grid(row=3, column=0, sticky="w")
        discount_frame = ttk.Frame(self)
        discount_frame.grid(row=3, column=1, sticky="e")
        entry = ttk.Entry(discount_frame, width=6, textvariable=self._discount_var, justify="right")
        entry.pack(side="left")
        ttk.Label(discount_frame, textvariable=self._discount_amount_var).pack(side="left", padx=(6, 0))

        ttk.Separator(self, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="we", pady=6)

        ttk.Label(self, text="Spolu bez DPH", font=("Segoe UI", 11, "bold")).grid(row=5, column=0, sticky="w")
        ttk.Label(self, textvariable=self._total_var, font=("Segoe UI", 11, "bold")).grid(row=5, column=1, sticky="e")

        ttk.Label(self, text=f"DPH {int(self._vat_rate*100)} %").grid(row=6, column=0, sticky="w")
        ttk.Label(self, textvariable=self._vat_var).grid(row=6, column=1, sticky="e")

        ttk.Label(self, text="Spolu s DPH", font=("Segoe UI", 12, "bold")).grid(row=7, column=0, sticky="w")
        ttk.Label(self, textvariable=self._total_vat_var, font=("Segoe UI", 12, "bold")).grid(row=7, column=1, sticky="e")

        for col in range(2):
            self.columnconfigure(col, weight=1)

        self._discount_var.trace_add("write", lambda *_: self._handle_discount_change())

    def _handle_discount_change(self) -> None:
        if self._updating:
            return
        raw = (self._discount_var.get() or "").strip().replace(",", ".")
        if raw == "":
            value = 0.0
        else:
            try:
                value = float(raw)
            except ValueError:
                return
        if value < 0:
            value = 0.0
        self._on_discount_change(value)

    def update_values(self, breakdown: PricingBreakdown, discount_pct: float) -> None:
        self._updating = True
        try:
            self._discount_var.set(f"{discount_pct:.2f}")
        finally:
            self._updating = False

        self._base_var.set(self._pricing.format_currency(breakdown.base))
        self._extras_var.set(self._pricing.format_currency(breakdown.extras))

        discount_amount = breakdown.total * (discount_pct / 100.0)
        subtotal = max(0.0, breakdown.total - discount_amount)
        vat = subtotal * self._vat_rate

        self._discount_amount_var.set(f"- {self._pricing.format_currency(discount_amount)}")
        self._total_var.set(self._pricing.format_currency(subtotal))
        self._vat_var.set(self._pricing.format_currency(vat))
        self._total_vat_var.set(self._pricing.format_currency(subtotal + vat))
