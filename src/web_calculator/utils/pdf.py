from __future__ import annotations

from pathlib import Path
from textwrap import wrap
import unicodedata
from typing import Iterable, Mapping, Sequence

from web_calculator.utils.qr import make_qr_matrix


def _normalize_ascii(text: str) -> str:
    """
    Remove diacritics to stay compatible with built-in PDF Type1 fonts (no Unicode embedding).
    Avoids question marks in output by downshifting to ASCII.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _escape_pdf_text(text: str) -> str:
    # Escape special characters; keep ASCII to avoid encoding issues.
    ascii_text = _normalize_ascii(text)
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_xref_entry(offset: int) -> str:
    return f"{offset:010d} 00000 n \n"


def _format_currency(value: float) -> str:
    return f"{value:,.2f} EUR"


def _draw_text(
    lines: Iterable[str], x: int, y: int, font: str, size: int, leading: int | None = None
) -> str:
    out = []
    spacing = leading or (size + 2)
    for line in lines:
        safe = _escape_pdf_text(str(line))
        out.append(f"BT {font} {size} Tf {x} {y} Td ({safe}) Tj ET\n")
        y -= spacing
    return "".join(out)


def _draw_rect(x: int, y: int, w: int, h: int, stroke: bool = True, fill: bool = False) -> str:
    op = ""
    if fill and stroke:
        op = "B"
    elif fill:
        op = "f"
    else:
        op = "S"
    return f"{x} {y} {w} {h} re {op}\n"


def _draw_qr(matrix: Sequence[Sequence[bool]], x: int, y: int, size: int) -> str:
    # matrix top-left at (x, y). size is pixel size.
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
    content_parts.append(
        _draw_text([f"Datum vystavenia: {issue_date}"], card_x + 16, header_y - 20, "/F1", 11)
    )

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
        f"IC DPH: {client.get("icdph","")}" if client.get("icdph") else "",
        client.get("email", ""),
    ]
    client_lines: list[str] = []
    for line in client_lines_raw:
        if not line:
            continue
        client_lines.extend(wrap(line, 42) or ["-"])
    content_parts.append(_draw_rect(left_x, client_y, col_width, box_height, stroke=True, fill=False))
    content_parts.append(
        _draw_text(client_lines, left_x + 12, client_y + box_height - 16, "/F2", 11, leading=13)
    )

    # Totals helpers
    vat_rate = totals.get("vat_rate", 0.23)
    discount_pct = float(totals.get("discount_pct", 0.0) or 0.0)
    discount_amount = float(totals.get("discount_amount", 0.0) or 0.0)
    total_before_discount = float(
        totals.get("total_before_discount", totals.get("total_no_vat", 0.0) + discount_amount)
    )
    total_no_vat = float(totals.get("total_no_vat", total_before_discount - discount_amount))
    vat_value = float(totals.get("vat", total_no_vat * vat_rate))
    total_with_vat = float(totals.get("total_with_vat", total_no_vat + vat_value))
    package_label = invoice_payload.get("package", "-")

    # Payment box with QR
    payment_h = 150
    payment_y = supplier_y
    content_parts.append(_draw_rect(right_x, payment_y, col_width, payment_h, stroke=True, fill=False))
    pay_lines = [
        f"Variabilny symbol: {invoice_no}",
        f"Datum vystavenia: {issue_date}",
        f"Balik: {package_label}",
        "Stav: Zaplatene",
        "",
        f"Pred zlavou: {_format_currency(total_before_discount)}",
        f"Zlava ({discount_pct:.2f}%): -{_format_currency(discount_amount)}",
        f"Bez DPH: {_format_currency(total_no_vat)}",
        f"DPH ({int(vat_rate*100)}%): {_format_currency(vat_value)}",
        f"Spolu s DPH: {_format_currency(total_with_vat)}",
    ]
    content_parts.append(
        _draw_text(["Prehlad platby"], right_x + 12, payment_y + payment_h - 16, "/F2", 11, leading=13)
    )
    content_parts.append(_draw_text(pay_lines, right_x + 12, payment_y + payment_h - 32, "/F1", 10, leading=12))

    if qr_matrix:
        qr_dim = len(qr_matrix)
        qr_px = qr_dim * qr_size
        qr_x = right_x + col_width - qr_px - 12
        qr_y = payment_y + payment_h - 10
        content_parts.append(accent + " RG " + accent + " rg ")
        content_parts.append(_draw_rect(qr_x - 4, qr_y - qr_px - 4, qr_px + 8, qr_px + 8, stroke=True, fill=False))
        content_parts.append("0 0 0 rg 0 0 0 RG ")
        content_parts.append(_draw_qr(qr_matrix, qr_x, qr_y, qr_size))

    # Totals box under payment
    totals_h = 120
    totals_y = client_y
    content_parts.append(_draw_rect(right_x, totals_y, col_width, totals_h, stroke=True, fill=False))
    totals_lines = [
        "Sumar",
        f"Pred zlavou: {_format_currency(total_before_discount)}",
        f"Zlava ({discount_pct:.2f}%): -{_format_currency(discount_amount)}",
        f"Bez DPH: {_format_currency(total_no_vat)}",
        f"DPH ({int(vat_rate*100)}%): {_format_currency(vat_value)}",
        f"Spolu s DPH: {_format_currency(total_with_vat)}",
    ]
    content_parts.append(
        _draw_text(totals_lines, right_x + 12, totals_y + totals_h - 16, "/F2", 11, leading=13)
    )

    # Items table header
    table_header_y = totals_y - 40
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
    available_rows = max(1, int((row_y - (card_y + 18)) / 24))
    extra_items = []
    table_items = list(items)
    if len(table_items) > available_rows:
        extra_items = table_items[available_rows - 1 :]
        table_items = table_items[: available_rows - 1]

    def _line_totals(item: Mapping) -> tuple[float, float]:
        total_no_vat = float(item.get("total", 0.0) or 0.0)
        total_with_vat = total_no_vat * (1 + vat_rate)
        return total_no_vat, total_with_vat

    for idx, item in enumerate(table_items):
        total_no_vat, total_with_vat = _line_totals(item)
        if idx % 2 == 0:
            content_parts.append(f"{row_alt} rg ")
            content_parts.append(_draw_rect(table_x, row_y, table_w, 24, stroke=False, fill=True))
        content_parts.append("0 0 0 rg 0 0 0 RG ")
        content_parts.append(_draw_rect(table_x, row_y, table_w, 24, stroke=True, fill=False))
        row_values = [
            item.get("name", ""),
            f"x{item.get('qty','-')}",
            _format_currency(total_no_vat),
            _format_currency(total_with_vat),
        ]
        for cx, text in zip(col_x, row_values):
            content_parts.append(_draw_text([text], cx, row_y + 14, "/F1", 10))
        row_y -= 24

    if extra_items:
        extra_qty = sum(float(i.get("qty", 0) or 0.0) for i in extra_items if isinstance(i.get("qty", 0), (int, float)))
        extra_no_vat = sum(_line_totals(i)[0] for i in extra_items)
        extra_with_vat = extra_no_vat * (1 + vat_rate)
        content_parts.append(f"{row_alt} rg ")
        content_parts.append(_draw_rect(table_x, row_y, table_w, 24, stroke=False, fill=True))
        content_parts.append("0 0 0 rg 0 0 0 RG ")
        content_parts.append(_draw_rect(table_x, row_y, table_w, 24, stroke=True, fill=False))
        extra_label = f"Dalsie polozky ({len(extra_items)} ks)"
        extra_row = [
            extra_label,
            f"x{int(extra_qty)}" if extra_qty else "-",
            _format_currency(extra_no_vat),
            _format_currency(extra_with_vat),
        ]
        for cx, text in zip(col_x, extra_row):
            content_parts.append(_draw_text([text], cx, row_y + 14, "/F1", 10))

    # Keep the content stream strictly ASCII to avoid fallback glyphs ("?") in PDF readers.
    content_stream = "".join(content_parts).encode("ascii", "ignore")
    stream_length = len(content_stream)

    # Build objects
    objs: list[bytes] = []
    objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objs.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
    objs.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >> endobj\n"
    )
    objs.append(
        f"4 0 obj << /Length {stream_length} >> stream\n".encode("ascii")
        + content_stream
        + b"\nendstream endobj\n"
    )
    objs.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objs.append(b"6 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n")

    # Assemble with dynamic offsets
    header = b"%PDF-1.4\n"
    offsets = [0]  # object 0 is the free head
    pdf_body = bytearray()
    current_offset = len(header)
    for obj in objs:
        offsets.append(current_offset)
        pdf_body += obj
        current_offset += len(obj)

    # xref table
    xref_entries = ["0000000000 65535 f \n"] + [_format_xref_entry(off) for off in offsets[1:]]
    xref = ("xref\n0 %d\n" % len(offsets)).encode("ascii") + "".join(xref_entries).encode("ascii")

    # trailer
    startxref = len(header) + len(pdf_body) + len(xref)
    trailer = (
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n"
    ).encode("ascii")

    pdf_bytes = header + pdf_body + xref + trailer
    path.write_bytes(pdf_bytes)
