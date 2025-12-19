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
        vat_mode: str = "add",
        on_discount_change=None,
        on_vat_change=None,
        on_vat_mode_change=None,
    ):
        super().__init__(master, fg_color="transparent")
        self._pricing = pricing
        self._vat_rate = vat_rate
        self._vat_mode = vat_mode
        self._mode_labels = {"add": "Pripocitat DPH", "included": "DPH v cene"}
        self._on_discount_change = on_discount_change or (lambda _val: None)
        self._on_vat_change = on_vat_change or (lambda _val: None)
        self._on_vat_mode_change = on_vat_mode_change or (lambda _val: None)
        self._updating = False

        self._discount_var = tk.StringVar(value="0")
        self._vat_rate_var = tk.StringVar(value=f"{vat_rate*100:.2f}")
        self._vat_mode_var = tk.StringVar(value=self._mode_labels.get(vat_mode, self._mode_labels["add"]))
        self._discount_amount_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._total_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._vat_var = tk.StringVar(value=self._pricing.format_currency(0))
        self._total_vat_var = tk.StringVar(value=self._pricing.format_currency(0))

        ctk.CTkLabel(self, text="Suhrn", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, text="Sadzba DPH (%)").grid(row=1, column=0, sticky="w", padx=8, pady=(0, 2))
        vat_frame = ctk.CTkFrame(self, fg_color="transparent")
        vat_frame.grid(row=1, column=1, sticky="e")
        vat_entry = ctk.CTkEntry(vat_frame, width=70, textvariable=self._vat_rate_var, justify="right")
        vat_entry.pack(side="left")
        ctk.CTkComboBox(
            vat_frame,
            values=list(self._mode_labels.values()),
            variable=self._vat_mode_var,
            width=150,
            state="readonly",
            command=lambda _val: self._handle_vat_mode_change(),
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(self, text="Zlava (%)").grid(row=2, column=0, sticky="w", padx=8)
        discount_frame = ctk.CTkFrame(self, fg_color="transparent")
        discount_frame.grid(row=2, column=1, sticky="e")
        entry = ctk.CTkEntry(discount_frame, width=70, textvariable=self._discount_var, justify="right")
        entry.pack(side="left")
        ctk.CTkLabel(discount_frame, textvariable=self._discount_amount_var).pack(side="left", padx=(6, 0))

        separator = ctk.CTkFrame(self, height=2, fg_color=theme.PALETTE["border"])
        separator.grid(row=3, column=0, columnspan=2, sticky="we", pady=6, padx=8)

        ctk.CTkLabel(self, text="Spolu bez DPH", font=("Segoe UI", 12, "bold")).grid(row=4, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._total_var, font=("Segoe UI", 12, "bold")).grid(row=4, column=1, sticky="e", padx=8)

        self._vat_label = ctk.CTkLabel(self, text=self._vat_label_text())
        self._vat_label.grid(row=5, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._vat_var).grid(row=5, column=1, sticky="e", padx=8)

        ctk.CTkLabel(self, text="Spolu s DPH", font=("Segoe UI", 13, "bold")).grid(row=6, column=0, sticky="w", padx=8)
        ctk.CTkLabel(self, textvariable=self._total_vat_var, font=("Segoe UI", 13, "bold")).grid(row=6, column=1, sticky="e", padx=8)

        for col in range(2):
            self.columnconfigure(col, weight=1)

        self._discount_var.trace_add("write", lambda *_: self._handle_discount_change())
        self._vat_rate_var.trace_add("write", lambda *_: self._handle_vat_change())

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

    def _handle_vat_change(self) -> None:
        if self._updating:
            return
        raw = (self._vat_rate_var.get() or "").strip().replace(",", ".")
        try:
            pct = float(raw)
        except ValueError:
            return
        if pct < 0:
            pct = 0.0
        self._on_vat_change(pct / 100.0)

    def _handle_vat_mode_change(self) -> None:
        if self._updating:
            return
        self._on_vat_mode_change(self._normalize_mode(self._vat_mode_var.get()))

    def _normalize_mode(self, value: str) -> str:
        val = (value or "").lower()
        if "inc" in val or "cene" in val:
            return "included"
        return "add"

    def _vat_label_text(self) -> str:
        mode_txt = " (pripocitana)" if self._vat_mode == "add" else " (uz v cene)"
        return f"DPH {self._vat_rate*100:.2f} %{mode_txt}"

    def update_values(self, breakdown: PricingBreakdown, discount_pct: float, vat_rate: float, vat_mode: str) -> None:
        self._updating = True
        try:
            self._discount_var.set(f"{discount_pct:.2f}")
            self._vat_rate_var.set(f"{vat_rate*100:.2f}")
            self._vat_mode_var.set(self._mode_labels.get(vat_mode, self._mode_labels["add"]))
        finally:
            self._updating = False

        self._vat_rate = vat_rate
        self._vat_mode = vat_mode
        discount_amount = breakdown.total * (discount_pct / 100.0)
        if vat_mode == "included":
            total_with_vat = max(0.0, breakdown.total - discount_amount)
            subtotal = total_with_vat / (1 + self._vat_rate) if self._vat_rate > 0 else total_with_vat
            vat = total_with_vat - subtotal
        else:
            subtotal = max(0.0, breakdown.total - discount_amount)
            vat = subtotal * self._vat_rate
            total_with_vat = subtotal + vat

        self._discount_amount_var.set(f"- {self._pricing.format_currency(discount_amount)}")
        self._total_var.set(self._pricing.format_currency(subtotal))
        self._vat_var.set(self._pricing.format_currency(vat))
        self._total_vat_var.set(self._pricing.format_currency(total_with_vat))
        self._vat_label.configure(text=self._vat_label_text())
