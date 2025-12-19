"""
Helpers to derive totals/original sums and prepared display items (balik + sluzby).
Mirrors legacy computations to keep PDF numbers consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


def format_currency(value: float) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return f"{numeric:,.2f} EUR"


def recompute_original_extras(items: Sequence[Mapping]) -> float:
    total = 0.0
    for it in items:
        try:
            qty = float(it.get("qty", 1) or 1)
        except (TypeError, ValueError):
            qty = 1.0
        try:
            unit_price = float(it.get("unit_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            unit_price = 0.0
        orig_total_val = it.get("original_total")
        orig_unit_val = it.get("original_unit_price")
        orig_total: float | None = None
        if orig_unit_val is not None:
            try:
                orig_unit = float(orig_unit_val)
                orig_total = orig_unit * qty
            except (TypeError, ValueError):
                orig_total = None
        if orig_total is None and orig_total_val is not None:
            try:
                orig_total = float(orig_total_val)
            except (TypeError, ValueError):
                orig_total = None
        if orig_total is None:
            try:
                current_total = float(it.get("total", unit_price * qty) or (unit_price * qty))
            except (TypeError, ValueError):
                current_total = unit_price * qty
            orig_total = current_total
        total += float(orig_total)
    return total


def prepare_display_items(payload: Mapping) -> tuple[list[Mapping], float]:
    """
    Return (display_items, recomputed_original_extras).
    Includes a synthetic package row when base>0.
    """
    totals = payload.get("totals", {}) or {}
    items = list(payload.get("items", []) or [])
    recomputed_original_extras = recompute_original_extras(items)
    package_label = payload.get("package", "-")
    display_items: list[Mapping] = []
    try:
        base_current = float(totals.get("base", 0.0) or 0.0)
    except (TypeError, ValueError):
        base_current = 0.0
    try:
        base_original = float(totals.get("original_base", base_current) or base_current)
    except (TypeError, ValueError):
        base_original = base_current
    if base_current > 0.0 or base_original > 0.0:
        display_items.append(
            {
                "name": f"Balik {package_label}",
                "qty": 1,
                "unit_price": base_current,
                "total": base_current,
                "original_unit_price": base_original,
                "original_total": base_original,
            }
        )
    display_items.extend(items)
    return display_items, recomputed_original_extras


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass(frozen=True)
class TotalsContext:
    vat_rate: float
    vat_value: float
    total_no_vat: float
    total_with_vat: float
    original_services_total: float


def derive_totals(totals: Mapping, recomputed_original_extras: float) -> TotalsContext:
    totals = totals or {}
    vat_rate = _safe_float(totals.get("vat_rate", 0.23), 0.0)
    vat_value = _safe_float(totals.get("vat", 0.0), 0.0)
    total_no_vat = _safe_float(totals.get("total_no_vat", 0.0), 0.0)
    total_with_vat_default = total_no_vat * (1 + vat_rate)
    total_with_vat = _safe_float(totals.get("total_with_vat", total_with_vat_default), total_with_vat_default)
    original_services_total = _safe_float(totals.get("original_services_total", recomputed_original_extras), recomputed_original_extras)
    return TotalsContext(
        vat_rate=vat_rate,
        vat_value=vat_value,
        total_no_vat=total_no_vat,
        total_with_vat=total_with_vat,
        original_services_total=original_services_total,
    )
