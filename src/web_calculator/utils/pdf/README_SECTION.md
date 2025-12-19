# utils/pdf
- `renderers/pdf_renderer.py`: new PDF orchestrator; tries new pipeline then falls back to legacy on exception.
- `core/`: shared primitives (fonts, drawing, layout constants, totals helpers, builder, legacy fallback).
- `sections/`: renderers for individual PDF blocks (supplier, client, payment, summary, items table).
- `exports/`: wrappers for quote/proforma/invoice exports used by UI.
- `utils/`: PDF-specific utilities (variable symbol).
- `info.md`: design notes and refactor status.
- `__init__.py`: re-exports `export_simple_pdf` from legacy for compatibility.
