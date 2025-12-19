"""
Layout and style constants for PDF rendering.
Values are extracted from the legacy renderer to keep parity.
"""

# Page geometry (A4, points)
PAGE_W, PAGE_H = 595, 842

# Card geometry (white background block)
CARD_X, CARD_Y, CARD_W, CARD_H = 32, 60, 531, 720
CARD_TOP = CARD_Y + CARD_H

# Section geometry
SECTION_HEIGHT = 150
SECTION_GAP = 0
SECTION_HEADER_SIZE = 12
SECTION_BODY_SIZE = 11
COL_GAP = 0
COL_WIDTH = 248

# Table geometry
TABLE_HEADER_HEIGHT = 30
TABLE_ROW_HEIGHT = 36

# Colors (RGB components in 0-1 space encoded as strings for PDF ops)
COLORS = {
    "dark": "0.12 0.16 0.22",
    "light": "0.96 0.97 0.99",
    "border": "0.82 0.86 0.90",
    "accent": "0.99 0.56 0.09",
    "muted": "0.45 0.50 0.56",
    "row_alt": "0.94 0.95 0.97",
}


def color(name: str) -> str:
    return COLORS.get(name, "0 0 0")
