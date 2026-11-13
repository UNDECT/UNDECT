"""공용 도구: 재질, 기본 형상, 부품·관절 기록, 스튜디오 조명, 렌더, 내보내기.
모든 에셋 스크립트가 이 파일을 쓴다. 실행 환경: `pip install bpy` (Blender 5.x 모듈) 또는 Blender 내장 파이썬.
단위는 m. 캐릭터와 차량은 -Y를 바라본다(Blender 관례). Z가 위.
"""
import bpy, bmesh, json, os, random
from math import radians, pi, sin, cos
from mathutils import Matrix, Vector

M = {}          # 재질 이름 -> Material
PARTS = {}      # 부품 이름 -> [오브젝트...]  (게임에서 따로 움직이는 단위)
PIVOTS = {}     # 관절 이름 -> {"pos": [x,y,z], "axis": [x,y,z], "parent": 부품, "child": 부품, "range": [lo,hi]}
COL = None
SAMPLES = int(os.environ.get("KIT_SAMPLES", "80"))
RES = (1400, 875)

RX = lambda d: Matrix.Rotation(radians(d), 4, "X")
RY = lambda d: Matrix.Rotation(radians(d), 4, "Y")
RZ = lambda d: Matrix.Rotation(radians(d), 4, "Z")
T = lambda x, y, z: Matrix.Translation((x, y, z))
S = lambda x, y, z: Matrix.Diagonal((x, y, z, 1))

def frame(X, Z, origin=(0, 0, 0)):
    """X축과 Z축 방향으로 좌표계 행렬을 만든다 (Y = Z x X)."""
    X = Vector(X).normalized(); Z = Vector(Z).normalized(); Y = Z.cross(X).normalized(); Z = X.cross(Y).normalized()
    m = Matrix.Identity(4)
    for i, ax in enumerate((X, Y, Z)):
        for r in range(3): m[r][i] = ax[r]
    for r in range(3): m[r][3] = origin[r]
    return m

# ------------------------------------------------------------------ 재질
def _nodes(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]

def _noise(nt, scale, stretch=(1, 1, 1), detail=4.0, coord="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coord], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    return nz

def _ramp(nt, src, lo, hi, a=0.0, b=1.0):
    mr = nt.nodes.new("ShaderNodeMapRange")
    for k, v in (("From Min", lo), ("From Max", hi), ("To Min", a), ("To Max", b)): mr.inputs[k].default_value = v
    nt.links.new(src, mr.inputs["Value"]); return mr.outputs["Result"]

def _math(nt, op, a, b):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def _bump(nt, b, src, strength, dist=0.0004):
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    nt.links.new(src, bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

def mat_simple(key, base, metallic=0.0, rough=0.5, emit=None, strength=0.0, alpha=1.0):
    m, nt, b = _nodes(key)
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Metallic"].default_value = metallic; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0: b.inputs["Alpha"].default_value = alpha
    M[key] = m; return m

def mat_metal(key, base, r_lo, r_hi, brushed=True, scale=90.0):
    m, nt, b = _nodes(key)
    b.inputs["Metallic"].default_value = 1.0
    nz = _noise(nt, scale, (0.03, 1, 1) if brushed else (1, 1, 1))
    nt.links.new(_ramp(nt, nz.outputs["Fac"], 0.3, 0.7, r_lo, r_hi), b.inputs["Roughness"])
    big = _noise(nt, scale / 15.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Fac"].default_value = 0.35
    mix.inputs["Color1"].default_value = (*base, 1)
    nt.links.new(big.outputs["Color"], mix.inputs["Color2"]); nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    _bump(nt, b, nz.outputs["Fac"], 0.15)
    M[key] = m; return m

def mat_paint(key, color, metal=(0.6, 0.6, 0.58), rough=(0.34, 0.56), wear=1.0, scale=1.0):
    """도장 금속: 모서리·흠집에서 칠이 벗겨지고, 큰 얼룩이 거칠기를 바꾼다. scale은 물체 크기(작은 부품 1, 차·로봇 0.25)."""
    m, nt, b = _nodes(key)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    edge = _ramp(nt, geo.outputs["Pointiness"], 0.58, 0.66)
    chips = _ramp(nt, _noise(nt, 45.0 * scale, (0.25, 1, 1), 6.0).outputs["Fac"], 0.70 - 0.04 * (wear - 1), 0.76)
    scratch = _ramp(nt, _noise(nt, 220.0 * scale, (0.015, 1, 1), 2.0).outputs["Fac"], 0.74, 0.78)
    w = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", edge, chips), _math(nt, "MULTIPLY", scratch, 0.6))
    w = _math(nt, "MULTIPLY", w, min(1.0, wear))
    col = nt.nodes.new("ShaderNodeMixRGB"); col.inputs["Color1"].default_value = (*color, 1); col.inputs["Color2"].default_value = (*metal, 1)
    # 때: 큰 노이즈로 색을 조금 어둡게
    grime = nt.nodes.new("ShaderNodeMixRGB"); grime.blend_type = "MULTIPLY"; grime.inputs["Color2"].default_value = (0.55, 0.52, 0.48, 1)
    nt.links.new(_ramp(nt, _noise(nt, 9.0 * scale, detail=6.0).outputs["Fac"], 0.45, 0.75, 0.0, 0.55), grime.inputs["Fac"])
    nt.links.new(w, col.inputs["Fac"]); nt.links.new(col.outputs["Color"], grime.inputs["Color1"])
    nt.links.new(grime.outputs["Color"], b.inputs["Base Color"]); nt.links.new(w, b.inputs["Metallic"])
    r = _math(nt, "SUBTRACT", _ramp(nt, _noise(nt, 14.0 * scale).outputs["Fac"], 0.3, 0.7, rough[0], rough[1]), _math(nt, "MULTIPLY", w, 0.2))
    nt.links.new(r, b.inputs["Roughness"])
    _bump(nt, b, _noise(nt, 60.0 * scale).outputs["Fac"], 0.06)
    M[key] = m; return m

def mat_fiber(key, color=(0.018, 0.018, 0.022)):
    m, nt, b = _nodes(key)
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = 0.42
    _bump(nt, b, _noise(nt, 160.0, (0.01, 1, 1), 2.0).outputs["Fac"], 1.0, 0.0012)
    M[key] = m; return m

def mat_concrete(key, color=(0.30, 0.29, 0.27), scale=1.0):
    """콘크리트: 큰 물자국과 얼룩, 거친 표면."""
    m, nt, b = _nodes(key)
    big = _noise(nt, 0.35 * scale, (1, 1, 0.25), 8.0); fine = _noise(nt, 18.0 * scale, detail=8.0)
    c = nt.nodes.new("ShaderNodeMixRGB"); c.inputs["Color1"].default_value = (*color, 1)
    c.inputs["Color2"].default_value = (color[0] * 0.42, color[1] * 0.42, color[2] * 0.44, 1)
    nt.links.new(_ramp(nt, big.outputs["Fac"], 0.42, 0.68), c.inputs["Fac"])
    c2 = nt.nodes.new("ShaderNodeMixRGB"); c2.blend_type = "MULTIPLY"; c2.inputs["Fac"].default_value = 0.5
    nt.links.new(c.outputs["Color"], c2.inputs["Color1"]); nt.links.new(fine.outputs["Color"], c2.inputs["Color2"])
    nt.links.new(c2.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(_ramp(nt, big.outputs["Fac"], 0.3, 0.7, 0.9, 0.6), b.inputs["Roughness"])
    _bump(nt, b, fine.outputs["Fac"], 0.5, 0.01)
    M[key] = m; return m

def mat_wet_asphalt(key):
    """젖은 아스팔트: 물웅덩이는 거울처럼, 나머지는 거칠게."""
    m, nt, b = _nodes(key)
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.014, 1)
    pud = _ramp(nt, _noise(nt, 0.22, detail=5.0).outputs["Fac"], 0.47, 0.56)
    nt.links.new(_ramp(nt, pud, 0.0, 1.0, 0.42, 0.015), b.inputs["Roughness"])
    grain = _noise(nt, 55.0, detail=6.0)
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Distance"].default_value = 0.004
    nt.links.new(_ramp(nt, pud, 0.0, 1.0, 0.7, 0.0), bp.inputs["Strength"]); nt.links.new(grain.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    M[key] = m; return m

def mat_windows(key, wall=(0.035, 0.035, 0.04), lit=(1.0, 0.62, 0.30), lit2=(0.45, 0.75, 1.0), ratio=0.3, cell=(3.2, 3.4), strength=6.0):
    """멀리 있는 건물용: 형상 없이 벽에 창문 불빛 격자를 그린다 (축에 나란한 벽 전용)."""
    m, nt, b = _nodes(key)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    u = _math(nt, "ADD", sep.outputs["X"], sep.outputs["Y"])
    cu = _math(nt, "FLOOR", _math(nt, "DIVIDE", u, cell[0]), 0.0); cv = _math(nt, "FLOOR", _math(nt, "DIVIDE", sep.outputs["Z"], cell[1]), 0.0)
    fu = _math(nt, "FRACT", _math(nt, "DIVIDE", u, cell[0]), 0.0); fv = _math(nt, "FRACT", _math(nt, "DIVIDE", sep.outputs["Z"], cell[1]), 0.0)
    comb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(cu, comb.inputs[0]); nt.links.new(cv, comb.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"; nt.links.new(comb.outputs[0], wn.inputs["Vector"])
    on = _math(nt, "LESS_THAN", wn.outputs["Value"], ratio)
    inu = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", fu, 0.14), _math(nt, "LESS_THAN", fu, 0.86))
    inv = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", fv, 0.30), _math(nt, "LESS_THAN", fv, 0.80))
    mask = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", inu, inv), on)
    pick = nt.nodes.new("ShaderNodeMixRGB"); pick.inputs["Color1"].default_value = (*lit, 1); pick.inputs["Color2"].default_value = (*lit2, 1)
    nt.links.new(_math(nt, "GREATER_THAN", wn.outputs["Color"], 0.72), pick.inputs["Fac"])
    b.inputs["Base Color"].default_value = (*wall, 1); b.inputs["Roughness"].default_value = 0.6
    nt.links.new(pick.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(_math(nt, "MULTIPLY", mask, _ramp(nt, wn.outputs["Value"], 0.0, ratio, strength * 0.25, strength)), b.inputs["Emission Strength"])
    M[key] = m; return m

def base_materials():
    mat_metal("titan", (0.56, 0.55, 0.53), 0.22, 0.42)
    mat_metal("dark", (0.035, 0.036, 0.042), 0.28, 0.45, brushed=False)
    mat_metal("steel", (0.30, 0.31, 0.33), 0.14, 0.30)
    mat_metal("gunmetal", (0.11, 0.115, 0.125), 0.30, 0.50, brushed=False)
    mat_simple("chrome", (0.92, 0.92, 0.93), 1.0, 0.07)
    mat_simple("rubber", (0.012, 0.012, 0.013), 0.0, 0.72)
    mat_simple("glass", (0.008, 0.012, 0.016), 0.0, 0.03)
    mat_simple("black", (0.004, 0.004, 0.005), 0.0, 0.55)
    mat_fiber("fiber")
    mat_simple("glow_cyan", (0, 0, 0), 0, 0.4, (0.05, 0.85, 1.0), 14.0)
    mat_simple("glow_white", (0, 0, 0), 0, 0.4, (1.0, 0.96, 0.9), 18.0)
    mat_simple("glow_red", (0, 0, 0), 0, 0.4, (1.0, 0.03, 0.02), 14.0)
    mat_simple("glow_amber", (0, 0, 0), 0, 0.4, (1.0, 0.45, 0.05), 12.0)
    mat_simple("glow_magenta", (0, 0, 0), 0, 0.4, (1.0, 0.05, 0.45), 12.0)

# ------------------------------------------------------------------ 형상
def finish(name, bm, mat, bevel=0.001, segs=2, Mx=None, part=None, smooth=True):
    if Mx is not None: bm.transform(Mx)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); COL.objects.link(ob); me.materials.append(M[mat])
    if bevel:
        md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = segs; md.limit_method = "ANGLE"; md.angle_limit = radians(38)
    if smooth:
        wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = False
    if part:
        ob["part"] = part; PARTS.setdefault(part, []).append(ob)
    return ob

def box(sx, sy, sz, x0=False, taper=1.0, taper_z=None, z0=False):
    """상자. x0: 원점이 -X 면 중심, z0: 원점이 바닥 중심. taper: +X 쪽 끝을 좁힌다."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        hi = v.co.x > 0
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        if hi: v.co.y *= taper; v.co.z *= (taper if taper_z is None else taper_z)
        if x0: v.co.x += sx / 2
        if z0: v.co.z += sz / 2
    return bm

def cyl(r1, r2, L, segs=28, axis="x", x0=False):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=L)
    if axis == "x": bm.transform(Matrix.Rotation(pi / 2, 4, "Y"))
    elif axis == "y": bm.transform(Matrix.Rotation(-pi / 2, 4, "X"))
    if x0: bm.transform(Matrix.Translation((L / 2, 0, 0) if axis == "x" else (0, L / 2, 0) if axis == "y" else (0, 0, L / 2)))
    return bm

def sphere(r, sx=1, sy=1, sz=1, u=24, v=14):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    for p in bm.verts: p.co.x *= sx; p.co.y *= sy; p.co.z *= sz
    return bm

def torus(R, r, seg=36, tube=10, axis="x"):
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * pi * i / seg
        rings.append([bm.verts.new((r * sin(2 * pi * j / tube), (R + r * cos(2 * pi * j / tube)) * cos(a), (R + r * cos(2 * pi * j / tube)) * sin(a))) for j in range(tube)])
    for i in range(seg):
        for j in range(tube):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % tube], rings[i][(j + 1) % tube]))
    if axis == "y": bm.transform(Matrix.Rotation(pi / 2, 4, "Z"))
    elif axis == "z": bm.transform(Matrix.Rotation(-pi / 2, 4, "Y"))
    return bm

def prism(pts, depth, axis="y"):
    """XZ 평면의 다각형(pts = [(x,z),...])을 Y 방향으로 depth만큼 민 기둥 (중심 정렬)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]; b = [bm.verts.new((x, depth / 2, z)) for x, z in pts]
    bm.faces.new(a); bm.faces.new(b[::-1]); n = len(pts)
    for i in range(n): bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    if axis == "x": bm.transform(Matrix.Rotation(pi / 2, 4, "Z"))
    elif axis == "z": bm.transform(Matrix.Rotation(pi / 2, 4, "X"))
    return bm

def loft(rings, cap=True):
    """같은 점 개수의 단면 고리들을 이어 껍질을 만든다."""
    bm = bmesh.new(); vs = [[bm.verts.new(p) for p in ring] for ring in rings]; n = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(n):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % n], vs[i][(j + 1) % n]))
    if cap: bm.faces.new(vs[0][::-1]); bm.faces.new(vs[-1])
    return bm

def shell(prof, x0, x1, a0, a1, off, thick, nx=12, na=10):
    """X축을 감싸는 굽은 장갑판. prof(x) -> (ry, rz), 각도 90도가 +Z."""
    def pt(x, a, o):
        ry, rz = prof(x); return Vector((x, (ry + o) * cos(radians(a)), (rz + o) * sin(radians(a))))
    bm = bmesh.new(); o = []; n = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        o.append([bm.verts.new(pt(x, a0 + (a1 - a0) * j / na, off)) for j in range(na + 1)])
        n.append([bm.verts.new(pt(x, a0 + (a1 - a0) * j / na, off - thick)) for j in range(na + 1)])
    for i in range(nx):
        for j in range(na):
            bm.faces.new((o[i][j], o[i + 1][j], o[i + 1][j + 1], o[i][j + 1])); bm.faces.new((n[i][j], n[i][j + 1], n[i + 1][j + 1], n[i + 1][j]))
        bm.faces.new((o[i][0], n[i][0], n[i + 1][0], o[i + 1][0])); bm.faces.new((o[i][na], o[i + 1][na], n[i + 1][na], n[i][na]))
    for j in range(na):
        bm.faces.new((o[0][j], o[0][j + 1], n[0][j + 1], n[0][j])); bm.faces.new((o[nx][j], n[nx][j], n[nx][j + 1], o[nx][j + 1]))
    return bm

def tube(prof, x0, x1, off=0.0, nx=16, na=32):
    rings = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx; ry, rz = prof(x)
        rings.append([(x, (ry + off) * cos(2 * pi * j / na), (rz + off) * sin(2 * pi * j / na)) for j in range(na)])
    return loft(rings)

def bolt(Mx, r=0.004, mat="chrome", part=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r, depth=r * 1.1)
    return finish("bolt", bm, mat, r * 0.12, 1, Mx, part)

def cable(name, pts, radius, mat, part=None):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 3; cu.resolution_u = 12
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu); COL.objects.link(ob); cu.materials.append(M[mat])
    if part: ob["part"] = part; PARTS.setdefault(part, []).append(ob)
    return ob

def text(name, body, size, Mx, mat, part=None, extrude=0.0004):
    cu = bpy.data.curves.new(name, "FONT"); cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu); COL.objects.link(ob); cu.materials.append(M[mat]); ob.matrix_world = Mx
    if part: ob["part"] = part; PARTS.setdefault(part, []).append(ob)
    return ob

def pivot(name, pos, axis, parent, child, rng=(-90, 90)):
    """관절 기록. 게임에서 뼈를 달 때 이 위치와 축을 쓴다."""
    PIVOTS[name] = {"pos": [round(c, 4) for c in pos], "axis": [round(c, 4) for c in axis], "parent": parent, "child": child, "range": list(rng)}
    e = bpy.data.objects.new("pivot_" + name, None); e.empty_display_size = 0.05; e.location = pos; COL.objects.link(e); e["pivot"] = name
    return e

# ------------------------------------------------------------------ 장면
def reset():
    global COL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    COL = bpy.context.scene.collection; M.clear(); PARTS.clear(); PIVOTS.clear(); base_materials()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.image_settings.file_format = "PNG"
    try: sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception as e: print("look:", e)
    return sc

def look_at(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()

def area(name, loc, target, size, power, color, sy=None):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = power; ld.color = color; ld.size = size
    if sy: ld.shape = "RECTANGLE"; ld.size_y = sy
    lo = bpy.data.objects.new(name, ld); COL.objects.link(lo); lo.location = loc; look_at(lo, target); return lo

def studio(center, scale=1.0, floor_z=0.0, top=1.0):
    """에셋 촬영용 어두운 스튜디오. scale = 대상 크기(m) 기준 배율."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.008, 1)
    me = bpy.data.meshes.new("floor"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30.0 * scale); bm.to_mesh(me); bm.free()
    fo = bpy.data.objects.new("stage_floor", me); COL.objects.link(fo); fo.location = (0, 0, floor_z)
    me.materials.append(mat_simple("stage_floor", (0.0035, 0.0038, 0.0045), 0.0, 0.6))
    c = Vector(center); k = scale; p = k * k
    area("key", c + Vector((-2.2 * k, -3.0 * k, 2.6 * k)), c, 2.2 * k, 420 * p, (1.0, 0.94, 0.86))
    area("top", c + Vector((0, 0.3 * k, 3.6 * k)), c, 5.0 * k, 160 * p * top, (0.85, 0.93, 1.0), 0.5 * k)
    area("rim_cyan", c + Vector((2.6 * k, 2.6 * k, 1.8 * k)), c, 1.8 * k, 380 * p, (0.15, 0.8, 1.0))
    area("fill_magenta", c + Vector((3.0 * k, -2.0 * k, 0.3 * k)), c, 1.6 * k, 60 * p, (1.0, 0.15, 0.55))

def shot(path, loc, target, lens=60, dof=None, res=None):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.clip_start = 0.01; cd.clip_end = 5000
    co = bpy.data.objects.new("cam", cd); COL.objects.link(co); co.location = loc; look_at(co, target)
    if dof: cd.dof.use_dof = True; cd.dof.focus_distance = (Vector(target) - Vector(loc)).length; cd.dof.aperture_fstop = dof
    sc.camera = co
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    sc.render.resolution_x, sc.render.resolution_y = RES
    bpy.data.objects.remove(co)

def asset_objects():
    return [o for o in COL.objects if o.type in ("MESH", "CURVE", "FONT") and not o.name.startswith("stage_")]

def stats():
    dg = bpy.context.evaluated_depsgraph_get(); tris = 0; per = {}
    for ob in asset_objects():
        ev = ob.evaluated_get(dg)
        try: me = ev.to_mesh()
        except Exception: continue
        me.calc_loop_triangles(); n = len(me.loop_triangles); tris += n
        per[ob.get("part", "_static")] = per.get(ob.get("part", "_static"), 0) + n; ev.to_mesh_clear()
    return tris, per

def export(out_dir, name, extra=None):
    """GLB + .blend + manifest.json (부품, 관절, 삼각형 수, 재질 목록)."""
    os.makedirs(out_dir, exist_ok=True)
    tris, per = stats()
    man = {"name": name, "units": "m", "forward": "-Y", "up": "+Z", "triangles": tris, "triangles_by_part": per,
           "parts": {k: [o.name for o in v] for k, v in PARTS.items()}, "pivots": PIVOTS,
           "materials": sorted({s.material.name for o in asset_objects() for s in o.material_slots if s.material})}
    if extra: man.update(extra)
    json.dump(man, open(os.path.join(out_dir, name + ".manifest.json"), "w"), indent=1, ensure_ascii=False)
    for o in bpy.context.scene.objects: o.select_set(o in asset_objects() or o.name.startswith("pivot_"))
    try: bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, name + ".glb"), export_apply=True, use_selection=True, export_extras=True)
    except Exception as e: print("gltf:", e)
    try: bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(out_dir, name + ".blend")), compress=True)
    except Exception as e: print("blend:", e)
    print(f"EXPORT {name} tris={tris} parts={len(PARTS)} pivots={len(PIVOTS)}")
    return man
