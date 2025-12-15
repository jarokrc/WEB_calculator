from dataclasses import dataclass


@dataclass
class Service:
    """Represents a single billable service or add-on."""

    code: str
    label: str
    source: str = ""
    unit: str = "od"
    price: float = 0.0
    price2: float = 0.0  # alternative cena (napr. v balíku)
    bundle: str = "NONE"  # START / MINI / BUSINESS / PRO_CMS / ESHOP_Z / ESHOP_P / NONE
    tag: str = ""
    info: str = ""
    # Optional package filter in future
