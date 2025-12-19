from pathlib import Path
from typing import Mapping

from web_calculator.utils.pdf.renderers.pdf_renderer import render_pdf


def export_proforma_pdf(path: Path, payload: Mapping) -> None:
    """
    Wrapper pre export predfaktury (spolocny layout).
    """
    render_pdf(path, payload)
