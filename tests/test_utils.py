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
        "totals": {"total_no_vat": 100.0, "vat": 23.0, "total_with_vat": 123.0, "vat_rate": 0.23},
        "items": [{"name": "Item A", "qty": 2, "unit_price": 50.0, "total": 100.0}],
        "qr_data": "INV-1",
    }
    out_path = tmp_path / "offer.pdf"

    pdf.export_simple_pdf(out_path, payload)

    data = out_path.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"INV-1" in data
    assert b"%%EOF" in data.rstrip()


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


def test_format_qty_formats_integers_and_floats():
    assert ServiceTable._format_qty(3) == "3"
    assert ServiceTable._format_qty(2.5) == "2.50"
