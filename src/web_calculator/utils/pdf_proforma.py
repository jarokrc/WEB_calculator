from pathlib import Path
from typing import Mapping

from web_calculator.utils.pdf import export_simple_pdf


def export_proforma_pdf(path: Path, payload: Mapping) -> None:
    """
    Wrapper pre export predfaktury (zatial pouziva spolocny layout).
    """
    export_simple_pdf(path, payload)
