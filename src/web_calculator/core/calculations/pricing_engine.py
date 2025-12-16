from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service


@dataclass
class PricingBreakdown:
    base: float
    extras: float

    @property
    def total(self) -> float:
        return self.base + self.extras


class PricingEngine:
    """Simple calculator that sums a base package with selected services."""

    def __init__(self, package: Package | None = None):
        self.package = package

    def update_package(self, package: Package | None) -> None:
        self.package = package

    def summarize(self, services: Iterable[tuple | Service]) -> PricingBreakdown:
        """
        Ak je zaznam tuple (service, qty [, original_price]), pouzije mnozstvo; inak qty=1.
        """
        base = self.package.base_price if self.package else 0.0
        extras = 0.0
        for item in services:
            if isinstance(item, tuple):
                if len(item) >= 2:
                    service, qty = item[0], item[1]
                else:
                    service, qty = item[0], 1
                extras += float(service.price) * float(qty)
            else:
                extras += float(item.price)
        return PricingBreakdown(base=base, extras=extras)

    @staticmethod
    def format_currency(value: float) -> str:
        # ASCII-friendly currency suffix to avoid encoding issues across UI/PDF.
        return f"{value:,.2f} EUR"
