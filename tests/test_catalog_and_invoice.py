import json

import pytest

from web_calculator.core.calculations.pricing_engine import PricingEngine
from web_calculator.core.services import catalog
from web_calculator.core.services import invoice


def test_load_catalog_from_json(tmp_path):
    json_path = tmp_path / "catalog.json"
    data = {
        "packages": [
            {"code": "PKG", "name": "Pkg", "description": "Desc", "base_price": 99.0},
        ],
        "services": [
            {"code": "SVC", "label": "Service", "price": 10.0},
        ],
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    cat = catalog.load_catalog(json_path)

    assert len(cat.packages) == 1
    assert cat.packages[0].code == "PKG"
    assert len(cat.services) == 1
    assert cat.services[0].label == "Service"


def test_load_catalog_missing_json_returns_empty(tmp_path):
    missing_dir = tmp_path / "no_data_here"
    cat = catalog.load_catalog(missing_dir)
    assert cat.packages == []
    assert cat.services == []


def test_build_invoice_payload(monkeypatch, sample_package, sample_service):
    class FakeDate(invoice.date):
        @classmethod
        def today(cls):
            return cls(2024, 1, 2)

    monkeypatch.setattr(invoice, "date", FakeDate)

    pricing = PricingEngine(sample_package)
    selections = [(sample_service, 2)]
    client = {"name": "Alice", "address": "Street 1"}

    payload = invoice.build_invoice_payload(
        package=sample_package,
        selections=selections,
        client=client,
        pricing=pricing,
        vat_rate=0.2,
        qr_data="QRDATA",
    )

    assert payload["invoice_no"] == "20240102"
    assert payload["package"] == sample_package.code
    assert payload["totals"]["base"] == sample_package.base_price
    assert payload["totals"]["extras"] == sample_service.price * 2
    assert payload["totals"]["vat_rate"] == 0.2
    assert payload["totals"]["total_with_vat"] == payload["totals"]["total_no_vat"] * 1.2
    assert payload["items"][0]["qty"] == 2
    assert payload["client"]["name"] == "Alice"


def test_build_invoice_payload_with_discount(monkeypatch, sample_package, sample_service):
    class FakeDate(invoice.date):
        @classmethod
        def today(cls):
            return cls(2024, 2, 3)

    monkeypatch.setattr(invoice, "date", FakeDate)

    pricing = PricingEngine(sample_package)
    selections = [(sample_service, 1)]
    payload = invoice.build_invoice_payload(
        package=sample_package,
        selections=selections,
        client={},
        pricing=pricing,
        vat_rate=0.23,
        discount_pct=10.0,
    )

    totals = payload["totals"]
    total_before = sample_package.base_price + sample_service.price
    discount_amount = total_before * 0.1
    assert totals["total_before_discount"] == total_before
    assert totals["discount_amount"] == pytest.approx(discount_amount)
    assert totals["total_no_vat"] == pytest.approx(total_before - discount_amount)
    assert totals["total_with_vat"] == pytest.approx(totals["total_no_vat"] * 1.23)
