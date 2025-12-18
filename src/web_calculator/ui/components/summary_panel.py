import tkinter as tk
import customtkinter as ctk

from web_calculator.core.calculations.pricing_engine import PricingBreakdown, PricingEngine
from web_calculator.ui.styles import theme


class SummaryPanel(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        pricing: PricingEngine,
        vat_rate: float = 0.23,
        on_discount_change=None,
    ):
        super().__init__(master, fg_color="transparent")
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

        ctk.CTkLabel(self, text="Suhrn", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, text="Balik").grid(row=1, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._base_var, font=("Segoe UI", 12, "bold")).grid(row=1, column=1, sticky="e", padx=8)

        ctk.CTkLabel(self, text="Doplnky").grid(row=2, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._extras_var).grid(row=2, column=1, sticky="e", padx=8)

        ctk.CTkLabel(self, text="Zlava (%)").grid(row=3, column=0, sticky="w", padx=8)
        discount_frame = ctk.CTkFrame(self, fg_color="transparent")
        discount_frame.grid(row=3, column=1, sticky="e")
        entry = ctk.CTkEntry(discount_frame, width=70, textvariable=self._discount_var, justify="right")
        entry.pack(side="left")
        ctk.CTkLabel(discount_frame, textvariable=self._discount_amount_var).pack(side="left", padx=(6, 0))

        separator = ctk.CTkFrame(self, height=2, fg_color=theme.PALETTE["border"])
        separator.grid(row=4, column=0, columnspan=2, sticky="we", pady=6, padx=8)

        ctk.CTkLabel(self, text="Spolu bez DPH", font=("Segoe UI", 12, "bold")).grid(row=5, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._total_var, font=("Segoe UI", 12, "bold")).grid(row=5, column=1, sticky="e", padx=8)

        ctk.CTkLabel(self, text=f"DPH {int(self._vat_rate*100)} %").grid(row=6, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._vat_var).grid(row=6, column=1, sticky="e", padx=8)

        ctk.CTkLabel(self, text="Spolu s DPH", font=("Segoe UI", 13, "bold")).grid(row=7, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._total_vat_var, font=("Segoe UI", 13, "bold")).grid(row=7, column=1, sticky="e", padx=8)

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
