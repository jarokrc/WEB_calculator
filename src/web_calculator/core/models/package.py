from dataclasses import dataclass, field
from typing import List


@dataclass
class Package:
    """Represents a predefined website package with a base price."""

    code: str
    name: str
    description: str
    base_price: float
    promo_price: float | None = None
    intra_price: float | None = None
    cms: str = ""
    backend: str = ""
    note: str = ""
    included_services: List[str] = field(default_factory=list)
    included_quantities: dict[str, int] = field(default_factory=dict)
