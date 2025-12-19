# WEB Calculator (CustomTkinter)

A desktop pricing calculator for website and e-shop projects. Built with Python and CustomTkinter/Tkinter, using JSON catalogs for packages and services. Supports selecting a package or standalone add-ons, applies bundle-specific pricing and free quotas, shows previews, and exports PDF quotes/proformas/invoices with configurable sections and company profiles.

## Features
- Package selection with price modes (base/promo/intra); auto-selects included services and free quotas per package (`included_quantities`).
- Add-ons grouped by source (PRIMARY/WEB/ESHOP), sortable/filterable by tag; quick search dialog.
- Inline edits: double-click to edit price/quantity or view service details.
- Package editor: double-click a package to adjust included services and free quotas; saves to JSON.
- VAT: editable rate, two modes (`add` = prices without VAT, `included` = prices with VAT).
- Discounts: apply a % discount to totals; reflected in preview/PDF.
- Client profiles: save/load JSON with package, services, quantities, client info, and discount.
- Company profiles: multiple suppliers with fields `code/label/value`, reusable `sources` for codes; active profile visible in titles.
- PDF export: quote/proforma/invoice; four editable sections (Dodavatel, Prehlad platby, Odberatel, Suvaha), items table, optional QR; per-document text overrides stored in `pdf_content.json`.
- Help/preview/search dialogs; responsive window sizing.

## Data model
- Split JSON in `src/web_calculator/data/` (ignored in git):
  - `packages.json`: `base_price`, optional `promo_price`/`intra_price`, `included_services`, `included_quantities`.
  - `services_*.json` (primary/web/eshop/extra): `price`, optional `price2`, `bundle` (package code), `source`, `tag`, `unit`, `info`.
  - `supplier.json`: `active` profile id, `profiles` list (`id/name/fields[code,label,value]`), `sources` list (`code/label`).
  - `pdf_content.json`: per doc-type arrays: `supplier_lines`, `payment_lines`, `client_lines`, `summary_lines`.
- Runtime uses only split JSON. Historical Excel/import helpers live in `vyvojarske_doplnky/`.

## Project structure
- `src/web_calculator/app.py` - entry point.
- `core/` - pricing engine, models, catalog loader (JSON only), invoice payload builder, supplier/pdf-content services.
- `ui/` - Tkinter layout components and controllers (`service_controller`, `actions_controller`); dialogs for supplier, PDF export/content, search/filter/preview.
- `utils/` - PDF renderer (`pdf.py` + wrappers `pdf_quote/proforma/invoice`), variable symbol generator, optional QR helper.


## Running
```bash
cd WEB_calculator/src
pip install customtkinter
# optional: pip install qrcode
python -m web_calculator.app
```

## Notes
- Data files in `src/web_calculator/data/` are git-ignored; place your JSON catalogs there to run the app.
- PDF export requires client info; QR is optional (uses `qrcode` if installed).
