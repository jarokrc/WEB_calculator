from __future__ import annotations

from typing import Iterable, Mapping

from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_text, _draw_price_cell
from web_calculator.utils.pdf.core.layout_common import TABLE_ROW_HEIGHT, TABLE_HEADER_HEIGHT


def render_items_table(
    items: Iterable[Mapping],
    x: int,
    start_y: int,
    table_w: int,
    header_bg: str,
    row_alt: str,
    vat_rate: float,
    min_y: int = 36,
) -> tuple[list[str], list[Mapping]]:
    """
    Render items table (header + rows). Returns (content_parts, overflow_items).
    """
    content: list[str] = []
    col_x = [x + 10, x + 220, x + 320, x + 420]
    headers = ["Názov", "Množstvo", "bez DPH", "s DPH"]

    content.append(f"{header_bg} rg {header_bg} RG ")
    content.append(_draw_rect(x, start_y, table_w, TABLE_HEADER_HEIGHT, stroke=True, fill=True))
    content.append("1 1 1 rg 1 1 1 RG ")
    for hx, text in zip(col_x, headers):
        content.append(_draw_text([text], hx, start_y + 20, "/F2", 10))

    row_y = start_y - 26
    available_rows = max(1, int((row_y - min_y) / TABLE_ROW_HEIGHT))
    items_list = list(items)
    overflow: list[Mapping] = []
    if len(items_list) > available_rows:
        overflow = items_list[available_rows - 1 :]
        items_list = items_list[: available_rows - 1]

    def _line_totals(item: Mapping) -> tuple[float, float, float | None, float | None]:
        qty = float(item.get("qty", 1) or 1)
        unit_price = float(item.get("unit_price", 0.0) or 0.0)
        computed_total = unit_price * qty
        try:
            total_no_vat = float(item.get("total", computed_total) or computed_total)
        except (TypeError, ValueError):
            total_no_vat = computed_total
        total_with_vat = total_no_vat * (1 + vat_rate)

        orig_no_vat: float | None = None
        orig_with_vat: float | None = None
        has_orig = ("original_unit_price" in item) or ("original_total" in item)
        if has_orig:
            orig_unit = item.get("original_unit_price")
            if orig_unit is None and item.get("original_total") is not None and qty:
                try:
                    orig_unit_f = float(item.get("original_total", 0.0)) / qty
                except (TypeError, ValueError):
                    orig_unit_f = None
            else:
                try:
                    orig_unit_f = float(orig_unit) if orig_unit is not None else None
                except (TypeError, ValueError):
                    orig_unit_f = None
            if orig_unit_f is None:
                orig_unit_f = unit_price
            computed_orig_total = orig_unit_f * qty
            try:
                orig_no_vat = float(item.get("original_total", computed_orig_total) or computed_orig_total)
            except (TypeError, ValueError):
                orig_no_vat = computed_orig_total
            orig_with_vat = orig_no_vat * (1 + vat_rate)

        return total_no_vat, total_with_vat, orig_no_vat, orig_with_vat

    for idx, item in enumerate(items_list):
        total_no_vat, total_with_vat, orig_no_vat, orig_with_vat = _line_totals(item)
        rh = TABLE_ROW_HEIGHT
        if idx % 2 == 0:
            content.append(f"{row_alt} rg ")
            content.append(_draw_rect(x, row_y, table_w, rh, stroke=False, fill=True))
        content.append("0 0 0 rg 0 0 0 RG ")
        content.append(_draw_rect(x, row_y, table_w, rh, stroke=True, fill=False))
        name = item.get("name", "")
        qty = item.get("qty", "-")
        content.append(_draw_text([name], col_x[0], row_y + rh - 26, "/F1", 10))
        content.append(_draw_text([f"x{qty}"], col_x[1], row_y + rh - 26, "/F1", 10))
        content.append(_draw_price_cell(total_no_vat, orig_no_vat, col_x[2], row_y + rh - 26, "/F1", 10))
        content.append(_draw_price_cell(total_with_vat, orig_with_vat, col_x[3], row_y + rh - 26, "/F1", 10))
        row_y -= rh

    return content, overflow

