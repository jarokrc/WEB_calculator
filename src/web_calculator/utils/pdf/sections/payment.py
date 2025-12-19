from __future__ import annotations

from typing import Iterable, Mapping

from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_text, _draw_qr


def render_payment(pay_lines: Iterable[str], x: int, y: int, w: int, h: int, header_size: int, body_size: int, qr_matrix, qr_data: str | None) -> str:
    parts: list[str] = []
    parts.append(_draw_rect(x, y, w, h, stroke=True, fill=False))
    parts.append(_draw_text(["Prehlad platby"], x + 12, y + h - 16, "/F2", header_size, leading=header_size + 1))
    parts.append(_draw_text(pay_lines, x + 12, y + h - 32, "/F1", body_size, leading=body_size + 2))

    # QR vpravo hore
    qr_side = 90
    qr_draw = ""
    if qr_matrix:
        qr_scale = max(2, qr_side // max(len(qr_matrix), len(qr_matrix[0])))
        qr_draw = _draw_qr(qr_matrix, x + w - qr_scale * len(qr_matrix) - 12, y + h - 12, qr_scale)
    elif qr_data:
        qr_draw = _draw_rect(x + w - qr_side - 12, y + h - qr_side - 12, qr_side, qr_side, stroke=True, fill=False) + _draw_text(["QR"], x + w - qr_side // 2 - 8, y + h - qr_side // 2 - 12, "/F2", 12)
    parts.append(qr_draw)
    return "".join(parts)


def build_payment_lines(invoice_payload: Mapping, invoice_no: str, issue_date: str) -> list[str]:
    return [
        f"Variabilny symbol: {invoice_no}",
        f"Datum vystavenia: {issue_date}",
        f"Balik: {invoice_payload.get('package', '-') or '-'}",
        "Stav: Nezaplateny",
    ]
