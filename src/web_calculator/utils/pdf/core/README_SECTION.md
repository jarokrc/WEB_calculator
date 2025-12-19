# utils/pdf/core
- `fonts.py`: loads Unicode TrueType fonts, builds PDF font objects, font map helpers.
- `drawing.py`: low-level PDF drawing helpers (text, rects, QR, currency formatting).
- `layout_common.py`: layout constants for page/sections/table and colors.
- `totals.py`: totals computations, currency formatting, display item prep.
- `builder.py`: assembles PDF objects and content streams into final PDF bytes.
- `legacy.py`: legacy monolithic renderer kept as cold fallback; called from `renderers/pdf_renderer.py` on exceptions.
- `__init__.py`: re-exports `export_simple_pdf` for compatibility.
