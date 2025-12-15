# Štruktúra dát pre WEB kalkulačku

- `packages.json` – balíky (kód, názov, popis, cena, included_services).
- `services_web.json` – webové služby/doplnky (vrátane `bundle` a `price2`).
- `services_eshop.json` – e‑shop služby/doplnky (vrátane `bundle` a `price2`).
- `catalog.json` – len balíky; ponechaný ako fallback kombinovaný súbor (pole `services` prázdne).
- `cennik_webu.xlsx` – zdrojový Excel (sheet `_DATA`) pre pôvodné texty a ceny.

Loader preferuje split súbory (`packages.json`, `services_web.json`, `services_eshop.json`); ak chýbajú, použije `catalog.json`, a napokon Excel.
