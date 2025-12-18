# WEB Calculator (CustomTkinter)

A desktop pricing calculator for website and e-shop projects. Built with Python and CustomTkinter/Tkinter, using JSON catalogs for packages and services. Supports selecting a package or standalone add-ons, applies bundle-specific pricing and free quotas, shows previews, and exports a one-page PDF offer.

## Features
- Package selection with price modes (base/promo/intra); auto-selects included services and free quotas per package (`included_quantities`).
- Add-ons grouped by source (PRIMARY/WEB/ESHOP), sortable/filterable by tag; quick search dialog.
- Inline edits: double-click to edit price/quantity or view service details.
- Package editor: double-click a package to adjust included services and free quotas; saves to JSON.
- Discounts: apply a % discount to totals; reflected in preview/PDF.
- Client profiles: save/load JSON with package, services, quantities, client info, and discount.
- PDF export: 1-page styled offer (supplier/client blocks, payment summary, items table, optional QR).
- Help/preview/search dialogs; responsive window sizing.

## Data model
- Split JSON in `src/web_calculator/data/` (ignored in git):
  - `packages.json`: fields include `base_price`, optional `promo_price`/`intra_price`, `included_services`, `included_quantities`.
  - `services_*.json` (primary/web/eshop/extra): `price`, optional `price2`, `bundle` (package code), `source`, `tag`, `info`.
- No Excel/catalog fallback in runtime. Historical import scripts and XLSX live in `vyvojarske_doplnky/`.

## Project structure
- `src/web_calculator/app.py` - entry point.
- `core/` - pricing engine, models, catalog loader (JSON only), invoice payload builder.
- `ui/` - Tkinter layout components and controllers (`service_controller`, `actions_controller`).
- `utils/` - PDF renderer, optional QR helper.


## Running
```bash
cd WEB_calculator/src
pip install customtkinter
python -m web_calculator.app
```

## Notes
- Data files in `src/web_calculator/data/` are git-ignored; place your JSON catalogs there to run the app.
- PDF export requires client info; QR is optional (uses `qrcode` if installed).
