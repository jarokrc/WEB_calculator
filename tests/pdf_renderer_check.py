"""
Sanity skript pre PDF renderer:
- generuje viac scenarov (overflow tabulky, rozne DPH rezimy, overrides)
- zapisuje PDF do dist/ a report do vyvojarske_doplnky/pdf_renderer_report.json
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from web_calculator.utils.pdf.core.totals import format_currency
from web_calculator.utils.pdf.renderers.pdf_renderer import render_pdf


ROOT = Path(__file__).resolve().parents[1]  # .../WEB_calculator
DIST = ROOT / "dist"
REPORT_PATH = ROOT.parent / "vyvojarske_doplnky" / "pdf_renderer_report.json"


def _compute_totals(items, base: float, vat_rate: float) -> dict:
    total_no_vat = base
    for it in items:
        qty = float(it.get("qty", 1) or 1)
        unit = float(it.get("unit_price", 0.0) or 0.0)
        total_no_vat += qty * unit
    vat_value = total_no_vat * vat_rate
    total_with_vat = total_no_vat + vat_value
    return {
        "vat_rate": vat_rate,
        "vat": vat_value,
        "total_no_vat": total_no_vat,
        "total_with_vat": total_with_vat,
        "original_services_total": total_no_vat,
        "base": base,
        "original_base": base,
    }


def _base_payload() -> dict:
    items = [
        {"name": "Balik - SEO", "qty": 1, "unit_price": 60.0, "original_unit_price": 80.0},
        {"name": "Sluzba A", "qty": 2, "unit_price": 25.0, "original_unit_price": 30.0},
        {"name": "Sluzba B", "qty": 1, "unit_price": 40.0},
    ]
    base_price = 50.0
    totals = _compute_totals(items, base=base_price, vat_rate=0.2)
    return {
        "invoice_no": "TEST-001",
        "issue_date": "2025-12-19",
        "doc_title": "Sanity PDF",
        "package": "A1",
        "supplier": {
            "name": "Dodavatel s.r.o.",
            "address": "Testovacia 123, Bratislava",
            "ico": "12345678",
            "iban": "SK6800000000000000000000",
        },
        "client": {
            "name": "Odberatel a.s.",
            "address": "Hlavna 1, Kosice",
            "ico": "87654321",
            "email": "zakaznik@example.com",
        },
        "items": items,
        "totals": totals,
    }


def _scenario_basic_add() -> dict:
    return _base_payload()


def _scenario_vat_included() -> dict:
    payload = deepcopy(_base_payload())
    gross_total = 210.0
    vat_rate = 0.2
    net = gross_total / (1 + vat_rate)
    payload["items"] = [
        {"name": "Pausal IT podpora", "qty": 1, "unit_price": net},
        {"name": "Licencia", "qty": 1, "unit_price": 0.0, "total": 0.0},
    ]
    payload["totals"] = {
        "vat_rate": 0.0,  # hodnoty uz obsahuju DPH
        "vat": 0.0,
        "total_no_vat": gross_total,
        "total_with_vat": gross_total,
        "original_services_total": gross_total,
        "base": 0.0,
        "original_base": 0.0,
    }
    payload["summary_lines_override"] = [
        "Rezim: DPH zahrnuta v cene",
        f"Odhad DPH 20%: {format_currency(gross_total - net)}",
        f"Cena bez DPH (odhad): {format_currency(net)}",
        f"Spolu s DPH: {format_currency(gross_total)}",
    ]
    return payload


def _scenario_overflow() -> dict:
    payload = deepcopy(_base_payload())
    long_items = []
    for idx in range(1, 22):
        long_items.append(
            {
                "name": f"Polozka {idx:02d}",
                "qty": 1 + (idx % 3),
                "unit_price": 10.0 + idx,
                "original_unit_price": 12.0 + idx,
            }
        )
    payload["items"] = long_items
    payload["totals"] = _compute_totals(long_items, base=0.0, vat_rate=0.2)
    return payload


def _scenario_overrides() -> dict:
    payload = deepcopy(_base_payload())
    payload["supplier_lines_override"] = ["Dodavatel Override", "Pravna forma: s.r.o.", "Tel: +421 123 456 789"]
    payload["client_lines_override"] = ["Odberatel Override", "Kontakt: tester@example.com"]
    payload["payment_lines_override"] = [
        "Variabilny symbol: 999",
        "Platba: prevodom do 7 dni",
        "IBAN: SK6800000000000000000000",
    ]
    payload["summary_lines_override"] = [
        "Custom suma: test",
        f"Cena bez DPH: {format_currency(100)}",
        f"DPH 20%: {format_currency(20)}",
        f"Spolu: {format_currency(120)}",
    ]
    return payload


SCENARIOS = {
    "basic_add": _scenario_basic_add,
    "vat_included": _scenario_vat_included,
    "overflow_table": _scenario_overflow,
    "overrides": _scenario_overrides,
}


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, str]] = {}

    for name, factory in SCENARIOS.items():
        out_path = DIST / f"test_pdf_renderer_{name}.pdf"
        try:
            render_pdf(out_path, factory())
            results[name] = {"status": "ok", "output": str(out_path.relative_to(ROOT.parent))}
        except Exception as exc:  # pragma: no cover - diagnostika pri behu
            results[name] = {"status": "error", "error": str(exc)}

    REPORT_PATH.write_text(json.dumps({"pdf_renderer_check": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
