#!/usr/bin/env python3
"""
Корпус T-Display-S3 (LCD) + аккумулятор 103565: проверки и скрипт для Fusion 360.

    python hardware/case/lcd/make.py

Размеры — в PARAMS в geometry.py. Скрипт Fusion (fusion/AgentStatusBarCase/) строит модель в открытом
документе и сам сохраняет STL каждой детали рядом с собой:
Utilities → Scripts and Add-Ins → «+» → папка AgentStatusBarCase → Run.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "amoled"))  # сеточные помощники из case.py
import geometry                                                    # noqa: E402
from case import Part, prism, write_stl, check_watertight, volume  # noqa: E402

# положение для печати: (поворот на 180° вокруг X?, подпись)
PRINT = {"shell": (False, "Корпус — лицом вниз"), "divider": (True, "Перегородка — рейками вверх"),
         "lid": (True, "Крышка — наружной стороной вниз"), "stand": (False, "Подставка")}
COLORS = {"shell": "#D97757", "divider": "#9A9A9F", "lid": "#E8E6E1", "stand": "#10A37F"}


def meshes(parts):
    out = {}
    for name, spec in parts.items():
        if "prism" in spec:
            out[name] = prism(spec["prism"], spec["x0"], spec["x1"])
        else:
            pt = Part(name)
            for b in spec["solids"]:
                pt.add(*b)
            for b in spec["holes"]:
                pt.cut(*b)
            pt.inner = [tuple(map(float, b)) for b in spec.get("inner", [])]
            out[name] = pt.mesh()
    return out


def for_print(tris, flip):
    t = tris.copy()
    if flip:                                   # поворот на 180° вокруг X: y → −y, z → −z (ориентация граней сохраняется)
        t[..., 1] *= -1
        t[..., 2] *= -1
    t -= t.reshape(-1, 3).min(0)
    return t


def preview(assembly, path, d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(13, 5), facecolor="#111111")
    views = [("Сборка (разнесено)", True, (24, -60)), ("Лицо", False, (62, -90)), ("Сзади, без крышки", False, (-35, -120))]
    for i, (title, explode, (el, az)) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", facecolor="#111111")
        allp = []
        for name, tris in assembly.items():
            if name == "stand" or (i == 2 and name == "lid"):
                continue
            t = tris.copy()
            if explode:
                t[..., 2] += {"shell": 0, "divider": 18, "lid": 34}[name]
            ax.add_collection3d(Poly3DCollection(t, facecolor=COLORS[name], edgecolor=(0, 0, 0, 0.25), linewidths=0.15))
            allp.append(t.reshape(-1, 3))
        pts = np.vstack(allp)
        mn, mx = pts.min(0), pts.max(0)
        span, c = (mx - mn).max(), (mn + mx) / 2
        ax.set_xlim(c[0] - span / 2, c[0] + span / 2); ax.set_ylim(c[1] - span / 2, c[1] + span / 2)
        ax.set_zlim(c[2] - span / 2, c[2] + span / 2)
        ax.view_init(elev=el, azim=az); ax.set_axis_off()
        ax.set_title(title, color="#DDDDDD", fontsize=11)
    plt.tight_layout()
    fig.suptitle(f"Корпус {d['ol']:.1f} × {d['ow']:.1f} × {d['oh'] + geometry.PARAMS['lid_t']:.1f} мм",
                 color="#DDDDDD", fontsize=12, y=0.99)
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())


def fusion_script():
    """Скрипт Fusion = geometry.py + построитель (fusion_builder.py), одним файлом."""
    src = open(os.path.join(HERE, "geometry.py"), encoding="utf-8").read()
    builder = open(os.path.join(HERE, "fusion_builder.py"), encoding="utf-8").read()
    out_dir = os.path.join(HERE, "fusion", "AgentStatusBarCase")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "AgentStatusBarCase.py"), "w", encoding="utf-8") as f:
        f.write("# Сгенерировано hardware/case/lcd/make.py — правьте geometry.py и fusion_builder.py\n")
        f.write(src + "\n\n" + builder)
    with open(os.path.join(out_dir, "AgentStatusBarCase.manifest"), "w", encoding="utf-8") as f:
        f.write('{\n  "autodeskProduct": "Fusion360",\n  "type": "script",\n  "author": "yakory777",\n'
                '  "description": {"": "Agent Status Bar case: T-Display-S3 LCD + 103565 battery"},\n'
                '  "supportedOS": "windows|mac",\n  "editEnabled": true\n}\n')
    return out_dir


def checks(parts, d, p):
    """Плата, аккумулятор и детали не пересекаются; аккумулятор входит в гнездо."""
    def ov(a, b):
        return all(a[i] < b[i + 3] - 1e-6 and b[i] < a[i + 3] - 1e-6 for i in range(3))
    board = (d["bx0"], d["by0"], p["front_t"], d["bx1"], d["by1"], d["z_board_back"])
    nx0, ny0, nx1, ny1 = d["nest"]
    f = p["frame_t"] + p["bat_fit"]
    bat = (nx0 + f, ny0 + f, d["z_div1"], nx1 - f, ny1 - f, d["z_div1"] + p["bat_t"])
    errors = []
    for name in ("shell", "divider", "lid"):
        for kind in ("solids", "inner"):
            for b in parts[name].get(kind, []):
                if name == "shell" and kind == "solids":
                    continue
                for obj, label in ((board, "плата"), (bat, "аккумулятор")):
                    if b in d.get("nubs", []) and label == "плата":
                        continue                       # выступ толкателя и должен касаться кнопки
                    if ov(b, obj):
                        errors.append(f"{name}/{kind} задевает: {label} {[round(x, 1) for x in b]}")
    for sx, sy in d["screws"]:                                     # головки винтов перегородки (≈Ø4 × 1,6)
        head = (sx - 2.2, sy - 2.2, d["z_div1"] + 0.01, sx + 2.2, sy + 2.2, d["z_div1"] + 1.8)
        for b in parts["divider"]["solids"][1:]:
            if ov(head, b):
                errors.append(f"головка винта перегородки упирается в {[round(x, 1) for x in b]}")
    for b in parts["divider"]["holes"]:                            # стойки крышки не задевают вырезы под провод
        for sx, sy in d["lid_screws"]:
            if ov((sx - p["boss"] / 2, sy - p["boss"] / 2, b[2], sx + p["boss"] / 2, sy + p["boss"] / 2, b[5]), b):
                errors.append(f"стойка крышки ({sx:.1f}, {sy:.1f}) попадает на вырез под провод")
    lg = parts["shell"].get("logo")                                # логотип: на лице, не на окне и не на язычке BOOT
    if lg:
        xs = [x for s in lg["shapes"] for loop in s for x, _ in loop]
        ys = [y for s in lg["shapes"] for loop in s for _, y in loop]
        box = (min(xs), min(ys), -1, max(xs), max(ys), lg["depth"])
        if box[0] < p["wall"] or box[1] < p["wall"] or box[4] > d["ow"] - p["wall"]:
            errors.append("логотип вылезает за лицо")
        for h in parts["shell"]["holes"]:
            if h[2] < 0.01 and ov(box, (h[0] - 1, h[1] - 1, h[2], h[3] + 1, h[4] + 1, h[5])):
                errors.append(f"логотип задевает вырез {[round(x, 1) for x in h]}")
        if lg["depth"] > p["front_t"] - 0.8:
            errors.append("логотип глубже, чем допускает лицо")
    for deco in parts["shell"].get("deco", []):                    # прорези: на стенке, мимо язычка RESET и торцов
        for loops in deco["shapes"]:
            xs = [x for x, _ in loops[0]]
            zs = [z for _, z in loops[0]]
            box = (min(xs), deco["y"] - deco["depth"], min(zs), max(xs), deco["y"] + deco["depth"], max(zs))
            if box[0] < p["foot_t"] + 3 or box[3] > d["ol"] - p["foot_t"] - 3 or box[2] < 2 or box[5] > d["depth"] - 2:
                errors.append(f"прорезь у края стенки {[round(x, 1) for x in box]}")
            for h in parts["shell"]["holes"]:
                if ov((box[0] - 1, box[1], box[2] - 1, box[3] + 1, box[4], box[5] + 1), h) and h[1] > p["wall"] and h[4] < d["ow"] - p["wall"]:
                    continue                                               # полость корпуса — не в счёт
                if h[0] > 0 and h[3] < d["ol"] and ov((box[0] - 1, box[1], box[2] - 1, box[3] + 1, box[4], box[5] + 1), h) and not (h[1] <= p["wall"] + 1e-6 and h[4] >= d["ow"] - p["wall"] - 1e-6):
                    errors.append(f"прорезь задевает вырез {[round(x, 1) for x in h]}")
        if deco["depth"] > p["wall"] - 0.8:
            errors.append("прорези слишком глубокие для стенки")
    pb = d["pwr"]["body"]                                          # корпус кнопки питания внутри
    for kind in ("inner",):
        for b in parts["shell"][kind]:
            if ov(pb, b):
                errors.append(f"кнопке питания мешает {[round(x, 1) for x in b]}")
    for b in parts["divider"]["solids"] + [board]:
        if ov(pb, b):
            errors.append(f"кнопке питания мешает {[round(x, 1) for x in b]}")
    if max(d["bite_div"], d["bite_lid"]) > p["pilot_depth"] - 0.3:
        errors.append("винт длиннее отверстия под него")
    assert abs((bat[3] - bat[0]) - p["bat_l"]) < 1e-6 and abs((bat[4] - bat[1]) - p["bat_w"]) < 1e-6
    return errors


def main():
    parts, d = geometry.build(geometry.PARAMS)
    errs = checks(parts, d, geometry.PARAMS)
    for e in errs:
        print("ОШИБКА:", e)
    out = fusion_script()
    print(f"винты: 8 × M2×{d['screw_len']:.0f} — 4 перегородка→корпус (в колонну {d['bite_div']:.1f} мм), "
          f"4 крышка→перегородка (в стойку {d['bite_lid']:.1f} мм)")
    print(f"толкатели: "
          f"BOOT: язычок x {d['tongue'][0]:.1f}–{d['tongue'][2]:.1f}, y {d['tongue'][1]:.1f}–{d['tongue'][3]:.1f}; "
          f"RESET: x {d['rst_tongue'][0]:.1f}–{d['rst_tongue'][2]:.1f}, z {d['rst_tongue'][1]:.1f}–{d['rst_tongue'][3]:.1f}")
    print(f"корпус {d['ol']:.1f} × {d['ow']:.1f} × {d['depth']:.1f} мм, экран под {geometry.PARAMS['tilt']:.0f}°; "
          f"проверки: {'ок' if not errs else len(errs)} → {os.path.relpath(out)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
