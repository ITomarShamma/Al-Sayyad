# -*- coding: utf-8 -*-
"""يولّد أيقونات الـPWA المؤقتة: علامة «ص» بيضاء على خلفية Tide.

تشغيل (مرة واحدة، النواتج تُرفع للمستودع):
    python scripts/make_pwa_icons.py

عند وصول اللوغو النهائي من Figma: استبدل ملفات static/img/pwa/ بنفس
الأسماء والمقاسات — لا يلزم أي تغيير بالكود.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "static" / "img" / "pwa"
TIDE = "#0E6B5E"

# خط IBM Plex بصيغة woff2 لا يفتحه Pillow — نستعمل أول خط نظام يحوي العربية
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\tahomabd.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]


def make_icon(size):
    font_path = next(p for p in FONT_CANDIDATES if Path(p).exists())
    icon = Image.new("RGB", (size, size), TIDE)
    draw = ImageDraw.Draw(icon)
    font = ImageFont.truetype(font_path, int(size * 0.52))
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
