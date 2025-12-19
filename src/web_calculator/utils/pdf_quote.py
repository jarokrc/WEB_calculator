from pathlib import Path
from typing import Mapping

from web_calculator.utils.pdf import export_simple_pdf


def export_quote_pdf(path: Path, payload: Mapping) -> None:
    """
    Wrapper pre export cenovej ponuky.
    """
    export_simple_pdf(path, payload)
