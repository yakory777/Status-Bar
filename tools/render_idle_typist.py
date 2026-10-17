#!/usr/bin/env python3
"""
Сцена ожидания Codex «машинистка»: слайм сидит за пиксельной клавиатурой
и печатает «Ready to work» в строке терминала — 536×240.

    python tools/render_idle_typist.py         # → docs/codex_idle_typist.gif
"""
import math
import os
from PIL import Image, ImageDraw

import slime_common as base
from slime_common import (W, H, K, FPS, PX, GREEN, GREEN_LT, WHITE,
                        f_word, CH, CAP, BODY_W, BODY_H, sprite_image, draw_status_icons,
                        clamp, lerp, ease_in, ease_out_q, spring, S)

KEY_BG = (40, 41, 50)
KEY = (64, 65, 79)
KEY_EDGE = (30, 31, 38)

# ---------- строка терминала ----------
TEXT = "Ready to work"
line_w = CH * (2 + len(TEXT) + 1)
TX = (W - line_w) / 2
BASE = 92
TEXT_X = TX + CH * 2

# ---------- клавиатура ----------
KW, KH, KG = 12, 8, 3                      # клавиша и зазор, px
SC = 1.5                                   # слайм крупнее, чем в сцене с прыжками
BW, BH = BODY_W * SC, BODY_H * SC
ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL") + ["ENTER"],
    list("ZXC") + ["SPACE"] + list("NM"),
]
SPACE_SLOTS = 5
board_w = 10 * KW + 11 * KG + 8
board_h = 3 * KH + 4 * KG
BX = (W - board_w) / 2
BY = 178
keys = {}                                  # подпись → (x, y, w, h)
for r, row in enumerate(ROWS):
    x = BX + KG + r * 4
    y = BY + KG + r * (KH + KG)
    for lab in row:
        w = KW * SPACE_SLOTS + KG * (SPACE_SLOTS - 1) if lab == "SPACE" else KW
        keys[lab] = (x, y, w, KH)
        x += w + KG


def key_for(ch):
    return "SPACE" if ch == " " else ch.upper()


# ---------- слайм за клавиатурой ----------
CX = W / 2
SEAT_Y = BY + 14                           # низ тела прячется за клавиатурой
SHOULDER_K = 0.62                          # плечи — на этой доле высоты тела
HOME_L, HOME_R = "F", "J"

# ---------- сценарий ----------
FADE_IN = (0.1, 0.5)
FALL = (0.45, 0.85)
strokes = []                               # (время, символ, индекс в тексте)
t = 1.25
rhythm = [0.0, 0.03, -0.02, 0.04, 0.0, -0.03, 0.02, 0.05, -0.01, 0.0, 0.03, -0.02, 0.01]
for i, ch in enumerate(TEXT):
    strokes.append((t, ch, i))
    t += (0.26 if ch == " " else 0.17) + rhythm[i % len(rhythm)]
LAST_KEY = strokes[-1][0]
ENTER_UP = LAST_KEY + 0.65                 # лапки вверх — замах
ENTER_HIT = ENTER_UP + 0.22                # удар по Enter
JOY = ENTER_HIT + 0.55                     # прыжок радости
JOY_LEN = 0.42
SETTLE = JOY + JOY_LEN
ZOOM = SETTLE + 1.9
ZOOM_LEN, HOLD, FADE = 0.9, 0.12, 0.5
END = ZOOM + ZOOM_LEN + HOLD + FADE

REACH, PRESS, BACK = 0.06, 0.05, 0.08


def key_top(lab):
    x, y, w, h = keys[lab]
    return x + w / 2, y + 2


def arm_for(lab):
    """Какой лапкой жать: левая половина клавиатуры — левой."""
    kx = keys[lab][0] + keys[lab][2] / 2
    return 0 if kx < CX else 1


def arm_tips(t):
    """Положение кончиков лапок и какие клавиши сейчас нажаты."""
    home = [key_top(HOME_L), key_top(HOME_R)]
    tips = list(home)
    pressed = {}
    for (ts, ch, _) in strokes:
        lab = key_for(ch)
        side = 1 if lab == "SPACE" and False else arm_for(lab)
        if lab == "SPACE":
            side = 1                       # пробел — правой, как многие печатают
        dt = t - ts
        tgt = key_top(lab)
        if -REACH <= dt < 0:
            p = ease_out_q((dt + REACH) / REACH)
            tips[side] = (lerp(home[side][0], tgt[0], p), lerp(home[side][1], tgt[1] - 6, p))
        elif 0 <= dt < PRESS:
            tips[side] = (tgt[0], tgt[1] + 2)
            pressed[lab] = 1.0
        elif PRESS <= dt < PRESS + BACK:
            p = ease_out_q((dt - PRESS) / BACK)
            tips[side] = (lerp(tgt[0], home[side][0], p), lerp(tgt[1], home[side][1], p))
    # Enter: правая лапка замахивается и бьёт, левая вскинута
    ex, ey = key_top("ENTER")
    up_y = SEAT_Y - BH - 8
    if ENTER_UP <= t < ENTER_HIT:
        p = ease_out_q((t - ENTER_UP) / (ENTER_HIT - ENTER_UP))
        tips = [(lerp(home[0][0], CX - BW / 2 - 10, p), lerp(home[0][1], up_y + 6, p)),
                (lerp(home[1][0], CX + BW / 2 + 12, p), lerp(home[1][1], up_y, p))]
    elif ENTER_HIT <= t < ENTER_HIT + 0.16:
        tips = [(CX - BW / 2 - 10, up_y + 6), (ex, ey + 2)]
        pressed["ENTER"] = 1.0
    elif ENTER_HIT + 0.16 <= t < ENTER_HIT + 0.3:
        p = ease_out_q((t - ENTER_HIT - 0.16) / 0.14)
        tips = [(lerp(CX - BW / 2 - 10, home[0][0], p), lerp(up_y + 6, home[0][1], p)),
                (lerp(ex, home[1][0], p), lerp(ey, home[1][1], p))]
    elif JOY <= t < JOY + JOY_LEN:         # лапки вверх от радости
        lift = 20 * 4 * ((t - JOY) / JOY_LEN) * (1 - (t - JOY) / JOY_LEN)
        tips = [(CX - BW / 2 - 8, SEAT_Y - BH - 6 - lift), (CX + BW / 2 + 8, SEAT_Y - BH - 6 - lift)]
    return tips, pressed


def key_glow(lab, t):
    """Подсветка клавиши после нажатия, 0..1."""
    best = 0.0
    times = [ts for (ts, ch, _) in strokes if key_for(ch) == lab]
    if lab == "ENTER":
        times = [ENTER_HIT]
    for ts in times:
        dt = t - ts
        if 0 <= dt < 0.35:
            best = max(best, 1 - dt / 0.35)
    return best


def body(t):
    """x, низ тела y, sx, sy, взгляд (dx, dy), глаза открыты, довольный."""
    if t < FALL[0]:
        return None
    if t < FALL[1]:
        p = ease_in((t - FALL[0]) / (FALL[1] - FALL[0]))
        st = 1 + 0.45 * p
        return CX, lerp(-10, SEAT_Y, p), 1 / math.sqrt(st), st, (0, 0), True, False
    x, y = CX, SEAT_Y
    dt0 = t - FALL[1]
    s = spring(dt0, 2.8, 4.2) * 0.38
    sx, sy = 1 + s * 0.9, 1 - s
    look, eyes, happy = (0, 0), True, False
    # каждое нажатие — кивок телом и наклон к лапке
    for (ts, ch, _) in strokes:
        dt = t - ts
        if 0 <= dt < 0.18:
            k = math.sin(dt / 0.18 * math.pi)
            side = 1 if key_for(ch) == "SPACE" else arm_for(key_for(ch))
            y += 2 * k
            x += (2 if side else -2) * k
            sy *= 1 - 0.05 * k
            sx *= 1 + 0.04 * k
    if 1.0 < t < ENTER_UP:
        look = (0, -1)                     # смотрит на экран, пока печатает
    if ENTER_UP <= t < ENTER_HIT:
        k = ease_out_q((t - ENTER_UP) / (ENTER_HIT - ENTER_UP))
        sy *= 1 + 0.12 * k
        sx *= 1 - 0.08 * k
        look = (0, -1)
    if ENTER_HIT <= t < JOY:
        s = spring(t - ENTER_HIT, 3.0, 5.0) * 0.3
        sy, sx = 1 - s, 1 + s * 0.9
        happy = True
    if JOY <= t < JOY + JOY_LEN:
        p = (t - JOY) / JOY_LEN
        y -= 20 * 4 * p * (1 - p)
        st = 1 + 0.25 * abs(1 - 2 * p)
        sx, sy = 1 / math.sqrt(st), st
        happy = True
    if t >= SETTLE:
        dt = t - SETTLE
        s = spring(dt, 2.8, 4.2) * 0.3
        br = math.sin(dt * 2 * math.pi / 2.0) * 0.045
        sy, sx = (1 - s) * (1 + br), (1 + s * 0.9) * (1 - br * 0.7)
        happy = dt < 0.4
        ph = dt % 3.0
        look = (0, -1) if ph < 1.0 else ((1, 0) if ph < 1.8 else (0, 0))
        if 1.1 <= dt < 1.24:
            eyes = False
    return x, y, sx, sy, look, eyes, happy


def sprite_look(look, eyes, happy, melt):
    """Взгляд вверх: глаза на пиксель выше."""
    spr = sprite_image(look[0], eyes, happy, melt)
    if look[1] < 0 and not happy:
        shifted = Image.new('RGBA', spr.size, (0, 0, 0, 0))
        shifted.paste(spr, (0, 0))
        px = spr.load()
        out = shifted.load()
        for x in range(spr.width):
            for y in (4, 5, 6):
                out[x, y] = px[x, y]
        eye = base.EYE + (255,)
        body_col = GREEN + (255,)
        for x in range(spr.width):
            if px[x, 6] == eye:
                out[x, 6] = body_col
                out[x, 4] = eye
        return shifted
    return spr


def draw_arm(d, shoulder, tip, k):
    """Пиксельная лапка: квадратики вдоль отрезка с шагом в полпикселя."""
    (x0, y0), (x1, y1) = shoulder, tip
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / (PX / 2)))
    col = tuple(int(c * k) for c in GREEN)
    for i in range(n + 1):
        p = i / n
        x = round(lerp(x0, x1, p) / (PX / 2)) * (PX / 2)
        y = round(lerp(y0, y1, p) / (PX / 2)) * (PX / 2)
        r = PX * 0.75
        d.rectangle([S(x - r), S(y - r), S(x + r), S(y + r)], fill=col)


def typed_count(t):
    return sum(1 for (ts, _, _) in strokes if t >= ts)


def draw_frame(t):
    if t >= ZOOM + ZOOM_LEN:
        p = clamp((t - ZOOM - ZOOM_LEN - HOLD) / FADE)
        return Image.new('RGB', (W, H), tuple(int(c * (1 - p) ** 1.5) for c in GREEN))
    im = Image.new('RGB', (W * K, H * K), (0, 0, 0))
    d = ImageDraw.Draw(im, 'RGBA')
    zp = clamp((t - ZOOM) / ZOOM_LEN) if t >= ZOOM else 0.0
    gone = clamp(zp * 2.5)
    fade = clamp((t - FADE_IN[0]) / (FADE_IN[1] - FADE_IN[0])) * (1 - gone)

    def dim(rgb, k): return tuple(int(v * k) for v in rgb)

    # ---- строка терминала ----
    d.text((S(TX), S(BASE)), ">", font=f_word, fill=dim(GREEN, fade), anchor='ls')
    enter_flash = clamp(1 - (t - ENTER_HIT) / 0.5) if t >= ENTER_HIT else 0.0
    for (ts, ch, idx) in strokes:
        if t < ts or ch == " ":
            continue
        word = TEXT[:idx].count(" ")
        target = GREEN if word == 2 else WHITE
        flash = max(1 - clamp((t - ts) / 0.3), enter_flash)
        col = tuple(int(lerp(a, b, flash * 0.8)) for a, b in zip(target, GREEN_LT))
        col = dim(col, 1 - gone)
        sy = lerp(0.35, 1.0, ease_out_q(clamp((t - ts) / 0.12)))
        layer = Image.new('RGBA', (S(CH) + 8, S(60)), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((0, S(50)), ch, font=f_word, fill=col + (255,), anchor='ls')
        nh = max(1, int(layer.height * sy))
        layer = layer.resize((layer.width, nh), Image.LANCZOS)
        im.paste(layer, (S(TEXT_X + CH * idx), S(BASE) - int(S(50) * sy)), layer)
    d = ImageDraw.Draw(im, 'RGBA')

    n = typed_count(t)
    cur_x = TEXT_X + CH * n
    typing = strokes[0][0] - 0.3 <= t < LAST_KEY + 0.25
    if fade > 0 and (typing or int(t * 2) % 2 == 0):
        d.rectangle([S(cur_x + 2), S(BASE - CAP), S(cur_x + CH * 0.62), S(BASE + 2)], fill=dim(WHITE, fade * 0.85))

    draw_status_icons(d, t, fade)

    # ---- слайм (до клавиатуры: клавиатура закрывает низ тела) ----
    b = body(t)
    tips, pressed = arm_tips(t)
    if b is not None and zp == 0:
        x, y, sx, sy, look, eyes, happy = b
        bw, bh = BW * sx, BH * sy
        spr = sprite_look(look, eyes, happy, 0.0)
        big = spr.resize((S(bw), S(bh)), Image.NEAREST)
        im.paste(big, (S(x - bw / 2), S(y - bh)), big)
        d = ImageDraw.Draw(im, 'RGBA')

    # ---- клавиатура ----
    if fade > 0:
        d.rounded_rectangle([S(BX), S(BY), S(BX + board_w), S(BY + board_h)], radius=S(4), fill=dim(KEY_BG, fade))
        for lab, (kx, ky, kw, kh) in keys.items():
            down = 2 if lab in pressed else 0
            glow = key_glow(lab, t)
            base_col = GREEN if lab == "ENTER" else KEY
            col = tuple(int(lerp(a, b_, glow)) for a, b_ in zip(base_col, GREEN_LT))
            d.rectangle([S(kx), S(ky + 2), S(kx + kw), S(ky + kh + 2)], fill=dim(KEY_EDGE, fade))
            d.rectangle([S(kx), S(ky + down), S(kx + kw), S(ky + kh - 2 + down)], fill=dim(col, fade))

    # ---- лапки поверх клавиатуры ----
    if b is not None and zp == 0 and t >= FALL[1]:
        x, y, sx, sy = b[0], b[1], b[2], b[3]
        bh = BH * sy
        top = y - bh
        for side, tip in enumerate(tips):
            sxo = (-1 if side == 0 else 1) * (BW * sx / 2 - 8)
            draw_arm(d, (x + sxo, top + bh * SHOULDER_K), tip, 1.0)

    # ---- финал: прыжок в камеру и растворение в зелёном ----
    if zp > 0 and b is not None:
        x, y = b[0], b[1]
        if zp < 0.18:
            k = math.sin(zp / 0.18 * math.pi / 2)
            sx, sy, happy = 1 + 0.3 * k, 1 - 0.34 * k, True
        else:
            q = (zp - 0.18) / 0.82
            g = 1 + 10 * q ** 2.2
            sx = sy = g
            happy = False
            x = lerp(x, W / 2, ease_out_q(q))
            y = lerp(y - BH / 2, H / 2, ease_out_q(q)) + BH * g / 2
        melt = clamp((zp - 0.45) / 0.35)
        spr = sprite_image(0, True, happy, melt)
        bw, bh = BW * sx, BH * sy
        big = spr.resize((S(bw), S(bh)), Image.NEAREST)
        im.paste(big, (S(x - bw / 2), S(y - bh)), big)
        if zp > 0.8:
            q = ease_in((zp - 0.8) / 0.2)
            r = q * math.hypot(W, H) * 0.62
            d = ImageDraw.Draw(im, 'RGBA')
            d.ellipse([S(x - r), S(y - bh / 2 - r), S(x + r), S(y - bh / 2 + r)], fill=GREEN + (255,))
    return im.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    frames = [draw_frame(i / FPS) for i in range(int(END * FPS))]
    pal = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    out = os.path.join(base.ROOT_DOCS, 'codex_idle_typist.gif')
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=int(1000 / FPS), loop=0, optimize=True, disposal=1)
    print(len(frames), 'frames', round(END, 1), 's')
