from pathlib import Path
from typing import Mapping

from web_calculator.utils.pdf.renderers.pdf_renderer import render_pdf


def export_invoice_pdf(path: Path, payload: Mapping) -> None:
    """
    Wrapper pre export faktury (zatial spolocny layout).
    """
    render_pdf(path, payload)
