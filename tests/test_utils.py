import builtins

from web_calculator.ui.components.service_table import ServiceTable
from web_calculator.utils import pdf, qr


def test_make_qr_matrix_without_qrcode(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qrcode":
            raise ImportError("missing qrcode")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert qr.make_qr_matrix("data") is None


def test_export_simple_pdf_creates_valid_pdf(tmp_path):
    payload = {
        "invoice_no": "INV-1",
        "issue_date": "2024-01-01",
        "doc_title": "Cenova ponuka",
        "supplier": {"name": "Supp", "address": "Addr", "ico": "1", "dic": "2", "email": ""},
        "client": {"name": "Client", "address": "Addr", "ico": "", "dic": "", "icdph": "", "email": ""},
        "totals": {
            "base": 0.0,
            "extras": 80.0,
            "vat_rate": 0.23,
            "vat": 18.4,
            "total_with_vat": 98.4,
            "original_base": 0.0,
            "original_extras": 100.0,
            "original_total_before_discount": 100.0,
        },
        "items": [{"name": "Item A", "qty": 2, "unit_price": 40.0, "total": 80.0, "original_unit_price": 50.0, "original_total": 100.0, "unit": "ks"}],
        "qr_data": "INV-1",
    }
    out_path = tmp_path / "offer.pdf"

    pdf.export_simple_pdf(out_path, payload)

    data = out_path.read_bytes()
    assert data.startswith(b"%PDF")
    startxref = int(data.split(b"startxref\n")[1].split(b"\n")[0])
    assert data[startxref : startxref + 4] == b"xref"
    assert b"INV-1" in data  # header
    # preškrtnuté hodnoty obsahujú obe ceny
    assert b"40.00 EUR" in data
    assert b"50.00 EUR" in data


def test_export_simple_pdf_collapses_overflow_items(tmp_path):
    payload = {
        "invoice_no": "INV-2",
        "issue_date": "2024-01-01",
        "doc_title": "Ponuka",
        "supplier": {"name": "Supp", "address": "Addr", "ico": "1", "dic": "2", "email": ""},
        "client": {"name": "Client", "address": "Addr", "ico": "", "dic": "", "icdph": "", "email": ""},
        "totals": {"total_no_vat": 300.0, "vat": 69.0, "total_with_vat": 369.0, "vat_rate": 0.23},
        "items": [{"name": f"Item {i}", "qty": 1, "unit_price": 10.0, "total": 10.0} for i in range(15)],
        "qr_data": None,
    }
    out_path = tmp_path / "overflow.pdf"

    pdf.export_simple_pdf(out_path, payload)

    text = out_path.read_text("latin-1")
    assert "Dalsie polozky" in text
    assert "Ponuka c. INV-2" in text
    assert "Nazov" in text


def test_export_pdf_placeholder_qr_when_library_missing(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qrcode":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    payload = {
        "invoice_no": "INV-QR",
        "issue_date": "2024-01-01",
        "doc_title": "Ponuka",
        "supplier": {"name": "Supp", "address": "Addr", "ico": "1", "dic": "2", "email": ""},
        "client": {"name": "Client", "address": "Addr", "ico": "", "dic": "", "icdph": "", "email": ""},
        "totals": {"total_no_vat": 10.0, "vat": 2.3, "total_with_vat": 12.3, "vat_rate": 0.23},
        "items": [{"name": "Item", "qty": 1, "unit_price": 10.0, "total": 10.0}],
        "qr_data": "ANY",
    }
    out_path = tmp_path / "qr_placeholder.pdf"
    pdf.export_simple_pdf(out_path, payload)
    text = out_path.read_text("latin-1")
    assert "QR" in text  # placeholder text rendered


def test_format_qty_formats_integers_and_floats():
    assert ServiceTable._format_qty(3) == "3"
    assert ServiceTable._format_qty(2.5) == "2.50"
