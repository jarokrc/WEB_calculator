from __future__ import annotations

import unicodedata
from typing import Iterable, Sequence

from web_calculator.utils.pdf.core import fonts
from web_calculator.utils.pdf.core.totals import format_currency


def _normalize_ascii(text: str) -> str:
    """Remove diacritics to stay compatible with built-in PDF Type1 fonts."""
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _escape_pdf_text(text: str) -> str:
    ascii_text = _normalize_ascii(text)
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _draw_text(lines: Iterable[str], x: int, y: int, font: str, size: int, leading: int | None = None) -> str:
    font_map = fonts.get_font_map()
    out = []
    spacing = leading or (size + 2)
    for line in lines:
        text = str(line)
        if font in font_map:
            hex_text = font_map[font].encode_text_hex(text)
            out.append(f"BT {font} {size} Tf {x} {y} Td <{hex_text}> Tj ET\n")
        else:
            safe = _escape_pdf_text(text)
            out.append(f"BT {font} {size} Tf {x} {y} Td ({safe}) Tj ET\n")
        y -= spacing
    return "".join(out)


def _draw_rect(x: int, y: int, w: int, h: int, stroke: bool = True, fill: bool = False) -> str:
    if fill and stroke:
        op = "B"
    elif fill:
        op = "f"
    else:
        op = "S"
    return f"{x} {y} {w} {h} re {op}\n"


def _draw_qr(matrix: Sequence[Sequence[bool]] | None, x: int, y: int, size: int) -> str:
    if not matrix:
        return ""
    ops = []
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    for r in range(rows):
        for c in range(cols):
            if matrix[r][c]:
                px = x + c * size
                py = y - (r + 1) * size  # PDF y grows up
                ops.append(_draw_rect(px, py, size, size, stroke=False, fill=True))
    return "".join(ops)


def _draw_price_cell(current: float, original: float | None, x: int, y: int, font: str, size: int) -> str:
    if original is not None and abs(original - current) > 0.01:
        orig_font_size = max(6, int(size * 0.8))
        orig_color = "0.55 0.55 0.55"
        orig_text = f"{orig_color} rg {orig_color} RG " + _draw_text([format_currency(original)], x, y + size + 4, font, orig_font_size)
        strike_len = len(format_currency(original)) * (orig_font_size * 0.52)
        line_y = y + size + 4 + orig_font_size * 0.3
        strike = f"{orig_color} RG {orig_font_size * 0.06:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n"
        return orig_text + strike + "0 0 0 rg 0 0 0 RG " + _draw_text([format_currency(current)], x, y, font, size)
    return "0 0 0 rg 0 0 0 RG " + _draw_text([format_currency(current)], x, y, font, size)


def _draw_total_row(label: str, value: float, orig: float | None, x: int, y: int) -> str:
    parts = []
    if orig is not None and abs(orig - value) > 0.01:
        color = "0.55 0.55 0.55"
        size = 9
        orig_text = f"Povodna {label}: {format_currency(orig)}"
        strike_len = len(orig_text) * (size * 0.52)
        line_y = y + 14 + size * 0.30
        parts.append(f"{color} rg {color} RG ")
        parts.append(_draw_text([orig_text], x, y + 14, "/F1", size))
        parts.append(f"{color} RG {size * 0.06:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    parts.append("0 0 0 rg 0 0 0 RG ")
    parts.append(_draw_text([f"{label}: {format_currency(value)}"], x, y, "/F2", 12))
    return "".join(parts)


def _draw_summary_lines(lines: list[str], x: int, y: int, header_font: str, header_size: int, body_font: str, body_size: int) -> str:
    out: list[str] = []
    spacing = body_size + 3
    for line in lines:
        text = str(line or "")
        lower = text.lower()
        if lower.startswith("povodna"):
            color = "0.55 0.55 0.55"
            out.append(f"{color} rg {color} RG ")
            out.append(_draw_text([text], x, y, body_font, body_size))
            strike_len = len(text) * (body_size * 0.52)
            line_y = y + body_size * 0.3
            out.append(f"{color} RG {body_size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
            out.append("0 0 0 rg 0 0 0 RG ")
        elif lower.startswith("spolu s dph"):
            out.append(_draw_text([text], x, y, header_font, header_size))
        else:
            out.append(_draw_text([text], x, y, body_font, body_size))
        y -= spacing
    return "".join(out)


def _format_currency(value: float) -> str:
    return format_currency(value)
