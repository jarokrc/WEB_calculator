"""
PDF export: original light layout with strike-through original prices.
Minimal implementation (no external deps).
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Mapping, Sequence

from web_calculator.utils.qr import make_qr_matrix


# -------- Helpers --------
def _normalize_ascii(text: str) -> str:
    """Remove diacritics to stay compatible with built-in PDF Type1 fonts."""
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _escape_pdf_text(text: str) -> str:
    ascii_text = _normalize_ascii(text)
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_xref_entry(offset: int) -> str:
    return f"{offset:010d} 00000 n \n"


def _format_currency(value: float) -> str:
    return f"{value:,.2f} EUR"


def _draw_text(lines: Iterable[str], x: int, y: int, font: str, size: int, leading: int | None = None) -> str:
    out = []
    spacing = leading or (size + 2)
    for line in lines:
        safe = _escape_pdf_text(str(line))
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


def _draw_price_line(label: str, value: float, orig: float | None, x: int, y: int, font: str, size: int) -> str:
    """
    Draw price label; if orig provided and different, draw muted orig one line above.
    """
    parts = []
    if orig is not None and abs(orig - value) > 0.01:
        orig_text = f"{label}: {_format_currency(orig)}"
        muted_size = int(size * 0.8)
        parts.append(_draw_text([orig_text], x, y + size + 4, font, muted_size))
        strike_len = len(orig_text) * (muted_size * 0.52)
        line_y = y + size + 4 + muted_size * 0.3
        parts.append(f"0.55 0.55 0.55 RG {muted_size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    parts.append(_draw_text([f"{label}: {_format_currency(value)}"], x, y, font, size))
    return "".join(parts)


def _draw_price_cell(current: float, original: float | None, x: int, y: int, font: str, size: int) -> str:
    if original is not None:
        orig_font_size = int(size * 0.8)
        orig_color = "0.55 0.55 0.55"
        orig_text = f"{orig_color} rg {orig_color} RG " + _draw_text([_format_currency(original)], x, y + size + 4, font, orig_font_size)
        # strike line over original
        strike_len = len(_format_currency(original)) * (orig_font_size * 0.55)
        line_y = y + size + 4 + orig_font_size * 0.3
        strike = f"{orig_color} RG {orig_font_size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n"
        return orig_text + strike + "0 0 0 rg 0 0 0 RG " + _draw_text([_format_currency(current)], x, y, font, size)
    return "0 0 0 rg 0 0 0 RG " + _draw_text([_format_currency(current)], x, y, font, size)


def _draw_total_row(label: str, value: float, orig: float | None, x: int, y: int) -> str:
    """
    Render totals row with original (grey, strike) above current (bold).
    y is baseline for current.
    """
    parts = []
    if orig is not None and abs(orig - value) > 0.01:
        color = "0.55 0.55 0.55"
        size = 10
        parts.append(f"{color} rg {color} RG ")
        orig_text = f"Pôvodná {label}: {_format_currency(orig)}"
        parts.append(_draw_text([orig_text], x, y + size + 6, "/F1", size))
        strike_len = len(orig_text) * (size * 0.52)
        line_y = y + size + 6 + size * 0.3
        parts.append(f"{color} RG {size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    parts.append("0 0 0 rg 0 0 0 RG ")
    parts.append(_draw_text([f"{label}: {_format_currency(value)}"], x, y, "/F2", 12))
    return "".join(parts)


# -------- Main export --------
def export_simple_pdf(path: Path, invoice_payload: Mapping) -> None:
    """
    Render a styled 1-page invoice PDF with balanced blocks and readable spacing.
    """
    # Geometry
    page_w, page_h = 595, 842  # A4 points
    card_x, card_y, card_w, card_h = 32, 60, 531, 720
    card_top = card_y + card_h

    # Colors
    dark = "0.12 0.16 0.22"
    light = "0.96 0.97 0.99"
    border = "0.82 0.86 0.90"
    accent = "0.99 0.56 0.09"
    muted = "0.45 0.50 0.56"
    row_alt = "0.94 0.95 0.97"

    invoice_no = str(invoice_payload.get("invoice_no", "-"))
    issue_date = str(invoice_payload.get("issue_date", ""))
    title = invoice_payload.get("doc_title", "Cenova ponuka")
    supplier = invoice_payload.get("supplier", {})
    client = invoice_payload.get("client", {})
    totals = invoice_payload.get("totals", {})
    items = invoice_payload.get("items", [])
    # Recompute original extras from items if not provided to ensure consistency
    def _sum_original_extras(itms: Sequence[Mapping]) -> float:
        total = 0.0
        for it in itms:
            try:
                qty = float(it.get("qty", 1) or 1)
            except (TypeError, ValueError):
                qty = 1.0
            # current unit_price/total (fallbacks only for deriving original when missing)
            try:
                unit_price = float(it.get("unit_price", 0.0) or 0.0)
            except (TypeError, ValueError):
                unit_price = 0.0
            # derive original_total
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
                # fallback to current total
                try:
                    current_total = float(it.get("total", unit_price * qty) or (unit_price * qty))
                except (TypeError, ValueError):
                    current_total = unit_price * qty
                orig_total = current_total
            total += float(orig_total)
        return total
    recomputed_original_extras = _sum_original_extras(items)
    qr_data = invoice_payload.get("qr_data") or invoice_no
    qr_matrix = make_qr_matrix(qr_data) if qr_data else None
    qr_size = 3  # px per module

    content_parts: list[str] = []

    # Background card
    content_parts.append(f"{light} rg {border} RG ")
    content_parts.append(_draw_rect(card_x, card_y, card_w, card_h, stroke=True, fill=True))
    content_parts.append("0 0 0 rg 0 0 0 RG ")

    # Header
    header_y = card_top - 18
    content_parts.append(_draw_text([f"{title} c. {invoice_no}"], card_x + 16, header_y, "/F2", 18))
    content_parts.append(_draw_text([f"Datum vystavenia: {issue_date}"], card_x + 16, header_y - 20, "/F1", 11))

    # Column geometry
    col_gap = 16
    col_width = 248
    left_x = card_x + 16
    right_x = left_x + col_width + col_gap

    # Supplier box
    box_height = 130
    supplier_y = header_y - 30 - box_height
    supplier_lines = [
        "Dodavatel",
        supplier.get("name", ""),
        supplier.get("address", ""),
        f"ICO: {supplier.get('ico','')}",
        f"DIC: {supplier.get('dic','')}",
        supplier.get("email", "") or "",
    ]
    content_parts.append(f"{border} RG ")
    content_parts.append(_draw_rect(left_x, supplier_y, col_width, box_height, stroke=True, fill=False))
    content_parts.append(_draw_text(supplier_lines, left_x + 12, supplier_y + box_height - 16, "/F2", 11, leading=13))

    # Client box
    client_y = supplier_y - box_height - 10
    client_lines_raw = [
        "Fakturacny profil",
        client.get("name", ""),
        client.get("address", ""),
        f"ICO: {client.get('ico','')}" if client.get("ico") else "",
        f"DIC: {client.get('dic','')}" if client.get("dic") else "",
        f"IC DPH: {client.get('icdph','')}" if client.get("icdph") else "",
        client.get("email", ""),
    ]
    client_lines: list[str] = []
    for line in client_lines_raw:
        if not line:
            continue
        client_lines.extend(wrap(line, 42) or ["-"])
    content_parts.append(_draw_rect(left_x, client_y, col_width, box_height, stroke=True, fill=False))
    content_parts.append(_draw_text(client_lines, left_x + 12, client_y + box_height - 16, "/F2", 11, leading=13))

    # Totals helpers
    vat_rate = float(totals.get("vat_rate", 0.23))
    discount_pct = float(totals.get("discount_pct", 0.0) or 0.0)
    discount_amount = float(totals.get("discount_amount", 0.0) or 0.0)
    total_before_discount = float(totals.get("total_before_discount", totals.get("total_no_vat", 0.0) + discount_amount))
    total_no_vat = float(totals.get("total_no_vat", total_before_discount - discount_amount))
    vat_value = float(totals.get("vat", total_no_vat * vat_rate))
    total_with_vat = float(totals.get("total_with_vat", total_no_vat + vat_value))
    # Originals for strike-through
    orig_base = float(totals.get("original_base", totals.get("base", total_no_vat)))
    # Use provided original_extras if present; otherwise, use recomputed from items
    if "original_extras" in totals:
        try:
            orig_extras = float(totals.get("original_extras", 0.0))
        except (TypeError, ValueError):
            orig_extras = recomputed_original_extras
    else:
        orig_extras = recomputed_original_extras
    # Original subtotal is before discount; prefer provided value, fallback to sum of orig parts
    try:
        orig_subtotal = float(totals.get("original_total_before_discount", orig_base + orig_extras))
    except (TypeError, ValueError):
        orig_subtotal = orig_base + orig_extras
    orig_vat = float(totals.get("original_vat", orig_subtotal * vat_rate))
    orig_total = float(totals.get("original_total", orig_subtotal + orig_vat))
    package_label = invoice_payload.get("package", "-")
    # Prepare a package row for display so that table sums match header totals
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
        display_items.append({
            "name": f"Balik {package_label}",
            "qty": 1,
            "unit_price": base_current,
            "total": base_current,
            "original_unit_price": base_original,
            "original_total": base_original,
        })
    # append real service items
    display_items.extend(items)

    # Payment block (right column top)
    payment_h = 140
    payment_y = supplier_y - 10  # posun mierne vyssie
    content_parts.append(_draw_rect(right_x, payment_y, col_width, payment_h, stroke=True, fill=False))
    pay_lines = [
        f"Variabilny symbol: {invoice_no}",
        f"Datum vystavenia: {issue_date}",
        f"Balik: {package_label}",
        "Stav: Zaplatene",
    ]
    content_parts.append(_draw_text(["Prehlad platby"], right_x + 12, payment_y + payment_h - 16, "/F2", 11, leading=13))
    content_parts.append(_draw_text(pay_lines, right_x + 12, payment_y + payment_h - 32, "/F1", 10, leading=12))

    # QR inside payment block (top-right)
    qr_side = 90
    qr_draw = ""
    if qr_matrix:
        qr_scale = max(2, qr_side // max(len(qr_matrix), len(qr_matrix[0])))
        qr_draw = _draw_qr(qr_matrix, right_x + col_width - qr_scale * len(qr_matrix) - 12, payment_y + payment_h - 12, qr_scale)
    elif qr_data:
        qr_draw = _draw_rect(right_x + col_width - qr_side - 12, payment_y + payment_h - qr_side - 12, qr_side, qr_side, stroke=True, fill=False) + _draw_text(["QR"], right_x + col_width - qr_side//2 - 8, payment_y + payment_h - qr_side//2 - 12, "/F2", 12)
    content_parts.append(qr_draw)

    # Totals block under payment/QR
    totals_y = payment_y - 60  # posun vyssie
    # Totals mini-table with larger spacing
    totals_lines = [
        ("Cena bez DPH", total_no_vat, orig_subtotal),
        (f"DPH ({int(vat_rate*100)}%)", vat_value, orig_vat),
        ("Spolu s DPH", total_with_vat, orig_total),
    ]
    box_w = 240
    box_h = 120
    totals_box_y = totals_y - 70
    content_parts.append(_draw_rect(right_x + 6, totals_box_y, box_w, box_h, stroke=True, fill=False))
    row_y = totals_box_y + box_h - 24
    for label, val, orig in totals_lines:
        content_parts.append(_draw_total_row(label, val, orig, right_x + 16, row_y))
        row_y -= 34


    # Items table header
    table_header_y = client_y - 40
    table_x = left_x
    table_w = card_w - 32
    content_parts.append(f"{dark} rg {dark} RG ")
    content_parts.append(_draw_rect(table_x, table_header_y, table_w, 30, stroke=True, fill=True))
    content_parts.append("1 1 1 rg 1 1 1 RG ")
    col_x = [table_x + 10, table_x + 260, table_x + 360, table_x + 450]
    headers = ["Nazov", "Mnozstvo", "bez DPH", "s DPH"]
    for hx, text in zip(col_x, headers):
        content_parts.append(_draw_text([text], hx, table_header_y + 20, "/F2", 10))

    # Item rows
    row_y = table_header_y - 26
    available_rows = max(1, int((row_y - (card_y + 18)) / 32))
    extra_items = []
    table_items = list(display_items)
    if len(table_items) > available_rows:
        extra_items = table_items[available_rows - 1 :]
        table_items = table_items[: available_rows - 1]

    def _line_totals(item: Mapping) -> tuple[float, float, float | None, float | None]:
        """
        Compute per-item totals consistently from unit prices and quantities.
        Prefer recomputation from unit_price * qty to avoid stale payload totals.
        If original_unit_price or original_total are provided, compute original totals for strike-through.
        """
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
            orig_unit_f: float | None
            if orig_unit is None and item.get("original_total") is not None and qty:
                # derive original unit from original_total when possible
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

    for idx, item in enumerate(table_items):
        total_no_vat, total_with_vat, orig_no_vat, orig_with_vat = _line_totals(item)
        has_strike = (orig_no_vat is not None and abs(orig_no_vat - total_no_vat) > 0.01) or (orig_with_vat is not None and abs(orig_with_vat - total_with_vat) > 0.01)
        rh = 26 if not has_strike else 36
        if idx % 2 == 0:
            content_parts.append(f"{row_alt} rg ")
            content_parts.append(_draw_rect(table_x, row_y, table_w, rh, stroke=False, fill=True))
        content_parts.append("0 0 0 rg 0 0 0 RG ")
        content_parts.append(_draw_rect(table_x, row_y, table_w, rh, stroke=True, fill=False))
        # values
        name = item.get("name", "")
        qty = item.get("qty", "-")
        row_values = [
            name,
            f"x{qty}",
        ]
        content_parts.append(_draw_text([_normalize_ascii(name)], col_x[0], row_y + rh - 26, "/F1", 10))
        content_parts.append(_draw_text([f"x{qty}"], col_x[1], row_y + rh - 26, "/F1", 10))
        content_parts.append(_draw_price_cell(total_no_vat, orig_no_vat, col_x[2], row_y + rh - 26, "/F1", 10))
        content_parts.append(_draw_price_cell(total_with_vat, orig_with_vat, col_x[3], row_y + rh - 26, "/F1", 10))
        row_y -= rh

    # Build pages (support multiple if extra_items exist)
    content_streams = ["".join(content_parts)]

    while extra_items:
        # new page content with only table
        content_parts_extra: list[str] = []
        # header for next page
        # title for overflow page
        content_parts_extra.append(_draw_text(["Dalsie polozky"], left_x + 16, page_h - 36, "/F2", 12))
        next_items = extra_items
        extra_items = []
        row_y = page_h - 80
        available_rows_page = max(1, int((row_y - 60) / 32))
        if len(next_items) > available_rows_page:
            extra_items = next_items[available_rows_page - 1 :]
            next_items = next_items[: available_rows_page - 1]
        # table header
        content_parts_extra.append(f"{dark} rg {dark} RG ")
        content_parts_extra.append(_draw_rect(table_x, row_y, table_w, 30, stroke=True, fill=True))
        content_parts_extra.append("1 1 1 rg 1 1 1 RG ")
        for hx, text in zip(col_x, headers):
            content_parts_extra.append(_draw_text([text], hx, row_y + 20, "/F2", 10))
        row_y -= 26
        for idx, item in enumerate(next_items):
            total_no_vat, total_with_vat, orig_no_vat, orig_with_vat = _line_totals(item)
            has_strike = (orig_no_vat is not None and abs(orig_no_vat - total_no_vat) > 0.01) or (orig_with_vat is not None and abs(orig_with_vat - total_with_vat) > 0.01)
            rh = 26 if not has_strike else 36
            if idx % 2 == 0:
                content_parts_extra.append(f"{row_alt} rg ")
                content_parts_extra.append(_draw_rect(table_x, row_y, table_w, rh, stroke=False, fill=True))
            content_parts_extra.append("0 0 0 rg 0 0 0 RG ")
            content_parts_extra.append(_draw_rect(table_x, row_y, table_w, rh, stroke=True, fill=False))
            name = item.get("name", "")
            qty = item.get("qty", "-")
            content_parts_extra.append(_draw_text([_normalize_ascii(name)], col_x[0], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_text([f"x{qty}"], col_x[1], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_price_cell(total_no_vat, orig_no_vat, col_x[2], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_price_cell(total_with_vat, orig_with_vat, col_x[3], row_y + rh - 26, "/F1", 10))
            row_y -= rh
        content_streams.append("".join(content_parts_extra))

    # Assemble PDF objects dynamically
    streams_bytes = [s.encode("ascii", "ignore") for s in content_streams]
    lengths = [len(s) for s in streams_bytes]

    objs: list[bytes] = []
    # Root and pages placeholder added later
    # Fonts
    font1_id = 3
    font2_id = 4
    pages_kids: list[int] = []

    # Content + page objects
    next_obj_id = 5
    for idx, (stream, length) in enumerate(zip(streams_bytes, lengths)):
        content_id = next_obj_id
        page_id = next_obj_id + 1
        pages_kids.append(page_id)
        objs.append(f"{content_id} 0 obj << /Length {length} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n")
        objs.append(
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R /Resources << /Font << /F1 {font1_id} 0 R /F2 {font2_id} 0 R >> >> >> endobj\n".encode(
                "ascii"
            )
        )
        next_obj_id += 2

    # Pages object
    kids_ref = " ".join(f"{kid} 0 R" for kid in pages_kids)
    pages_obj = f"2 0 obj << /Type /Pages /Count {len(pages_kids)} /Kids [{kids_ref}] >> endobj\n".encode("ascii")
    catalog_obj = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    font1_obj = b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    font2_obj = b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n"

    objs = [catalog_obj, pages_obj, font1_obj, font2_obj] + objs

    # Assemble offsets/xref
    header = b"%PDF-1.4\n"
    offsets = [0]
    pdf_body = bytearray()
    current_offset = len(header)
    for obj in objs:
        offsets.append(current_offset)
        pdf_body += obj
        current_offset += len(obj)

    xref_entries = ["0000000000 65535 f \n"] + [_format_xref_entry(off) for off in offsets[1:]]
    xref = ("xref\n0 %d\n" % len(offsets)).encode("ascii") + "".join(xref_entries).encode("ascii")
    startxref = len(header) + len(pdf_body) + len(xref)
    trailer = f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("ascii")

    pdf_bytes = header + pdf_body + xref + trailer
    path.write_bytes(pdf_bytes)
