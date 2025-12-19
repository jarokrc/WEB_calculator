# Technicka dokumentacia

## Prehľad
- Desktopová appka (CustomTkinter) pre tvorbu cenových ponúk/predfaktúr/faktúr: výber balíkov/služieb, výpočet cien s DPH/bez DPH, export PDF.
- Dáta sa čítajú z bundlovaných JSON v `src/web_calculator/data/` (katalóg, balíky, supplier, PDF texty), ukladanie zmien prebieha priamo do týchto súborov.
- PDF export využíva nový renderer (`utils/pdf/renderers/pdf_renderer.py`) s fallbackom na legacy len pri chybe.

## Projektová štruktúra (hlavné časti)
- `src/web_calculator/core/`: pricing engine, modely (service, package), služby (katalóg, payload builder pre PDF, supplier, pdf_content).
- `src/web_calculator/ui/`: hlavné okno, layouty, kontroléry (actions/service), komponenty (dialógy, tabuľky, selektory), témy/ikony.
- `src/web_calculator/utils/pdf/`: kompletná PDF pipeline (core/renderers/sections/exports/utils), popísaná v `info.md`; `__init__.py` reexportuje legacy `export_simple_pdf`.
- `tests/`: sanity PDF skript `tests/pdf_renderer_check.py` + jednotkové testy `tests/test_utils.py` (legacy export).
- Build špecifikácie pre PyInstaller: `RedBlueCalculator.spec`, `RedBlueCalculator_2.0.spec`, `RedBlueCalculator_2.1.spec`.

## Hlavná logika a dátové toky
- Spustenie: `app.py` vytvorí `MainWindow` s načítaným katalógom.
- Výber služieb/balíkov:
  - `ServiceController` (ui/controllers) spravuje výber, množstvá, zľavy, režim DPH.
  - `PackageSelector` a `ServiceArea` (ui/components/layouts) zobrazujú a menia výber; `SummaryPanel` počíta sumy cez `PricingEngine`.
  - Supplier a klient: dialógy `supplier_dialog.py`, `client_dialog.py`; údaje sa ukladajú do `data/supplier.json`.
- Export PDF:
  - `ActionsController.export_pdf` postaví payload cez `core/services/invoice.build_invoice_payload`, aplikuje uložené texty z `pdf_content.py`, zavolá wrapper z `utils/pdf/exports` (quote/proforma/invoice) -> `render_pdf`.
  - `render_pdf` (nový renderer) načíta fonty, skladá sekcie (`sections/*`), tabuľku položiek, builder uloží PDF; pri chybe fallback na `core/legacy.export_simple_pdf`.
  - Layout sekcií bez medzier (`COL_GAP=0`, `SECTION_GAP=0`), aby bloky lícovali.
- UI okná:
  - `main_window.py` sa pri štarte maximalizuje; sleduje monitor a po 3 s nečinnosti sa prispôsobí aktuálnemu monitoru a maximalizuje. Resize je povolený; pri stave „normal“ sa jednorazovo zmenší na ~polovicu poslednej plnej veľkosti, potom sa opäť roztiahne.
  - Dialógy (export, content editor, supplier, client, search, filter, service editor, preview) majú definované `geometry`/`minsize` a používajú `fill/expand` pre responzívnosť.

## PDF renderer (detaily)
- Orchestrátor: `renderers/pdf_renderer.py`, fallback na `legacy` v try/except.
- Core:
  - `fonts.py`: `_FONT_MAP` manažment (`load_font_map/clear_font_map`), Unicode TTF, Helvetica fallback.
  - `drawing.py`: kreslenie textov/obdĺžnikov/QR, formátovanie cien.
  - `layout_common.py`: rozmery stránky/sekcií/tabuľky, farby, medzery (aktuálne 0 pre gapy sekcií/stĺpcov).
  - `totals.py`: `derive_totals`, `format_currency`, `prepare_display_items` (syntetický balík), `recompute_original_extras`.
  - `builder.py`: skladá PDF objekty, fonty, obsah.
  - `legacy.py`: monolitický renderer, necháva sa ako cold fallback.
- Sekcie: `sections/supplier.py`, `client.py`, `payment.py`, `summary.py`, `items_table.py` (overflow na ďalšie strany).
- Exporty: `utils/pdf/exports/{quote,proforma,invoice}.py` (wrappers volané z UI).
- Testovanie: `tests/pdf_renderer_check.py` generuje scenáre (basic_add, vat_included, overflow_table, overrides), výstupy v `dist/`, report `vyvojarske_doplnky/pdf_renderer_report.json`.

## Build a spustenie
- Lokálne spustenie: `python -m web_calculator.app` (alebo `python src/web_calculator/app.py`), PYTHONPATH musí obsahovať `src`.
- PyInstaller: `pyinstaller RedBlueCalculator_2.1.spec` (windowed, ikona `data/redblueico.ico`, datas `src/web_calculator/data`). Výstup v `dist/RedBlueCalculator_2.1/`, logy v `build/RedBlueCalculator_2.1/`.

## Poznámky a odporúčania
- Legacy PDF neupravovať (slúži len ako poistka).
- README_SECTION.md v každom priečinku poskytuje stručný popis; `info.md` v PDF module zachytáva stav refaktora.
- Pri úpravách UI kontrolovať minimálne veľkosti dialógov a pracovať s `fill/expand`, aby nezmizli ovládacie prvky na menších displejoch.
