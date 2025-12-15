from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from web_calculator.core.models.package import Package
from web_calculator.core.models.service import Service


@dataclass
class Catalog:
    packages: list[Package]
    services: list[Service]


def _load_packages(path: Path) -> list[Package]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("packages", data)
    packages: list[Package] = []
    for item in raw:
        item = dict(item)
        item.setdefault("included_services", [])
        item.setdefault("included_quantities", {})
        packages.append(Package(**item))
    return packages


def _load_services(path: Path) -> list[Service]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("services", data)
    services: list[Service] = []
    for item in raw:
        item = dict(item)
        item.setdefault("price2", 0.0)
        item.setdefault("bundle", "NONE")
        services.append(Service(**item))
    return services


def _load_from_combined(json_path: Path) -> Catalog:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    packages = [Package(**item) for item in data.get("packages", [])]
    services = _load_services(Path(json_path))
    return Catalog(packages=packages, services=services)


def _load_from_split(base_dir: Path) -> Catalog:
    packages_path = base_dir / "data" / "packages.json"
    services_paths = [
        base_dir / "data" / "services_web.json",
        base_dir / "data" / "services_primary.json",
        base_dir / "data" / "services_eshop.json",
        base_dir / "data" / "services_extra.json",
    ]
    packages = _load_packages(packages_path)

    services: list[Service] = []
    for spath in services_paths:
        if spath.exists():
            services.extend(_load_services(spath))
    return Catalog(packages=packages, services=services)


def load_catalog(path: str | Path | None = None) -> Catalog:
    """
    Load catalog primarne zo split JSON (packages + services_*); fallback Excel.

    - Split JSON: `data/packages.json`, `data/services_web.json`, `data/services_eshop.json`, `data/services_primary.json`, volitelne `services_extra.json`
    - Fallback Excel: odstranene (historicky len na import)
    """

    base_dir = Path(__file__).resolve().parents[2]

    if path:
        custom = Path(path)
        if custom.is_dir():
            base_dir = custom
        elif custom.exists():
            # Allow explicit combined path pre-existing, but prefer split if folder is provided.
            try:
                return _load_from_combined(custom)
            except Exception as exc:
                print(f"Warning: failed to load provided catalog {custom}: {exc}")

    packages_path = base_dir / "data" / "packages.json"
    if packages_path.exists():
        try:
            return _load_from_split(base_dir)
        except Exception as exc:
            print(f"Warning: failed to load split catalog: {exc}")

    # If split JSON is missing alebo poskodene, vrat prazdny katalog.
    return Catalog(packages=[], services=[])


def save_catalog(catalog: Catalog, path: str | Path | None = None) -> Path:
    """
    Persist catalog do split JSON (packages.json + services_*).
    Returns path to packages file.
    """
    base_dir = Path(__file__).resolve().parents[2]
    target_dir = Path(path) if path else base_dir / "data"
    if target_dir.is_file():
        target_dir = target_dir.parent
    pkg_path = target_dir / "packages.json"
    services_paths = {
        "WEB": target_dir / "services_web.json",
        "PRIMARY": target_dir / "services_primary.json",
        "ESHOP": target_dir / "services_eshop.json",
        "EXTRA": target_dir / "services_extra.json",
    }

    pkg_payload = {"packages": [asdict(p) for p in catalog.packages]}
    pkg_path.write_text(json.dumps(pkg_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    grouped: dict[str, list[Service]] = {"WEB": [], "PRIMARY": [], "ESHOP": [], "EXTRA": []}
    for svc in catalog.services:
        src = (svc.source or "").upper()
        if src.startswith("WEB"):
            grouped["WEB"].append(svc)
        elif src.startswith("PRIMARY"):
            grouped["PRIMARY"].append(svc)
        elif src.startswith("ESHOP"):
            grouped["ESHOP"].append(svc)
        else:
            grouped["EXTRA"].append(svc)

    for key, items in grouped.items():
        path = services_paths[key]
        payload = {"services": [asdict(s) for s in items]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return pkg_path


def save_packages(catalog: Catalog, path: str | Path | None = None) -> Path:
    """
    Persist only packages to split JSON (packages.json). Keeps services bez zmeny.
    Returns resulting path.
    """
    base_dir = Path(__file__).resolve().parents[2]
    pkg_path = Path(path) if path else base_dir / "data" / "packages.json"
    payload = {"packages": [asdict(p) for p in catalog.packages]}
    pkg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return pkg_path
