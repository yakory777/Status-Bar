"""
Геометрия корпуса для LilyGO T-Display-S3 (LCD 1,9″) с аккумулятором 103565 за платой.

Чистый Python без импортов: этот файл целиком встраивается в скрипт Fusion 360 (см. make.py).

Оси (мм): X — вдоль платы и аккумулятора (USB-C со стороны x = max), Y — поперёк (y = 0 — низ, когда
корпус стоит), Z — от лица к задней крышке (окно дисплея на z = 0).

Размеры платы, кнопок и разъёмов взяты из официальной 3D-модели LilyGO (репозиторий T-Display-S3,
dimensions/t-display-s3-full.stl): плата 60,8 × 26 × 9,9 мм, кнопки BOOT и KEY — на лице у USB по обе
стороны от разъёма, RST — на боковом торце, разъём аккумулятора — на обороте у USB.

Сборка: плата стеклом к окну, USB-C в проём → перегородка: площадки прижимают край платы, 4 винта M2×8
в угловые колонны → аккумулятор в гнездо (торец с платой защиты и проводом — к USB, провод вниз в отверстие
к разъёму) → крышка заподлицо на 4 винтах M2×8 в стойки перегородки. Кнопки нажимаются через корпус:
язычок в лице над верхней кнопкой у USB и язычок RST в верхней стенке — плату ставят кнопкой RST вверх.

    лицо z=0 ─┬─ передняя стенка с окном дисплея и двумя толкателями
              ├─ плата (стекло к окну), рёбра по бокам, упор с торца
              ├─ площадки перегородки прижимают край платы
              ├─ перегородка на колоннах; гнездо аккумулятора, у USB — отверстие под провод
              ├─ аккумулятор 103565 + прокладка
    зад ──────┴─ крышка заподлицо на 4 × M2×8
"""

PARAMS = dict(
    # --- плата: размеры из официальной 3D-модели LilyGO (dimensions/t-display-s3-full.stl) ---
    board_l=60.8,        # печатная плата вдоль, без выступающего USB-C
    board_w=26.0,        # поперёк (плата и стекло дисплея одной ширины)
    board_t=6.4,         # от стекла дисплея до оборота печатной платы
    board_back=3.6,      # самые высокие детали на обороте (разъёмы у USB — 3,5 мм)
    clear=0.15,          # зазор вокруг платы — плата не болтается
    usb_out=1.2,         # USB-C выступает за край платы и входит в проём стенки
    usb_from_glass=3.6,  # центр USB-C от стекла (разъём на лицевой стороне платы)
    usb_w=12.4,          # проём — «капсула» по форме штекера USB-C с корпусом кабеля
    usb_h=6.8,
    usb_chamfer=0.8,     # фаска по краю проёма снаружи
    wire_d=6.02,         # отверстие под провод в перегородке у торца напротив USB (6 мм + 0,02)
    wire_room=1.0,       # гнездо сдвинуто от этого торца, чтобы отверстие поместилось
    wire_in_end=False,   # True — то же отверстие ещё и в торце корпуса
    wire_chamfer=0.5,
    win_from_usb=31.6,   # центр стекла дисплея от края платы с USB
    win_l=41.02,         # окно: видимая часть дисплея 41 мм (измерено) + 0,02
    win_w=24.0,
    # кнопки BOOT и KEY — на лице платы у USB, по обе стороны от разъёма; толкатель в лице — над верхней
    btn_from_usb=2.25,   # от края платы с USB до центра кнопки
    btn_dy=9.2,          # от средней линии платы поперёк, в обе стороны
    btn_depth=2.7,       # кнопка утоплена за плоскость стекла на столько мм
    btn_sides=(1,),      # какие кнопки нажимать через лицо: 1 — верхняя (к y = max), -1 — нижняя
    # кнопка RST — на боковом торце платы; плату ставят кнопкой RST к верхней стенке
    rst_from_usb=10.3,
    rst_from_glass=7.5,  # центр кнопки от стекла
    rst_protrude=0.4,    # на сколько кнопка выступает за край платы
    rst_sides=(1,),      # толкатель RST: 1 — в верхней стенке (y = max), -1 — в нижней
    tongue_w=4.0,        # гибкий язычок
    tongue_l=8.0,
    tongue_t=1.0,        # язычок тоньше панели, чтобы гнулся
    slot=0.8,            # ширина прорези вокруг язычка
    nub=2.5,             # выступ изнутри, давит на кнопку
    press_gap=0.2,       # от выступа до кнопки в покое
    # прижим платы: площадки перегородки давят на край печатной платы там, где на обороте нет деталей
    pad_spans=((16.0, 28.0), (38.0, 52.0)),   # от края платы с USB, мм
    pad_w=1.1,
    guide_spans=((15.0, 21.0), (30.0, 36.0), (53.0, 59.0)),   # боковые рёбра (мимо кнопки RST)
    # --- аккумулятор 103565 (реальный, с платой защиты и плёнкой) ---
    bat_l=68.0,
    bat_w=36.0,
    bat_t=10.5,
    bat_fit=0.4,         # зазор в гнезде
    bat_foam=1.0,        # место под мягкую прокладку между аккумулятором и крышкой
    frame_t=1.2,         # стенки гнезда
    frame_h=5.0,         # высота стенок гнезда
    frame_stub=6.0,      # торец гнезда со стороны USB открыт: только уголки, провод и плата защиты проходят
    cable_gap=6.0,       # место у торца с USB между гнездом и стенкой — провод уходит вниз к разъёму платы
    # --- корпус ---
    wall=2.0,
    front_t=1.6,
    boss=4.6,            # угловые колонны под винты M2
    pilot_d=1.7,         # отверстие под саморез M2×8: каждый уровень на своих винтах
    pilot_depth=8.0,
    post_len=6.0,        # упоры под перегородку на длинных стенках
    post_w=2.0,
    guide_t=1.2,         # рёбра, которые держат плату
    guide_h=6.0,
    # --- перегородка ---
    divider_t=1.2,
    divider_gap=0.25,
    cable_w=12.0,        # отверстие под провод аккумулятора у торца с USB — над разъёмом аккумулятора на плате
    # --- крышка: заподлицо, на винтах ---
    lid_t=2.4,
    lid_gap=0.2,
    screw_d=2.4,         # отверстие под винт M2
    head_d=4.2,          # гнездо под головку
    head_depth=1.2,
    screw_l=8.0,         # длина винтов M2 (8 шт.: 4 перегородка→корпус, 4 крышка→перегородка)
    lid_screw_y=10.5,    # винты крышки: на торцах, на столько мм от длинной стенки (между угловым винтом и проводом)
    # --- кнопка питания PBS-101G1 (с фиксацией, ON-OFF) в верхней стенке, у торца напротив USB ---
    # Внутри там свободно: плата короче корпуса, а перед перегородкой — 10 мм по глубине.
    pwr_hole=7.2,        # отверстие под резьбу; если у вашей кнопки резьба толще — рассверлите
    pwr_x=13.0,          # центр от наружного торца напротив USB
    pwr_body=10.0,       # место под корпус кнопки внутри (Ø), проверяется в make.py
    pwr_depth=17.0,      # корпус кнопки уходит внутрь на столько мм
    # --- выключатель SS12D00 на торце x = 0 под плёнкой skin (вместо него теперь PBS-101G1) ---
    sw_window=False,
    skin=0.6,
    sw_w=7.0,
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
    d["il"] = max(p["boss"] + 0.4 + p["wire_room"] + nest_l + p["cable_gap"], p["board_l"] + 2 * p["clear"] + p["guide_t"] + p["boss"])
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
    d["nx0"] = w + b + 0.4 + p["wire_room"]              # гнездо — от торца напротив USB, у USB — место под провод
    d["nx1"] = d["nx0"] + nest_l
    lx0, lx1 = d["nx0"] - 1.5, d["nx1"] + 1.5          # стойки крышки: у стенок гнезда, мимо головок угловых винтов
    d["lid_screws"] = [(lx0, ly), (lx1, ly), (lx0, d["ow"] - ly), (lx1, d["ow"] - ly)]
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
    wx = bx1 - p["win_from_usb"]                                         # окно — по центру стекла дисплея
    H.append((wx - p["win_l"] / 2, ow / 2 - p["win_w"] / 2, -1, wx + p["win_l"] / 2, ow / 2 + p["win_w"] / 2, ft + 1))
    uz = ft + p["usb_from_glass"]                                        # USB-C, торец x = max
    usb_hole = (ol - w - 0.5, ow / 2 - p["usb_w"] / 2, uz - p["usb_h"] / 2, ol + 1, ow / 2 + p["usb_w"] / 2, uz + p["usb_h"] / 2)
    r_usb = p["usb_h"] / 2 - 0.01                                         # капсула: полукруглые концы
    usb = dict(profile=_round_rect(ow / 2 - p["usb_w"] / 2, uz - p["usb_h"] / 2, ow / 2 + p["usb_w"] / 2,
                                   uz + p["usb_h"] / 2, r_usb, n=10),
               x0=ol - w - 0.5, x1=ol + 0.5, chamfer=p["usb_chamfer"], box=usb_hole, face="max")
    wz = (ft + zd0) / 2                                                  # провод: торец напротив USB, отсек платы
    r_w = p["wire_d"] / 2
    wire = dict(profile=_circle(ow / 2, wz, r_w, n=36), x0=-0.5, x1=w + 0.5, chamfer=p["wire_chamfer"],
                box=(-0.5, ow / 2 - r_w, wz - r_w, w + 0.5, ow / 2 + r_w, wz + r_w), face="min")
    d["wire_hole"] = wire["box"]
    tw, tl, s_, tt = p["tongue_w"], p["tongue_l"], p["slot"], p["tongue_t"]
    nubs, tongues = [], []
    # толкатели RST (по умолчанию — только в верхней стенке): язычок вдоль стенки, корень — к середине
    rxk, rzk = bx1 - p["rst_from_usb"], ft + p["rst_from_glass"]
    x_free, x_root = rxk + 2.0, rxk + 2.0 - tl
    for side in p["rst_sides"]:
        if side > 0:
            yi, yo, ythin0, ythin1 = ow - w - 0.5, ow + 1, ow - w - 0.01, ow - tt
            tip = by1 + p["rst_protrude"] + p["press_gap"]
            nb = (rxk - p["nub"] / 2, tip, rzk - p["nub"] / 2, rxk + p["nub"] / 2, ow - tt, rzk + p["nub"] / 2)
        else:
            yi, yo, ythin0, ythin1 = -1, w + 0.5, tt, w + 0.01
            tip = by0 - p["rst_protrude"] - p["press_gap"]
            nb = (rxk - p["nub"] / 2, tt, rzk - p["nub"] / 2, rxk + p["nub"] / 2, tip, rzk + p["nub"] / 2)
        H.append((x_root, yi, rzk - tw / 2 - s_, x_free + s_, yo, rzk - tw / 2))
        H.append((x_root, yi, rzk + tw / 2, x_free + s_, yo, rzk + tw / 2 + s_))
        H.append((x_free, yi, rzk - tw / 2 - s_, x_free + s_, yo, rzk + tw / 2 + s_))
        H.append((x_root, ythin0, rzk - tw / 2, x_free, ythin1, rzk + tw / 2))   # язычок тоньше стенки
        nubs.append(nb)
    d["rst_tongue"] = (x_root, rzk - tw / 2, x_free, rzk + tw / 2)
    k = p["skin"]                                                        # окно под выключатель: снаружи остаётся skin
    sz = (zd1 + oh) / 2
    sw_hole = (k, ow / 2 - p["sw_w"] / 2, sz - p["sw_h"] / 2, w + 0.5, ow / 2 + p["sw_w"] / 2, sz + p["sw_h"] / 2)
    if p["sw_window"]:
        H.append(sw_hole)
    # кнопка питания: круглое отверстие в верхней стенке, корпус кнопки — в пустом углу перед перегородкой
    pz = (ft + zd0) / 2
    d["pwr"] = dict(x=p["pwr_x"], z=pz, body=(p["pwr_x"] - p["pwr_body"] / 2, ow - w - p["pwr_depth"], pz - p["pwr_body"] / 2,
                                                p["pwr_x"] + p["pwr_body"] / 2, ow - w, pz + p["pwr_body"] / 2))
    # толкатели BOOT и KEY в лице: U-образная прорезь, язычок тоньше панели, корень — к длинной стенке
    kx = bx1 - p["btn_from_usb"]
    for side in p["btn_sides"]:
        ky = ow / 2 + side * p["btn_dy"]
        y_free = ky - side * 2.5
        y_root = y_free + side * tl
        ya, yb = min(y_free, y_root), max(y_free, y_root)
        ys0, ys1 = (ya, yb + s_) if side < 0 else (ya - s_, yb)
        H.append((kx - tw / 2 - s_, ys0, -1, kx - tw / 2, ys1, ft + 1))
        H.append((kx + tw / 2, ys0, -1, kx + tw / 2 + s_, ys1, ft + 1))
        yf0 = y_free if side < 0 else y_free - s_
        H.append((kx - tw / 2 - s_, yf0, -1, kx + tw / 2 + s_, yf0 + s_, ft + 1))
        H.append((kx - tw / 2, ya, tt, kx + tw / 2, yb, ft + 0.01))     # язычок тоньше
        nubs.append((kx - p["nub"] / 2, ky - p["nub"] / 2, tt, kx + p["nub"] / 2, ky + p["nub"] / 2,
                     ft + p["btn_depth"] - p["press_gap"]))
        tongues.append((kx - tw / 2, ya, kx + tw / 2, yb))
    d["tongue"] = tongues[0]
    d["tongues"] = tongues
    for sx, sy in d["screws"]:                                           # колонны под винты — до перегородки
        I.append((sx - b / 2, sy - b / 2, ft, sx + b / 2, sy + b / 2, zd0))
        C.append((sx, sy, zd0 - p["pilot_depth"], zd0 + 0.1, p["pilot_d"]))
    for xc in (ol / 2 - 12, ol / 2 + 12):                                # упоры под середину перегородки
        for ya_, yb_ in ((w, w + p["post_w"]), (w + iw - p["post_w"], w + iw)):
            I.append((xc - p["post_len"] / 2, ya_, ft, xc + p["post_len"] / 2, yb_, zd0))
    gt, gh, c = p["guide_t"], p["guide_h"], p["clear"]
    for a, z in p["guide_spans"]:                                        # рёбра по бокам платы — мимо кнопки RST
        xa, xb = bx1 - z, bx1 - a
        I.append((xa, by0 - c - gt, ft, xb, by0 - c, ft + gh))
        I.append((xa, by1 + c, ft, xb, by1 + c + gt, ft + gh))
    I.append((bx0 - c - gt, by0, ft, bx0 - c, by1, ft + gh))             # упор с торца напротив USB
    I += nubs
    d["nubs"] = nubs
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
        recut = [sw_hole] if p["sw_window"] else []                     # щёки закрыли бы окно выключателя
        d["support"] = dict(front=(y_front, 0), tip=(y_tip, z_tip))
    lx0 = w + 0.5                                                         # логотип — между стенкой и фаской окна
    lx1 = wx - p["win_l"] / 2 - 1.0
    d["logo_at"] = ((lx0 + lx1) / 2, ow / 2)
    logo = dict(shapes=logo_shapes(d["logo_at"][0], ow / 2, p["logo_mm"]), depth=p["logo_depth"])
    deco = [dict(y=yy, depth=p["deco_depth"], shapes=deco_shapes(ol / 2, dep / 2, p)) for yy in (0.0, ow)]
    side_holes = [dict(y=ow, depth=w + 0.5, shapes=[[_circle(p["pwr_x"], pz, p["pwr_hole"] / 2, n=36)]])]   # сквозь стенку
    parts["shell"] = dict(solids=S, holes=H, inner=I, cyl_holes=C, prisms=P, recut=recut, logo=logo, deco=deco, ports=[usb, wire] if p["wire_in_end"] else [usb],
                          side_holes=side_holes)

    # ---------- перегородка: гнездо аккумулятора, стойки под винты ----------
    g = p["divider_gap"]
    S = [(w + g, w + g, zd0, w + il - g, w + iw - g, zd1)]
    for a, z in p["pad_spans"]:                                          # площадки прижимают край платы
        S.append((bx1 - z, by0 + 0.1, zbb, bx1 - a, by0 + 0.1 + p["pad_w"], zd0))
        S.append((bx1 - z, by1 - 0.1 - p["pad_w"], zbb, bx1 - a, by1 - 0.1, zd0))
    nx0, ny0 = d["nx0"], ow / 2 - d["nest_w"] / 2                        # гнездо аккумулятора
    nx1, ny1, ft_, fh = d["nx1"], ny0 + d["nest_w"], p["frame_t"], zd1 + p["frame_h"]
    st = p["frame_stub"]
    S += [(nx0, ny0, zd1, nx1, ny0 + ft_, fh), (nx0, ny1 - ft_, zd1, nx1, ny1, fh),
          (nx0, ny0, zd1, nx0 + ft_, ny1, fh),                           # глухой торец — напротив USB
          (nx1 - ft_, ny0, zd1, nx1, ny0 + st, fh), (nx1 - ft_, ny1 - st, zd1, nx1, ny1, fh)]   # у USB — только уголки
    for sx, sy in d["lid_screws"]:                                       # стойки под винты крышки
        S.append((sx - b / 2, sy - b / 2, zd1, sx + b / 2, sy + b / 2, oh))
    H = [(nx1 + 0.4, ow / 2 - p["cable_w"] / 2, zd0 - 1, w + il - g - 0.6, ow / 2 + p["cable_w"] / 2, zd1 + 1)]   # провод вниз — к разъёму у USB
    wx_ = nx0 - 0.6 - p["frame_t"] / 2                                   # провод сквозь перегородку у торца напротив USB
    H.append((wx_ - p["wire_d"] / 2, ow / 2 - p["wire_d"] / 2, zd1 - 0.1, wx_ + p["wire_d"] / 2,
              ow / 2 + p["wire_d"] / 2, fh + 1))                         # и вырез в торцевой стенке гнезда над ним
    C = [(sx, sy, zd0 - 1, zd1 + 1, p["screw_d"]) for sx, sy in d["screws"]]        # винты в колонны корпуса
    C.append((wx_, ow / 2, zd0 - 1, zd1 + 1, p["wire_d"]))
    d["div_wire"] = (wx_, ow / 2)
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
