from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

# Font cache (Unicode TTFs, fallback to built-in Type1)
_FONT_MAP: Dict[str, "TrueTypeFont"] = {}


def get_font_map() -> Dict[str, "TrueTypeFont"]:
    return _FONT_MAP


def set_font_map(font_map: Dict[str, "TrueTypeFont"]) -> Dict[str, "TrueTypeFont"]:
    global _FONT_MAP
    _FONT_MAP = font_map
    return _FONT_MAP


def load_font_map() -> Dict[str, "TrueTypeFont"]:
    return set_font_map(_try_load_unicode_fonts())


def clear_font_map() -> None:
    global _FONT_MAP
    _FONT_MAP = {}


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
    candidates.append((Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf")))
    candidates.append((Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")))

    for regular_path, bold_path in candidates:
        try:
            if not regular_path.exists() or not bold_path.exists():
                continue
            regular = TrueTypeFont(regular_path, pdf_name="/UnicodeRegular")
            bold = TrueTypeFont(bold_path, pdf_name="/UnicodeBold")
            regular.used_gids.add(regular.glyph_id(ord(" ")))
            bold.used_gids.add(bold.glyph_id(ord(" ")))
            return {"/F1": regular, "/F2": bold}
        except Exception:
            continue
    return {}


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
            f"/FontDescriptor {desc_id} 0 R /CIDToGIDMap /Identity /DW {dw}{w_part} >> endobj\n"
        ).encode("ascii")

    def type0_font_obj(obj_id: int, cid_id: int) -> bytes:
        return f"{obj_id} 0 obj << /Type /Font /Subtype /Type0 /BaseFont {regular.pdf_name}-Identity-H /Encoding /Identity-H /DescendantFonts [{cid_id} 0 R] >> endobj\n".encode(
            "ascii"
        )

    objs = [
        fontfile_obj(reg_file_id, regular),
        font_descriptor_obj(reg_desc_id, reg_file_id, regular),
        cid_font_obj(reg_cid_id, reg_desc_id, regular),
        type0_font_obj(reg_type0_id, reg_cid_id),
        fontfile_obj(bold_file_id, bold),
        font_descriptor_obj(bold_desc_id, bold_file_id, bold),
        cid_font_obj(bold_cid_id, bold_desc_id, bold),
        type0_font_obj(bold_type0_id, bold_cid_id),
    ]
    return objs, reg_type0_id, bold_type0_id, next_free
