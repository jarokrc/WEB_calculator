from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.models.service import Service


def test_pricing_engine_sums_package_and_quantities(sample_package, sample_service):
    engine = PricingEngine(sample_package)
    extra = Service(code="GEN-SEO", label="SEO", price=30.0)

    breakdown = engine.summarize([(sample_service, 2), extra])

    assert breakdown.base == sample_package.base_price
    assert breakdown.extras == sample_service.price * 2 + extra.price
    assert breakdown.total == breakdown.base + breakdown.extras


def test_format_currency_uses_eur_suffix():
    formatted = PricingEngine.format_currency(1234.5)
    assert formatted.endswith("EUR")
    assert "1,234.50" in formatted
