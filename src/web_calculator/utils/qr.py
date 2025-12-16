"""
Minimal QR helper.
Uses the `qrcode` library if available; otherwise returns graceful fallbacks.
"""

from __future__ import annotations

import base64
import io
from typing import Optional, Sequence


def make_qr_matrix(data: str) -> Optional[Sequence[Sequence[bool]]]:
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(border=1, box_size=1)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    return matrix


def generate_qr_png_base64(data: str) -> str:
    """
    Return QR code as base64-encoded PNG. Empty string if generation is unavailable.
    """
    try:
        import qrcode
    except ImportError:
        return ""

    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
