from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

PDF_CONTENT_PATH = Path(__file__).resolve().parents[2] / "data" / "pdf_content.json"

DEFAULT_CONTENT: Dict[str, dict] = {
    "quote": {
        "supplier_lines": [],
        "payment_lines": [],
        "client_lines": [],
    },
    "proforma": {
        "supplier_lines": [],
        "payment_lines": [],
        "client_lines": [],
    },
    "invoice": {
        "supplier_lines": [],
        "payment_lines": [],
        "client_lines": [],
    },
}


def load_pdf_content(path: Path | None = None) -> dict:
    target = path or PDF_CONTENT_PATH
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONTENT))


def save_pdf_content(data: dict, path: Path | None = None) -> Path:
    target = path or PDF_CONTENT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
