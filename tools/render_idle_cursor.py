#!/usr/bin/env python3
"""
Сцена ожидания «живой курсор»: курсор с глазами стоит на месте следующей буквы,
подпрыгивает вперёд, и за ним остаётся напечатанная буква.

    python tools/render_idle_cursor.py --theme claude   # → docs/claude_idle_cursor.gif
    python tools/render_idle_cursor.py --theme codex    # → docs/codex_idle_cursor.gif
"""
import argparse
import math
import os

from PIL import Image, ImageDraw

from anim_common import (W, H, K, FPS, DOCS, THEMES, font, clamp, lerp, ease_in, ease_out_q,
                         spring, S, dim, mix, draw_status_icons, melt_sprite, save_gif)

TEXT = "Ready to work"
SW, SH = 5, 12                                  # спрайт курсора в «пикселях»


class Scene:
    def __init__(self, theme_name):
        self.name = theme_name
        th = self.th = THEMES[theme_name]
        # шрифт подбирается так, чтобы строка влезла с полями
        size = 50
        while True:
            self.f_word = font(th['word_font'][0], size, th['word_font'][1])
            m = ImageDraw.Draw(Image.new('RGB', (1, 1)))
            self.m = m
            lead = m.textlength(th['prompt'] + " ", font=self.f_word) / K
            text_w = m.textlength(TEXT, font=self.f_word) / K
            self.cur_w = m.textlength("n", font=self.f_word) / K * 0.62
            line_w = lead + text_w + self.cur_w + 4
            if line_w <= W - 80 or size <= 30:
                break
            size -= 2
        self.f_small = font(th['small_font'][0], 14 if theme_name == 'codex' else 15, th['small_font'][1])
        self.cap = -m.textbbox((0, 0), "R", font=self.f_word, anchor='ls')[1] / K
        self.tx = (W - line_w) / 2
        self.base = 140
        self.text_x = self.tx + lead
        self.cur_h = self.cap + 6
        self.foot = self.base + 6
        self.body_col = th['accent'] if theme_name == 'claude' else th['text']
        self._timeline()

    # позиция знакоместа i: левый край + половина курсора
    def slot_x(self, i):
        return self.text_x + self.m.textlength(TEXT[:i], font=self.f_word) / K + self.cur_w / 2 + 2

    def _timeline(self):
        self.PROMPT_IN = (0.15, 0.45)
        self.APPEAR, self.WAKE, self.START = 0.45, 1.75, 2.2
        hops, t = [], self.START
        for i, ch in enumerate(TEXT):
            if ch == " ":
                continue
            space_next = i + 1 < len(TEXT) and TEXT[i + 1] == " "
            j = i + 2 if space_next else i + 1
            cr, air, hgt = (0.08, 0.30, 26) if space_next else (0.06, 0.16, 10)
            hops.append((t, cr, air, i, min(j, len(TEXT)), hgt, i))
            t += cr + air + (0.10 if space_next else 0.04)
        self.DONE = t
        self.LOOK_BACK = t + 0.5
        self.JOY, self.JOY_LEN = t + 1.5, 0.4
        hops.append((self.JOY, 0.1, self.JOY_LEN, len(TEXT), len(TEXT), 22, None))
        self.GAG = self.JOY + 0.1 + self.JOY_LEN + 0.45
        self.ZOOM = self.GAG + 1.3
        self.ZOOM_LEN, self.HOLD, self.FADE = 0.9, 0.12, 0.5
        self.END = self.ZOOM + self.ZOOM_LEN + self.HOLD + self.FADE
        self.hops = hops
        self.typed_at = {h[6]: h[0] + h[1] for h in hops if h[6] is not None}

    def sprite(self, look, eyes, happy, melt, body):
        im = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
        if body:
            for y in range(SH):
                for x in range(SW):
                    im.putpixel((x, y), self.body_col + (255,))
        if eyes is not None:
            eye_col = (self.th['eye'] if body else self.th['text']) + (255,)
            dx = int(round(look))
            for ex in (1, 3):
                x = min(SW - 1, max(0, ex + dx))
                pts = [(x, 4)] if (happy or not eyes) else [(x, 3), (x, 4)]
                for p in pts:
                    im.putpixel(p, eye_col)
        return melt_sprite(im, self.th['accent'], melt)

    def cursor(self, t):
        if t < self.APPEAR:
            return None
        x, y = self.slot_x(0), self.foot
        if t < self.WAKE:                           # обычный мигающий курсор
            return x, y, 1, 1, 0, None, False, int((t - self.APPEAR) * 2) % 2 == 0
        if t < self.START:                          # просыпается
            dt = t - self.WAKE
            s = spring(dt, 3.0, 5.0) * 0.18
            return x, y, 1 - s * 0.7, 1 + s, (1 if dt > 0.2 else 0), not (0.25 <= dt < 0.33), False, True
        last, slot = self.START, 0
        for (ts, cr, air, a, b, hgt, _) in self.hops:
            if t < ts:
                break
            if t < ts + cr:
                k = math.sin((t - ts) / cr * math.pi / 2)
                return self.slot_x(a), self.foot, 1 + 0.18 * k, 1 - 0.22 * k, 1, True, False, True
            if t < ts + cr + air:
                p = (t - ts - cr) / air
                st = 1 + 0.2 * abs(1 - 2 * p)
                return (lerp(self.slot_x(a), self.slot_x(b), p), self.foot - hgt * 4 * p * (1 - p),
                        1 / math.sqrt(st), st, 1 if b > a else 0, True, False, True)
            last, slot = ts + cr + air, b
        dt = t - last
        s = spring(dt, 3.4, 6.0) * 0.22
        sy, sx = 1 - s, 1 + s * 0.8
        look, happy, body = 1, False, True
        if t >= self.DONE:
            happy = dt < 0.35 or (t >= self.JOY and dt < 0.5)
            if self.LOOK_BACK <= t < self.JOY:
                look = -1
            if t >= self.GAG:                        # тело гаснет, глаза висят в воздухе
                gt = t - self.GAG
                body = not (0.15 <= gt < 0.45 or 0.75 <= gt < 1.05)
                look = 0 if gt < 0.6 else 1
            sy *= 1 + math.sin((t - self.DONE) * 2 * math.pi / 1.8) * 0.035
        return self.slot_x(slot), self.foot, sx, sy, look, True, happy, body

    def frame(self, t):
        th = self.th
        if t >= self.ZOOM + self.ZOOM_LEN:
            p = clamp((t - self.ZOOM - self.ZOOM_LEN - self.HOLD) / self.FADE)
            return Image.new('RGB', (W, H), dim(th['accent'], (1 - p) ** 1.5))
        im = Image.new('RGB', (W * K, H * K), (0, 0, 0))
        d = ImageDraw.Draw(im, 'RGBA')
        zp = clamp((t - self.ZOOM) / self.ZOOM_LEN) if t >= self.ZOOM else 0.0
        gone = clamp(zp * 2.5)
        fade = clamp((t - self.PROMPT_IN[0]) / (self.PROMPT_IN[1] - self.PROMPT_IN[0])) * (1 - gone)

        d.text((S(self.tx), S(self.base)), th['prompt'], font=self.f_word, fill=dim(th['accent'], fade), anchor='ls')

        for i, ch in enumerate(TEXT):
            if ch == " " or i not in self.typed_at or t < self.typed_at[i]:
                continue
            dt = t - self.typed_at[i]
            target = th['accent'] if TEXT[:i].count(" ") == 2 else th['text']
            col = dim(mix(target, th['flash'], (1 - clamp(dt / 0.35)) * 0.85), 1 - gone)
            sy = lerp(0.25, 1.0, ease_out_q(clamp(dt / 0.14)))
            cw = self.m.textlength(ch, font=self.f_word)
            layer = Image.new('RGBA', (int(cw) + 8, S(80)), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((0, S(64)), ch, font=self.f_word, fill=col + (255,), anchor='ls')
            nh = max(1, int(layer.height * sy))
            layer = layer.resize((layer.width, nh), Image.LANCZOS)
            x = self.text_x + self.m.textlength(TEXT[:i], font=self.f_word) / K
            im.paste(layer, (S(x), S(self.base) - int(S(64) * sy)), layer)
        d = ImageDraw.Draw(im, 'RGBA')

        draw_status_icons(d, t, fade, th, self.f_small)

        c = self.cursor(t)
        if c is None:
            return im.resize((W, H), Image.LANCZOS)
        x, y, sx, sy, look, eyes, happy, body = c
        melt = 0.0
        if zp > 0:
            look, body, eyes = 0, True, True
            if zp < 0.18:
                k = math.sin(zp / 0.18 * math.pi / 2)
                sx, sy, happy = 1 + 0.25 * k, 1 - 0.3 * k, True
            else:
                q = (zp - 0.18) / 0.82
                g = 1 + 16 * q ** 2.2
                sx, sy, happy = g * 1.35, g, False
                x = lerp(x, W / 2, ease_out_q(q))
                y = lerp(y - self.cur_h / 2, H / 2, ease_out_q(q)) + self.cur_h * sy / 2
            melt = clamp((zp - 0.45) / 0.35)
        spr = self.sprite(look, eyes, happy, melt, body)
        bw, bh = self.cur_w * sx, self.cur_h * sy
        big = spr.resize((max(1, S(bw)), max(1, S(bh))), Image.NEAREST)
        if zp == 0 and fade < 1:
            big.putalpha(big.split()[3].point(lambda v: int(v * fade)))
        im.paste(big, (S(x - bw / 2), S(y - bh)), big)
        if zp > 0.8:
            q = ease_in((zp - 0.8) / 0.2)
            r = q * math.hypot(W, H) * 0.62
            d = ImageDraw.Draw(im, 'RGBA')
            d.ellipse([S(x - r), S(y - bh / 2 - r), S(x + r), S(y - bh / 2 + r)], fill=th['accent'] + (255,))
        return im.resize((W, H), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', choices=sorted(THEMES), default='claude')
    ap.add_argument('--out')
    a = ap.parse_args()
    sc = Scene(a.theme)
    frames = [sc.frame(i / FPS) for i in range(int(sc.END * FPS))]
    out = a.out or os.path.join(DOCS, f'{a.theme}_idle_cursor.gif')
    save_gif(frames, out)
    print(f'{len(frames)} кадров, {sc.END:.1f} с → {out}')


if __name__ == '__main__':
    main()
