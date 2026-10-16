#!/usr/bin/env python3
"""Общее для сцены со слаймом (тема Codex): палитра, шрифты, спрайт, индикаторы."""
import math
import os
from PIL import Image, ImageDraw, ImageFont

W, H, K = 536, 240, 2
FPS = 30
PX = 4

# палитра OpenAI / ChatGPT
GREEN = (16, 163, 127)          # #10A37F
GREEN_LT = (120, 230, 196)
GREEN_DK = (9, 108, 84)
EYE = (6, 28, 22)
WHITE = (236, 236, 241)         # #ECECF1
GRAY = (142, 142, 160)          # #8E8EA0
DIM = (52, 53, 65)              # #343541

_FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
MONO_B = os.path.join(_FONTS, 'DejaVuSansMono-Bold.ttf')
MONO = os.path.join(_FONTS, 'DejaVuSansMono.ttf')
f_word = ImageFont.truetype(MONO_B, 40 * K)
f_small = ImageFont.truetype(MONO, 14 * K)

# ---------- слайм ----------
SPRITE = [
    "....GGGG....",
    "..GGGGGGGG..",
    ".GHHGGGGGGG.",
    ".GHGGGGGGGG.",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    "GGGGGGGGGGGG",
    ".DDDDDDDDDD.",
]
SW, SH = len(SPRITE[0]), len(SPRITE)
BODY_W, BODY_H = SW * PX, SH * PX


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease_in(t): return t * t
def ease_out_q(t): return 1 - (1 - t) ** 2
def spring(t, freq=3.2, damp=5.0): return math.exp(-damp * t) * math.cos(2 * math.pi * freq * t)


def sprite_image(look, eyes_open, happy, melt=0.0):
    im = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
    pal = {'G': GREEN, 'H': GREEN_LT, 'D': GREEN_DK}
    for y, row in enumerate(SPRITE):
        for x, c in enumerate(row):
            if c in pal:
                im.putpixel((x, y), pal[c] + (255,))
    dx = int(round(look))
    for ex in (3, 7):
        x = ex + dx
        if happy:
            pts = ((x, 5), (x + 1, 5), (x - 1, 6), (x + 2, 6))
        elif eyes_open:
            pts = [(x + i, y) for y in (5, 6) for i in (0, 1)]
        else:
            pts = ((x, 6), (x + 1, 6))
        for p in pts:
            im.putpixel(p, EYE + (255,))
    if melt > 0:
        px = im.load()
        for yy in range(SH):
            for xx in range(SW):
                r, g, b, a = px[xx, yy]
                if a:
                    px[xx, yy] = (int(lerp(r, GREEN[0], melt)), int(lerp(g, GREEN[1], melt)),
                                  int(lerp(b, GREEN[2], melt)), 255)
    return im


def S(v): return int(round(v * K))


# ---------- индикаторы Wi-Fi и батарея (как в теме Claude) ----------
U = 2
BATTERY = 78
WIFI_MAP = [".33333.", "3.....3", "..222..", ".2...2.", ".......", "...1..."]
WIFI_PIX = [(x, y, int(c)) for y, row in enumerate(WIFI_MAP) for x, c in enumerate(row) if c != "."]


def battery_color(pct):
    if pct > 50:
        return (48, 209, 88)
    if pct > 20:
        return (255, 159, 10)
    return (255, 69, 58)


def draw_status_icons(d, t, k, top=14):
    if k <= 0:
        return
    def c(rgb): return tuple(int(v * k) for v in rgb)
    on, off = c(WHITE), c(DIM)
    right = W - 16
    bw, bh = 13 * U, 7 * U
    bx, by = right - bw - U, top
    d.rectangle([S(bx), S(by), S(bx + bw), S(by + bh)], outline=on, width=S(U))
    d.rectangle([S(bx + bw), S(by + 2 * U), S(bx + bw + U), S(by + bh - 2 * U)], fill=on)
    fw = round((bw - 4 * U) * BATTERY / 100 / U) * U
    if fw > 0:
        d.rectangle([S(bx + 2 * U), S(by + 2 * U), S(bx + 2 * U + fw), S(by + bh - 2 * U)],
                    fill=c(battery_color(BATTERY)))
    d.text((S(bx - 6), S(by + bh / 2 + 0.5)), f"{BATTERY}%", font=f_small, fill=c(GRAY), anchor='rm')
    pct_w = d.textlength(f"{BATTERY}%", font=f_small) / K
    lit = (int(t * 6) % 4) if t < 1.6 else 3
    wx, wy = bx - 6 - pct_w - 10 - 7 * U, by - U
    for (px, py, lvl) in WIFI_PIX:
        d.rectangle([S(wx + px * U), S(wy + py * U), S(wx + px * U + U), S(wy + py * U + U)],
                    fill=on if lvl <= lit else off)
    return wx


ROOT_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

_m = ImageDraw.Draw(Image.new('RGB', (1, 1)))
CH = _m.textlength("M", font=f_word) / K           # ширина знака моноширинного шрифта
CAP = -_m.textbbox((0, 0), "R", font=f_word, anchor='ls')[1] / K
