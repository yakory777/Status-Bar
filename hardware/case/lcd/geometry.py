"""
Геометрия корпуса для LilyGO T-Display-S3 (LCD 1,9″) с аккумулятором 103565 за платой.

Чистый Python без импортов: этот файл целиком встраивается в скрипт Fusion 360 (см. make.py).

Оси (мм): X — вдоль платы и аккумулятора (USB-C со стороны x = max), Y — поперёк (y = 0 — низ, когда
корпус стоит), Z — от лица к задней крышке (окно дисплея на z = 0).

Сборка: плата лицом в корпус → перегородка (ложится на колонны и упоры) → аккумулятор в гнездо →
крышка заподлицо. Четыре винта M2×20 проходят крышку, стойки и перегородку и вкручиваются в колонны
корпуса — одни винты держат и крышку, и перегородку. По бокам — тонкие ножки-рамки: корпус сам стоит
на столе, экран под углом tilt к столу. На лице — гибкий толкатель кнопки BOOT.

    лицо z=0 ─┬─ передняя стенка с окном дисплея
              ├─ плата (дисплей к окну)
              ├─ рейки перегородки прижимают плату за края
              ├─ перегородка на упорах; гнездо аккумулятора с вырезом под провода
              ├─ аккумулятор 103565 + прокладка
    зад ──────┴─ крышка заподлицо; 4 × M2×20 сквозь крышку и перегородку в колонны
"""

PARAMS = dict(
    # --- плата (уточните штангенциркулем) ---
    board_l=62.0,        # длина платы
    board_w=26.0,        # ширина платы
    board_t=10.0,        # от стекла дисплея до обратной стороны печатной платы
    board_back=2.0,      # высота деталей на обороте платы
    clear=0.3,           # зазор вокруг платы
    win_l=43.5,          # окно дисплея: видимая область ≈ 42,7 × 22,7 мм + запас
    win_w=23.5,
    win_dx=2.5,          # смещение окна от центра платы вдоль X (от USB — плюс); уточнить
    usb_w=12.0,          # проём USB-C на торце x = max под штекер с корпусом кабеля
    usb_h=7.0,
    usb_from_back=2.5,   # центр разъёма ближе к лицу, чем оборот платы, на столько мм
    # толкатель RESET в верхней стенке y = max: кнопка на боковом торце платы; уточнить её место
    rst_from_usb=8.0,    # от торца платы с USB до центра кнопки
    rst_from_back=1.8,   # центр кнопки ближе к лицу, чем оборот платы, на столько мм
    rst_protrude=0.8,    # на сколько кнопка выступает за край платы
    # толкатель BOOT на лице: кнопка на лицевой стороне платы; уточнить её место
    boot_from_usb=5.0,   # от торца платы с USB до центра кнопки
    boot_dy=-8.0,        # от средней линии платы поперёк (минус — к низу корпуса)
    tongue_w=5.0,        # гибкий язычок в лицевой панели
    tongue_l=11.0,
    tongue_t=1.0,        # язычок тоньше панели, чтобы гнулся
    slot=0.8,            # ширина прорези вокруг язычка
    nub=2.5,             # выступ изнутри, давит на кнопку
    nub_h=1.6,           # высота выступа: от внутренней стороны панели до кнопки минус 0,2 мм; уточнить
    # --- аккумулятор 103565 ---
    bat_l=65.0,
    bat_w=35.0,
    bat_t=10.0,
    bat_fit=0.3,         # зазор в гнезде — аккумулятор входит плотно
    bat_foam=1.0,        # место под мягкую прокладку между аккумулятором и крышкой
    frame_t=1.2,         # стенки гнезда
    frame_h=6.0,         # высота стенок гнезда
    frame_notch=10.0,    # вырез в стенке гнезда под провода (со стороны USB)
    # --- корпус ---
    wall=2.0,
    front_t=1.6,
    boss=4.6,            # угловые колонны под винты M2
    pilot_d=1.7,         # отверстие под саморез M2×8: каждый уровень на своих винтах
    pilot_depth=8.0,
    post_len=6.0,        # упоры под перегородку на длинных стенках
    post_w=2.0,
    guide_t=1.2,         # рёбра, которые держат плату
    guide_len=6.0,
    guide_h=6.0,
    # --- перегородка ---
    divider_t=1.2,
    divider_gap=0.25,
    rail_w=2.0,
    cable_w=12.0,        # отверстие под провод аккумулятора у торца с USB
    # --- крышка: заподлицо, на винтах ---
    lid_t=2.4,
    lid_gap=0.2,
    screw_d=2.4,         # отверстие под винт M2
    head_d=4.2,          # гнездо под головку
    head_depth=1.2,
    screw_l=8.0,         # длина винтов M2 (8 шт.: 4 перегородка→корпус, 4 крышка→перегородка)
    lid_screw_y=10.5,    # винты крышки: на торцах, на столько мм от длинной стенки (между угловым винтом и проводом)
    # --- на будущее: окна толщиной skin, выдавливаются ножом ---
    skin=0.6,
    sw_w=7.0,            # выключатель SS12D00 на торце x = 0 (напротив USB)
    sw_h=3.0,
    # --- наклон: экран под углом tilt к столу (90 — стоит вертикально, без опор) ---
    tilt=60.0,
    foot_t=2.0,          # толщина ножек (вровень с торцевыми стенками)
    leg_h=26.0,          # докуда задняя ножка поднимается по задней стенке, от низа
    leg_back=30.0,       # на сколько задняя ножка выступает назад
    leg_bar=3.0,         # ширина перемычек вокруг проёмов в ножках
    leg_round=2.0,       # скругление углов ножек и проёмов
    # --- логотип на лице, между окном и торцом с выключателем (docs/logo/logo.svg) ---
    logo_mm=19.0,        # сторона квадрата 100 × 100 единиц логотипа
    logo_depth=0.5,      # глубина гравировки (лицо печатается вниз — поддержки не нужны)
    # --- декоративные прорези на длинных стенках: ряд наклонных «делений», высота — волной ---
    deco_n=9,            # сколько прорезей в ряду
    deco_w=2.2,          # ширина прорези
    deco_pitch=4.4,      # шаг вдоль стенки
    deco_hmin=7.0,       # длина крайних прорезей
    deco_hmax=19.0,      # длина средней
    deco_slant=30.0,     # наклон от поперёк стенки, градусы (эхо экрана под 60°)
    deco_depth=1.0,      # глубина — половина стенки, насквозь не прорезает
)

# Логотип в единицах 0..100, ось v вниз — те же фигуры, что в docs/logo/logo.svg и draw_logo() прошивки.
# На корпусе гравируются рамка экрана, «>», курсор, три заполненных деления и точка «в эфире».
LOGO = dict(
    frame=((4, 14, 96, 86, 15.5), (11, 21, 89, 79, 8.5)),        # внешний и внутренний скруглённый прямоугольник
    chevron=((24, 34), (40, 46), (24, 58)), stroke=7,
    cursor=(46, 52, 62, 58, 1.5),
    segments=[(22 + 12 * i, 67, 32 + 12 * i, 74, 1.5) for i in range(3)],
    dot=(78, 32, 4.5),
)


def _round_rect(x0, y0, x1, y1, r, n=6):
    import math
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for j in range(n + 1):
            a = math.radians(a0 + 90 * j / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _circle(cx, cy, r, n=24):
    import math
    return [(cx + r * math.cos(2 * math.pi * j / n), cy + r * math.sin(2 * math.pi * j / n)) for j in range(n)]


def _stroke3(pts, width, n=8):
    """Контур ломаной из трёх точек толщиной width: круглые концы, круглый внешний изгиб."""
    import math
    (ax, ay), (bx, by), (cx, cy) = pts
    h = width / 2

    def unit(x, y):
        l = math.hypot(x, y)
        return x / l, y / l
    d1, d2 = unit(bx - ax, by - ay), unit(cx - bx, cy - by)
    n1, n2 = (-d1[1], d1[0]), (-d2[1], d2[0])
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    s_in = 1 if cross > 0 else -1                                   # внутренняя сторона изгиба
    k = h / (1 + n1[0] * n2[0] + n1[1] * n2[1])
    miter = (bx + s_in * k * (n1[0] + n2[0]), by + s_in * k * (n1[1] + n2[1]))

    def arc(px, py, fx, fy, tx, ty):                                # дуга радиуса h от направления f к t
        a0, a1 = math.atan2(fy, fx), math.atan2(ty, tx)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        if abs(abs(da) - math.pi) < 1e-6:
            da = math.pi
        return [(px + h * math.cos(a0 + da * j / n), py + h * math.sin(a0 + da * j / n)) for j in range(n + 1)]
    so = -s_in
    out = [(ax + so * h * n1[0], ay + so * h * n1[1])]
    out += arc(bx, by, so * n1[0], so * n1[1], so * n2[0], so * n2[1])     # внешний изгиб
    out.append((cx + so * h * n2[0], cy + so * h * n2[1]))
    cap = arc(cx, cy, so * n2[0], so * n2[1], d2[0], d2[1])[1:] + arc(cx, cy, d2[0], d2[1], -so * n2[0], -so * n2[1])[1:]
    out += cap
    out.append(miter)
    out.append((ax - so * h * n1[0], ay - so * h * n1[1]))
    out += arc(ax, ay, -so * n1[0], -so * n1[1], -d1[0], -d1[1])[1:] + arc(ax, ay, -d1[0], -d1[1], so * n1[0], so * n1[1])[1:-1]
    return out


def deco_shapes(xc, zc, p):
    """Прорези-«деления» на стенке в координатах (x, z): наклонные капсулы, длина плавно растёт к середине."""
    import math
    n, out = p["deco_n"], []
    a = math.radians(p["deco_slant"])
    for i in range(n):
        u = i / (n - 1)
        h = p["deco_hmin"] + (p["deco_hmax"] - p["deco_hmin"]) * math.sin(math.pi * u)
        x0 = xc + (i - (n - 1) / 2) * p["deco_pitch"]
        r = p["deco_w"] / 2 - 0.01
        pill = _round_rect(-p["deco_w"] / 2, -h / 2, p["deco_w"] / 2, h / 2, r, n=6)
        out.append([[(x0 + x * math.cos(a) + z * math.sin(a), zc - x * math.sin(a) + z * math.cos(a)) for x, z in pill]])
    return out


def logo_shapes(cx, cy, size):
    """Фигуры логотипа на лице z = 0: список контуров-петель (одна петля — сплошная фигура, две — кольцо).
    Смотрим на лицо снаружи (против +z): вправо — это −x, вверх — +y, поэтому u отражается."""
    s = size / 100.0

    def m(poly):
        return [(cx - (u - 50) * s, cy - (v - 50) * s) for u, v in poly]
    L = LOGO
    shapes = [[m(_round_rect(*L["frame"][0])), m(_round_rect(*L["frame"][1]))],
              [m(_stroke3(L["chevron"], L["stroke"]))],
              [m(_round_rect(*L["cursor"], n=3))]]
    shapes += [[m(_round_rect(*sg, n=3))] for sg in L["segments"]]
    shapes.append([m(_circle(*L["dot"]))])
    return shapes


def dims(p):
    """Основные размеры и координаты, общие для всех деталей."""
    import math
    d = {}
    w = p["wall"]
    nest_l = p["bat_l"] + 2 * (p["bat_fit"] + p["frame_t"])          # гнездо снаружи
    nest_w = p["bat_w"] + 2 * (p["bat_fit"] + p["frame_t"])
    d["nest_l"], d["nest_w"] = nest_l, nest_w
    d["il"] = max(nest_l + 2 * (p["boss"] + 0.4), p["board_l"] + 2 * p["clear"] + p["guide_t"] + p["boss"])
    d["iw"] = max(nest_w + 2 * p["divider_gap"] + 0.4, p["board_w"] + 2 * (p["clear"] + p["guide_t"] + p["boss"]))
    d["ol"] = d["il"] + 2 * w
    d["ow"] = d["iw"] + 2 * w
    d["z_board_back"] = p["front_t"] + p["board_t"]
    d["z_div0"] = d["z_board_back"] + p["board_back"]
    d["z_div1"] = d["z_div0"] + p["divider_t"]
    d["oh"] = d["z_div1"] + p["bat_t"] + p["bat_foam"]                 # где лежит крышка
    d["depth"] = d["oh"] + p["lid_t"]                                   # полная толщина корпуса
    d["bx1"] = d["il"] + w - p["clear"]                                 # плата прижата к торцу с USB (x = max)
    d["bx0"] = d["bx1"] - p["board_l"]
    d["by0"] = d["ow"] / 2 - p["board_w"] / 2
    d["by1"] = d["by0"] + p["board_w"]
    b = p["boss"]
    il, iw = d["il"], d["iw"]
    d["screws"] = [(w + b / 2, w + b / 2), (w + il - b / 2, w + b / 2),
                   (w + b / 2, w + iw - b / 2), (w + il - b / 2, w + iw - b / 2)]
    g = p["divider_gap"]
    ly = p["lid_screw_y"]
    lx = (d["il"] - nest_l) / 2 + w - 1.5            # у стенки гнезда: от края крышки до гнезда головки ≥ 1,5 мм
    d["lid_screws"] = [(lx, ly), (d["ol"] - lx, ly), (lx, d["ow"] - ly), (d["ol"] - lx, d["ow"] - ly)]
    d["lean"] = math.radians(90 - p["tilt"])
    return d


def tilt_y(d, z):
    """Плоскость стола в координатах корпуса: y(z). Касается заднего нижнего ребра (y = 0, z = depth)."""
    import math
    return (z - d["depth"]) * math.tan(d["lean"])


def _shrink(tri, t):
    """Треугольник, сдвинутый внутрь на t (стороны параллельны) — проём ножки-рамки."""
    import math
    (ax, ay), (bx, by), (cx, cy) = tri
    la, lb, lc = math.dist((bx, by), (cx, cy)), math.dist((ax, ay), (cx, cy)), math.dist((ax, ay), (bx, by))
    per = la + lb + lc
    ix, iy = (la * ax + lb * bx + lc * cx) / per, (la * ay + lb * by + lc * cy) / per
    area = abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2
    r = 2 * area / per
    if r <= t + 0.5:
        return None
    k = (r - t) / r
    return [(ix + (x - ix) * k, iy + (y - iy) * k) for x, y in tri]


def build(p):
    """Детали: {имя: {"solids", "holes", "inner", "cyl_holes", "prisms"}}.
    Тело = solids − holes + inner; затем круглые отверстия cyl_holes (x, y, z0, z1, диаметр)
    и призмы prisms ({"profile": [(y, z), …], "hole": [...] или None, "x0", "x1", "round"}) — профиль в
    плоскости YZ, вытянутый по X, с проёмом и скруглёнными углами.
    Блок — (x0, y0, z0, x1, y1, z1) в мм, все детали — в положении сборки."""
    d = dims(p)
    w, il, iw, ol, ow, oh, dep = p["wall"], d["il"], d["iw"], d["ol"], d["ow"], d["oh"], d["depth"]
    bx0, bx1, by0, by1 = d["bx0"], d["bx1"], d["by0"], d["by1"]
    ft, zbb, zd0, zd1 = p["front_t"], d["z_board_back"], d["z_div0"], d["z_div1"]
    b = p["boss"]
    parts = {}

    # ---------- корпус ----------
    S, H, I, C, P = [], [], [], [], []
    S.append((0, 0, 0, ol, ow, dep))
    H.append((w, w, ft, w + il, w + iw, dep + 1))                       # полость
    wx = (bx0 + bx1) / 2 - p["win_dx"]                                   # окно дисплея — дальше от USB
    H.append((wx - p["win_l"] / 2, ow / 2 - p["win_w"] / 2, -1, wx + p["win_l"] / 2, ow / 2 + p["win_w"] / 2, ft + 1))
    uz = zbb - p["usb_from_back"]                                        # USB-C, торец x = max
    usb_hole = (ol - w - 0.5, ow / 2 - p["usb_w"] / 2, uz - p["usb_h"] / 2, ol + 1, ow / 2 + p["usb_w"] / 2, uz + p["usb_h"] / 2)
    H.append(usb_hole)
    # толкатель RESET: такой же язычок в верхней стенке, длинный выступ внутрь до кнопки на торце платы
    rxk, rzk = bx1 - p["rst_from_usb"], zbb - p["rst_from_back"]
    tw, tl, s_ = p["tongue_w"], p["tongue_l"], p["slot"]
    x_free, x_root = rxk + 2.5, rxk + 2.5 - tl                           # корень — к середине, свободный конец — к USB
    yi, yo = ow - w - 0.5, ow + 1                                        # сквозь стенку
    H.append((x_root, yi, rzk - tw / 2 - s_, x_free + s_, yo, rzk - tw / 2))
    H.append((x_root, yi, rzk + tw / 2, x_free + s_, yo, rzk + tw / 2 + s_))
    H.append((x_free, yi, rzk - tw / 2 - s_, x_free + s_, yo, rzk + tw / 2 + s_))
    H.append((x_root, ow - w - 0.01, rzk - tw / 2, x_free, ow - p["tongue_t"], rzk + tw / 2))   # язычок тоньше
    tip = by1 + p["rst_protrude"] + 0.2                                  # до кнопки остаётся 0,2 мм
    rnub = (rxk - p["nub"] / 2, tip, rzk - p["nub"] / 2, rxk + p["nub"] / 2, ow - p["tongue_t"], rzk + p["nub"] / 2)
    d["rst_tongue"] = (x_root, rzk - tw / 2, x_free, rzk + tw / 2)
    k = p["skin"]                                                        # окно под выключатель: снаружи остаётся skin
    sz = (zd1 + oh) / 2
    sw_hole = (k, ow / 2 - p["sw_w"] / 2, sz - p["sw_h"] / 2, w + 0.5, ow / 2 + p["sw_w"] / 2, sz + p["sw_h"] / 2)
    H.append(sw_hole)
    # толкатель BOOT: U-образная прорезь в лице, язычок тоньше панели, выступ изнутри над кнопкой
    kx, ky = bx1 - p["boot_from_usb"], ow / 2 + p["boot_dy"]
    tw, tl, s_ = p["tongue_w"], p["tongue_l"], p["slot"]
    fy = 1 if p["boot_dy"] < 0 else -1                                    # корень язычка — к середине корпуса
    y_free, y_root = ky - fy * 2.5, ky - fy * 2.5 + fy * tl
    ya, yb = min(y_free, y_root), max(y_free, y_root)
    H.append((kx - tw / 2 - s_, ya - (s_ if fy > 0 else 0), -1, kx - tw / 2, yb + (0 if fy > 0 else s_), ft + 1))
    H.append((kx + tw / 2, ya - (s_ if fy > 0 else 0), -1, kx + tw / 2 + s_, yb + (0 if fy > 0 else s_), ft + 1))
    yf = y_free - s_ if fy > 0 else y_free
    H.append((kx - tw / 2 - s_, min(yf, yf + s_), -1, kx + tw / 2 + s_, max(yf, yf + s_), ft + 1))
    H.append((kx - tw / 2, ya, p["tongue_t"], kx + tw / 2, yb, ft + 0.01))   # язычок тоньше
    nub = (kx - p["nub"] / 2, ky - p["nub"] / 2, p["tongue_t"], kx + p["nub"] / 2, ky + p["nub"] / 2, ft + p["nub_h"])
    d["nub"], d["tongue"] = nub, (kx - tw / 2, ya, kx + tw / 2, yb)
    for sx, sy in d["screws"]:                                           # колонны под винты — до перегородки
        I.append((sx - b / 2, sy - b / 2, ft, sx + b / 2, sy + b / 2, zd0))
        C.append((sx, sy, zd0 - p["pilot_depth"], zd0 + 0.1, p["pilot_d"]))
    for xc in (ol / 2 - 12, ol / 2 + 12):                                # упоры под середину перегородки
        for ya_, yb_ in ((w, w + p["post_w"]), (w + iw - p["post_w"], w + iw)):
            I.append((xc - p["post_len"] / 2, ya_, ft, xc + p["post_len"] / 2, yb_, zd0))
    gt, gl, gh, c = p["guide_t"], p["guide_len"], p["guide_h"], p["clear"]
    for xa in (bx0 + 1, bx1 - 30 - gl):                                  # рёбра по бокам платы
        I.append((xa, by0 - c - gt, ft, xa + gl, by0 - c, ft + gh))
        I.append((xa, by1 + c, ft, xa + gl, by1 + c + gt, ft + gh))
    I.append((bx0 - c - gt, by0, ft, bx0 - c, by1, ft + gh))             # упор с торца напротив USB
    I.append(nub)
    I.append(rnub)
    d["nubs"] = [nub, rnub]
    recut = []
    if p["tilt"] < 89.9:
        # Боковые «щёки» — торцевая стенка и ножки одной пластиной: лицо корпуса продолжается вниз
        # в переднюю ножку, низ щеки — прямая по столу, сзади — опора. В ножках — облегчающие проёмы.
        # Скругляются только углы ножек и проёмов; углы самого корпуса остаются как у корпуса.
        y_front = tilt_y(d, 0)
        z_tip = dep + p["leg_back"]
        y_tip = tilt_y(d, z_tip)
        cheek = [(ow, 0), (y_front, 0), (y_tip, z_tip), (p["leg_h"], dep), (ow, dep)]
        holes = [h for h in (_shrink([(0, 0), (y_front, 0), (0, dep)], p["leg_bar"]),
                             _shrink([(0, dep), (p["leg_h"], dep), (y_tip, z_tip)], p["leg_bar"])) if h]
        for xa, xb in ((0, p["foot_t"]), (ol - p["foot_t"], ol)):
            P.append(dict(profile=cheek, holes=holes, x0=xa, x1=xb, round=p["leg_round"],
                          keep_sharp=[(ow, 0), (ow, dep)]))
        recut = [usb_hole, sw_hole]                                      # щёки закрыли бы проёмы в торцах
        d["support"] = dict(front=(y_front, 0), tip=(y_tip, z_tip))
    lx0 = w + 0.5                                                         # логотип — между стенкой и фаской окна
    lx1 = wx - p["win_l"] / 2 - 1.0
    d["logo_at"] = ((lx0 + lx1) / 2, ow / 2)
    logo = dict(shapes=logo_shapes(d["logo_at"][0], ow / 2, p["logo_mm"]), depth=p["logo_depth"])
    deco = [dict(y=yy, depth=p["deco_depth"], shapes=deco_shapes(ol / 2, dep / 2, p)) for yy in (0.0, ow)]
    parts["shell"] = dict(solids=S, holes=H, inner=I, cyl_holes=C, prisms=P, recut=recut, logo=logo, deco=deco)

    # ---------- перегородка: гнездо аккумулятора, стойки под винты ----------
    g = p["divider_gap"]
    S = [(w + g, w + g, zd0, w + il - g, w + iw - g, zd1)]
    rw = p["rail_w"]
    S.append((bx0 + 2, by0 + 0.5, zbb, bx1 - 2, by0 + 0.5 + rw, zd0))   # рейки к краям платы
    S.append((bx0 + 2, by1 - 0.5 - rw, zbb, bx1 - 2, by1 - 0.5, zd0))
    nx0, ny0 = ol / 2 - d["nest_l"] / 2, ow / 2 - d["nest_w"] / 2       # гнездо аккумулятора
    nx1, ny1, ft_, fh = nx0 + d["nest_l"], ny0 + d["nest_w"], p["frame_t"], zd1 + p["frame_h"]
    S += [(nx0, ny0, zd1, nx1, ny0 + ft_, fh), (nx0, ny1 - ft_, zd1, nx1, ny1, fh),
          (nx0, ny0, zd1, nx0 + ft_, ny1, fh), (nx1 - ft_, ny0, zd1, nx1, ny1, fh)]
    for sx, sy in d["lid_screws"]:                                       # стойки под винты крышки
        S.append((sx - b / 2, sy - b / 2, zd1, sx + b / 2, sy + b / 2, oh))
    H = [(nx0 - 1, ow / 2 - p["frame_notch"] / 2, zd1, nx0 + ft_ + 1, ow / 2 + p["frame_notch"] / 2, fh + 1)]
    H.append((w + g + 0.6, ow / 2 - p["cable_w"] / 2, zd0 - 1, nx0 - 0.6, ow / 2 + p["cable_w"] / 2, zd1 + 1))
    C = [(sx, sy, zd0 - 1, zd1 + 1, p["screw_d"]) for sx, sy in d["screws"]]        # винты в колонны корпуса
    C += [(sx, sy, oh - p["pilot_depth"], oh + 0.1, p["pilot_d"]) for sx, sy in d["lid_screws"]]
    parts["divider"] = dict(solids=S, holes=H, cyl_holes=C)

    # ---------- крышка заподлицо ----------
    lg = p["lid_gap"]
    S = [(w + lg, w + lg, oh, w + il - lg, w + iw - lg, dep)]
    C = []
    for sx, sy in d["lid_screws"]:
        C.append((sx, sy, oh - 1, dep + 1, p["screw_d"]))
        C.append((sx, sy, dep - p["head_depth"], dep + 1, p["head_d"]))
    parts["lid"] = dict(solids=S, holes=[], cyl_holes=C)

    d["window_center_x"] = wx
    d["nest"] = (nx0, ny0, nx1, ny1)
    d["bite_div"] = p["screw_l"] - p["divider_t"]                        # сколько винт входит в колонну
    d["bite_lid"] = p["screw_l"] - (p["lid_t"] - p["head_depth"])        # и в стойку перегородки
    d["screw_len"] = p["screw_l"]
    return parts, d
