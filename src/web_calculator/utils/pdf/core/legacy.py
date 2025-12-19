"""
Tento skript slúži len ako poistka: ak nový renderer spadne, fallback sa spúšťa z
`renderers/pdf_renderer.py` (blok try/except vola `legacy.export_simple_pdf`).
This module is only a cold fallback: the exception handler in `renderers/pdf_renderer.py`
calls `legacy.export_simple_pdf` when the new pipeline fails.
"""

from __future__ import annotations

import os
import struct
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Callable, Iterable, Mapping, Sequence

from web_calculator.utils.qr import make_qr_matrix


# -------- Helpers --------
_FONT_MAP: dict[str, "TrueTypeFont"] = {}


@dataclass(frozen=True)
class _TtfTables:
    cmap: tuple[int, int]
    head: tuple[int, int]
    hhea: tuple[int, int]
    hmtx: tuple[int, int]
    maxp: tuple[int, int]


class TrueTypeFont:
    def __init__(self, path: Path, pdf_name: str):
        self.path = path
        self.pdf_name = pdf_name  # Name object, e.g. "/SegoeUI"
        self.data = path.read_bytes()
        self.tables = self._parse_tables(self.data)

        head_offset, _ = self.tables.head
        self.units_per_em = struct.unpack_from(">H", self.data, head_offset + 18)[0]
        x_min, y_min, x_max, y_max = struct.unpack_from(">hhhh", self.data, head_offset + 36)
        self.bbox = (x_min, y_min, x_max, y_max)

        hhea_offset, _ = self.tables.hhea
        self.ascent, self.descent = struct.unpack_from(">hh", self.data, hhea_offset + 4)
        self.number_of_hmetrics = struct.unpack_from(">H", self.data, hhea_offset + 34)[0]

        maxp_offset, _ = self.tables.maxp
        self.num_glyphs = struct.unpack_from(">H", self.data, maxp_offset + 4)[0]

        self._advance_widths = self._load_advance_widths()
        self._cmap_lookup = self._build_cmap_lookup()
        self.used_gids: set[int] = set()

    @staticmethod
    def _parse_tables(data: bytes) -> _TtfTables:
        if len(data) < 12:
            raise ValueError("Invalid TTF (too small)")
        num_tables = struct.unpack_from(">H", data, 4)[0]
        directory_offset = 12
        entries: dict[str, tuple[int, int]] = {}
        for i in range(num_tables):
            base = directory_offset + i * 16
            tag = data[base : base + 4].decode("ascii", "replace")
            offset = struct.unpack_from(">I", data, base + 8)[0]
            length = struct.unpack_from(">I", data, base + 12)[0]
            entries[tag] = (offset, length)

        required = ["cmap", "head", "hhea", "hmtx", "maxp"]
        missing = [t for t in required if t not in entries]
        if missing:
            raise ValueError(f"TTF missing tables: {', '.join(missing)}")
        return _TtfTables(
            cmap=entries["cmap"],
            head=entries["head"],
            hhea=entries["hhea"],
            hmtx=entries["hmtx"],
            maxp=entries["maxp"],
        )

    def _load_advance_widths(self) -> list[int]:
        hmtx_offset, _ = self.tables.hmtx
        widths: list[int] = []
        count = min(self.number_of_hmetrics, self.num_glyphs)
        for i in range(count):
            adv = struct.unpack_from(">H", self.data, hmtx_offset + i * 4)[0]
            widths.append(int(adv))
        if not widths:
            widths = [int(self.units_per_em)]
        if len(widths) < self.num_glyphs:
            widths.extend([widths[-1]] * (self.num_glyphs - len(widths)))
        return widths

    def width_1000(self, gid: int) -> int:
        if gid < 0 or gid >= len(self._advance_widths):
            return 500
        adv = self._advance_widths[gid]
        return max(0, int(round((adv * 1000.0) / float(self.units_per_em or 1000))))

    def glyph_id(self, codepoint: int) -> int:
        gid = self._cmap_lookup(codepoint)
        if gid is None:
            return 0
        if gid < 0 or gid >= self.num_glyphs:
            return 0
        return int(gid)

    def encode_text_hex(self, text: str) -> str:
        out = bytearray()
        for ch in str(text):
            gid = self.glyph_id(ord(ch))
            self.used_gids.add(gid)
            out += int(gid).to_bytes(2, "big", signed=False)
        return out.hex().upper()

    def _build_cmap_lookup(self) -> Callable[[int], int | None]:
        cmap_offset, _ = self.tables.cmap
        version, num_tables = struct.unpack_from(">HH", self.data, cmap_offset)
        if version != 0 or num_tables <= 0:
            raise ValueError("Invalid cmap table")

        records = []
        for i in range(num_tables):
            base = cmap_offset + 4 + i * 8
            platform_id, encoding_id, sub_offset = struct.unpack_from(">HHI", self.data, base)
            records.append((platform_id, encoding_id, sub_offset))

        preferred = [
            (3, 10),  # Windows, Unicode full repertoire (format 12)
            (3, 1),  # Windows, Unicode BMP (format 4)
            (0, 4),  # Unicode platform
            (0, 3),
            (0, 2),
            (0, 1),
        ]
        chosen = None
        for pid, eid in preferred:
            match = next((r for r in records if r[0] == pid and r[1] == eid), None)
            if match:
                chosen = match
                break
        if not chosen:
            chosen = records[0]

        _, _, sub_offset = chosen
        subtable_start = cmap_offset + sub_offset
        fmt = struct.unpack_from(">H", self.data, subtable_start)[0]
        if fmt == 4:
            return self._parse_cmap_format4(subtable_start)
        if fmt == 12:
            return self._parse_cmap_format12(subtable_start)
        raise ValueError(f"Unsupported cmap format: {fmt}")

    def _parse_cmap_format4(self, start: int) -> Callable[[int], int | None]:
        seg_count_x2 = struct.unpack_from(">H", self.data, start + 6)[0]
        seg_count = int(seg_count_x2 // 2)
        end_codes_offset = start + 14
        end_codes = list(struct.unpack_from(f">{seg_count}H", self.data, end_codes_offset))
        start_codes_offset = end_codes_offset + 2 * seg_count + 2
        start_codes = list(struct.unpack_from(f">{seg_count}H", self.data, start_codes_offset))
        id_delta_offset = start_codes_offset + 2 * seg_count
        id_deltas = list(struct.unpack_from(f">{seg_count}h", self.data, id_delta_offset))
        id_range_offset_offset = id_delta_offset + 2 * seg_count
        id_range_offsets = list(struct.unpack_from(f">{seg_count}H", self.data, id_range_offset_offset))

        def lookup(codepoint: int) -> int | None:
            if codepoint < 0 or codepoint > 0xFFFF:
                return None
            c = int(codepoint)
            for i in range(seg_count):
                if start_codes[i] <= c <= end_codes[i]:
                    ro = id_range_offsets[i]
                    if ro == 0:
                        return (c + id_deltas[i]) & 0xFFFF
                    glyph_index_addr = id_range_offset_offset + 2 * i + ro + 2 * (c - start_codes[i])
                    if glyph_index_addr + 2 > len(self.data):
                        return None
                    glyph_index = struct.unpack_from(">H", self.data, glyph_index_addr)[0]
                    if glyph_index == 0:
                        return 0
                    return (glyph_index + id_deltas[i]) & 0xFFFF
            return None

        return lookup

    def _parse_cmap_format12(self, start: int) -> Callable[[int], int | None]:
        # format (2), reserved (2), length (4), language (4), nGroups (4)
        n_groups = struct.unpack_from(">I", self.data, start + 12)[0]
        groups_offset = start + 16
        groups: list[tuple[int, int, int]] = []
        for i in range(n_groups):
            base = groups_offset + i * 12
            start_char, end_char, start_gid = struct.unpack_from(">III", self.data, base)
            groups.append((start_char, end_char, start_gid))

        def lookup(codepoint: int) -> int | None:
            c = int(codepoint)
            for start_char, end_char, start_gid in groups:
                if start_char <= c <= end_char:
                    return int(start_gid + (c - start_char))
            return None

        return lookup


def _try_load_unicode_fonts() -> dict[str, TrueTypeFont]:
    """
    Try to load a Unicode-capable TrueType font (Windows), so PDF can render diacritics.
    Falls back to ASCII-only mode if unavailable.
    """
    override = os.environ.get("WEB_CALCULATOR_PDF_FONT")
    base_dir = Path(override) if override else None
    candidates: list[tuple[Path, Path]] = []
    if base_dir and base_dir.is_dir():
        candidates.append((base_dir / "regular.ttf", base_dir / "bold.ttf"))
    # Windows defaults
    candidates.append((Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf")))
    candidates.append((Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")))

    for regular_path, bold_path in candidates:
        try:
            if not regular_path.exists() or not bold_path.exists():
                continue
            regular = TrueTypeFont(regular_path, pdf_name="/UnicodeRegular")
            bold = TrueTypeFont(bold_path, pdf_name="/UnicodeBold")
            # ensure space is tracked for widths defaults
            regular.used_gids.add(regular.glyph_id(ord(" ")))
            bold.used_gids.add(bold.glyph_id(ord(" ")))
            return {"/F1": regular, "/F2": bold}
        except Exception:
            continue
    return {}


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


def _build_supplier_lines(supplier: Mapping) -> list[str]:
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


def _draw_text(lines: Iterable[str], x: int, y: int, font: str, size: int, leading: int | None = None) -> str:
    out = []
    spacing = leading or (size + 2)
    for line in lines:
        text = str(line)
        if font in _FONT_MAP:
            hex_text = _FONT_MAP[font].encode_text_hex(text)
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


def _draw_price_line(label: str, value: float, orig: float | None, x: int, y: int, font: str, size: int) -> str:
    """
    Draw price label; if orig provided and different, draw muted orig one line above.
    """
    parts = []
    # if orig is not None and abs(orig - value) > 0.01:
    #     orig_text = f"{label}: {_format_currency(orig)}"
    #     muted_size = int(size * 0.8)
    #     parts.append(_draw_text([orig_text], x, y + size + 4, font, muted_size))
    #     strike_len = len(orig_text) * (muted_size * 0.52)
    #     line_y = y + size + 4 + muted_size * 0.3
    #     parts.append(f"0.55 0.55 0.55 RG {muted_size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    parts.append(_draw_text([f"{label}: {_format_currency(value)}"], x, y, font, size))
    return "".join(parts)


def _draw_price_cell(current: float, original: float | None, x: int, y: int, font: str, size: int) -> str:
    if original is not None and abs(original - current) > 0.01:
        orig_font_size = max(6, int(size * 0.8))
        orig_color = "0.55 0.55 0.55"
        orig_text = _format_currency(original)
        strike_len = len(orig_text) * (orig_font_size * 0.52)
        line_y = y + size + 4 + orig_font_size * 0.30
        return (
            f"{orig_color} rg {orig_color} RG "
            + _draw_text([orig_text], x, y + size + 4, font, orig_font_size)
            + f"{orig_color} RG {orig_font_size * 0.06:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n"
            + "0 0 0 rg 0 0 0 RG "
            + _draw_text([_format_currency(current)], x, y, font, size)
        )
#     if original is not None:
#         orig_font_size = int(size * 0.8)
#         orig_color = "0.55 0.55 0.55"
#         orig_text = f"{orig_color} rg {orig_color} RG " + _draw_text([_format_currency(original)], x, y + size + 4, font, orig_font_size)
#         # strike line over original
#         strike_len = len(_format_currency(original)) * (orig_font_size * 0.55)
#         line_y = y + size + 4 + orig_font_size * 0.3
#         strike = f"{orig_color} RG {orig_font_size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n"
#         return orig_text + strike + "0 0 0 rg 0 0 0 RG " + _draw_text([_format_currency(current)], x, y, font, size)
    return "0 0 0 rg 0 0 0 RG " + _draw_text([_format_currency(current)], x, y, font, size)


def _draw_total_row(label: str, value: float, orig: float | None, x: int, y: int) -> str:
    """
    Render totals row with original (grey, strike) above current (bold).
    y is baseline for current.
    """
    parts = []
    # if orig is not None and abs(orig - value) > 0.01:
    #     color = "0.55 0.55 0.55"
    #     size = 10
    #     parts.append(f"{color} rg {color} RG ")
    #     orig_text = f"P├┤vodn├í {label}: {_format_currency(orig)}"
    #     parts.append(_draw_text([orig_text], x, y + size + 6, "/F1", size))
    #     strike_len = len(orig_text) * (size * 0.52)
    #     line_y = y + size + 6 + size * 0.3
    #     parts.append(f"{color} RG {size * 0.05:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    if orig is not None and abs(orig - value) > 0.01:
        color = "0.55 0.55 0.55"
        size = 9
        orig_text = f"Povodna {label}: {_format_currency(orig)}"
        strike_len = len(orig_text) * (size * 0.52)
        line_y = y + 14 + size * 0.30
        parts.append(f"{color} rg {color} RG ")
        parts.append(_draw_text([orig_text], x, y + 14, "/F1", size))
        parts.append(f"{color} RG {size * 0.06:.2f} w {x} {line_y:.2f} m {x + strike_len:.2f} {line_y:.2f} l S\n")
    parts.append("0 0 0 rg 0 0 0 RG ")
    parts.append(_draw_text([f"{label}: {_format_currency(value)}"], x, y, "/F2", 12))
    return "".join(parts)


def _draw_summary_lines(lines: list[str], x: int, y: int, header_font: str, header_size: int, body_font: str, body_size: int) -> str:
    """
    Render summary lines with styling:
    - Lines starting with 'povodna' are grey and strike-through.
    - Line starting with 'spolu s dph' is bold (header_font).
    """
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


def _scale_font_units(value: int, units_per_em: int) -> int:
    if units_per_em <= 0:
        return int(value)
    return int(round(value * 1000.0 / float(units_per_em)))


def _format_cid_widths(font: TrueTypeFont) -> str:
    gids = sorted(font.used_gids)
    if not gids:
        return ""
    parts: list[str] = []
    i = 0
    while i < len(gids):
        start = gids[i]
        widths = [font.width_1000(start)]
        j = i + 1
        while j < len(gids) and gids[j] == gids[j - 1] + 1:
            widths.append(font.width_1000(gids[j]))
            j += 1
        parts.append(f"{start} [{' '.join(str(w) for w in widths)}]")
        i = j
    return " ".join(parts)


def _build_unicode_font_objs(
    regular: TrueTypeFont,
    bold: TrueTypeFont,
) -> tuple[list[bytes], int, int, int]:
    """
    Return (font_objects, font1_ref, font2_ref, next_free_obj_id).

    Uses a CIDFontType2 composite font with Identity-H and CIDToGIDMap Identity, so we can
    emit glyph IDs directly as 2-byte hex strings in content streams.
    """
    # Object ids layout:
    # 3 FontFile2 regular, 4 FontDescriptor regular, 5 CIDFont regular, 6 Type0 regular
    # 7 FontFile2 bold,    8 FontDescriptor bold,    9 CIDFont bold,   10 Type0 bold
    reg_file_id, reg_desc_id, reg_cid_id, reg_type0_id = 3, 4, 5, 6
    bold_file_id, bold_desc_id, bold_cid_id, bold_type0_id = 7, 8, 9, 10
    next_free = 11

    def fontfile_obj(obj_id: int, font: TrueTypeFont) -> bytes:
        data = font.data
        return (
            f"{obj_id} 0 obj << /Length {len(data)} >> stream\n".encode("ascii")
            + data
            + b"\nendstream endobj\n"
        )

    def font_descriptor_obj(obj_id: int, fontfile_id: int, font: TrueTypeFont) -> bytes:
        units = int(font.units_per_em or 1000)
        x_min, y_min, x_max, y_max = font.bbox
        bbox = [
            _scale_font_units(x_min, units),
            _scale_font_units(y_min, units),
            _scale_font_units(x_max, units),
            _scale_font_units(y_max, units),
        ]
        ascent = _scale_font_units(int(font.ascent), units)
        descent = _scale_font_units(int(font.descent), units)
        cap_height = ascent
        return (
            f"{obj_id} 0 obj << /Type /FontDescriptor /FontName {font.pdf_name} "
            f"/Flags 32 /FontBBox [{bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}] "
            f"/ItalicAngle 0 /Ascent {ascent} /Descent {descent} /CapHeight {cap_height} "
            f"/StemV 80 /FontFile2 {fontfile_id} 0 R >> endobj\n"
        ).encode("ascii")

    def cid_font_obj(obj_id: int, desc_id: int, font: TrueTypeFont) -> bytes:
        space_gid = font.glyph_id(ord(" "))
        dw = font.width_1000(space_gid) or 500
        widths = _format_cid_widths(font)
        w_part = f" /W [{widths}]" if widths else ""
        return (
            f"{obj_id} 0 obj << /Type /Font /Subtype /CIDFontType2 /BaseFont {font.pdf_name} "
            f"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
            f"/FontDescriptor {desc_id} 0 R /DW {dw}{w_part} /CIDToGIDMap /Identity >> endobj\n"
        ).encode("ascii")

    def type0_font_obj(obj_id: int, cid_id: int, font: TrueTypeFont) -> bytes:
        return (
            f"{obj_id} 0 obj << /Type /Font /Subtype /Type0 /BaseFont {font.pdf_name} "
            f"/Encoding /Identity-H /DescendantFonts [{cid_id} 0 R] >> endobj\n"
        ).encode("ascii")

    objs: list[bytes] = [
        fontfile_obj(reg_file_id, regular),
        font_descriptor_obj(reg_desc_id, reg_file_id, regular),
        cid_font_obj(reg_cid_id, reg_desc_id, regular),
        type0_font_obj(reg_type0_id, reg_cid_id, regular),
        fontfile_obj(bold_file_id, bold),
        font_descriptor_obj(bold_desc_id, bold_file_id, bold),
        cid_font_obj(bold_cid_id, bold_desc_id, bold),
        type0_font_obj(bold_type0_id, bold_cid_id, bold),
    ]
    return objs, reg_type0_id, bold_type0_id, next_free


# -------- Main export --------
def export_simple_pdf(path: Path, invoice_payload: Mapping) -> None:
    """
    Render a styled 1-page invoice PDF with balanced blocks and readable spacing.
    """
    global _FONT_MAP
    _FONT_MAP = _try_load_unicode_fonts()
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
    title = invoice_payload.get("doc_title", "Cenov├í ponuka")
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
    content_parts.append(_draw_text([f"D├ítum vystavenia: {issue_date}"], card_x + 16, header_y - 20, "/F1", 11))

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

    # --- Legacy payment/totals layout (kept for reference) ---
    # payment_h = 140
    # payment_y = supplier_y - 10  # posun mierne vyssie
    # content_parts.append(_draw_rect(right_x, payment_y, col_width, payment_h, stroke=True, fill=False))
    # pay_lines = invoice_payload.get("payment_lines_override") or [
    #     f"Variabilny symbol: {invoice_no}",
    #     f"Datum vystavenia: {issue_date}",
    #     f"Balik: {package_label}",
    #     "Stav: Nezaplateny",
    # ]
    # content_parts.append(_draw_text(["Prehlad platby"], right_x + 12, payment_y + payment_h - 16, "/F2", 11, leading=13))
    # content_parts.append(_draw_text(pay_lines, right_x + 12, payment_y + payment_h - 32, "/F1", 10, leading=12))
    #
    # # QR inside payment block (top-right)
    # qr_side = 90
    # qr_draw = ""
    # if qr_matrix:
    #     qr_scale = max(2, qr_side // max(len(qr_matrix), len(qr_matrix[0])))
    #     qr_draw = _draw_qr(qr_matrix, right_x + col_width - qr_scale * len(qr_matrix) - 12, payment_y + payment_h - 12, qr_scale)
    # elif qr_data:
    #     qr_draw = _draw_rect(right_x + col_width - qr_side - 12, payment_y + payment_h - qr_side - 12, qr_side, qr_side, stroke=True, fill=False) + _draw_text(["QR"], right_x + col_width - qr_side//2 - 8, payment_y + payment_h - qr_side//2 - 12, "/F2", 12)
    # content_parts.append(qr_draw)
    #
    # # Totals block under payment/QR
    # totals_y = payment_y - 60  # posun vyssie
    # totals_lines = [
    #     ("Cena bez DPH", total_no_vat, None),
    #     (f"DPH ({int(vat_rate*100)}%)", vat_value, None),
    #     ("Spolu s DPH", total_with_vat, None),
    # ]
    # box_w = 240
    # box_h = 120
    # totals_box_y = totals_y - 70
    # content_parts.append(_draw_rect(right_x + 6, totals_box_y, box_w, box_h, stroke=True, fill=False))
    # orig_services_total = float(totals.get("original_services_total", orig_extras) or 0.0)
    # content_parts.append(f"{muted} rg {muted} RG ")
    # content_parts.append(
    #     _draw_text(
    #         [f"Povodna cena sluzieb (bez balika)/bez DPH: {_format_currency(orig_services_total)}"],
    #         right_x + 16,
    #         totals_box_y + box_h - 14,
    #         "/F1",
    #         8,
    #     )
    # )
    # content_parts.append("0 0 0 rg 0 0 0 RG ")
    # row_y = totals_box_y + box_h - 34
    # for label, val, orig in totals_lines:
    #     content_parts.append(_draw_total_row(label, val, orig, right_x + 16, row_y))
    #     row_y -= 30


    # Column geometry
    col_gap = 16
    col_width = 248
    left_x = card_x + 16
    right_x = left_x + col_width + col_gap
    section_height = 150
    section_gap = 12
    section_header_size = 12
    section_body_size = 11

    # Supplier box (Dodavatel)
    supplier_y = header_y - 30 - section_height
    supplier_lines = invoice_payload.get("supplier_lines_override") or _build_supplier_lines(supplier)
    content_parts.append(f"{border} RG ")
    content_parts.append(_draw_rect(left_x, supplier_y, col_width, section_height, stroke=True, fill=False))
    content_parts.append(_draw_text(["Dodavatel"], left_x + 12, supplier_y + section_height - 16, "/F2", section_header_size, leading=section_header_size + 1))
    content_parts.append(_draw_text(supplier_lines, left_x + 12, supplier_y + section_height - 32, "/F1", section_body_size, leading=section_body_size + 2))

    # Client box (Odberatel)
    client_y = supplier_y - section_gap - section_height
    client_lines_raw = [
        "Odberatel",
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
    client_override = invoice_payload.get("client_lines_override")
    if client_override:
        client_lines = list(client_override)
    content_parts.append(_draw_rect(left_x, client_y, col_width, section_height, stroke=True, fill=False))
    content_parts.append(_draw_text(["Odberatel"], left_x + 12, client_y + section_height - 16, "/F2", section_header_size, leading=section_header_size + 1))
    content_parts.append(_draw_text(client_lines, left_x + 12, client_y + section_height - 32, "/F1", section_body_size, leading=section_body_size + 2))

    # Payment block (right column top)
    payment_y = supplier_y  # align with supplier top
    content_parts.append(_draw_rect(right_x, payment_y, col_width, section_height, stroke=True, fill=False))
    pay_lines = invoice_payload.get("payment_lines_override") or [
        f"Variabilny symbol: {invoice_no}",
        f"Datum vystavenia: {issue_date}",
        f"Balik: {package_label}",
        "Stav: Nezaplateny",
    ]
    content_parts.append(_draw_text(["Prehlad platby"], right_x + 12, payment_y + section_height - 16, "/F2", section_header_size, leading=section_header_size + 1))
    content_parts.append(_draw_text(pay_lines, right_x + 12, payment_y + section_height - 32, "/F1", section_body_size, leading=section_body_size + 2))

    # QR inside payment block (top-right)
    qr_side = 90
    qr_draw = ""
    if qr_matrix:
        qr_scale = max(2, qr_side // max(len(qr_matrix), len(qr_matrix[0])))
        qr_draw = _draw_qr(qr_matrix, right_x + col_width - qr_scale * len(qr_matrix) - 12, payment_y + section_height - 12, qr_scale)
    elif qr_data:
        qr_draw = _draw_rect(right_x + col_width - qr_side - 12, payment_y + section_height - qr_side - 12, qr_side, qr_side, stroke=True, fill=False) + _draw_text(["QR"], right_x + col_width - qr_side//2 - 8, payment_y + section_height - qr_side//2 - 12, "/F2", 12)
    content_parts.append(qr_draw)

    # Totals block (Suvaha)
    totals_y = client_y  # align with client top
    orig_services_total = float(totals.get("original_services_total", orig_extras) or 0.0)
    summary_lines = invoice_payload.get("summary_lines_override") or [
        f"Povodna cena sluzieb: {_format_currency(orig_services_total)}",
        f"Cena bez DPH: {_format_currency(total_no_vat)}",
        f"DPH ({int(vat_rate*100)}%): {_format_currency(vat_value)}",
        f"Spolu s DPH: {_format_currency(total_with_vat)}",
    ]
    content_parts.append(_draw_rect(right_x, totals_y, col_width, section_height, stroke=True, fill=False))
    content_parts.append(_draw_text(["Suvaha"], right_x + 12, totals_y + section_height - 16, "/F2", section_header_size, leading=section_header_size + 1))
    content_parts.append(
        _draw_summary_lines(
            summary_lines,
            right_x + 12,
            totals_y + section_height - 32,
            "/F2",
            section_header_size,
            "/F1",
            section_body_size,
        )
    )

    # Items table header
    table_header_y = client_y - 40
    table_x = left_x
    table_w = card_w - 32
    content_parts.append(f"{dark} rg {dark} RG ")
    content_parts.append(_draw_rect(table_x, table_header_y, table_w, 30, stroke=True, fill=True))
    content_parts.append("1 1 1 rg 1 1 1 RG ")
    col_x = [table_x + 10, table_x + 220, table_x + 320, table_x + 420]
    headers = ["N├ízov", "Mno┼żstvo", "bez DPH", "s DPH"]
    for hx, text in zip(col_x, headers):
        content_parts.append(_draw_text([text], hx, table_header_y + 20, "/F2", 10))

    # Item rows (use uniform row height so package and services align)
    row_y = table_header_y - 26
    row_height = 36
    available_rows = max(1, int((row_y - (card_y + 36)) / row_height))
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
        rh = row_height
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
        content_parts.append(_draw_text([name], col_x[0], row_y + rh - 26, "/F1", 10))
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
        available_rows_page = max(1, int((row_y - 60) / row_height))
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
            rh = row_height
            if idx % 2 == 0:
                content_parts_extra.append(f"{row_alt} rg ")
                content_parts_extra.append(_draw_rect(table_x, row_y, table_w, rh, stroke=False, fill=True))
            content_parts_extra.append("0 0 0 rg 0 0 0 RG ")
            content_parts_extra.append(_draw_rect(table_x, row_y, table_w, rh, stroke=True, fill=False))
            name = item.get("name", "")
            qty = item.get("qty", "-")
            content_parts_extra.append(_draw_text([name], col_x[0], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_text([f"x{qty}"], col_x[1], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_price_cell(total_no_vat, orig_no_vat, col_x[2], row_y + rh - 26, "/F1", 10))
            content_parts_extra.append(_draw_price_cell(total_with_vat, orig_with_vat, col_x[3], row_y + rh - 26, "/F1", 10))
            row_y -= rh
        content_streams.append("".join(content_parts_extra))

    # Assemble PDF objects dynamically
    streams_bytes = [s.encode("ascii", "ignore") for s in content_streams]
    lengths = [len(s) for s in streams_bytes]

    page_objs: list[bytes] = []
    unicode_fonts = bool(_FONT_MAP)
    if unicode_fonts:
        font_objs, font1_id, font2_id, next_obj_id = _build_unicode_font_objs(_FONT_MAP["/F1"], _FONT_MAP["/F2"])
    else:
        font1_id = 3
        font2_id = 4
        font_objs = [
            b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n",
        ]
        next_obj_id = 5
    pages_kids: list[int] = []

    # Content + page objects
    for idx, (stream, length) in enumerate(zip(streams_bytes, lengths)):
        content_id = next_obj_id
        page_id = next_obj_id + 1
        pages_kids.append(page_id)
        page_objs.append(
            f"{content_id} 0 obj << /Length {length} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n"
        )
        page_objs.append(
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R /Resources << /Font << /F1 {font1_id} 0 R /F2 {font2_id} 0 R >> >> >> endobj\n".encode(
                "ascii"
            )
        )
        next_obj_id += 2

    # Pages object
    kids_ref = " ".join(f"{kid} 0 R" for kid in pages_kids)
    pages_obj = f"2 0 obj << /Type /Pages /Count {len(pages_kids)} /Kids [{kids_ref}] >> endobj\n".encode("ascii")
    catalog_obj = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"

    objs = [catalog_obj, pages_obj] + font_objs + page_objs

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
    _FONT_MAP = {}
