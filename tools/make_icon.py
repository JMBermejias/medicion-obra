#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Genera los iconos de la app (icon-192.png y icon-512.png).
# Copyright (C) 2026 JMBernabeu - GPL-3.0
import os
import sys
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/run/host/fonts/truetype/noto/NotoSans-Bold.ttf"
if not os.path.exists(FONT_BOLD):
    FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
if not os.path.exists(FONT_BOLD):
    raise SystemExit("No se encontro la fuente Noto Sans Bold")

TOP = (79, 195, 247)      # #4FC3F7
BOTTOM = (2, 136, 209)    # #0288D1
WHITE = (255, 255, 255, 255)
TICK = (2, 112, 174, 255)
SCALE = 4


def rounded_gradient(size, radius):
    img = Image.new("RGBA", (size * SCALE, size * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    mask = Image.new("L", (size * SCALE, size * SCALE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * SCALE - 1, size * SCALE - 1), radius=radius * SCALE, fill=255
    )
    grad = Image.new("RGBA", (size * SCALE, size * SCALE))
    gd = ImageDraw.Draw(grad)
    for y in range(size * SCALE):
        t = y / (size * SCALE - 1)
        color = tuple(int(BOTTOM[i] + (TOP[i] - BOTTOM[i]) * t) for i in range(3))
        gd.line((0, y, size * SCALE - 1, y), fill=color + (255,))
    img.paste(grad, (0, 0), mask)
    return img


def ruler(draw, cx, y, width, thick, tick_h):
    x0, x1 = cx - width // 2, cx + width // 2
    draw.rounded_rectangle(
        (x0, y, x1, y + thick), radius=thick // 2, fill=WHITE
    )
    n = 13
    step = width / (n - 1)
    for i in range(n):
        if i % 2 == 0:
            th = tick_h
            lw = max(2 * SCALE, int(SCALE * 0.8))
        else:
            th = tick_h * 0.55
            lw = max(2 * SCALE, int(SCALE * 0.5))
        tx = x0 + int(round(i * step))
        draw.line(
            (tx, y + thick - lw, tx, y + thick + th),
            fill=TICK, width=lw,
        )


def draw_icon(size, out_path):
    S = size * SCALE
    img = rounded_gradient(size, int(size * 0.22))
    draw = ImageDraw.Draw(img)

    # Letra "M"
    font = ImageFont.truetype(FONT_BOLD, int(size * 0.52 * SCALE))
    text = "M"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = S // 2
    ty = int(S * 0.14)
    draw.text((cx - tw // 2 - bbox[0], ty - bbox[1]), text,
              font=font, fill=WHITE)

    # Regla de medicion (fajita inferior)
    rw = int(S * 0.72)
    ry = int(S * 0.62)
    rt = int(S * 0.055)
    th2 = int(S * 0.09)
    ruler(draw, cx, ry, rw, rt, th2)

    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, "PNG")
    print("Generado:", out_path, size, "x", size)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    draw_icon(512, os.path.join(root, "icon-512.png"))
    draw_icon(192, os.path.join(root, "icon-192.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
