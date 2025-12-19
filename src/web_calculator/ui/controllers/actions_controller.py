from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox

from web_calculator.core.services.invoice import build_invoice_payload
from web_calculator.core.services.catalog import save_packages, save_catalog
from web_calculator.core.services.pdf_content import load_pdf_content, save_pdf_content
from web_calculator.ui.components.pdf_export_dialog import PdfExportDialog
from web_calculator.ui.components.pdf_content_dialog import PdfContentDialog
from web_calculator.utils.pdf.exports import export_quote_pdf, export_proforma_pdf, export_invoice_pdf


class ActionsController:
    """
    Obsluhuje akcie ulozit/nacitat klienta, export PDF a reset stavu.
    Drzi referenciu na hlavne okno, aby nemusel duplicovat stav.
    """

    def __init__(self, window) -> None:
        self.w = window
        self._pdf_content = load_pdf_content()

    # --- UI helpers ---
    def update_save_buttons(self) -> None:
        if not hasattr(self.w, "actions"):
            return
        has_data = self.w.has_client_data()
        self.w.actions.set_enabled(has_data)

    # --- Actions ---
    def save_client(self) -> None:
        client = self.w.client_data()
        if not self.w.has_client_data():
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
            "price_mode": getattr(self.w, "_price_mode", "base"),
            "vat_rate": getattr(self.w, "_vat_rate", 0.23),
            "vat_mode": getattr(self.w, "_vat_mode", "add"),
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
        price_mode = str(data.get("price_mode") or "base")
        self.w.package_selector.set_price_mode(price_mode)
        pkg_code = data.get("package")
        self.w.package_selector.select_package(pkg_code)
        self.w._selected_services = set(data.get("services", []))
        self.w._service_qty = data.get("quantities", {code: 1 for code in self.w._selected_services})
        self.w._discount_pct = float(data.get("discount_pct", 0.0) or 0.0)
        self.w._vat_rate = float(data.get("vat_rate", getattr(self.w, "_vat_rate", 0.23)) or 0.0)
        self.w._vat_mode = str(data.get("vat_mode", getattr(self.w, "_vat_mode", "add")) or "add")
        self.w.set_client_data(data.get("client", {}))
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.w._services.update_summary()
        self.update_save_buttons()

    def export_pdf(self) -> None:
        PdfExportDialog(self.w, on_select=self._export_pdf_with_type, on_edit=self._open_pdf_content_editor, firm_name=self.w._supplier_display_name())

    def _open_pdf_content_editor(self, doc_type: str) -> None:
        payload_preview = self._build_payload_for_preview(doc_type)
        if payload_preview is None:
            return
        data = self._build_section_content(doc_type, payload_preview)
        supplier_fields = self.w.supplier_fields()
        supplier_options = []
        for f in supplier_fields:
            code = f.get("code") or f.get("label") or ""
            label = f.get("label") or f.get("code") or ""
            value = f.get("value") or ""
            if code or label or value:
                supplier_options.append((code, label, value))

        payload_preview = self._build_payload_for_preview(doc_type)
        totals = payload_preview.get("totals", {}) if payload_preview else {}
        fmt = self.w._pricing.format_currency
        payment_options = [
            ("vs", "Variabilny symbol", str(payload_preview.get("invoice_no", ""))),
            ("issue_date", "Datum vystavenia", str(payload_preview.get("issue_date", ""))),
            ("package", "Balik", str(payload_preview.get("package", ""))),
            ("status", "Stav", "Nezaplateny"),
            ("extra", "Extra", ""),
        ]

        summary_options = [
            ("orig_services_no_vat", "Povodna cena sluzieb bez DPH", fmt(totals.get("original_services_total", 0))),
            ("total_no_vat", "Cena bez DPH", fmt(totals.get("total_no_vat", 0))),
            ("vat", "DPH", fmt(totals.get("vat", 0))),
            ("total_with_vat", "Spolu s DPH", fmt(totals.get("total_with_vat", 0))),
            ("orig_services_with_vat", "Povodna cena sluzieb s DPH", fmt((totals.get("original_services_total", 0) or 0) * (1 + totals.get("vat_rate", 0)))),
        ]

        client = self.w.client_data()
        client_options = []
        def add_client_opt(code, label, value):
            if value:
                client_options.append((code, label, value))
        add_client_opt("name", "Meno", client.get("name", ""))
        add_client_opt("email", "Email", client.get("email", ""))
        add_client_opt("address", "Adresa", client.get("address", ""))
        add_client_opt("phone", "Mobil", client.get("phone", "") or client.get("mobile", ""))
        add_client_opt("company", "Nazov odberatela", client.get("company", ""))
        add_client_opt("ico", "ICO", client.get("ico", ""))
        add_client_opt("dic", "DIC", client.get("dic", ""))
        add_client_opt("icdph", "IC DPH", client.get("icdph", ""))

        available_sections = {
            "supplier_lines": supplier_options,
            "payment_lines": payment_options,
            "client_lines": client_options,
            "summary_lines": summary_options,
        }

        def save_data(new_data: dict) -> None:
            self._pdf_content[doc_type] = new_data
            save_pdf_content(self._pdf_content)

        PdfContentDialog(
            self.w,
            doc_type=doc_type,
            data=data,
            on_save=save_data,
            available_fields=available_sections,
            firm_name=self.w._supplier_display_name(),
        )

    def _export_pdf_with_type(self, doc_type: str) -> None:
        if not self.w.has_client_data():
            messagebox.showwarning("Export PDF", "Vypln aspon jeden udaj o klientovi alebo firme.")
            return
        doc_map = {
            "quote": ("Cenova ponuka", export_quote_pdf, "ponuka"),
            "proforma": ("Predfaktura", export_proforma_pdf, "predfaktura"),
            "invoice": ("Faktura", export_invoice_pdf, "faktura"),
        }
        title, exporter, default_name = doc_map.get(doc_type, doc_map["quote"])
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
            title=title,
            initialfile=f"{default_name}.pdf",
        )
        if not path:
            return
        out_path = Path(path)

        payload = self._build_payload_for_preview(doc_type, title=title)
        if payload is None:
            return
        # apply per-document overrides for freeform text sections
        defaults = self._build_section_content(doc_type, payload)
        payload["supplier_lines_override"] = defaults.get("supplier_lines", [])
        payload["payment_lines_override"] = defaults.get("payment_lines", [])
        payload["client_lines_override"] = defaults.get("client_lines", [])
        payload["summary_lines_override"] = defaults.get("summary_lines", [])
        try:
            total_with_vat = payload.get("totals", {}).get("total_with_vat", 0)
            payload["qr_data"] = f"{title}:{payload.get('invoice_no','')}:SUMA{total_with_vat}"
        except Exception:
            pass
        try:
            exporter(out_path, payload)
        except PermissionError:
            messagebox.showerror(
                title,
                "Export zlyhal: subor je pravdepodobne otvoreny alebo zamknuty.\n"
                "Zatvor PDF prehliadac alebo zvol iny nazov umiestnenia a skus znova.",
            )
            return
        except Exception as exc:  # pragma: no cover (UI feedback)
            messagebox.showerror(title, f"Export zlyhal:\n{exc}")
            return
        messagebox.showinfo(title, f"PDF ulozene:\n{out_path}")

    def _build_payload_for_preview(self, doc_type: str, title: str | None = None) -> dict | None:
        selections = []
        for s in self.w._catalog.services:
            if s.code not in self.w._selected_services:
                continue
            eff = self.w._services.with_effective_price(s)
            qty = self.w._service_qty.get(s.code, 1)
            original_price = self.w._base_prices.get(s.code, (s.price, s.price2))[0]
            selections.append((eff, qty, original_price))

        payload = build_invoice_payload(
            self.w._current_package,
            selections,
            self.w.client_data(),
            self.w._pricing,
            supplier=self.w.supplier_data(),
            vat_rate=self.w._vat_rate,
            vat_mode=self.w._vat_mode,
            discount_pct=self.w._discount_pct,
            doc_title=title or doc_type,
            original_package_price=self.w._current_package_raw.base_price if self.w._current_package_raw else None,
        )
        return payload

    def _build_section_defaults(self, doc_type: str, payload: dict) -> dict:
        fmt = self.w._pricing.format_currency
        supplier_lines: list[str] = []
        for f in self.w.supplier_fields():
            label = (f.get("label") or f.get("code") or "").strip()
            val = (f.get("value") or "").strip()
            if label and val:
                supplier_lines.append(f"{label} {val}")
            elif label:
                supplier_lines.append(label)

        invoice_no = payload.get("invoice_no", "")
        issue_date = payload.get("issue_date", "")
        package_label = payload.get("package", "-") or "-"
        payment_lines = [
            f"Variabilny symbol: {invoice_no}",
            f"Datum vystavenia: {issue_date}",
            f"Balik: {package_label}",
            "Stav: Nezaplateny",
        ]

        client = payload.get("client", {}) or {}
        client_lines = []
        def add_client_line(label: str, value: str) -> None:
            if value:
                client_lines.append(f"{label}: {value}")
        add_client_line("Meno", client.get("name", ""))
        add_client_line("Email", client.get("email", ""))
        add_client_line("Adresa", client.get("address", ""))
        add_client_line("ICO", client.get("ico", ""))
        add_client_line("DIC", client.get("dic", ""))
        add_client_line("IC DPH", client.get("icdph", ""))

        totals = payload.get("totals", {}) or {}
        vat_rate = totals.get("vat_rate", 0.0) or 0.0
        orig_services_total = totals.get("original_services_total", 0.0) or 0.0
        total_no_vat = totals.get("total_no_vat", 0.0) or 0.0
        vat_val = totals.get("vat", 0.0) or 0.0
        total_with_vat = totals.get("total_with_vat", 0.0) or 0.0
        summary_lines = [
            f"Povodna cena sluzieb: {fmt(orig_services_total)}",
            f"Cena bez DPH: {fmt(total_no_vat)}",
            f"DPH ({int(vat_rate*100)}%): {fmt(vat_val)}",
            f"Spolu s DPH: {fmt(total_with_vat)}",
        ]

        return {
            "supplier_lines": supplier_lines,
            "payment_lines": payment_lines,
            "client_lines": client_lines,
            "summary_lines": summary_lines,
        }

    def _build_section_content(self, doc_type: str, payload: dict) -> dict:
        """
        Combine ulozene uzivatelske upravy s defaultmi.
        Ak uzivatel odstrani nejaky riadok (napr. IBAN), ponechame prazdny zoznam a neregenerujeme ho z defaultov.
        """
        defaults = self._build_section_defaults(doc_type, payload)
        saved = self._pdf_content.get(doc_type, {}) or {}
        result: dict[str, list[str]] = {}
        for key, def_lines in defaults.items():
            if key in saved:
                result[key] = list(saved.get(key) or [])
            else:
                result[key] = def_lines
        return result

    def reset_selection(self) -> None:
        self.w._selected_services.clear()
        self.w._current_package = None
        self.w._current_package_raw = None
        self.w._service_qty = {s.code: 1 for s in self.w._catalog.services}
        self.w._discount_pct = 0.0
        self.w.package_selector.select_none()
        self.w.service_area.refresh_selection(self.w._selected_services, self.w._service_qty)
        self.w._services.update_summary()
        self.update_save_buttons()
