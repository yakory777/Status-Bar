#!/usr/bin/env python3
"""
Рендер превью анимации ожидания «Ready to work» — 536×240, как на дисплее.

    pip install pillow
    python tools/render_idle_gif.py            # → docs/idle.gif

Это эталон движения для прошивки: тайминги, кривые и спрайт робота
отсюда переносятся в LVGL один в один.
"""
import os
import math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT = os.path.join(HERE, 'fonts', 'Lora-Variable.ttf')
from PIL import Image, ImageDraw, ImageFont

W, H, K = 536, 240, 2
FPS = 30
PX = 4
GROUND = 150

ORANGE = (217, 119, 87)
ORANGE_DK = (160, 78, 52)
SCREEN = (38, 20, 14)
EYE = (250, 236, 222)
LAMP_ON = (255, 214, 140)
LAMP_OFF = (110, 60, 40)
WHITE = (250, 249, 245)
DIM = (52, 50, 48)
GRAY = (0x8E, 0x8E, 0x93)

f_word = ImageFont.truetype(FONT, 54 * K)
f_word.set_variation_by_name('Bold')

SPRITE = [
    ".....LL.....",
    ".....DD.....",
    ".BBBBBBBBBB.",
    "BBBBBBBBBBBB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BSSSSSSSSSSB",
    "BBBBBBBBBBBB",
    "DBBBBBBBBBBD",
    ".DDDDDDDDDD.",
    ".FFF....FFF.",
]
SW, SH = len(SPRITE[0]), len(SPRITE)
BODY_W, BODY_H = SW * PX, SH * PX


def sprite_image(look, eyes_open, lamp, happy, melt=0.0):
    im = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
    pal = {'B': ORANGE, 'D': ORANGE_DK, 'S': SCREEN, 'F': ORANGE_DK,
           'L': LAMP_ON if lamp else LAMP_OFF}
    for y, row in enumerate(SPRITE):
        for x, c in enumerate(row):
            if c in pal:
                im.putpixel((x, y), pal[c] + (255,))
    dx = int(round(look))
    for ex in (3, 7):
        x = ex + dx
        if happy:
            pts = ((x, 6), (x + 1, 6), (x - 1, 7), (x + 2, 7))
        elif eyes_open:
            pts = [(x + i, y) for y in (5, 6, 7) for i in (0, 1)]
        else:
            pts = ((x, 7), (x + 1, 7))
        for p in pts:
            im.putpixel(p, EYE + (255,))
    if melt > 0:                                     # всё перетекает в оранжевый
        px = im.load()
        for yy in range(SH):
            for xx in range(SW):
                r, g, b, a = px[xx, yy]
                if a:
                    px[xx, yy] = (int(lerp(r, ORANGE[0], melt)), int(lerp(g, ORANGE[1], melt)),
                                  int(lerp(b, ORANGE[2], melt)), 255)
    return im


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease_in(t): return t * t
def ease_out_q(t): return 1 - (1 - t) ** 2
def spring(t, freq=3.2, damp=5.0): return math.exp(-damp * t) * math.cos(2 * math.pi * freq * t)


# ---------- буквы ----------
TEXT = "Ready to work"
GAP_BOT = 26
BASE = 150
_m = ImageDraw.Draw(Image.new('RGB', (1, 1)))
text_w = _m.textlength(TEXT, font=f_word) / K
TX = (W - (text_w + GAP_BOT + BODY_W)) / 2

letters = []                       # (char, x, centre_x, top_y, word_index)
word = 0
for i, ch in enumerate(TEXT):
    if ch == ' ':
        word += 1
        continue
    x = TX + _m.textlength(TEXT[:i], font=f_word) / K
    w = _m.textlength(ch, font=f_word) / K
    bbox = _m.textbbox((0, 0), ch, font=f_word, anchor='ls')
    top = BASE + bbox[1] / K
    letters.append((ch, x, x + w / 2, top, word))
REST_X = TX + text_w + GAP_BOT + BODY_W / 2

# ---------- сценарий ----------
TEXT_IN = (0.2, 0.8)
FALL = (0.8, 1.25)
hops = []                          # (start, crouch, air, xa, ya, xb, yb, height)
land_on = {0: FALL[1]}             # индекс буквы → время приземления
t = FALL[1] + 0.22
for i in range(1, len(letters)):
    _, _, xa, ya, wa = letters[i - 1]
    _, _, xb, yb, wb = letters[i]
    gap = wb != wa
    crouch, air, hgt = (0.12, 0.40, 34) if gap else (0.07, 0.24, 16)
    hops.append((t, crouch, air, xa, ya, xb, yb, hgt))
    land_on[i] = t + crouch + air
    t += crouch + air + (0.14 if gap else 0.05)
t += 0.25
_, _, xl, yl, _ = letters[-1]
hops.append((t, 0.16, 0.50, xl, yl, REST_X, GROUND, 30))
SETTLE = t + 0.16 + 0.55
IDLE_HOP = SETTLE + 1.9
hops.append((IDLE_HOP, 0.12, 0.38, REST_X, GROUND, REST_X, GROUND, 22))
ZOOM = SETTLE + 3.6               # робот вырастает и заливает экран
ZOOM_LEN, HOLD, FADE = 0.9, 0.12, 0.5
END = ZOOM + ZOOM_LEN + HOLD + FADE
LANDS = [(FALL[1], letters[0][2])] + [(h[0] + h[1] + h[2], h[5]) for h in hops]


def character(t):
    if t < FALL[0]:
        return None
    x0, y0 = letters[0][2], letters[0][3]
    if t < FALL[1]:
        p = ease_in((t - FALL[0]) / (FALL[1] - FALL[0]))
        st = 1 + 0.35 * p
        return x0, lerp(-BODY_H - 10, y0, p), 1 / math.sqrt(st), st, 0, True, False

    x, y, last = x0, y0, FALL[1]
    for (ts, cr, air, xa, ya, xb, yb, hgt) in hops:
        if t < ts:
            break
        direction = 1 if xb > xa else 0
        if t < ts + cr:
            k = math.sin((t - ts) / cr * math.pi / 2)
            return xa, ya, 1 + 0.2 * k, 1 - 0.26 * k, direction, True, False
        if t < ts + cr + air:
            p = (t - ts - cr) / air
            xx = lerp(xa, xb, p)
            yy = lerp(ya, yb, p) - hgt * 4 * p * (1 - p)
            st = 1 + 0.2 * abs(1 - 2 * p)
            return xx, yy, 1 / math.sqrt(st), st, direction, True, False
        x, y, last = xb, yb, ts + cr + air

    dt = t - last
    if y < GROUND:                                   # стоит на букве — проседает вместе с ней
        y += max(0.0, spring(dt, 2.6, 6.0)) * 7
    s = spring(dt, 3.6, 7.0) * 0.26
    sy, sx = 1 - s, 1 + s * 0.8
    look, eyes, happy = 1, True, dt < 0.22
    if t > SETTLE:
        happy = dt < 0.45
        br = math.sin((t - SETTLE) * 2 * math.pi / 2.4) * 0.03
        sy *= 1 + br
        sx *= 1 - br * 0.6
        ph = (t - SETTLE) % 4.0
        look = -1 if ph < 1.8 else (0 if ph < 3.4 else 1)
        for bt in (SETTLE + 1.2, SETTLE + 3.0):
            if bt <= t < bt + 0.14:
                eyes = False
    return x, y, sx, sy, look, eyes, happy


def S(v): return int(round(v * K))


# ---------- индикаторы: Wi-Fi и батарея ----------
f_small = ImageFont.truetype(FONT, 15 * K)
f_small.set_variation_by_name('SemiBold')
U = 2                                   # «пиксель» иконок
BATTERY = 78                            # %
CHARGING = False


WIFI_MAP = [
    ".33333.",
    "3.....3",
    "..222..",
    ".2...2.",
    ".......",
    "...1...",
]
WIFI_PIX = [(x, y, int(c)) for y, row in enumerate(WIFI_MAP) for x, c in enumerate(row) if c != "."]


def wifi_bars(t):
    """0..3 — сколько полосок горит. В начале цикла идёт поиск сети."""
    if t < 1.6:
        return int(t * 6) % 4
    return 3


BAT_GREEN, BAT_ORANGE, BAT_RED = (48, 209, 88), (255, 159, 10), (255, 69, 58)


def battery_color(pct):
    """> 50% — зелёный, 21–50% — оранжевый, ≤ 20% — красный."""
    if pct > 50:
        return BAT_GREEN
    if pct > 20:
        return BAT_ORANGE
    return BAT_RED


def draw_status_icons(d, t, k, top=14):
    """k — яркость 0..1 (для появления и ухода)."""
    if k <= 0:
        return
    def c(rgb): return tuple(int(v * k) for v in rgb)
    on, off = c(WHITE), c(DIM)
    right = W - 16

    # батарея: корпус 13×7 U + носик
    bw, bh = 13 * U, 7 * U
    bx, by = right - bw - U, top
    d.rectangle([S(bx), S(by), S(bx + bw), S(by + bh)], outline=on, width=S(U))
    d.rectangle([S(bx + bw), S(by + 2 * U), S(bx + bw + U), S(by + bh - 2 * U)], fill=on)
    level = BATTERY / 100
    fill_col = c(battery_color(BATTERY))
    inner = bw - 4 * U
    fw = round(inner * level / U) * U
    if fw > 0:
        d.rectangle([S(bx + 2 * U), S(by + 2 * U), S(bx + 2 * U + fw), S(by + bh - 2 * U)], fill=fill_col)

    # процент слева от батареи
    d.text((S(bx - 6), S(by + bh / 2 + 0.5)), f"{BATTERY}%", font=f_small, fill=c(GRAY), anchor='rm')
    pct_w = d.textlength(f"{BATTERY}%", font=f_small) / K

    # Wi-Fi: пиксельный «веер» — точка и две дуги, горят по уровню сигнала
    lit = wifi_bars(t)
    gw = 7 * U
    wx = bx - 6 - pct_w - 10 - gw
    wy = by - U
    for (px, py, lvl) in WIFI_PIX:
        col = on if lvl <= lit else off
        d.rectangle([S(wx + px * U), S(wy + py * U), S(wx + px * U + U), S(wy + py * U + U)], fill=col)
    return wx                                        # левый край блока индикаторов


def draw_frame(t):
    im = Image.new('RGB', (W * K, H * K), (0, 0, 0))
    d = ImageDraw.Draw(im, 'RGBA')

    # земля
    if t >= ZOOM + ZOOM_LEN:                        # финал: оранжевый экран гаснет
        p = clamp((t - ZOOM - ZOOM_LEN - HOLD) / FADE)
        col = tuple(int(c * (1 - p) ** 1.5) for c in ORANGE)
        return Image.new('RGB', (W, H), col)
    zp = clamp((t - ZOOM) / ZOOM_LEN) if t >= ZOOM else 0.0
    gone = clamp(zp * 2.5)                          # надпись уходит при зуме

    # буквы
    fade = clamp((t - TEXT_IN[0]) / (TEXT_IN[1] - TEXT_IN[0]))
    for i, (ch, x, cx, top, wi) in enumerate(letters):
        tl = land_on[i]
        lit = clamp((t - tl) / 0.18) if t >= tl else 0.0
        dip = 0.0
        if t >= tl:
            dip = max(0.0, spring(t - tl, 2.6, 6.0)) * 7
        target = ORANGE if wi == 2 else WHITE
        col = tuple(int(lerp(a, b, lit)) for a, b in zip(DIM, target))
        k_ = fade * (1 - gone)                      # фон чёрный: прозрачность = затемнение
        col = tuple(int(c * k_) for c in col)
        d.text((S(x), S(BASE + dip)), ch, font=f_word, fill=col, anchor='ls')

    draw_status_icons(d, t, fade * (1 - gone))

    # пиксельная пыль при каждом приземлении
    for lt, lx in LANDS:
        dt = t - lt
        if 0 <= dt < 0.35:
            c = character(lt + 0.001)
            ly = c[1] if c else GROUND
            p = dt / 0.35
            for side in (-1, 1):
                for k in range(2):
                    sz = PX * (2 if k == 0 else 1)
                    px = lx + side * (BODY_W / 2 + 4 + p * (12 + k * 9))
                    py = ly - 4 - k * 4 - math.sin(p * math.pi) * (3 + k * 3)
                    px, py = round(px / PX) * PX, round(py / PX) * PX
                    d.rectangle([S(px), S(py), S(px + sz), S(py + sz)], fill=GRAY + (int(160 * (1 - p)),))

    c = character(t)
    if c is not None:
        x, y, sx, sy, look, eyes, happy = c
        lamp = (int(t * 1.6) % 2 == 0) if t > SETTLE else True
        if zp > 0:                                  # замах, затем рост к центру экрана
            lamp, look = True, 0
            if zp < 0.18:                           # приседает перед «прыжком в камеру»
                k = math.sin(zp / 0.18 * math.pi / 2)
                sx, sy = 1 + 0.2 * k, 1 - 0.25 * k
                happy = True
            else:
                q = (zp - 0.18) / 0.82
                g = 1 + 13 * q ** 2.2
                sx = sy = g
                happy = False
                cy_body = y - BODY_H / 2
                x = lerp(x, W / 2, ease_out_q(q))
                y = lerp(cy_body, H / 2 + BODY_H * 0.9 * min(g, 6) / 6 * 0, ease_out_q(q)) + BODY_H * g / 2
        melt = clamp((zp - 0.45) / 0.35) if zp > 0 else 0.0
        spr = sprite_image(look, eyes, lamp, happy, melt)
        bw, bh = max(PX, BODY_W * sx), max(PX, BODY_H * sy)
        big = spr.resize((S(bw), S(bh)), Image.NEAREST)
        im.paste(big, (S(x - bw / 2), S(y - bh)), big)
        if zp > 0.8:                                # добиваем края экрана
            q = ease_in((zp - 0.8) / 0.2)
            r = q * math.hypot(W, H) * 0.62
            cx_, cy_ = x, y - bh / 2
            d = ImageDraw.Draw(im, 'RGBA')
            d.ellipse([S(cx_ - r), S(cy_ - r), S(cx_ + r), S(cy_ + r)], fill=ORANGE + (255,))
    return im.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    frames = [draw_frame(i / FPS) for i in range(int(END * FPS))]
    pal = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    out = os.path.join(ROOT, 'docs', 'idle.gif')
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=int(1000 / FPS), loop=0, optimize=True, disposal=1)
    print(f'{len(frames)} кадров, {END:.1f} с → {out}')
