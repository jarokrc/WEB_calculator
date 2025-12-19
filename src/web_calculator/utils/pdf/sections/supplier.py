from __future__ import annotations

from typing import Iterable, Mapping

from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_text


def render_supplier(supplier_lines: Iterable[str], x: int, y: int, w: int, h: int, header_size: int, body_size: int) -> str:
    parts: list[str] = []
    parts.append(_draw_rect(x, y, w, h, stroke=True, fill=False))
    parts.append(_draw_text(["Dodavatel"], x + 12, y + h - 16, "/F2", header_size, leading=header_size + 1))
    parts.append(_draw_text(supplier_lines, x + 12, y + h - 32, "/F1", body_size, leading=body_size + 2))
    return "".join(parts)


def build_supplier_lines(supplier: Mapping) -> list[str]:
    s = supplier or {}
    lines = ["Dodavatel"]
    name = s.get("name") or s.get("company") or ""
    if name:
        lines.append(str(name))
    address = s.get("address") or ""
    if address:
        lines.append(str(address))
    known = {
        "ico": "ICO",
        "dic": "DIC",
        "icdph": "IC DPH",
        "iban": "IBAN",
        "email": "Email",
        "phone": "Tel",
    }
    for key, label in known.items():
        val = s.get(key, "")
        if val:
            lines.append(f"{label}: {val}")
    extras = [k for k in s.keys() if k not in known and k not in ("name", "company", "address")]
    for key in extras:
        val = s.get(key, "")
        if val:
            lines.append(f"{key}: {val}")
    return lines

