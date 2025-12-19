# core/services
- `catalog.py`: loads and filters catalog/packages from data JSON; handles saving updates.
- `invoice.py`: builds invoice/quote/proforma payloads using pricing engine and selected services.
- `pdf_content.py`: loads/saves user-edited PDF section texts (`data/pdf_content.json`).
- `supplier.py`: handles supplier profile data (load/save/validation).
- `__init__.py`: package marker.
