"""
PDF package entrypoint.

For kompatibilitu exportujeme povodnu funkciu `export_simple_pdf` z legacy modulu.
Postupne sa bude kod refaktorovat do podmodulov.
"""

from web_calculator.utils.pdf.core.legacy import export_simple_pdf  # noqa: F401

