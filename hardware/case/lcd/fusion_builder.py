# ---------------- Fusion 360: построение модели по build() ----------------
# Все детали — телами одного компонента (подходит и для документа «Part Design»).
# Блок — эскиз-прямоугольник на XY, выдавленный от z0 до z1; блоки объединяются, вырезы вычитаются.
# Затем: скругление углов корпуса, фаска окна, круглые отверстия, полозья и упоры, гравировка.
# В конце STL каждой детали сохраняются в папку STL_DIR (или рядом со скриптом).

import os
import traceback

import adsk.core
import adsk.fusion

CM = 0.1                     # Fusion API работает в сантиметрах
CORNER_R = 2.5               # скругление углов корпуса, мм
WINDOW_CHAMFER = 0.8         # фаска окна дисплея снаружи, мм
ENGRAVE = "Agent Status Bar\nprod by yakory777"
ENGRAVE_H, ENGRAVE_DEPTH = 3.4, 0.4
TITLES = {"shell": "Корпус", "divider": "Перегородка", "lid": "Крышка"}
COLORS = {"shell": (217, 119, 87), "divider": (150, 150, 155), "lid": (232, 230, 225)}
STL_DIR = ""                 # куда сохранить STL; пусто — рядом со скриптом (если он запущен из файла)


def _v(mm):
    return adsk.core.ValueInput.createByReal(mm * CM)


def _box(comp, b, name):
    x0, y0, z0, x1, y1, z1 = b
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = name
    sk.isComputeDeferred = True
    sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(x0 * CM, y0 * CM, 0),
                                                     adsk.core.Point3D.create(x1 * CM, y1 * CM, 0))
    sk.isComputeDeferred = False
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    if abs(z0) > 1e-9:
        inp.startExtent = adsk.fusion.OffsetStartDefinition.create(_v(z0))
    inp.setDistanceExtent(False, _v(z1 - z0))
    return ext.add(inp).bodies.item(0)


def _combine(comp, target, tools, op):
    if not tools:
        return
    col = adsk.core.ObjectCollection.create()
    for t in tools:
        col.add(t)
    inp = comp.features.combineFeatures.createInput(target, col)
    inp.operation = op
    inp.isKeepToolBodies = False
    comp.features.combineFeatures.add(inp)


def _part(comp, name, spec):
    J, C = adsk.fusion.FeatureOperations.JoinFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation
    bodies = [_box(comp, b, f"{name} блок {i + 1}") for i, b in enumerate(spec["solids"])]
    holes = [_box(comp, b, f"{name} вырез {i + 1}") for i, b in enumerate(spec.get("holes", []))]
    body = bodies[0]
    _combine(comp, body, bodies[1:], J)
    _combine(comp, body, holes, C)
    inner = [_box(comp, b, f"{name} внутри {i + 1}") for i, b in enumerate(spec.get("inner", []))]
    _combine(comp, body, inner, J)
    return body


def _cyl_holes(comp, body, holes, name):
    """Круглые отверстия (x, y, z0, z1, диаметр) вдоль Z."""
    ext = comp.features.extrudeFeatures
    for i, (x, y, z0, z1, dia) in enumerate(holes):
        sk = comp.sketches.add(comp.xYConstructionPlane)
        sk.name = f"{name} отверстие {i + 1}"
        sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(x * CM, y * CM, 0), dia / 2 * CM)
        inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        inp.startExtent = adsk.fusion.OffsetStartDefinition.create(_v(z0))
        inp.setDistanceExtent(False, _v(z1 - z0))
        inp.participantBodies = [body]
        ext.add(inp)


def _prisms(comp, body, prisms, name):
    """Ножки: профиль (y, z) в плоскости YZ с проёмом, вытянутый по X; углы скругляются, потом присоединяются."""
    ext = comp.features.extrudeFeatures
    made = []
    for i, pr in enumerate(prisms):
        sk = comp.sketches.add(comp.yZConstructionPlane)
        sk.name = f"{name} ножка {i + 1}"
        lines = sk.sketchCurves.sketchLines
        for poly in [pr["profile"]] + list(pr.get("holes") or []):
            pts = [sk.modelToSketchSpace(adsk.core.Point3D.create(0, y * CM, z * CM)) for y, z in poly]
            for j in range(len(pts)):
                lines.addByTwoPoints(pts[j], pts[(j + 1) % len(pts)])
        prof = max((sk.profiles.item(j) for j in range(sk.profiles.count)), key=lambda q: q.profileLoops.count)
        inp = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        if abs(pr["x0"]) > 1e-9:
            inp.startExtent = adsk.fusion.OffsetStartDefinition.create(_v(pr["x0"]))
        inp.setDistanceExtent(False, _v(pr["x1"] - pr["x0"]))
        leg = ext.add(inp).bodies.item(0)
        if pr.get("round"):                            # скругляем углы рамки: рёбра вдоль X
            col = adsk.core.ObjectCollection.create()
            sharp = [(y * CM, z * CM) for y, z in pr.get("keep_sharp", [])]
            for e in leg.edges:
                a, b = e.startVertex.geometry, e.endVertex.geometry
                if abs(a.y - b.y) < 1e-6 and abs(a.z - b.z) < 1e-6:
                    if not any(abs(a.y - sy) < 1e-6 and abs(a.z - sz) < 1e-6 for sy, sz in sharp):
                        col.add(e)
            try:
                fl = comp.features.filletFeatures
                fi = fl.createInput()
                fi.addConstantRadiusEdgeSet(col, _v(pr["round"]), False)
                fl.add(fi)
            except Exception:
                pass
        made.append(leg)
    _combine(comp, body, made, adsk.fusion.FeatureOperations.JoinFeatureOperation)


def _corner_edges(body):
    """Внешние рёбра вдоль Z на углах габарита тела."""
    bb = body.boundingBox
    xs, ys = (bb.minPoint.x, bb.maxPoint.x), (bb.minPoint.y, bb.maxPoint.y)
    col = adsk.core.ObjectCollection.create()
    for e in body.edges:
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if abs(a.x - b.x) > 1e-6 or abs(a.y - b.y) > 1e-6:
            continue
        if any(abs(a.x - x) < 1e-6 for x in xs) and any(abs(a.y - y) < 1e-6 for y in ys):
            col.add(e)
    return col


def _fillet(comp, body, r):
    edges = _corner_edges(body)
    if edges.count == 0:
        return False
    fl = comp.features.filletFeatures
    inp = fl.createInput()
    inp.addConstantRadiusEdgeSet(edges, _v(r), False)
    fl.add(inp)
    return True


def _chamfer_window(comp, body, d, p):
    cx, cy = d["window_center_x"], d["ow"] / 2
    hx, hy = p["win_l"] / 2 + 0.01, p["win_w"] / 2 + 0.01
    col = adsk.core.ObjectCollection.create()
    for e in body.edges:
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if abs(a.z) > 1e-6 or abs(b.z) > 1e-6:
            continue
        if all(abs(q.x / CM - cx) <= hx and abs(q.y / CM - cy) <= hy for q in (a, b)):
            col.add(e)
    if col.count == 0:
        return False
    ch = comp.features.chamferFeatures
    inp = ch.createInput2()
    inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, _v(WINDOW_CHAMFER), False)
    ch.add(inp)
    return True


def _engrave_logo(comp, body, logo):
    """Логотип на лице: каждая фигура — свой эскиз на z = 0, вырез внутрь (+z)."""
    ext = comp.features.extrudeFeatures
    for i, loops in enumerate(logo["shapes"]):
        sk = comp.sketches.add(comp.xYConstructionPlane)
        sk.name = f"логотип {i + 1}"
        sk.isComputeDeferred = True
        lines = sk.sketchCurves.sketchLines
        for poly in loops:
            pts = [adsk.core.Point3D.create(x * CM, y * CM, 0) for x, y in poly]
            for j in range(len(pts)):
                lines.addByTwoPoints(pts[j], pts[(j + 1) % len(pts)])
        sk.isComputeDeferred = False
        prof = max((sk.profiles.item(j) for j in range(sk.profiles.count)), key=lambda q: q.profileLoops.count)
        inp = ext.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        inp.setDistanceExtent(False, _v(logo["depth"]))
        inp.participantBodies = [body]
        ext.add(inp).name = f"логотип {i + 1}"


def _engrave_walls(comp, body, decos):
    """Декоративные прорези на длинных стенках: эскиз в плоскости XZ на y стенки, вырез в обе стороны на depth."""
    ext, planes = comp.features.extrudeFeatures, comp.constructionPlanes
    for k, deco in enumerate(decos):
        pin = planes.createInput()
        pin.setByOffset(comp.xZConstructionPlane, _v(deco["y"]))
        plane = planes.add(pin)
        plane.name = f"стенка {k + 1}"
        sk = comp.sketches.add(plane)
        sk.name = f"прорези {k + 1}"
        sk.isComputeDeferred = True
        lines = sk.sketchCurves.sketchLines
        for loops in deco["shapes"]:
            for poly in loops:
                pts = [sk.modelToSketchSpace(adsk.core.Point3D.create(x * CM, deco["y"] * CM, z * CM)) for x, z in poly]
                for j in range(len(pts)):
                    lines.addByTwoPoints(pts[j], pts[(j + 1) % len(pts)])
        sk.isComputeDeferred = False
        col = adsk.core.ObjectCollection.create()
        for j in range(sk.profiles.count):
            col.add(sk.profiles.item(j))
        inp = ext.createInput(col, adsk.fusion.FeatureOperations.CutFeatureOperation)
        inp.setSymmetricExtent(_v(2 * deco["depth"]), True)
        inp.participantBodies = [body]
        ext.add(inp).name = f"прорези {k + 1}"


def _usb_port(comp, body, usb):
    """Проём в торце (USB-C, провод): контур в плоскости YZ сквозь стенку и фаска по наружному краю."""
    sk = comp.sketches.add(comp.yZConstructionPlane)
    sk.name = "проём в торце"
    sk.isComputeDeferred = True
    lines = sk.sketchCurves.sketchLines
    pts = [sk.modelToSketchSpace(adsk.core.Point3D.create(0, y * CM, z * CM)) for y, z in usb["profile"]]
    for j in range(len(pts)):
        lines.addByTwoPoints(pts[j], pts[(j + 1) % len(pts)])
    sk.isComputeDeferred = False
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(_v(usb["x0"]))
    inp.setDistanceExtent(False, _v(usb["x1"] - usb["x0"]))
    inp.participantBodies = [body]
    ext.add(inp).name = "проём в торце"
    if not usb.get("chamfer"):
        return
    x_out = body.boundingBox.maxPoint.x if usb.get("face", "max") == "max" else body.boundingBox.minPoint.x
    b = usb["box"]
    col = adsk.core.ObjectCollection.create()
    for e in body.edges:                                   # рёбра проёма на наружной стороне торца
        a, c = e.startVertex.geometry if e.startVertex else None, e.endVertex.geometry if e.endVertex else None
        pts_ = [q for q in (a, c) if q is not None] or [e.pointOnEdge]
        if all(abs(q.x - x_out) < 1e-5 and b[1] - 0.1 <= q.y / CM <= b[4] + 0.1 and b[2] - 0.1 <= q.z / CM <= b[5] + 0.1
               for q in pts_):
            col.add(e)
    if col.count:
        ch = comp.features.chamferFeatures
        ci = ch.createInput2()
        ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, _v(usb["chamfer"]), True)
        ch.add(ci)


def _engrave(comp, body, d, p):
    """Надпись на наружной стороне крышки, между винтами."""
    z = d["depth"]
    planes = comp.constructionPlanes
    pin = planes.createInput()
    pin.setByOffset(comp.xYConstructionPlane, _v(z))
    plane = planes.add(pin)
    plane.name = "плоскость гравировки"
    sk = comp.sketches.add(plane)
    sk.name = "гравировка"
    w, h = d["il"] - 2 * p["boss"] - 8, ENGRAVE_H * 3
    c1 = sk.modelToSketchSpace(adsk.core.Point3D.create((d["ol"] / 2 - w / 2) * CM, (d["ow"] / 2 - h / 2) * CM, z * CM))
    c2 = sk.modelToSketchSpace(adsk.core.Point3D.create((d["ol"] / 2 + w / 2) * CM, (d["ow"] / 2 + h / 2) * CM, z * CM))
    ti = sk.sketchTexts.createInput2(ENGRAVE, ENGRAVE_H * CM)
    ti.setAsMultiLine(c1, c2, adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                      adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    txt = sk.sketchTexts.add(ti)
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(txt, adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, _v(-ENGRAVE_DEPTH))
    inp.participantBodies = [body]
    ext.add(inp).name = "гравировка"


def _appearance(des, body, name):
    try:
        lib = adsk.core.Application.get().materialLibraries.itemByName("Fusion Appearance Library")
        base = lib.appearances.itemByName("Plastic - Matte (Yellow)")
        key = f"ASB {name}"
        ap = des.appearances.itemByName(key) or des.appearances.addByCopy(base, key)
        for prop in ap.appearanceProperties:
            if isinstance(prop, adsk.core.ColorProperty) and prop.id in ("opaque_albedo", "generic_diffuse"):
                r, g, b = COLORS[name]
                prop.value = adsk.core.Color.create(r, g, b, 255)
        body.appearance = ap
    except Exception:
        pass


def _export_stl(des, bodies, folder):
    os.makedirs(folder, exist_ok=True)
    em = des.exportManager
    out = []
    for name, body in bodies.items():
        path = os.path.join(folder, f"asb-lcd-{name}.stl")
        opt = em.createSTLExportOptions(body, path)
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        em.execute(opt)
        out.append(path)
    return out


def run(context):
    app = adsk.core.Application.get()
    notes = []
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        des.designType = adsk.fusion.DesignTypes.ParametricDesignType
        tl = des.timeline
        if tl.count:                                   # начисто: прошлая версия модели удаляется
            tl.markerPosition = 0
            tl.deleteAllAfterMarker()
        comp = des.rootComponent
        for pl in list(comp.constructionPlanes):
            pl.deleteMe()
        p = PARAMS
        parts, d = build(p)
        made = {}
        for name in ("shell", "divider", "lid"):
            spec = parts[name]
            body = _part(comp, name, spec)
            if spec.get("prisms"):
                _prisms(comp, body, spec["prisms"], name)
            if spec.get("recut"):                      # проёмы в торцах заново — щёки их закрыли
                _combine(comp, body, [_box(comp, b, f"{name} проём {i + 1}") for i, b in enumerate(spec["recut"])],
                         adsk.fusion.FeatureOperations.CutFeatureOperation)
            for port in spec.get("ports") or []:
                try:
                    _usb_port(comp, body, port)
                except Exception as e:
                    notes.append(f"проём в торце — {e}")
            if name == "shell":
                try:
                    _fillet(comp, body, CORNER_R) or notes.append("углы корпуса не скруглены")
                except Exception as e:
                    notes.append(f"скругление — {e}")
                try:
                    _chamfer_window(comp, body, d, p) or notes.append("фаска окна: рёбра не найдены")
                except Exception as e:
                    notes.append(f"фаска окна — {e}")
                if spec.get("logo"):
                    try:
                        _engrave_logo(comp, body, spec["logo"])
                    except Exception as e:
                        notes.append(f"логотип — {e}")
                if spec.get("deco"):
                    try:
                        _engrave_walls(comp, body, spec["deco"])
                    except Exception as e:
                        notes.append(f"прорези — {e}")
                if spec.get("side_holes"):
                    try:
                        _engrave_walls(comp, body, spec["side_holes"])
                    except Exception as e:
                        notes.append(f"отверстие кнопки питания — {e}")
            if spec.get("cyl_holes"):
                _cyl_holes(comp, body, spec["cyl_holes"], name)
            body.name = TITLES[name]
            made[name] = body
            _appearance(des, body, name)
        try:
            _engrave(comp, made["lid"], d, p)
        except Exception as e:
            notes.append(f"гравировка — {e}")
        app.activeViewport.fit()
        print(f"Корпус {d['ol']:.1f} x {d['ow']:.1f} x {d['depth']:.1f} мм, экран под {p['tilt']:.0f}° к столу")
        for name, b in made.items():
            print(name, "граней", b.faces.count, "объём см³", round(b.volume, 2))
        bad = [i for i in range(tl.count) if tl.item(i).healthState != 0]
        print("шагов истории", tl.count, "с ошибками", len(bad))
        folder = STL_DIR or (os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "")
        if folder:
            for path in _export_stl(des, made, folder):
                print("STL:", path)
        for n in notes:
            print("заметка:", n)
    except Exception:
        print("ОШИБКА:\n" + traceback.format_exc())
