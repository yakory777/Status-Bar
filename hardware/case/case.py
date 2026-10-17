#!/usr/bin/env python3
"""
Корпус для LilyGO T-Display-S3 AMOLED (1,91″): лоток, рамка экрана и подставка-клин.

    python hardware/case/case.py            # → hardware/case/*.stl и preview.png

Все размеры — в PARAMS ниже, в миллиметрах. Перед печатью сверьте их со своей платой:
размеры взяты из характеристик (60 × 25,5 × 10 мм) и фотографий, а не с чертежа.

Как устроено: детали собираются из прямоугольных блоков (тело) и вырезов,
затем на неравномерной решётке по всем границам блоков строится замкнутая
поверхность. Поэтому STL получается герметичным (каждое ребро — ровно у двух
треугольников), без внутренних граней, и любой слайсер печатает его как есть.
"""
import math
import os
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

PARAMS = dict(
    board_l=60.0,          # длина платы (вдоль экрана)
    board_w=25.5,          # ширина платы
    board_t=10.0,          # толщина платы с экраном и деталями
    clear=0.35,            # зазор вокруг платы
    wall=2.0,              # толщина стенок
    floor=1.6,             # толщина дна
    battery_h=6.0,         # место под аккумулятор под платой (0 — без аккумулятора)
    ledge=1.6,             # ширина полочек, на которых лежит плата
    # USB-C на коротком торце (со стороны x = 0), по центру ширины
    usb_w=9.6, usb_h=4.0, usb_z=2.6,          # z — от низа платы до центра разъёма
    # прорезь к боковым кнопкам BOOT/RST на длинной стороне у USB
    btn_from=4.0, btn_len=16.0, btn_h=3.2, btn_z=3.0,
    # окно экрана в рамке (активная область 1,91″ ≈ 44 × 20 мм) и его смещение от центра платы
    win_l=45.0, win_w=21.0, win_dx=1.5, win_dy=0.0,
    bezel_t=1.6,           # толщина рамки
    lip_h=2.2, lip_t=1.2,  # «юбка» рамки, которая входит внутрь лотка
    lip_gap=0.2,           # зазор юбки для посадки с натягом
    stand_angle=22.0,      # наклон экрана на подставке, градусы
    stand_depth=34.0,      # глубина подставки
    stand_lip=4.0,         # бортик спереди, в который упирается корпус
)


# ---------------- прямоугольная CSG ----------------

class Part:
    """Тело = объединение блоков минус объединение вырезов. Блок — (x0, y0, z0, x1, y1, z1)."""

    def __init__(self, name):
        self.name = name
        self.solids, self.holes = [], []

    def add(self, *b):
        self.solids.append(tuple(map(float, b)))
        return self

    def cut(self, *b):
        self.holes.append(tuple(map(float, b)))
        return self

    def mesh(self):
        """Треугольники поверхности: массив (N, 3, 3)."""
        boxes = self.solids + self.holes
        xs = sorted({b[0] for b in boxes} | {b[3] for b in boxes})
        ys = sorted({b[1] for b in boxes} | {b[4] for b in boxes})
        zs = sorted({b[2] for b in boxes} | {b[5] for b in boxes})
        cx = (np.array(xs[:-1]) + np.array(xs[1:])) / 2
        cy = (np.array(ys[:-1]) + np.array(ys[1:])) / 2
        cz = (np.array(zs[:-1]) + np.array(zs[1:])) / 2
        X, Y, Z = np.meshgrid(cx, cy, cz, indexing="ij")

        def inside(b):
            return (X > b[0]) & (X < b[3]) & (Y > b[1]) & (Y < b[4]) & (Z > b[2]) & (Z < b[5])

        fill = np.zeros(X.shape, bool)
        for b in self.solids:
            fill |= inside(b)
        for b in self.holes:
            fill &= ~inside(b)

        pad = np.pad(fill, 1)                       # снаружи — пусто
        tris = []
        xs, ys, zs = np.array(xs), np.array(ys), np.array(zs)
        for axis in range(3):
            a = np.take(pad, range(0, pad.shape[axis] - 1), axis=axis)
            b = np.take(pad, range(1, pad.shape[axis]), axis=axis)
            # грань там, где заполненность меняется; ориентация — наружу от заполненной ячейки
            for sign, mask in ((+1, a & ~b), (-1, ~a & b)):
                idx = np.argwhere(mask)
                for i, j, k in idx:
                    tris.extend(_face(axis, sign, (i, j, k), xs, ys, zs))
        return np.array(tris)


def _face(axis, sign, ijk, xs, ys, zs):
    """Квадрат на границе ячеек (индексы в «паддинговой» сетке) → два треугольника."""
    i, j, k = ijk
    # индексы ячейки без паддинга; плоскость — между ячейкой и соседом по оси
    g = [i - 1, j - 1, k - 1]
    coords = [xs, ys, zs]
    plane = coords[axis][g[axis] + 1]
    u, v = [d for d in range(3) if d != axis]
    u0, u1 = coords[u][g[u]], coords[u][g[u] + 1]
    v0, v1 = coords[v][g[v]], coords[v][g[v] + 1]

    def P(uu, vv):
        p = [0.0, 0.0, 0.0]
        p[axis], p[u], p[v] = plane, uu, vv
        return p

    q = [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)]
    # нормаль квадрата (u × v) смотрит по +axis для axis = x, z и по −axis для y — поправляем
    normal_positive = (axis != 1)
    if normal_positive != (sign > 0):
        q = q[::-1]
    return [(q[0], q[1], q[2]), (q[0], q[2], q[3])]


def prism(profile_yz, x0, x1):
    """Призма: выпуклый профиль в плоскости YZ (против часовой), вытянутый по X."""
    tris = []
    n = len(profile_yz)
    a = [(x0, y, z) for y, z in profile_yz]
    b = [(x1, y, z) for y, z in profile_yz]
    for i in range(1, n - 1):
        tris.append((a[0], a[i + 1], a[i]))        # торец x0 — наружу по −x
        tris.append((b[0], b[i], b[i + 1]))        # торец x1 — наружу по +x
    for i in range(n):
        j = (i + 1) % n
        tris.append((a[i], a[j], b[j]))
        tris.append((a[i], b[j], b[i]))
    return np.array(tris)


# ---------------- детали ----------------

def build(p):
    il = p["board_l"] + 2 * p["clear"]              # внутренняя полость
    iw = p["board_w"] + 2 * p["clear"]
    ol, ow = il + 2 * p["wall"], iw + 2 * p["wall"]
    board_z0 = p["floor"] + p["battery_h"]          # где лежит низ платы
    oh = board_z0 + p["board_t"]                    # лоток по верх платы
    w = p["wall"]

    tray = Part("tray")
    tray.add(0, 0, 0, ol, ow, oh)
    tray.cut(w, w, p["floor"], w + il, w + iw, oh + 1)                    # полость
    if p["battery_h"] > 0:                                                 # полочки под плату
        tray.add(w, w, p["floor"], w + il, w + p["ledge"], board_z0)
        tray.add(w, w + iw - p["ledge"], p["floor"], w + il, w + iw, board_z0)
    uz = board_z0 + p["usb_z"]                                             # USB-C на торце x = 0
    tray.cut(-1, ow / 2 - p["usb_w"] / 2, uz - p["usb_h"] / 2, w + 0.5, ow / 2 + p["usb_w"] / 2, uz + p["usb_h"] / 2)
    bz = board_z0 + p["btn_z"]                                             # прорезь к кнопкам, сторона y = 0
    tray.cut(w + p["btn_from"], -1, bz - p["btn_h"] / 2, w + p["btn_from"] + p["btn_len"], w + 0.5, bz + p["btn_h"] / 2)

    bezel = Part("bezel")                          # печатается лицом вниз
    t = p["bezel_t"]
    bezel.add(0, 0, 0, ol, ow, t)
    cxw, cyw = ol / 2 + p["win_dx"], ow / 2 + p["win_dy"]
    bezel.cut(cxw - p["win_l"] / 2, cyw - p["win_w"] / 2, -1, cxw + p["win_l"] / 2, cyw + p["win_w"] / 2, t + 1)
    g, lt = p["lip_gap"], p["lip_t"]               # юбка по внутреннему периметру лотка
    x0, y0, x1, y1 = w + g, w + g, w + il - g, w + iw - g
    lh = t + p["lip_h"]
    bezel.add(x0, y0, t, x1, y0 + lt, lh)
    bezel.add(x0, y1 - lt, t, x1, y1, lh)
    bezel.add(x0, y0, t, x0 + lt, y1, lh)
    bezel.add(x1 - lt, y0, t, x1, y1, lh)
    bezel.cut(-1, ow / 2 - p["usb_w"] / 2 - 1, t, w + lt + g + 1, ow / 2 + p["usb_w"] / 2 + 1, lh + 1)   # юбка не мешает USB

    # подставка: клин с наклонной гранью и бортиком спереди; корпус ложится на наклон
    a = math.radians(p["stand_angle"])
    d, lip = p["stand_depth"], p["stand_lip"]
    hgt = d * math.tan(a)
    profile = [(0, 0), (d, 0), (d, hgt + 2), (0, 2 + lip)]   # YZ, против часовой при взгляде с +X
    stand = prism(profile, 0, ol)
    meta = dict(outer=(ol, ow, oh), bezel_t=t, lip_h=p["lip_h"], stand_h=hgt + 2)
    return tray, bezel, stand, meta


# ---------------- вывод ----------------

def write_stl(path, tris, name):
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            v0, v1, v2 = np.array(t[0]), np.array(t[1]), np.array(t[2])
            n = np.cross(v1 - v0, v2 - v0)
            ln = np.linalg.norm(n)
            n = n / ln if ln else n
            f.write(struct.pack("<12fH", *n, *v0, *v1, *v2, 0))


def check_watertight(tris):
    """Каждое ребро должно встречаться ровно дважды, в противоположных направлениях."""
    from collections import Counter
    def key(p):
        return tuple(round(c, 4) for c in p)
    edges = Counter()
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edges[(key(a), key(b))] += 1
    bad = [e for e, n in edges.items() if n != 1 or edges.get((e[1], e[0]), 0) != 1]
    return len(bad) == 0, len(bad)


def volume(tris):
    v = 0.0
    for t in tris:
        a, b, c = map(np.array, t)
        v += np.dot(a, np.cross(b, c)) / 6
    return v


def preview(parts, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(12, 4.2), facecolor="#111111")
    titles = {"tray": "Лоток", "bezel": "Рамка (лицом вниз)", "stand": "Подставка"}
    colors = {"tray": "#D97757", "bezel": "#E8E6E1", "stand": "#10A37F"}
    for i, (name, tris) in enumerate(parts):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", facecolor="#111111")
        pc = Poly3DCollection(tris, facecolor=colors[name], edgecolor=(0, 0, 0, 0.25), linewidths=0.2)
        ax.add_collection3d(pc)
        pts = tris.reshape(-1, 3)
        mn, mx = pts.min(0), pts.max(0)
        span = (mx - mn).max()
        c = (mn + mx) / 2
        ax.set_xlim(c[0] - span / 2, c[0] + span / 2)
        ax.set_ylim(c[1] - span / 2, c[1] + span / 2)
        ax.set_zlim(c[2] - span / 2, c[2] + span / 2)
        ax.view_init(elev=28, azim=-58 if name != "stand" else -35)
        ax.set_axis_off()
        size = mx - mn
        ax.set_title(f"{titles[name]}\n{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} мм",
                     color="#DDDDDD", fontsize=11)
    plt.tight_layout()
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())


def main():
    tray, bezel, stand, meta = build(PARAMS)
    parts = [("tray", tray.mesh()), ("bezel", bezel.mesh()), ("stand", stand)]
    for name, tris in parts:
        ok, nbad = check_watertight(tris)
        out = os.path.join(HERE, f"agent-status-bar-{name}.stl")
        write_stl(out, tris, f"agent-status-bar {name}")
        print(f"{name:6s} {len(tris):6d} треугольников, объём {volume(tris) / 1000:6.2f} см³, "
              f"герметичен: {'да' if ok else f'нет ({nbad} рёбер)'} → {os.path.relpath(out)}")
    preview(parts, meta, os.path.join(HERE, "preview.png"))
    ol, ow, oh = meta["outer"]
    print(f"корпус в сборе: {ol:.1f} × {ow:.1f} × {oh + meta['bezel_t']:.1f} мм")


if __name__ == "__main__":
    main()
