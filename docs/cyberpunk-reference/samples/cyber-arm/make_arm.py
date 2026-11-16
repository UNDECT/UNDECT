"""사이버웨어 팔 시범 모델 (자체 디자인, 절차 생성).
실행: python make_arm.py <출력폴더> [closed|open|all]
좌표: X = 팔꿈치→손끝, Y = 왼쪽(엄지 쪽), Z = 위(손등 쪽). 단위 m.
"""
import bpy, bmesh, math, sys, os
from math import radians, pi, sin, cos
from mathutils import Matrix, Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
MODE = sys.argv[2] if len(sys.argv) > 2 else "all"
QUALITY = int(os.environ.get("ARM_SAMPLES", "96"))

# ---------------------------------------------------------------- 재질
def _nodes(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    return m, nt, b

def mat_simple(name, base, metallic, rough, emit=None, strength=0.0):
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m

def _noise(nt, scale, stretch=(1, 1, 1), detail=4.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = stretch
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    return nz

def _ramp(nt, src, lo, hi, a=0.0, b=1.0):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi
    mr.inputs["To Min"].default_value = a; mr.inputs["To Max"].default_value = b
    nt.links.new(src, mr.inputs["Value"]); return mr.outputs["Result"]

def _bump(nt, b, height_src, strength, dist=0.0004):
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = dist
    nt.links.new(height_src, bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

def mat_metal(name, base, r_lo, r_hi, brushed=True):
    """결이 있는 금속: 길이 방향으로 늘린 노이즈가 거칠기와 미세 요철을 만든다."""
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Metallic"].default_value = 1.0
    nz = _noise(nt, 90.0, (0.03, 1, 1) if brushed else (1, 1, 1))
    nt.links.new(_ramp(nt, nz.outputs["Fac"], 0.3, 0.7, r_lo, r_hi), b.inputs["Roughness"])
    big = _noise(nt, 6.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Fac"].default_value = 0.35
    mix.inputs["Color1"].default_value = (*base, 1)
    nt.links.new(big.outputs["Color"], mix.inputs["Color2"]); nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    _bump(nt, b, nz.outputs["Fac"], 0.15)
    return m

def mat_paint(name, color, metal=(0.62, 0.60, 0.57)):
    """도장: 모서리와 긁힌 자리에서 칠이 벗겨져 금속이 드러난다."""
    m, nt, b = _nodes(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    edge = _ramp(nt, geo.outputs["Pointiness"], 0.60, 0.68)
    nz = _noise(nt, 45.0, (0.25, 1, 1), 6.0)
    chips = _ramp(nt, nz.outputs["Fac"], 0.70, 0.76)
    scr = _noise(nt, 220.0, (0.015, 1, 1), 2.0)
    scratch = _ramp(nt, scr.outputs["Fac"], 0.74, 0.78)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(edge, mx.inputs[0]); nt.links.new(chips, mx.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 0.6
    nt.links.new(scratch, mul.inputs[0])
    mx2 = nt.nodes.new("ShaderNodeMath"); mx2.operation = "MAXIMUM"
    nt.links.new(mx.outputs[0], mx2.inputs[0]); nt.links.new(mul.outputs[0], mx2.inputs[1])
    wear = mx2.outputs[0]
    col = nt.nodes.new("ShaderNodeMixRGB")
    col.inputs["Color1"].default_value = (*color, 1); col.inputs["Color2"].default_value = (*metal, 1)
    nt.links.new(wear, col.inputs["Fac"]); nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(wear, b.inputs["Metallic"])
    dirt = _noise(nt, 14.0)
    rr = nt.nodes.new("ShaderNodeMath"); rr.operation = "SUBTRACT"
    nt.links.new(_ramp(nt, dirt.outputs["Fac"], 0.3, 0.7, 0.36, 0.58), rr.inputs[0])
    sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "MULTIPLY"; sub.inputs[1].default_value = 0.2
    nt.links.new(wear, sub.inputs[0]); nt.links.new(sub.outputs[0], rr.inputs[1])
    nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    _bump(nt, b, nz.outputs["Fac"], 0.08)
    return m

def mat_fiber(name):
    """장갑 사이로 보이는 인공 근육 다발."""
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (0.018, 0.018, 0.022, 1)
    b.inputs["Roughness"].default_value = 0.42; b.inputs["Metallic"].default_value = 0.0
    nz = _noise(nt, 160.0, (0.01, 1, 1), 2.0)
    _bump(nt, b, nz.outputs["Fac"], 1.0, 0.0012)
    return m

M = {}
def build_materials():
    M["titan"] = mat_metal("titanium", (0.56, 0.55, 0.53), 0.22, 0.42)
    M["dark"] = mat_metal("dark_anodized", (0.035, 0.036, 0.042), 0.28, 0.45, brushed=False)
    M["chrome"] = mat_simple("chrome", (0.92, 0.92, 0.93), 1.0, 0.07)
    M["paint"] = mat_paint("paint_accent", (0.86, 0.11, 0.008))
    M["graph"] = mat_paint("paint_graphite", (0.045, 0.048, 0.055), (0.5, 0.5, 0.5))
    M["rubber"] = mat_simple("rubber", (0.012, 0.012, 0.013), 0.0, 0.72)
    M["fiber"] = mat_fiber("synthetic_muscle")
    M["glow"] = mat_simple("emissive_cyan", (0, 0, 0), 0.0, 0.4, (0.05, 0.85, 1.0), 14.0)
    M["glow_hot"] = mat_simple("emissive_edge", (0, 0, 0), 0.0, 0.4, (0.35, 0.95, 1.0), 30.0)
    M["cable_o"] = mat_simple("cable_orange", (0.65, 0.16, 0.02), 0.0, 0.5)
    M["steel"] = mat_metal("blade_steel", (0.30, 0.31, 0.33), 0.12, 0.26)

# ---------------------------------------------------------------- 형상 도구
COL = None
PARTS = {}

def finish(name, bm, mat, bevel=0.0010, segs=2, Mx=None, group=None):
    if Mx is not None: bm.transform(Mx)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); COL.objects.link(ob); me.materials.append(M[mat])
    if bevel:
        md = ob.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = segs
        md.limit_method = "ANGLE"; md.angle_limit = radians(38)
    wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = False
    if group: PARTS.setdefault(group, []).append(ob)
    return ob

def bm_box(sx, sy, sz, x0=False, taper=1.0, taper_z=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        hi = v.co.x > 0
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        if hi: v.co.y *= taper; v.co.z *= (taper if taper_z is None else taper_z)
        if x0: v.co.x += sx / 2
    return bm

def bm_cyl(r1, r2, L, segs=28, axis="x", x0=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=L)
    if axis == "x": bm.transform(Matrix.Rotation(pi / 2, 4, "Y"))
    elif axis == "y": bm.transform(Matrix.Rotation(-pi / 2, 4, "X"))
    if x0: bm.transform(Matrix.Translation((L / 2, 0, 0)))
    return bm

def bm_sphere(r, sx=1, sy=1, sz=1):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r)
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    return bm

def bm_torus(R, r, seg=36, tube=12, axis="x"):
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * pi * i / seg; ring = []
        for j in range(tube):
            t = 2 * pi * j / tube; rr = R + r * cos(t)
            ring.append(bm.verts.new((r * sin(t), rr * cos(a), rr * sin(a))))
        rings.append(ring)
    for i in range(seg):
        for j in range(tube):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % tube], rings[i][(j + 1) % tube]))
    if axis == "y": bm.transform(Matrix.Rotation(pi / 2, 4, "Z"))
    return bm

def prof(x):
    """전완 단면 반지름 (가로 ry, 세로 rz). 팔꿈치 쪽이 굵고 손목 쪽이 납작하다."""
    s = min(1.0, max(0.0, (x - 0.02) / 0.24))
    ry = 0.049 - 0.017 * s + 0.006 * sin(pi * min(1.0, s * 1.5))
    rz = ry * (0.94 - 0.16 * s)
    return ry, rz

def surf(x, a_deg, off=0.0):
    ry, rz = prof(x); a = radians(a_deg)
    return Vector((x, (ry + off) * cos(a), (rz + off) * sin(a)))

def bm_panel(x0, x1, a0, a1, off, thick, nx=14, na=10):
    bm = bmesh.new(); o = []; n = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx; ro = []; rn = []
        for j in range(na + 1):
            a = a0 + (a1 - a0) * j / na
            ro.append(bm.verts.new(surf(x, a, off))); rn.append(bm.verts.new(surf(x, a, off - thick)))
        o.append(ro); n.append(rn)
    for i in range(nx):
        for j in range(na):
            bm.faces.new((o[i][j], o[i + 1][j], o[i + 1][j + 1], o[i][j + 1]))
            bm.faces.new((n[i][j], n[i][j + 1], n[i + 1][j + 1], n[i + 1][j]))
    for i in range(nx):
        bm.faces.new((o[i][0], n[i][0], n[i + 1][0], o[i + 1][0]))
        bm.faces.new((o[i][na], o[i + 1][na], n[i + 1][na], n[i][na]))
    for j in range(na):
        bm.faces.new((o[0][j], o[0][j + 1], n[0][j + 1], n[0][j]))
        bm.faces.new((o[nx][j], n[nx][j], n[nx][j + 1], o[nx][j + 1]))
    return bm

def bm_tube(x0, x1, off, nx=26, na=40):
    bm = bmesh.new(); rings = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        rings.append([bm.verts.new(surf(x, 360.0 * j / na, off)) for j in range(na)])
    for i in range(nx):
        for j in range(na):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % na], rings[i][(j + 1) % na]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[nx])
    return bm

def align_z(n):
    return Vector((0, 0, 1)).rotation_difference(Vector(n).normalized()).to_matrix().to_4x4()

def bolt(x, a, off, r=0.0022, group=None, mat="chrome"):
    p = surf(x, a, off); ar = radians(a)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r, depth=0.0024)
    finish("bolt", bm, mat, 0.0003, 1, Matrix.Translation(p) @ align_z((0, cos(ar), sin(ar))), group)

def curve_cable(name, pts, radius, mat):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 4
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.resolution_u = 16
    ob = bpy.data.objects.new(name, cu); COL.objects.link(ob); cu.materials.append(M[mat]); return ob

RY = lambda d: Matrix.Rotation(radians(d), 4, "Y")
RZ = lambda d: Matrix.Rotation(radians(d), 4, "Z")
RX = lambda d: Matrix.Rotation(radians(d), 4, "X")
T = lambda x, y, z: Matrix.Translation((x, y, z))

# ---------------------------------------------------------------- 조립
def build_forearm(open_blade):
    finish("core_muscle", bm_tube(0.012, 0.262, -0.0035), "fiber", 0)
    # 등쪽 장갑 4장 (칼날이 나올 때 양옆으로 열리는 문)
    doors = []
    for side, (a0, a1) in (("L", (94.5, 150.0)), ("R", (30.0, 85.5))):
        for seg, (x0, x1, off, mat) in (("rear", (0.030, 0.128, 0.0075, "titan")), ("front", (0.133, 0.238, 0.0050, "paint"))):
            ob = finish(f"dorsal_{seg}_{side}", bm_panel(x0, x1, a0, a1, off, 0.0045), mat, 0.0012, 3, group=f"door_{side}")
            hinge_a = a1 if side == "L" else a0
            doors.append((ob, side, x0, x1, hinge_a, off))
            # 덧댄 2겹 판
            ia0, ia1 = (a0 + 9, a1 - 12) if side == "L" else (a0 + 12, a1 - 9)
            finish(f"dorsal_{seg}_{side}_inlay", bm_panel(x0 + 0.014, x1 - 0.014, ia0, ia1, off + 0.0018, 0.0022, 8, 6),
                   "graph" if mat == "paint" else "dark", 0.0006, 2, group=f"door_{side}")
            for bx in (x0 + 0.007, x1 - 0.007):
                for ba in (a0 + 4, a1 - 4):
                    bolt(bx, ba, off, group=f"door_{side}")
    # 옆 장갑 + 방열 슬릿
    for side, (a0, a1), ca in (("L", (156.0, 204.0), 180.0), ("R", (-24.0, 24.0), 0.0)):
        finish(f"side_{side}", bm_panel(0.042, 0.150, a0, a1, 0.0048, 0.004), "graph", 0.0010, 3)
        for k in range(6):
            x = 0.066 + k * 0.0125; p = surf(x, ca, 0.0052)
            finish("vent", bm_box(0.0055, 0.0030, 0.024), "dark", 0.0005, 1, T(*p) @ RX(8 if side == "L" else -8))
        for bx in (0.049, 0.143):
            for ba in (a0 + 4, a1 - 4): bolt(bx, ba, 0.0048)
        # 유압 피스톤: 옆 장갑 앞에서 손목 고리까지
        y = 1 if side == "R" else -1
        p0 = Vector((0.150, y * 0.036, -0.004)); p1 = Vector((0.262, y * 0.031, -0.003)); d = p1 - p0
        Mx = Matrix.Translation(p0) @ Vector((1, 0, 0)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        finish("piston_sleeve", bm_cyl(0.0072, 0.0072, 0.062, 20, "x", True), "dark", 0.0006, 2, Mx)
        finish("piston_collar", bm_cyl(0.0088, 0.0088, 0.008, 20, "x", True), "titan", 0.0006, 2, Mx @ T(0.056, 0, 0))
        finish("piston_rod", bm_cyl(0.0038, 0.0038, d.length - 0.06, 16, "x", True), "chrome", 0, 1, Mx @ T(0.06, 0, 0))
        finish("piston_eye", bm_cyl(0.0062, 0.0062, 0.009, 16, "y"), "titan", 0.0005, 1, T(*p1))
    # 배쪽 장갑
    for a0, a1 in ((212.0, 264.0), (276.0, 328.0)):
        finish("ventral", bm_panel(0.050, 0.215, a0, a1, 0.0040, 0.004), "graph", 0.0010, 3)
    # 등쪽 이음매 발광선 (닫힌 상태에서 장갑 사이로 새어 나오는 빛)
    finish("seam_glow", bm_panel(0.034, 0.236, 87.0, 93.0, 0.0030, 0.0015, 14, 2), "glow", 0)
    # 손목 쪽 띠
    finish("wrist_band", bm_panel(0.240, 0.258, 0.0, 359.9, 0.0030, 0.0040, 2, 40), "titan", 0.0008, 2)
    for a in (60, 90, 120):
        p = surf(0.249, a, 0.0034)
        finish("wrist_led", bm_box(0.008, 0.0035, 0.0012), "glow", 0, 1, T(*p) @ RX(a - 90))
    # 식별 표기가 붙는 구동기 덮개
    hp = surf(0.090, 180.0, 0.0085)
    finish("actuator_housing", bm_box(0.060, 0.007, 0.030), "titan", 0.0014, 3, T(*hp))
    txt = bpy.data.curves.new("label", "FONT"); txt.body = "KR-07 // 044"; txt.size = 0.0058; txt.extrude = 0.00015
    txt.align_x = "CENTER"; txt.align_y = "CENTER"
    to = bpy.data.objects.new("label", txt); COL.objects.link(to); txt.materials.append(M["titan"])
    la = 57.0; lp = surf(0.079, la, 0.0075 + 0.0020); n = Vector((0, cos(radians(la)), sin(radians(la))))
    Xt = Vector((-1, 0, 0)); Yt = n.cross(Xt).normalized(); Lm = Matrix.Identity(4)
    for i, ax in enumerate((Xt, Yt, n)):
        for r in range(3): Lm[r][i] = ax[r]
    for r in range(3): Lm[r][3] = lp[r]
    to.matrix_world = Lm; PARTS.setdefault("door_R", []).append(to)
    return doors

def open_doors(doors):
    done = set()
    for ob, side, x0, x1, ha, off in doors:
        if side in done: continue
        done.add(side)
        p0 = surf(0.030, ha, 0.004); p1 = surf(0.238, ha, 0.004); ax = (p1 - p0).normalized()
        ang = radians(56) * (1 if side == "L" else -1)
        Rm = Matrix.Translation(p0) @ Matrix.Rotation(ang, 4, ax) @ Matrix.Translation(-p0)
        for o in PARTS[f"door_{side}"]: o.matrix_world = Rm @ o.matrix_world

def dorsal_frame():
    """등쪽 중심선에 맞춘 좌표계 (X = 팔 방향, Z = 표면 바깥)."""
    p0 = surf(0.034, 90.0, 0.0); p1 = surf(0.238, 90.0, 0.0)
    X = (p1 - p0).normalized(); Y = Vector((0, 1, 0)); Z = X.cross(Y).normalized()
    Mx = Matrix.Identity(4)
    for i, ax in enumerate((X, Y, Z)):
        for r in range(3): Mx[r][i] = ax[r]
    for r in range(3): Mx[r][3] = p0[r]
    return Mx

def build_blade(open_blade):
    # 칼날 받침과 레일: 장갑 문 아래에 숨어 있다가 문이 열리면 보인다
    finish("blade_carriage", bm_panel(0.036, 0.236, 62.0, 118.0, 0.0002, 0.0030, 14, 8), "dark", 0.0006, 2)
    for a in (70.0, 110.0):
        finish("blade_rail", bm_panel(0.038, 0.234, a - 2.5, a + 2.5, 0.0016, 0.0016, 14, 2), "chrome", 0.0004, 1)
    if not open_blade: return
    D = dorsal_frame(); Bx = D @ T(0.040, 0, 0.0125)
    def blade_plate(name, pts, th, mat, z=0.0, bev=0.0016):
        bm = bmesh.new(); top = [bm.verts.new((x, y, th / 2)) for x, y in pts]; bot = [bm.verts.new((x, y, -th / 2)) for x, y in pts]
        bm.faces.new(top); bm.faces.new(bot[::-1]); n = len(pts)
        for i in range(n): bm.faces.new((top[i], bot[i], bot[(i + 1) % n], top[(i + 1) % n]))
        return finish(name, bm, mat, bev, 2, Bx @ T(0, 0, z), "blade")
    # 칼집(받침 슬리브): 칼날이 여기서 미끄러져 나온다
    finish("blade_sleeve", bm_box(0.215, 0.040, 0.0105, True, 0.92, 0.9), "dark", 0.0020, 3, Bx, "blade")
    finish("blade_sleeve_top", bm_box(0.150, 0.022, 0.0020, True, 0.9, 1.0), "titan", 0.0008, 2, Bx @ T(0.030, 0.002, 0.0060), "blade")
    for y in (-0.0208, 0.0208):
        finish("blade_sleeve_glow", bm_box(0.170, 0.0012, 0.0022, True), "glow", 0, 1, Bx @ T(0.022, y, 0.0), "blade")
    finish("blade_collar", bm_box(0.026, 0.046, 0.0135, True), "titan", 0.0018, 3, Bx @ T(0.196, 0, 0), "blade")
    for x in (0.024, 0.090, 0.156):
        finish("blade_pin", bm_cyl(0.0034, 0.0034, 0.0022, 6, "z"), "chrome", 0.0003, 1, Bx @ T(x, -0.013, 0.0058), "blade")
    # 칼날: 날 쪽으로 얇아지는 단면 (P = 날 끝선, Q = 두꺼운 등 부분)
    th = 0.0056
    P = [(0.205, -0.0235), (0.500, -0.0235), (0.605, 0.0190), (0.585, 0.0212), (0.205, 0.0212)]
    Q = [(0.205, -0.0115), (0.486, -0.0115), (0.574, 0.0182), (0.570, 0.0196), (0.205, 0.0196)]
    bm = bmesh.new(); n = len(P)
    pv = [bm.verts.new((x, y, 0)) for x, y in P]
    qt = [bm.verts.new((x, y, th / 2)) for x, y in Q]; qb = [bm.verts.new((x, y, -th / 2)) for x, y in Q]
    bm.faces.new(qt); bm.faces.new(qb[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((qt[i], pv[i], pv[j], qt[j])); bm.faces.new((qb[i], qb[j], pv[j], pv[i]))
    finish("blade_main", bm, "steel", 0, 1, Bx @ T(0, 0, 0.0005), "blade")
    blade_plate("blade_fuller", [(0.228, -0.0030), (0.470, -0.0030), (0.515, 0.0125), (0.228, 0.0125)], 0.0012, "dark", 0.0005 + th / 2, 0.0004)
    # 날 가장자리 발광선
    e = 0.0011
    blade_plate("blade_edge", [(0.222, -0.0235 - e), (0.5005, -0.0235 - e), (0.6065, 0.0190), (0.605, 0.0190 + e), (0.4995, -0.0235 + e * 0.2), (0.222, -0.0235 + e * 0.2)], 0.0010, "glow_hot", 0.0005, 0)
    finish("blade_lock", bm_box(0.020, 0.052, 0.012), "titan", 0.0014, 3, D @ T(0.214, 0, 0.0085), "blade")

def build_elbow():
    finish("elbow_hinge", bm_cyl(0.039, 0.039, 0.094, 40, "y"), "titan", 0.0016, 3)
    for y in (-1, 1):
        finish("elbow_cap", bm_cyl(0.030, 0.027, 0.008, 36, "y"), "dark", 0.0012, 2, T(0, y * 0.050, 0))
        finish("elbow_cap_core", bm_cyl(0.011, 0.011, 0.012, 24, "y"), "chrome", 0.0008, 2, T(0, y * 0.052, 0))
        for k in range(8):
            a = 2 * pi * k / 8
            bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0026, radius2=0.0026, depth=0.003)
            finish("elbow_bolt", bm, "chrome", 0.0003, 1, T(0.021 * cos(a), y * 0.0545, 0.021 * sin(a)) @ align_z((0, y, 0)))
        finish("clevis", bm_box(0.070, 0.006, 0.050, True, 0.9, 0.72), "dark", 0.0016, 3, T(-0.006, y * 0.0445, 0))
    U = RY(-28)
    for k in range(5):
        finish("bellows", bm_torus(0.044 + 0.0012 * k, 0.0062, 40, 10), "rubber", 0, 1, U @ T(-0.042 - k * 0.0115, 0, 0))
    finish("upper_cuff", bm_cyl(0.054, 0.051, 0.075, 40, "x"), "graph", 0.0018, 3, U @ T(-0.138, 0, 0))
    finish("upper_ring", bm_cyl(0.056, 0.056, 0.010, 40, "x"), "titan", 0.0012, 2, U @ T(-0.104, 0, 0))
    finish("upper_glow", bm_cyl(0.0548, 0.0548, 0.0030, 40, "x"), "glow", 0, 1, U @ T(-0.150, 0, 0))
    finish("upper_end", bm_cyl(0.049, 0.045, 0.012, 40, "x"), "dark", 0.0012, 2, U @ T(-0.181, 0, 0))
    finish("upper_socket", bm_cyl(0.030, 0.030, 0.010, 32, "x"), "chrome", 0.0010, 2, U @ T(-0.190, 0, 0))
    # 팔꿈치를 넘어가는 케이블
    for i, (y, mat, r) in enumerate(((0.020, "rubber", 0.0036), (0.006, "cable_o", 0.0028), (-0.010, "rubber", 0.0036), (-0.023, "rubber", 0.0026))):
        a = U @ Vector((-0.100, y, 0.056)); b = U @ Vector((-0.050, y * 1.05, 0.060))
        pts = [a, b, Vector((0.000, y * 1.1, 0.048 + 0.003 * (i % 2))), Vector((0.022, y * 0.9, 0.047)), Vector((0.036, y * 0.7, 0.040))]
        curve_cable("cable", pts, r, mat)

def build_hand():
    H = T(0.268, 0, 0) @ RY(7)
    finish("wrist_ball", bm_sphere(0.023, 1, 1.15, 0.85), "dark", 0, 1, H @ T(0.006, 0, -0.001))
    finish("wrist_ring", bm_torus(0.0245, 0.0048, 36, 10), "titan", 0, 1, H @ T(0.012, 0, -0.001) @ Matrix.Diagonal((1, 1.2, 0.86, 1)))
    P = H @ T(0.022, 0, -0.002)
    finish("palm", bm_box(0.088, 0.078, 0.027, True, 1.06, 0.82), "dark", 0.0030, 3, P)
    finish("palm_pad", bm_box(0.060, 0.062, 0.006, True), "rubber", 0.0020, 2, P @ T(0.016, -0.002, -0.0135))
    finish("hand_plate", bm_box(0.064, 0.066, 0.0060, True, 1.05, 1.0), "paint", 0.0016, 3, P @ T(0.010, 0, 0.0150))
    finish("hand_plate_inlay", bm_box(0.034, 0.040, 0.0030, True), "graph", 0.0008, 2, P @ T(0.022, 0, 0.0185))
    for yy in (-0.027, 0.027):
        for xx in (0.016, 0.068):
            bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0022, radius2=0.0022, depth=0.0024)
            finish("hand_bolt", bm, "chrome", 0.0003, 1, P @ T(xx, yy, 0.0185))
    finish("knuckle_glow", bm_box(0.0030, 0.058, 0.0020), "glow", 0, 1, P @ T(0.081, 0, 0.0160))
    # 손가락: (y 위치, 폭, 마디 길이 3개, 굽힘 3개)
    fingers = [(0.0295, 0.0168, (0.046, 0.027, 0.022), (14, 22, 14)),
               (0.0098, 0.0176, (0.051, 0.031, 0.024), (17, 26, 16)),
               (-0.0100, 0.0168, (0.047, 0.029, 0.023), (21, 30, 18)),
               (-0.0292, 0.0148, (0.037, 0.022, 0.020), (25, 33, 20))]
    for fi, (y, w, lens, curls) in enumerate(fingers):
        Mx = P @ T(0.090, y, -0.001) @ RZ((1.5 - fi) * 2.2)
        finger_chain(Mx, w, lens, curls, f"finger{fi}")
    # 엄지
    Mx = P @ T(0.020, 0.042, -0.004) @ RZ(36) @ RX(-62)
    finish("thumb_base", bm_sphere(0.0125, 1.3, 1, 1), "dark", 0, 1, Mx @ T(-0.004, 0, 0))
    finger_chain(Mx, 0.0190, (0.040, 0.031, 0.025), (2, 12, 10), "thumb")

def finger_chain(Mx, w, lens, curls, name):
    for i, (L, c) in enumerate(zip(lens, curls)):
        Mx = Mx @ RY(c)
        wi = w * (1.0 - 0.07 * i); h = wi * 0.86
        finish(f"{name}_joint{i}", bm_cyl(h * 0.56, h * 0.56, wi * 1.06, 20, "y"), "titan", 0.0006, 2, Mx)
        finish(f"{name}_pin{i}", bm_cyl(h * 0.22, h * 0.22, wi * 1.16, 12, "y"), "chrome", 0.0003, 1, Mx)
        finish(f"{name}_seg{i}", bm_box(L - h * 0.55, wi * 0.90, h, True, 0.93, 0.93), "dark", 0.0018, 3, Mx @ T(h * 0.30, 0, 0))
        finish(f"{name}_plate{i}", bm_box((L - h * 0.55) * 0.80, wi * 0.80, 0.0030, True, 0.94, 1.0),
               "titan" if i else "paint", 0.0009, 2, Mx @ T(h * 0.42, 0, h * 0.5 + 0.0006))
        if i == len(lens) - 1:
            finish(f"{name}_tip", bm_sphere(h * 0.50, 1.25, 0.92, 0.95), "rubber", 0, 1, Mx @ T(L - h * 0.20, 0, -h * 0.04))
        Mx = Mx @ T(L, 0, 0)

# ---------------------------------------------------------------- 장면
def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def build_stage():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.008, 1)
    floor = bpy.data.meshes.new("floor"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0); bm.to_mesh(floor); bm.free()
    fo = bpy.data.objects.new("floor", floor); COL.objects.link(fo); fo.location = (0, 0, -0.150)
    fm = mat_simple("floor", (0.006, 0.0065, 0.008), 0.0, 0.58); floor.materials.append(fm)
    # 받침대
    finish("stand_base", bm_cyl(0.075, 0.068, 0.012, 48, "z"), "dark", 0.0020, 3, T(0.11, 0, -0.144))
    finish("stand_rod", bm_cyl(0.007, 0.007, 0.096, 20, "z"), "chrome", 0, 1, T(0.11, 0, -0.092))
    finish("stand_cradle", bm_box(0.060, 0.050, 0.008), "dark", 0.0020, 3, T(0.11, 0, -0.046))
    def area(name, loc, target, size, power, color, sy=None):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = power; ld.color = color; ld.size = size
        if sy: ld.shape = "RECTANGLE"; ld.size_y = sy
        lo = bpy.data.objects.new(name, ld); COL.objects.link(lo); lo.location = loc; look_at(lo, target); return lo
    c = (0.17, 0, 0.0)
    area("key", (0.55, 0.75, 0.85), c, 0.7, 26, (1.0, 0.93, 0.85))
    area("top_strip", (0.15, -0.25, 0.95), c, 1.6, 9, (0.85, 0.93, 1.0), 0.14)
    area("rim_cyan", (-0.55, -0.80, 0.35), c, 0.6, 30, (0.15, 0.80, 1.0))
    area("fill_magenta", (0.85, -0.55, 0.05), c, 0.5, 3.5, (1.0, 0.15, 0.55))
    area("front_low", (0.95, 0.30, -0.02), c, 0.4, 3, (1.0, 0.75, 0.55))

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = QUALITY
    sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
    sc.render.resolution_x = 1600; sc.render.resolution_y = 1000; sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception as e: print("look:", e)

def shot(name, loc, target, lens=70, res=None, dof=None):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.01
    co = bpy.data.objects.new(name, cd); COL.objects.link(co); co.location = loc; look_at(co, target)
    if dof:
        cd.dof.use_dof = True; cd.dof.focus_distance = (Vector(target) - Vector(loc)).length; cd.dof.aperture_fstop = dof
    sc.camera = co
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000

def stats():
    dg = bpy.context.evaluated_depsgraph_get(); tris = 0; n = 0
    for ob in COL.objects:
        if ob.type not in ("MESH", "CURVE", "FONT") or ob.name == "floor" or ob.name.startswith("stand"): continue
        ev = ob.evaluated_get(dg)
        try: me = ev.to_mesh()
        except Exception: continue
        me.calc_loop_triangles(); tris += len(me.loop_triangles); n += 1; ev.to_mesh_clear()
    return n, tris

def build(open_blade):
    global COL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; COL = sc.collection; PARTS.clear(); M.clear()
    build_materials(); setup_render(); build_stage()
    doors = build_forearm(False); build_blade(open_blade); build_elbow(); build_hand()
    if open_blade: open_doors(doors)

if MODE in ("closed", "all"):
    build(False)
    n, t = stats(); print(f"STATS closed objects={n} tris={t}")
    shot("arm_closed_34", (0.80, 0.78, 0.42), (0.14, 0.0, -0.01), 62, dof=11)
    if MODE == "all":
        shot("arm_closed_hand", (0.66, 0.36, 0.20), (0.335, 0.0, -0.015), 90, dof=5.6)
        shot("arm_closed_side", (0.15, 1.30, 0.06), (0.15, 0.0, -0.02), 85)
        try:
            bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "cyber_arm_closed.glb"), export_apply=True)
        except Exception as e: print("gltf:", e)
if MODE in ("open", "all"):
    build(True)
    n, t = stats(); print(f"STATS open objects={n} tris={t}")
    shot("arm_blade_34", (1.15, 1.00, 0.60), (0.25, 0.0, -0.005), 50, dof=11)
    if MODE == "all":
        shot("arm_blade_detail", (0.46, 0.44, 0.40), (0.17, 0.0, 0.03), 75, dof=6.3)
