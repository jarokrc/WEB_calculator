# Refaktor rodiny PDF

## Stav a ciele
- Povodny renderer bol v monolite `utils/pdf.py`; presunuty do `core/legacy.py` (legacy API `export_simple_pdf`).
- Nova struktura pod `utils/pdf/`:
  - `core/`: `fonts.py`, `drawing.py`, `layout_common.py`, `totals.py`, `builder.py`, `legacy.py` (zatial fallback).
  - `sections/`: `supplier.py`, `client.py`, `payment.py`, `summary.py`, `items_table.py` (renderery blokov).
  - `renderers/`: `pdf_renderer.py` (novy orchestrator s fallbackom na legacy), export wrappery v `pdf/exports/` (`quote/proforma/invoice`) volaju `render_pdf`.
  - `utils/variable_symbol.py` presunuty do `utils/pdf/utils/variable_symbol.py` (stary stub reexportuje).
- Exporty v UI pouzivaju `render_pdf` (cez `export_quote/proforma/invoice` v `pdf/exports`, aliasovane aj v `utils/pdf_*.py`), takze novy renderer bezi; ak zlyha, fallbackne na legacy.

## Novy renderer (_render_new v renderers/pdf_renderer.py)
- Fonty sa nacitavaju cez `fonts.load_font_map()` (core/fonts.py); ak nenajde Unicode TTF, builder pouzije Helvetica. Po vyrendrovani sa vola `clear_font_map()`.
- Geometria a farby su v `core/layout_common.py` (PAGE/SECTION/TABLE dimenzie, COLORS).
- Sekcie stavaju riadky takto:
  - Dodavatel: `supplier_lines_override` alebo `build_supplier_lines(supplier)`.
  - Klient: `client_lines_override` alebo `build_client_lines(client)`.
  - Platba: `payment_lines_override` alebo `build_payment_lines` (VS/datum/balik/stav, QR z `qr_data`/`invoice_no`).
  - Suvaha: `summary_lines_override` alebo `build_summary_lines` (pouziva `TotalsContext/derive_totals` a `format_currency` z `core/totals.py`).
- Polozky: `prepare_display_items` prida synteticky riadok balika ak ma cenu a prepoita povodne extras; tabulka cez `sections/items_table` (overflow na dalsie stranky).
- Builder: `core/builder.build_pdf_bytes` sklada obsah a fonty, vytvori PDF.
- Layout: stlpce a sekcie su bez medzier (`COL_GAP=0`, `SECTION_GAP=0`), aby okraje susediacich blokov lícovali.

## Co este zostava (odstrihnut legacy)
- Legacy nechavame ako studeny fallback; nove moduly na neho neviazeme, spusti sa len pri chybe renderera.
- Presunut zvysne vypocty/konstanty z legacy do `core`/`sections` a odstranit odkazovanie, nasledne vypnut fallback.
- Overit importy v projekte (UI kontrolery pouzivaju `pdf_quote/proforma/invoice`, tie volaju novy renderer).

## Testovanie
- Sanity skript `tests/pdf_renderer_check.py` generuje scenare: `basic_add`, `vat_included`, `overflow_table`, `overrides`; vystupy idu do `dist/test_pdf_renderer_<scenario>.pdf` a report do `vyvojarske_doplnky/pdf_renderer_report.json`.
- Odporucane dalsie behy: s/bez balika, rozne DPH, overflow tabulky, overrides (pokriva ich aktualny skript).

## Poznamky
- Legacy ostava ako zdroj pravdy, kym novy renderer nebude plne odladeny; fallback je poistka.
- Pri dalsom refaktore drzat parity layoutu s legacy (geometria, farby) a kontrolovat sumy.
- Uprava `render_pdf` na pouzitie novych modulov je hotova; fallback sluzi len ako poistka, mozno ho neskor odstranit.
