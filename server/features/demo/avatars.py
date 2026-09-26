"""Abstract avatars for demo people — never a generated face, just a small
gradient mark, deterministic from their name so the same person always gets
the same one. A real photo (asked for at sign-up) always wins over this."""
from __future__ import annotations

import base64
import zlib

# A quiet, varied set of hues — nothing neon, nothing that reads as a brand colour.
_HUES = [210, 260, 15, 340, 25, 170, 200, 280, 45, 190]


def _seed(name: str) -> int:
    return zlib.crc32(name.encode("utf-8"))


def for_name(name: str) -> str:
    n = _seed(name)
    hue = _HUES[n % len(_HUES)]
    hue2 = (hue + 25 + (n >> 8) % 40) % 360
    cx1, cy1 = 30 + (n % 40), 25 + ((n >> 4) % 40)
    cx2, cy2 = 70 - (n >> 8) % 40, 75 - ((n >> 12) % 40)
    r1 = 46 + (n % 20)
    r2 = 40 + ((n >> 6) % 22)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="hsl({hue},62%,58%)"/>'
        f'<stop offset="1" stop-color="hsl({hue2},62%,46%)"/></linearGradient></defs>'
        f'<rect width="100" height="100" fill="hsl({hue},55%,92%)"/>'
        f'<circle cx="{cx1}" cy="{cy1}" r="{r1}" fill="url(#g)" opacity="0.9"/>'
        f'<circle cx="{cx2}" cy="{cy2}" r="{r2}" fill="hsl({hue2},58%,50%)" opacity="0.55"/>'
        f'</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
