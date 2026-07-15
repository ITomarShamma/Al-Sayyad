# -*- coding: utf-8 -*-
"""يولّد أيقونات الـPWA المؤقتة: علامة «ص» بيضاء على تدرّج الشفق
(فيروزي → بنفسجي) — نفس علامة الهيدر brand__mark في هوية «شفق».

تشغيل (مرة واحدة، النواتج تُرفع للمستودع):
    pip install fonttools brotli   # لتحويل خط المستودع woff2 → ttf
    python scripts/make_pwa_icons.py

عند وصول اللوغو النهائي من Figma: استبدل ملفات static/img/pwa/ بنفس
الأسماء والمقاسات — لا يلزم أي تغيير بالكود.
"""

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img" / "pwa"

TEAL = (22, 184, 198)     # #16B8C6
VIOLET = (124, 92, 255)   # #7C5CFF

# خط المستودع نفسه (IBM Plex Sans Arabic Bold) — Pillow لا يفتح woff2،
# فنحوّله مرة واحدة إلى ttf مؤقت عبر fontTools. لا اعتماد على خطوط النظام.
BRAND_WOFF2 = ROOT / "static" / "fonts" / "ibm-plex-sans-arabic-arabic-700-normal.woff2"


def brand_font_path():
    from fontTools.ttLib import TTFont

    tmp = Path(tempfile.gettempdir()) / "sayyad-plex-arabic-700.ttf"
    if not tmp.exists():
        font = TTFont(BRAND_WOFF2)
        font.flavor = None
        font.save(tmp)
    return str(tmp)


def aurora_gradient(size):
    """تدرّج قطري فيروزي → بنفسجي مثل --grad-mark في tokens.css."""
    icon = Image.new("RGB", (size, size))
    px = icon.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))          # 0 بالزاوية العليا ← 1 بالسفلى
            px[x, y] = tuple(round(TEAL[i] + (VIOLET[i] - TEAL[i]) * t) for i in range(3))
    return icon


def make_icon(size):
    icon = aurora_gradient(size)
    draw = ImageDraw.Draw(icon)
    font = ImageFont.truetype(brand_font_path(), int(size * 0.52))
    # التمركز على صندوق الحبر الفعلي للحرف (لا صندوق السطر) — وإلا
    # ظهرت «ص» نازلة لأن كتلتها البصرية أسفل خط الأساس
    left, top, right, bottom = draw.textbbox((0, 0), "ص", font=font)
    x = (size - (right - left)) / 2 - left
    y = (size - (bottom - top)) / 2 - top
    draw.text((x, y), "ص", font=font, fill="#FFFFFF")
    return icon


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512),
                       ("apple-touch-icon.png", 180)]:
        make_icon(size).save(OUT / name)
        print(f"✓ {name} ({size}×{size})")
