from __future__ import annotations

from pathlib import Path
from typing import Mapping

from web_calculator.utils.pdf.core import fonts, legacy
from web_calculator.utils.pdf.core.builder import build_pdf_bytes
from web_calculator.utils.pdf.core.drawing import _draw_rect, _draw_text
from web_calculator.utils.pdf.core.layout_common import (
    CARD_H,
    CARD_TOP,
    CARD_W,
    CARD_X,
    CARD_Y,
    COL_GAP,
    COL_WIDTH,
    COLORS,
    PAGE_W,
    PAGE_H,
    SECTION_BODY_SIZE,
    SECTION_GAP,
    SECTION_HEADER_SIZE,
    SECTION_HEIGHT,
    TABLE_HEADER_HEIGHT,
    TABLE_ROW_HEIGHT,
)
from web_calculator.utils.pdf.core.totals import derive_totals, prepare_display_items
from web_calculator.utils.pdf.sections.supplier import render_supplier, build_supplier_lines
from web_calculator.utils.pdf.sections.client import render_client, build_client_lines
from web_calculator.utils.pdf.sections.payment import render_payment, build_payment_lines
from web_calculator.utils.pdf.sections.summary import render_summary, build_summary_lines
from web_calculator.utils.pdf.sections.items_table import render_items_table
from web_calculator.utils.qr import make_qr_matrix


def render_pdf(path: Path, payload: Mapping) -> None:
    """
    High-level renderer. Preferuje novy modul; pri chybe fallback na legacy.
    """
    try:
        _render_new(path, payload)
    except Exception:
        # Bezpecny fallback na legacy export
        legacy.export_simple_pdf(path, payload)


def _render_new(path: Path, invoice_payload: Mapping) -> None:
    # fonty
    fonts.load_font_map()

    # farby
    dark = COLORS["dark"]
    light = COLORS["light"]
    border = COLORS["border"]
    row_alt = COLORS["row_alt"]

    invoice_no = str(invoice_payload.get("invoice_no", "-"))
    issue_date = str(invoice_payload.get("issue_date", ""))
    title = invoice_payload.get("doc_title", "Cenova ponuka")
    supplier = invoice_payload.get("supplier", {})
    client = invoice_payload.get("client", {})
    totals = invoice_payload.get("totals", {})
    qr_data = invoice_payload.get("qr_data") or invoice_no
    qr_matrix = make_qr_matrix(qr_data) if qr_data else None

    display_items, recomputed_original_extras = prepare_display_items(invoice_payload)

    totals_ctx = derive_totals(totals, recomputed_original_extras)

    supplier_lines = invoice_payload.get("supplier_lines_override") or build_supplier_lines(supplier)
    client_lines = invoice_payload.get("client_lines_override") or build_client_lines(client)
    payment_lines = invoice_payload.get("payment_lines_override") or build_payment_lines(invoice_payload, invoice_no, issue_date)
    summary_lines = invoice_payload.get("summary_lines_override") or build_summary_lines(totals_ctx)
    vat_rate = totals_ctx.vat_rate

    content_parts: list[str] = []

    # Background card
    content_parts.append(f"{light} rg {border} RG ")
    content_parts.append(_draw_rect(CARD_X, CARD_Y, CARD_W, CARD_H, stroke=True, fill=True))
    content_parts.append("0 0 0 rg 0 0 0 RG ")

    # Header
    header_y = CARD_TOP - 18
    content_parts.append(_draw_text([f"{title} c. {invoice_no}"], CARD_X + 16, header_y, "/F2", 18))
    content_parts.append(_draw_text([f"Dátum vystavenia: {issue_date}"], CARD_X + 16, header_y - 20, "/F1", 11))

    # Geometry
    left_x = CARD_X + 16
    right_x = left_x + COL_WIDTH + COL_GAP

    # Supplier
    supplier_y = header_y - 30 - SECTION_HEIGHT
    content_parts.append(render_supplier(supplier_lines, left_x, supplier_y, COL_WIDTH, SECTION_HEIGHT, SECTION_HEADER_SIZE, SECTION_BODY_SIZE))

    # Client
    client_y = supplier_y - SECTION_GAP - SECTION_HEIGHT
    content_parts.append(render_client(client_lines, left_x, client_y, COL_WIDTH, SECTION_HEIGHT, SECTION_HEADER_SIZE, SECTION_BODY_SIZE))

    # Payment
    payment_y = supplier_y
    content_parts.append(render_payment(payment_lines, right_x, payment_y, COL_WIDTH, SECTION_HEIGHT, SECTION_HEADER_SIZE, SECTION_BODY_SIZE, qr_matrix, qr_data))

    # Summary
    summary_y = client_y
    content_parts.append(render_summary(summary_lines, right_x, summary_y, COL_WIDTH, SECTION_HEIGHT, SECTION_HEADER_SIZE, SECTION_BODY_SIZE))

    # Table
    table_header_y = client_y - 40
    table_x = left_x
    table_w = CARD_W - 32
    content_parts.append(f"{dark} rg {dark} RG ")
    content_parts.append(_draw_rect(table_x, table_header_y, table_w, TABLE_HEADER_HEIGHT, stroke=True, fill=True))
    content_parts.append("1 1 1 rg 1 1 1 RG ")
    col_x = [table_x + 10, table_x + 220, table_x + 320, table_x + 420]
    headers = ["Názov", "Množstvo", "bez DPH", "s DPH"]
    for hx, text in zip(col_x, headers):
        content_parts.append(_draw_text([text], hx, table_header_y + 20, "/F2", 10))

    row_y = table_header_y - 26
    min_y = CARD_Y + 36
    table_content, overflow = render_items_table(display_items, table_x, table_header_y, table_w, dark, row_alt, vat_rate, min_y)
    content_parts.extend(table_content)

    # Extra pages for overflow
    content_streams = ["".join(content_parts)]
    while overflow:
        extra = overflow
        overflow = []
        row_y = PAGE_H - 80
        available_rows_page = max(1, int((row_y - 60) / TABLE_ROW_HEIGHT))
        if len(extra) > available_rows_page:
            overflow = extra[available_rows_page - 1 :]
            extra = extra[: available_rows_page - 1]
        content_page: list[str] = []
        content_page.append(_draw_text(["Dalsie polozky"], left_x + 16, PAGE_H - 36, "/F2", 12))
        content_page.append(f"{dark} rg {dark} RG ")
        content_page.append(_draw_rect(table_x, row_y, table_w, TABLE_HEADER_HEIGHT, stroke=True, fill=True))
        content_page.append("1 1 1 rg 1 1 1 RG ")
        for hx, text in zip(col_x, headers):
            content_page.append(_draw_text([text], hx, row_y + 20, "/F2", 10))
        row_y -= 26
        extra_content, overflow = render_items_table(extra, table_x, row_y + 26, table_w, dark, row_alt, vat_rate, min_y=60)
        content_page.extend(extra_content)
        content_streams.append("".join(content_page))

    pdf_bytes = build_pdf_bytes(content_streams, page_size=(PAGE_W, PAGE_H))
    path.write_bytes(pdf_bytes)
    fonts.clear_font_map()
