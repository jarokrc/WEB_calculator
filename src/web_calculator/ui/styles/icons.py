from __future__ import annotations

from typing import Dict

import customtkinter as ctk
from PIL import Image


_ICON_PATTERNS: dict[str, list[str]] = {
    "search": [
        "................",
        ".....XXXX.......",
        "....XX..XX......",
        "...XX....XX.....",
        "...XX....XX.....",
        "...XX....XX.....",
        "....XX..XX......",
        ".....XXXX.......",
        "........XX......",
        ".........XX.....",
        "..........XX....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "preview": [
        "................",
        "....XXXXXX......",
        "...XX....XX.....",
        "..XX......XX....",
        ".XX..XXXX..XX...",
        ".XX..X..X..XX...",
        ".XX..XXXX..XX...",
        "..XX......XX....",
        "...XX....XX.....",
        "....XXXXXX......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "help": [
        ".....XXXX.......",
        "....XX..XX......",
        "........XX......",
        ".......XX.......",
        "......XX........",
        "......XX........",
        "................",
        "......XX........",
        "......XX........",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "save": [
        "..XXXXXXXXXX....",
        ".XX........XX...",
        ".XX........XX...",
        ".XX..XXXX..XX...",
        ".XX..XXXX..XX...",
        ".XX........XX...",
        ".XX........XX...",
        ".XX..XXXX..XX...",
        ".XX..XXXX..XX...",
        ".XX........XX...",
        "..XXXXXXXXXX....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "load": [
        ".......XX.......",
        ".......XX.......",
        ".......XX.......",
        "..XXXXXXXXXX....",
        ".....XXXX.......",
        "......XX........",
        ".......XX.......",
        "................",
        "..XXXXXXXXXX....",
        ".XX........XX...",
        "..XXXXXXXXXX....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "reset": [
        "XX..........XX..",
        ".XX........XX...",
        "..XX......XX....",
        "...XX....XX.....",
        "....XX..XX......",
        ".....XXXX.......",
        "....XX..XX......",
        "...XX....XX.....",
        "..XX......XX....",
        ".XX........XX...",
        "XX..........XX..",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "pdf": [
        "..XXXXXXXXX.....",
        "..XX.....XX.....",
        "..XX......XX....",
        "..XX......XX....",
        "..XX......XX....",
        "..XX......XX....",
        "..XX......XX....",
        "..XX.....XX.....",
        "..XXXXXXXXX.....",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
}


def _hex_to_rgba(color: str) -> tuple[int, int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        return (0, 0, 0, 255)
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return (r, g, b, 255)


def _build_image(pattern: list[str], color: str) -> Image.Image:
    height = len(pattern)
    width = max(len(row) for row in pattern)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pix = img.load()
    rgba = _hex_to_rgba(color)
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch != ".":
                pix[x, y] = rgba
    return img


def build_icons(color: str, size: tuple[int, int] = (16, 16)) -> Dict[str, ctk.CTkImage]:
    return {
        name: ctk.CTkImage(light_image=_build_image(pattern, color), dark_image=_build_image(pattern, color), size=size)
        for name, pattern in _ICON_PATTERNS.items()
    }
