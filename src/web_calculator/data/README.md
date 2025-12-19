# Struktura dat pre WEB kalkulacku

- `packages.json` - baliky (kod, nazov, popis, ceny `base/promo/intra`, `included_services`, `included_quantities`).
- `services_web.json` - webove sluzby/doplnky (zdroj `WEB`, vratane `bundle` a `price2`).
- `services_eshop.json` - e-shop sluzby/doplnky (zdroj `ESHOP`, vratane `bundle` a `price2`).
- `services_primary.json` - primarne sluzby (zdroj `PRIMARY`); volitelne `services_extra.json`.
- `supplier.json` - firemne profily: `{"active": "id", "profiles": [{"id","name","fields":[{"code","label","value"}]}], "sources":[{"code","label"}]}`.
- `pdf_content.json` - texty sekcii PDF pre kazdy typ dokumentu (`quote/proforma/invoice`): polia `supplier_lines`, `payment_lines`, `client_lines`, `summary_lines`.
- Historicke zdroje: `catalog.json` a `cennik_webu.xlsx` (sheet `_DATA`) len ako backup/import; runtime pouziva split JSON.
