# utils
- `pdf_quote.py`, `pdf_proforma.py`, `pdf_invoice.py`: thin aliases to `utils/pdf/exports` wrappers calling the new renderer.
- `qr.py`: helper to build QR matrix; used by PDF rendering when qrcode lib is available.
- `variable_symbol.py`: legacy stub re-exporting `utils/pdf/utils/variable_symbol`.
- Subpackage `pdf/`: full PDF rendering pipeline (core/layout/renderers/sections/exports/utils).
- `__init__.py`: package marker.
