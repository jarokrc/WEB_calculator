from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service


SUPPLIER = {
    "name": "RedBlue Solutions s. r. o.",
    "ico": "55522467",
    "dic": "2122005897",
    "address": "Sadova 2719/3A, 905 01 Senica",
}


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
    vat_rate: float = 0.23,
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
    subtotal_no_vat = max(0.0, breakdown.total - discount_amount)
    vat = subtotal_no_vat * vat_rate
    today = date.today().isoformat()
    invoice_no = today.replace("-", "")

    base_original = original_package_price if original_package_price is not None else (package.base_price if package else 0.0)

    items = []
    extras_original = 0.0
    for selection in selections:
        if len(selection) == 3:
            svc, qty, orig_price = selection  # type: ignore[misc]
        else:
            svc, qty = selection  # type: ignore[misc]
            orig_price = svc.price
        line_total = svc.price * qty
        original_total = float(orig_price) * qty
        extras_original += original_total
        items.append(
            {
                "name": svc.label,
                "unit": svc.unit,
                "qty": qty,
                "unit_price": svc.price,
                "total": line_total,
                "original_unit_price": float(orig_price),
                "original_total": original_total,
            }
        )

    total_original_before_discount = base_original + extras_original
    original_services_total = extras_original

    return {
        "invoice_no": invoice_no,
        "issue_date": today,
        "package": package.code if package else "-",
        "supplier": SUPPLIER,
        "client": {
            "name": client.get("name") or client.get("company") or "-",
            "address": client.get("address") or "-",
            "ico": client.get("ico") or "",
            "dic": client.get("dic") or "",
            "icdph": client.get("icdph") or "",
            "email": client.get("email") or "",
        },
        "totals": {
            "base": breakdown.base,
            "extras": breakdown.extras,
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
            "total_with_vat": subtotal_no_vat + vat,
            "vat_rate": vat_rate,
            "original_total_before_discount": total_original_before_discount,
        },
        "items": items,
        "qr_data": qr_data,
        "doc_title": doc_title,
    }
