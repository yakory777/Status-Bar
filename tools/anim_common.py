"""Общее для рендеров превью: экран, кривые, темы Claude и Codex, индикаторы Wi-Fi и батареи."""
import math
import os

from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(HERE, 'fonts')
DOCS = os.path.join(ROOT, 'docs')

W, H = 536, 240            # разрешение дисплея
K = 2                      # суперсэмплинг для гладких краёв
FPS = 30


def font(name, size, variation=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), int(size * K))
    if variation:
        f.set_variation_by_name(variation)
    return f


# ---------- кривые ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease_in(t): return t * t
def ease_out_q(t): return 1 - (1 - t) ** 2
def spring(t, freq=3.2, damp=5.0): return math.exp(-damp * t) * math.cos(2 * math.pi * freq * t)
def S(v): return int(round(v * K))
def dim(rgb, k): return tuple(int(v * k) for v in rgb)
def mix(a, b, t): return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


# ---------- темы ----------
THEMES = {
    'claude': dict(
        accent=(217, 119, 87),          # оранжевый Claude
        accent_dk=(160, 78, 52),
        flash=(255, 196, 160),
        eye=(38, 20, 14),
        text=(250, 249, 245),
        gray=(0x8E, 0x8E, 0x93),
        dim=(52, 50, 48),
        word_font=('Lora-Variable.ttf', 'Bold'),
        small_font=('Lora-Variable.ttf', 'SemiBold'),
        prompt='>',
    ),
    'codex': dict(
        accent=(16, 163, 127),          # зелёный ChatGPT #10A37F
        accent_dk=(9, 108, 84),
        flash=(120, 230, 196),
        eye=(10, 12, 14),
        text=(236, 236, 241),
        gray=(142, 142, 160),
        dim=(52, 53, 65),
        word_font=('DejaVuSansMono-Bold.ttf', None),
        small_font=('DejaVuSansMono.ttf', None),
        prompt='>',
    ),
}


# ---------- индикаторы ----------
U = 2                                   # «пиксель» иконок
WIFI_MAP = [".33333.", "3.....3", "..222..", ".2...2.", ".......", "...1..."]
WIFI_PIX = [(x, y, int(c)) for y, row in enumerate(WIFI_MAP) for x, c in enumerate(row) if c != "."]
BAT_GREEN, BAT_ORANGE, BAT_RED = (48, 209, 88), (255, 159, 10), (255, 69, 58)


def battery_color(pct):
    """> 50% — зелёный, 21–50% — оранжевый, ≤ 20% — красный."""
    if pct > 50:
        return BAT_GREEN
    if pct > 20:
        return BAT_ORANGE
    return BAT_RED


def wifi_level(t):
    """0..3. Первые 1,6 с цикла — поиск сети."""
    return int(t * 6) % 4 if t < 1.6 else 3


def draw_status_icons(d, t, k, theme, small_font, battery=78, top=14):
    """Wi-Fi и батарея в правом верхнем углу. k — яркость 0..1. Возвращает левый край блока."""
    if k <= 0:
        return None
    on, off = dim(theme['text'], k), dim(theme['dim'], k)
    right = W - 16
    bw, bh = 13 * U, 7 * U
    bx, by = right - bw - U, top
    d.rectangle([S(bx), S(by), S(bx + bw), S(by + bh)], outline=on, width=S(U))
    d.rectangle([S(bx + bw), S(by + 2 * U), S(bx + bw + U), S(by + bh - 2 * U)], fill=on)
    fw = round((bw - 4 * U) * battery / 100 / U) * U
    if fw > 0:
        d.rectangle([S(bx + 2 * U), S(by + 2 * U), S(bx + 2 * U + fw), S(by + bh - 2 * U)],
                    fill=dim(battery_color(battery), k))
    d.text((S(bx - 6), S(by + bh / 2 + 0.5)), f"{battery}%", font=small_font, fill=dim(theme['gray'], k), anchor='rm')
    pct_w = d.textlength(f"{battery}%", font=small_font) / K
    lit = wifi_level(t)
    wx, wy = bx - 6 - pct_w - 10 - 7 * U, by - U
    for (px, py, lvl) in WIFI_PIX:
        d.rectangle([S(wx + px * U), S(wy + py * U), S(wx + px * U + U), S(wy + py * U + U)],
                    fill=on if lvl <= lit else off)
    return wx


def melt_sprite(im, color, amount):
    """Перекрашивает непрозрачные пиксели спрайта в цвет темы (финальный зум)."""
    if amount <= 0:
        return im
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = mix((r, g, b), color, amount) + (255,)
    return im


def save_gif(frames, path):
    pal = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=int(1000 / FPS),
                loop=0, optimize=True, disposal=1)
