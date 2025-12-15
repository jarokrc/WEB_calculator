"""
Minimal QR helper.
Uses the `qrcode` library if available; otherwise returns None (no QR).
"""

from __future__ import annotations

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
