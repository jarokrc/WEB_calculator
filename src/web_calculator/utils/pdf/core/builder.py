"""
PDF object builder: assembles content streams and fonts into a minimal PDF byte output.
"""

from __future__ import annotations

from typing import List

from web_calculator.utils.pdf.core import fonts
from web_calculator.utils.pdf.core.fonts import _build_unicode_font_objs


def build_pdf_bytes(content_streams: List[str], page_size=(595, 842)) -> bytes:
    """
    Given list of page content streams (str), return ready-to-write PDF bytes.
    """
    streams_bytes = [s.encode("ascii", "ignore") for s in content_streams]
    lengths = [len(s) for s in streams_bytes]

    page_objs: list[bytes] = []
    font_map = fonts.get_font_map()
    unicode_fonts = "/F1" in font_map and "/F2" in font_map
    if unicode_fonts:
        font_objs, font1_id, font2_id, next_obj_id = _build_unicode_font_objs(font_map["/F1"], font_map["/F2"])
    else:
        font1_id = 3
        font2_id = 4
        font_objs = [
            b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n",
        ]
        next_obj_id = 5
    pages_kids: list[int] = []

    for stream, length in zip(streams_bytes, lengths):
        content_id = next_obj_id
        page_id = next_obj_id + 1
        pages_kids.append(page_id)
        page_objs.append(
            f"{content_id} 0 obj << /Length {length} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n"
        )
        page_objs.append(
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_size[0]} {page_size[1]}] /Contents {content_id} 0 R /Resources << /Font << /F1 {font1_id} 0 R /F2 {font2_id} 0 R >> >> >> endobj\n".encode(
                "ascii"
            )
        )
        next_obj_id += 2

    kids_ref = " ".join(f"{kid} 0 R" for kid in pages_kids)
    pages_obj = f"2 0 obj << /Type /Pages /Count {len(pages_kids)} /Kids [{kids_ref}] >> endobj\n".encode("ascii")
    catalog_obj = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"

    objs = [catalog_obj, pages_obj] + font_objs + page_objs

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

    return header + pdf_body + xref + trailer


def _format_xref_entry(offset: int) -> str:
    return f"{offset:010d} 00000 n \n"
