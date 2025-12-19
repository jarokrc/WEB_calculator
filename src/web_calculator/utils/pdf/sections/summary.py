from __future__ import annotations

from typing import Iterable

from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_summary_lines, _draw_text
from web_calculator.utils.pdf.core.totals import TotalsContext, format_currency


def render_summary(lines: Iterable[str], x: int, y: int, w: int, h: int, header_size: int, body_size: int) -> str:
    parts: list[str] = []
    parts.append(_draw_rect(x, y, w, h, stroke=True, fill=False))
    parts.append(_draw_text(["Suvaha"], x + 12, y + h - 16, "/F2", header_size, leading=header_size + 1))
    parts.append(
        _draw_summary_lines(
            list(lines),
            x + 12,
            y + h - 32,
            "/F2",
            header_size,
            "/F1",
            body_size,
        )
    )
    return "".join(parts)


def build_summary_lines(totals: TotalsContext) -> list[str]:
    return [
        f"Povodna cena sluzieb: {format_currency(totals.original_services_total)}",
        f"Cena bez DPH: {format_currency(totals.total_no_vat)}",
        f"DPH ({int(totals.vat_rate * 100)}%): {format_currency(totals.vat_value)}",
        f"Spolu s DPH: {format_currency(totals.total_with_vat)}",
    ]
