from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service


from web_calculator.core.services.supplier import load_supplier
from web_calculator.utils.variable_symbol import generate_variable_symbol

SUPPLIER = load_supplier()


def _format_client_block(client: dict) -> list[str]:
    return [
        "Fakturacny profil",
        f"{client.get('name') or client.get('company') or '-'}",
        client.get("address") or "-",
        client.get("ico") or "",
        client.get("dic") or "",
        client.get("icdph") or "",
        client.get("email") or "",
    ]


def _format_supplier_block() -> list[str]:
    return [
        "Dodavatel",
        SUPPLIER["name"],
        SUPPLIER["address"],
        f"ICO: {SUPPLIER['ico']}",
        f"DIC: {SUPPLIER['dic']}",
    ]


def build_invoice_payload(
    package: Package | None,
    selections: Iterable[tuple[Service, int] | tuple[Service, int, float]],
    client: dict,
    pricing: PricingEngine,
    supplier: dict | None = None,
    vat_rate: float = 0.23,
    vat_mode: str = "add",
    qr_data: Optional[str] = None,
    doc_title: str = "Cenova ponuka",
    discount_pct: float = 0.0,
    original_package_price: float | None = None,
) -> dict:
    """
    Build structured payload for invoice PDF rendering.
    Zlava sa uplatnuje na sumu bez DPH.
    - selections mozu obsahovat aj povodnu cenu: (service, qty, original_price).
    """
    selections = list(selections)
    breakdown = pricing.summarize(selections)
    discount_amount = breakdown.total * (discount_pct / 100.0)
    if vat_mode == "included":
        total_with_vat = max(0.0, breakdown.total - discount_amount)
        subtotal_no_vat = total_with_vat / (1 + vat_rate) if vat_rate > 0 else total_with_vat
        vat = total_with_vat - subtotal_no_vat
    else:
        subtotal_no_vat = max(0.0, breakdown.total - discount_amount)
        vat = subtotal_no_vat * vat_rate
        total_with_vat = subtotal_no_vat + vat
    today = date.today()
    issue_date = today.strftime("%d/%m/%Y")
    invoice_no = generate_variable_symbol()

    base_raw = package.base_price if package else 0.0
    base_original_raw = original_package_price if original_package_price is not None else base_raw
    if vat_mode == "included" and vat_rate > 0:
        base_current = base_raw / (1 + vat_rate)
        base_original = base_original_raw / (1 + vat_rate)
    else:
        base_current = base_raw
        base_original = base_original_raw

    items = []
    extras_original = 0.0
    extras_current = 0.0
    for selection in selections:
        if len(selection) == 3:
            svc, qty, orig_price = selection  # type: ignore[misc]
        else:
            svc, qty = selection  # type: ignore[misc]
            orig_price = svc.price
        if vat_mode == "included" and vat_rate > 0:
            unit_no_vat = svc.price / (1 + vat_rate)
            orig_unit_no_vat = float(orig_price) / (1 + vat_rate)
        else:
            unit_no_vat = svc.price
            orig_unit_no_vat = float(orig_price)

        line_total = unit_no_vat * qty
        original_total = float(orig_unit_no_vat) * qty
        extras_original += original_total
        extras_current += line_total
        items.append(
            {
                "name": svc.label,
                "unit": svc.unit,
                "qty": qty,
                "unit_price": unit_no_vat,
                "total": line_total,
                "original_unit_price": float(orig_unit_no_vat),
                "original_total": original_total,
            }
        )

    total_original_before_discount = base_original + extras_original
    original_services_total = extras_original
    base_for_totals = base_current if vat_mode == "included" else breakdown.base

    return {
        "invoice_no": invoice_no,
        "issue_date": issue_date,
        "package": package.code if package else "-",
        "supplier": supplier or SUPPLIER,
        "client": {
            "name": client.get("name") or client.get("company") or "-",
            "address": client.get("address") or "-",
            "ico": client.get("ico") or "",
            "dic": client.get("dic") or "",
            "icdph": client.get("icdph") or "",
            "email": client.get("email") or "",
        },
        "totals": {
            "base": base_for_totals,
            "extras": extras_current if vat_mode == "included" else breakdown.extras,
            "original_base": base_original,
            "original_extras": extras_original,
            # Original services total is calculated "bez balika" (sum of service base prices).
            # This value is used for the "povodna cena sluzieb" comparison in PDF.
            "original_services_total": original_services_total,
            "discount_pct": discount_pct,
            "discount_amount": discount_amount,
            "total_before_discount": breakdown.total,
            "total_no_vat": subtotal_no_vat,
            "vat": vat,
            "total_with_vat": total_with_vat,
            "vat_rate": vat_rate,
            "vat_mode": vat_mode,
            "original_total_before_discount": total_original_before_discount,
        },
        "items": items,
        "qr_data": qr_data,
        "doc_title": doc_title,
    }
