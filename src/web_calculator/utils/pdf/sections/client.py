from __future__ import annotations

from textwrap import wrap
from typing import Iterable

from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_text


def render_client(client_lines: Iterable[str], x: int, y: int, w: int, h: int, header_size: int, body_size: int) -> str:
    parts: list[str] = []
    parts.append(_draw_rect(x, y, w, h, stroke=True, fill=False))
    parts.append(_draw_text(["Odberatel"], x + 12, y + h - 16, "/F2", header_size, leading=header_size + 1))
    parts.append(_draw_text(client_lines, x + 12, y + h - 32, "/F1", body_size, leading=body_size + 2))
    return "".join(parts)


def build_client_lines(client: dict, wrap_width: int = 42) -> list[str]:
    raw = [
        "Odberatel",
        client.get("name", ""),
        client.get("address", ""),
        f"ICO: {client.get('ico','')}" if client.get("ico") else "",
        f"DIC: {client.get('dic','')}" if client.get("dic") else "",
        f"IC DPH: {client.get('icdph','')}" if client.get("icdph") else "",
        client.get("email", ""),
    ]
    lines: list[str] = []
    for line in raw:
        if not line:
            continue
        lines.extend(wrap(line, wrap_width) or ["-"])
    return lines

