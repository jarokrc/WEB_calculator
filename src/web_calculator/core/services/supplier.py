from __future__ import annotations

import json
from pathlib import Path


SUPPLIER_PATH = Path(__file__).resolve().parents[2] / "data" / "supplier.json"

DEFAULT_SUPPLIER = {
    "active": "default",
    "profiles": [
        {
            "id": "default",
            "name": "Default",
            "fields": [
                {"code": "name", "label": "Nazov", "value": "RedBlue Solutions s. r. o."},
                {"code": "address", "label": "Adresa", "value": "Sadova 2719/3A, 905 01 Senica"},
                {"code": "ico", "label": "ICO", "value": "55522467"},
                {"code": "dic", "label": "DIC", "value": "2122005897"},
                {"code": "icdph", "label": "IC DPH", "value": ""},
                {"code": "iban", "label": "IBAN", "value": ""},
                {"code": "email", "label": "Email", "value": ""},
            ],
        }
    ],
    "sources": [
        {"code": "name", "label": "Nazov"},
        {"code": "address", "label": "Adresa"},
        {"code": "ico", "label": "ICO"},
        {"code": "dic", "label": "DIC"},
        {"code": "icdph", "label": "IC DPH"},
        {"code": "iban", "label": "IBAN"},
        {"code": "email", "label": "Email"},
    ],
}


def load_supplier(path: Path | None = None) -> dict:
    target = path or SUPPLIER_PATH
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            # Accept older dict format: convert to profiles list
            if isinstance(data, dict) and "profiles" not in data:
                if "fields" in data:
                    fields_raw = data.get("fields", [])
                    fields = []
                    for item in fields_raw:
                        if isinstance(item, dict):
                            fields.append(
                                {
                                    "code": str(item.get("code") or item.get("label") or "").strip(),
                                    "label": str(item.get("label") or item.get("code") or "").strip(),
                                    "value": str(item.get("value") or "").strip(),
                                }
                            )
                        else:
                            fields.append({"code": str(item), "label": str(item), "value": str(getattr(item, "value", ""))})
                else:
                    fields = [{"code": str(k), "label": str(k), "value": str(v)} for k, v in data.items()]
                data = {"active": "default", "profiles": [{"id": "default", "name": "Default", "fields": fields}]}

            profiles = []
            for prof in data.get("profiles", []):
                if not isinstance(prof, dict):
                    continue
                fields = []
                for item in prof.get("fields", []):
                    if not isinstance(item, dict):
                        continue
                    fields.append(
                        {
                            "code": str(item.get("code") or item.get("label") or "").strip(),
                            "label": str(item.get("label") or item.get("code") or "").strip(),
                            "value": str(item.get("value") or "").strip(),
                        }
                    )
                if not fields:
                    continue
                profiles.append(
                    {
                        "id": str(prof.get("id") or prof.get("name") or f"profile_{len(profiles)+1}"),
                        "name": str(prof.get("name") or prof.get("id") or f"Profil {len(profiles)+1}"),
                        "fields": fields,
                    }
                )
            if not profiles:
                profiles = DEFAULT_SUPPLIER["profiles"]
            active = data.get("active") or profiles[0]["id"]
            if active not in {p["id"] for p in profiles}:
                active = profiles[0]["id"]
            sources_raw = data.get("sources", [])
            sources: list[dict] = []
            for src in sources_raw:
                if not isinstance(src, dict):
                    continue
                code = str(src.get("code") or "").strip()
                label = str(src.get("label") or code).strip()
                if not code and not label:
                    continue
                sources.append({"code": code or label, "label": label or code})
            if not sources:
                sources = DEFAULT_SUPPLIER.get("sources", [])
            return {"active": active, "profiles": profiles, "sources": sources}
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_SUPPLIER))


def save_supplier(data: dict, path: Path | None = None) -> Path:
    target = path or SUPPLIER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
