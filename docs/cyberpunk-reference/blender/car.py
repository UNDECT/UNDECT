"""도시형 세단 (자체 디자인, 각진 쐐기형). 실행: python car.py <출력폴더> [render|all] [변형]
변형: crimson(기본), cab(택시: 자체 도색 + 지붕 표시등), corp(흰색 기업 차량), teal, patrol(보안 순찰차: 경광등, 밀대 범퍼)
앞이 -Y. 길이 4.7 m, 폭 1.92 m, 높이 1.30 m. 왼쪽(+X)이 운전석이다.
따로 움직이는 부품: 바퀴 4개, 문 4개(door_FL/FR/RL/RR, 앞 모서리 축으로 열림), 운전대(steering). 실내(좌석, 계기판)는 차체에 붙어 있다.
환경 변수 CAR_DOOR=FL:62,RL:40 처럼 주면 그 문을 연 상태로 만든다(사진용). 내보낼 때는 다 닫는다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, text, pivot, frame, RX, RY, RZ, T, S

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/car"
MODE = sys.argv[2] if len(sys.argv) > 2 else ""
VARIANT = sys.argv[3] if len(sys.argv) > 3 else "crimson"

VARIANTS = {
    "crimson": {"body": (0.42, 0.012, 0.02), "trim": "glow_cyan", "under": "glow_magenta", "roof": None},
    "cab": {"body": (0.86, 0.47, 0.01), "trim": "glow_white", "under": None, "roof": "CAB"},
    "corp": {"body": (0.72, 0.73, 0.75), "trim": "glow_cyan", "under": None, "roof": None},
    "teal": {"body": (0.02, 0.16, 0.17), "trim": "glow_amber", "under": "glow_cyan", "roof": None},
    "patrol": {"body": (0.055, 0.085, 0.14), "trim": "glow_white", "under": None, "roof": "SEC"},
}
DOORS = {"FL": (1, -0.640, 0.400), "FR": (-1, -0.640, 0.400), "RL": (1, 0.420, 1.300), "RR": (-1, 0.420, 1.300)}   # 쪽, 앞 끝 y, 뒤 끝 y
SEATS = {"driver": (0.40, 0.36), "passenger": (-0.40, 0.36), "rear_L": (0.40, 1.26), "rear_R": (-0.40, 1.26)}
OPEN = {k.split(":")[0]: float(k.split(":")[1]) for k in os.environ.get("CAR_DOOR", "").split(",") if ":" in k}
# 단면: (y, 문턱 반폭, 최대 반폭, 지붕 반폭, 바닥 z, 허리선 z, 어깨선 z, 지붕 z)
STATIONS = [
    (-2.35, 0.66, 0.74, 0.58, 0.31, 0.42, 0.50, 0.535),
    (-2.18, 0.87, 0.94, 0.76, 0.22, 0.40, 0.585, 0.635),
    (-1.45, 0.90, 0.96, 0.82, 0.20, 0.43, 0.765, 0.805),
    (-0.72, 0.90, 0.96, 0.82, 0.20, 0.45, 0.845, 0.890),
    (0.08, 0.90, 0.96, 0.61, 0.20, 0.45, 0.86, 1.285),
    (0.98, 0.90, 0.96, 0.61, 0.20, 0.45, 0.88, 1.275),
    (1.80, 0.90, 0.96, 0.76, 0.20, 0.46, 0.90, 0.975),
    (2.24, 0.87, 0.93, 0.74, 0.25, 0.48, 0.86, 0.915),
    (2.35, 0.80, 0.86, 0.68, 0.34, 0.50, 0.79, 0.835),
]
WHEELS = {"FL": (0.805, -1.45), "FR": (-0.805, -1.45), "RL": (0.805, 1.42), "RR": (-0.805, 1.42)}
WR, WW = 0.345, 0.270

def ring(st):
    y, w0, w1, w2, zf, zm, zb, zr = st
    half = [(0, zf), (w0 - 0.08, zf), (w0, zf + 0.09), (w1, zm), (w1 - 0.035, zb), (w2, zr - 0.03), (0, zr)]
    pts = half + [(-x, z) for x, z in half[-2:0:-1]]
    return [(x, y, z) for x, z in pts]

def hull(name, shrink=0.0, y0=-9.0, y1=9.0):
    """차체 껍질 메시. shrink > 0이면 그만큼 안쪽으로 줄인 것(실내 공간, 문 두께를 파낼 때 쓴다)."""
    rings = []
    for st in STATIONS:
        y, w0, w1, w2, zf, zm, zb, zr = st
        if y < y0 or y > y1: continue
        rings.append(ring((y, w0 - shrink, w1 - shrink, w2 - shrink, zf + shrink * 1.2, zm, zb, zr - shrink * 0.7)))
    bm = loft(rings); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); kit.COL.objects.link(ob)
    return ob, me

def cutter(name, bm, Mx=None, mat="black"):
    if Mx is not None: bm.transform(Mx)
    cm = bpy.data.meshes.new(name); bm.to_mesh(cm); bm.free()
    co = bpy.data.objects.new("stage_cut_" + name, cm); kit.COL.objects.link(co); cm.materials.append(kit.M[mat])
    co.hide_render = True; co.display_type = "WIRE"; return co

def boolean(ob, name, other, op="DIFFERENCE"):
    md = ob.modifiers.new(name, "BOOLEAN"); md.operation = op; md.object = other
    try: md.solver = "EXACT"; md.material_mode = "TRANSFER"
    except Exception as e: print("bool:", e)

def skin(ob, me):
    """껍질에 재질(차체, 유리)을 입힌다."""
    n = 12
    for k in ("body", "glass", "black", "trim_in"): me.materials.append(kit.M[k])
    glass = {3: (4, 5, 6, 7), 4: (4, 7), 5: (4, 5, 6, 7)}
    for p in me.polygons:
        p.use_smooth = True; i, j = divmod(p.index, n)
        if i in glass and j in glass[i]: p.material_index = 1

def soften(ob):
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = 0.014; bv.segments = 3; bv.limit_method = "ANGLE"; bv.angle_limit = radians(18)
    wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = False

def door_matrix(name):
    """문을 앞 모서리의 세로축으로 여는 변환."""
    s, y0, y1 = DOORS[name]; h = Vector((0.955 * s, y0 + 0.02, 0.60)); a = OPEN.get(name, 0.0)
    return T(*h) @ RZ(-a * s) @ T(*(-h)), h

def build_body(v):
    kit.mat_paint("body", v["body"], rough=(0.20, 0.36), wear=0.35, scale=0.10)
    kit.mat_paint("body_dark", (0.03, 0.032, 0.036), (0.4, 0.4, 0.4), rough=(0.30, 0.5), wear=0.6, scale=0.12)
    kit.mat_simple("glass", (0.010, 0.016, 0.020), 0.0, 0.03, alpha=0.42)          # 실내가 비쳐 보이는 짙은 유리
    kit.mat_simple("trim_in", (0.020, 0.021, 0.024), 0.0, 0.62); kit.mat_simple("seat", (0.030, 0.012, 0.012), 0.0, 0.55); kit.mat_simple("seat_dark", (0.012, 0.012, 0.014), 0.0, 0.6)
    ob, me = hull("body"); skin(ob, me)
    cabin, cm = hull("stage_cut_cabin", 0.075, -0.80, 1.90); cm.materials.append(kit.M["trim_in"]); cabin.hide_render = True; cabin.display_type = "WIRE"
    arches = {}
    for name, (x, y) in WHEELS.items():   # 바퀴집: 원통으로 파낸다 (파낸 면은 검은색)
        arches[name] = cutter("arch_" + name, cyl(WR + 0.050, WR + 0.050, 0.50, 36, "x"), T(x + (0.10 if x > 0 else -0.10), y, WR)); boolean(ob, "arch_" + name, arches[name])
    boolean(ob, "cabin", cabin)                                                    # 실내 공간
    for name, (sd, y0, y1) in DOORS.items():
        boolean(ob, "hole_" + name, cutter("hole_" + name, box(0.80, y1 - y0, 1.20), T(sd * 0.86, (y0 + y1) / 2, 0.86), "trim_in"))   # 문 구멍
        d, dm = hull("door_" + name); skin(d, dm)
        boolean(d, "slab", cutter("slab_" + name, box(0.80, y1 - y0 - 0.012, 1.188), T(sd * 0.86, (y0 + y1) / 2, 0.86), "trim_in"), "INTERSECT")
        boolean(d, "inner", cabin)                                                 # 문 두께만 남긴다
        if name[0] == "R": boolean(d, "arch", arches["R" + name[1]])
        soften(d); Md, h = door_matrix(name); d.matrix_world = Md
        d["part"] = "door_" + name; kit.PARTS.setdefault("door_" + name, []).append(d)
        pivot("door_" + name, tuple(h), (0, 0, 1), "body", "door_" + name, (0, 65))
        pivot("enter_" + name, (sd * 1.75, (y0 + y1) / 2, 0.0), (-sd, 0, 0), "body", "fx")       # 문 앞에 서는 자리
        pivot("handle_" + name, (sd * 0.955, y1 - 0.11, 0.76), (sd, 0, 0), "door_" + name, "fx")  # 손잡이(문 뒤쪽 끝)
    soften(ob); ob["part"] = "body"; kit.PARTS.setdefault("body", []).append(ob)

def interior(v):
    """실내: 바닥, 좌석 4개, 계기판, 운전대, 가운데 콘솔. 왼쪽(+X)이 운전석."""
    p = "body"
    finish("floor", box(1.66, 2.70, 0.03), "trim_in", 0, 1, T(0, 0.52, 0.275), p); finish("firewall", box(1.60, 0.04, 0.50), "trim_in", 0, 1, T(0, -0.78, 0.52), p)
    finish("rear_shelf", box(1.50, 0.42, 0.03), "trim_in", 0.004, 1, T(0, 1.66, 0.86), p); finish("rear_wall", box(1.56, 0.04, 0.56), "trim_in", 0, 1, T(0, 1.86, 0.56), p)
    finish("dash", box(1.60, 0.34, 0.20), "trim_in", 0.03, 3, T(0, -0.56, 0.80) @ RX(-8), p); finish("dash_top", box(1.62, 0.44, 0.04), "seat_dark", 0.012, 2, T(0, -0.60, 0.905) @ RX(-6), p)
    finish("cluster", box(0.34, 0.012, 0.085), "glow_cyan", 0, 1, T(0.40, -0.392, 0.845) @ RX(-8), "dash_glow")
    finish("screen", box(0.36, 0.014, 0.20), v["trim"], 0, 1, T(0, -0.392, 0.800) @ RX(-8), "dash_glow"); finish("screen_frame", box(0.40, 0.020, 0.24), "black", 0.006, 2, T(0, -0.386, 0.800) @ RX(-8), p)
    finish("dash_line", box(1.50, 0.006, 0.008), v["trim"], 0, 1, T(0, -0.388, 0.705) @ RX(-8), "dash_glow")
    finish("console", box(0.24, 1.10, 0.20), "trim_in", 0.02, 2, T(0, 0.20, 0.39), p); finish("console_top", box(0.20, 0.50, 0.03), "seat_dark", 0.01, 2, T(0, 0.40, 0.50), p)
    finish("shifter", box(0.05, 0.09, 0.07), "titan", 0.012, 2, T(0, -0.02, 0.52), p)
    for name, (x, y) in SEATS.items():
        rear = name.startswith("rear")
        finish("seat_base", box(0.50, 0.50, 0.14), "seat", 0.04, 3, T(x, y, 0.40), p)
        finish("seat_back", box(0.50, 0.13, 0.62), "seat", 0.04, 3, T(x, y + 0.30, 0.74) @ RX(-(10 if rear else 16)), p)
        finish("seat_head", box(0.26, 0.10, 0.18), "seat_dark", 0.03, 3, T(x, y + 0.385, 1.085) @ RX(-10), p)
        for sx in (-1, 1): finish("seat_bolster", box(0.07, 0.44, 0.10), "seat_dark", 0.03, 2, T(x + sx * 0.235, y, 0.455), p)
        finish("seat_stripe", box(0.06, 0.008, 0.46), v["trim"], 0, 1, T(x, y + 0.232, 0.76) @ RX(-(10 if rear else 16)), "dash_glow")
        pivot("seat_" + name, (x, y + 0.02, 0.475), (0, -1, 0), "body", "fx")
    for sx in (-1, 1): finish("pedal", box(0.07, 0.03, 0.10), "titan", 0.004, 1, T(0.40 + sx * 0.09, -0.66, 0.36) @ RX(-30), p)
    # 운전대 (따로 도는 부품)
    Ms = T(0.40, -0.265, 0.775) @ RX(-22)
    finish("wheel_rim", torus(0.165, 0.016, 28, 10, "y"), "seat_dark", 0, 1, Ms, "steering")
    finish("wheel_hub", box(0.11, 0.04, 0.08), "trim_in", 0.02, 3, Ms @ T(0, 0.012, 0), "steering"); finish("wheel_led", box(0.06, 0.004, 0.012), v["trim"], 0, 1, Ms @ T(0, -0.012, 0.02), "steering")
    for a in (90, 210, 330): finish("wheel_spoke", box(0.022, 0.016, 0.15), "titan", 0.004, 1, Ms @ RY(a) @ T(0, 0, 0.085), "steering")
    finish("column", cyl(0.028, 0.028, 0.26, 12, "y"), "trim_in", 0.004, 1, T(0.40, -0.39, 0.725) @ RX(-22), p)
    pivot("steering", tuple(Ms.translation), tuple(Ms.to_3x3() @ Vector((0, 1, 0))), "body", "steering", (-450, 450))
    pivot("hand_L", tuple(Ms @ Vector((0.160, -0.01, 0.045))), (0, 1, 0), "steering", "fx"); pivot("hand_R", tuple(Ms @ Vector((-0.160, -0.01, 0.045))), (0, 1, 0), "steering", "fx")
    pivot("hotwire", (0.40, -0.47, 0.62), (0, 1, 0), "body", "fx")   # 계기판 아래: 시동 따는 자리
    # 문 안쪽 판
    for name, (sd, y0, y1) in DOORS.items():
        Md, h = door_matrix(name)
        finish("door_card", box(0.03, y1 - y0 - 0.10, 0.40), "trim_in", 0.01, 2, Md @ T(sd * 0.845, (y0 + y1) / 2, 0.58), "door_" + name)
        finish("door_rest", box(0.07, (y1 - y0) * 0.6, 0.05), "seat_dark", 0.015, 2, Md @ T(sd * 0.815, (y0 + y1) / 2, 0.66), "door_" + name)
        finish("door_glow", box(0.004, (y1 - y0) * 0.7, 0.008), v["trim"], 0, 1, Md @ T(sd * 0.828, (y0 + y1) / 2, 0.74), "dash_glow")

def details(v):
    p = "body"
    # 앞
    finish("light_bar_f", box(1.26, 0.020, 0.022), v["trim"] if v["trim"] != "glow_amber" else "glow_white", 0, 1, T(0, -2.358, 0.468), p)
    for s in (-1, 1):
        finish("headlamp", box(0.30, 0.030, 0.050), "glow_white", 0, 1, T(0.50 * s, -2.300, 0.535) @ RZ(-16 * s) @ RX(-28), p)
        finish("headlamp_frame", box(0.34, 0.040, 0.075), "black", 0.006, 2, T(0.50 * s, -2.286, 0.532) @ RZ(-16 * s) @ RX(-28), p)
    finish("intake", box(1.18, 0.060, 0.085), "black", 0.006, 2, T(0, -2.330, 0.360), p)
    for k in range(5): finish("intake_fin", box(0.012, 0.070, 0.080), "body_dark", 0.002, 1, T(-0.44 + 0.22 * k, -2.336, 0.360), p)
    finish("splitter", box(1.74, 0.300, 0.030), "body_dark", 0.008, 2, T(0, -2.200, 0.205), p)
    finish("hood_vent", box(0.70, 0.22, 0.012), "black", 0.004, 2, T(0, -1.05, 0.856) @ RX(-7), p)
    for k in range(4): finish("hood_slat", box(0.66, 0.018, 0.012), "body_dark", 0.002, 1, T(0, -1.125 + 0.05 * k, 0.852 + 0.006 * k) @ RX(-30), p)
    # 옆
    for s in (-1, 1):
        finish("skirt", box(0.070, 2.10, 0.085), "body_dark", 0.010, 2, T(0.905 * s, -0.01, 0.228), p)
        for dn, y, L in (("F", -0.12, 1.00), ("R", 0.86, 0.84)):
            nm = dn + ("L" if s > 0 else "R")
            finish("side_line", box(0.006, L, 0.010), v["trim"], 0, 1, door_matrix(nm)[0] @ T(0.9635 * s, y, 0.452), "door_" + nm)
        finish("mirror_stalk", box(0.090, 0.022, 0.016), "body_dark", 0.004, 1, T(0.935 * s, -0.640, 0.862), p)
        finish("mirror_cam", box(0.045, 0.110, 0.042, taper=1.0), "body", 0.010, 3, T(0.990 * s, -0.625, 0.872), p)
        finish("mirror_lens", box(0.030, 0.006, 0.026), "glow_cyan", 0, 1, T(0.990 * s, -0.568, 0.872), p)
        for dn, y in (("F", 0.29), ("R", 1.19)):
            nm = dn + ("L" if s > 0 else "R")
            finish("door_handle", box(0.008, 0.130, 0.020), "black", 0.003, 1, door_matrix(nm)[0] @ T(0.9500 * s, y, 0.760), "door_" + nm)
        finish("intake_side", prism([(0.95, 0.30), (1.22, 0.30), (1.22, 0.52), (1.05, 0.52)], 0.012, "x"), "black", 0.003, 1, T(0.966 * s, 0, 0), p)
        finish("pillar_b", box(0.030, 0.050, 0.42), "black", 0.004, 2, T(0.770 * s, 0.41, 1.07) @ RY(-27 * s), p)
    # 뒤
    finish("light_bar_r", box(1.50, 0.022, 0.034), "glow_red", 0, 1, T(0, 2.357, 0.735), p)
    finish("tail_panel", box(1.56, 0.030, 0.110), "black", 0.006, 2, T(0, 2.345, 0.735), p)
    finish("diffuser", box(1.56, 0.26, 0.105), "body_dark", 0.010, 2, T(0, 2.235, 0.290), p)
    for k in range(6): finish("diffuser_fin", box(0.014, 0.24, 0.085), "black", 0.002, 1, T(-0.55 + 0.22 * k, 2.270, 0.275), p)
    finish("spoiler", box(1.50, 0.16, 0.022), "body_dark", 0.006, 2, T(0, 2.200, 0.935) @ RX(8), p)
    finish("plate", box(0.36, 0.008, 0.095), "titan", 0.003, 1, T(0, 2.3585, 0.560), p)
    text("plate_text", "KX7 0412", 0.052, frame((-1, 0, 0), (0, 1, 0), (0, 2.3635, 0.560)), "black", p)
    # 지붕
    finish("roof_fin", prism([(1.02, 1.270), (1.26, 1.250), (1.26, 1.330), (1.14, 1.345)], 0.016, "x"), "body_dark", 0.004, 2, part=p)
    finish("roof_sensor", box(0.30, 0.34, 0.035), "body_dark", 0.010, 2, T(0, 0.30, 1.298), p)
    finish("roof_sensor_eye", box(0.20, 0.010, 0.014), "glow_cyan", 0, 1, T(0, 0.128, 1.300), p)
    if v["roof"] == "SEC":   # 보안 순찰차: 경광등, 밀대 범퍼, 표기
        finish("bar_base", box(1.10, 0.26, 0.05), "black", 0.012, 2, T(0, 0.52, 1.315), p)
        for k in range(6): finish("bar_cell", box(0.165, 0.22, 0.07), "glow_red" if k < 3 else "glow_cyan", 0.01, 2, T(-0.455 + k * 0.182, 0.52, 1.365), "lightbar_L" if k < 3 else "lightbar_R")
        finish("bar_spot", box(0.10, 0.06, 0.06), "glow_white", 0, 1, T(0, 0.39, 1.36), p)
        for s2 in (-1, 1):
            finish("push_post", box(0.06, 0.10, 0.42), "black", 0.012, 2, T(0.36 * s2, -2.40, 0.46), p)
            text("sec_text", "SECURITY", 0.115, frame((0, s2, 0), (s2, 0, 0), (0.9665 * s2, 0.42, 0.60)), "glow_white", "door_R" + ("L" if s2 > 0 else "R"), 0.002)
            finish("sec_stripe", box(0.006, 3.3, 0.05), "glow_white", 0, 1, T(0.9640 * s2, 0.0, 0.38), p)
        for k in range(3): finish("push_bar", box(0.86, 0.05, 0.05), "black", 0.012, 2, T(0, -2.42, 0.30 + k * 0.16), p)
        text("sec_hood", "07", 0.26, T(0, -1.55, 0.800) @ RX(-6.5), "glow_white", p, 0.002)
    elif v["roof"]:
        finish("cab_sign", box(0.78, 0.20, 0.105), "black", 0.012, 2, T(0, 0.66, 1.345), p)
        finish("cab_sign_face_f", box(0.70, 0.006, 0.070), "glow_amber", 0, 1, T(0, 0.557, 1.348), p)
        finish("cab_sign_face_r", box(0.70, 0.006, 0.070), "glow_amber", 0, 1, T(0, 0.763, 1.348), p)
        text("cab_text", v["roof"], 0.060, frame((1, 0, 0), (0, -1, 0), (0, 0.5525, 1.348)), "black", p)
        for s in (-1, 1):
            for k in range(7):
                if k % 2 == 0: finish("cab_check", box(0.006, 0.11, 0.055), "black", 0, 1, door_matrix("F" + ("L" if s > 0 else "R"))[0] @ T(0.9605 * s, -0.42 + 0.11 * k, 0.61), "door_F" + ("L" if s > 0 else "R"))
    if v["under"]:
        finish("underglow", box(1.50, 3.30, 0.010), v["under"], 0, 1, T(0, 0, 0.175), p)

def wheels():
    for name, (x, y) in WHEELS.items():
        s = 1 if x > 0 else -1; p = "wheel_" + name; Mx = T(x, y, WR)
        finish("tire", cyl(WR, WR, WW, 44, "x"), "rubber", 0.030, 4, Mx, p)
        for k in range(3): finish("tread", torus(WR - 0.004, 0.010, 44, 6, "x"), "black", 0, 1, Mx @ T((k - 1) * 0.075, 0, 0), p)
        finish("rim", cyl(0.250, 0.250, WW + 0.006, 36, "x"), "gunmetal", 0.004, 2, Mx, p)
        finish("aero_cover", cyl(0.238, 0.205, 0.030, 36, "x"), "body_dark", 0.004, 2, Mx @ T(s * (WW / 2 + 0.008), 0, 0) @ (RZ(180) if s < 0 else Matrix.Identity(4)), p)
        finish("hub_ring", torus(0.176, 0.007, 36, 8, "x"), "glow_cyan", 0, 1, Mx @ T(s * (WW / 2 + 0.020), 0, 0), p)
        finish("hub", cyl(0.060, 0.050, 0.030, 20, "x"), "titan", 0.004, 2, Mx @ T(s * (WW / 2 + 0.030), 0, 0) @ (RZ(180) if s < 0 else Matrix.Identity(4)), p)
        for k in range(5):
            a = 2 * pi * k / 5 + 0.3
            finish("cover_slot", box(0.006, 0.030, 0.085), "black", 0.002, 1, Mx @ T(s * (WW / 2 + 0.024), 0, 0) @ RX(k * 72 + 17) @ T(0, 0, 0.130), p)
        finish("brake", cyl(0.200, 0.200, 0.020, 28, "x"), "steel", 0.002, 1, Mx @ T(-s * 0.060, 0, 0), p)
        pivot("wheel_" + name, (x, y, WR), (1, 0, 0), "body", p, (-360, 360))

def build(variant="crimson"):
    kit.reset(); parts(variant)

def parts(variant="crimson"):
    """kit.reset() 없이 부품만 만든다 (다른 장면에 넣을 때 쓴다)."""
    v = VARIANTS[variant]; build_body(v); interior(v); details(v); wheels()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); tag = "" if VARIANT == "crimson" else "_" + VARIANT
    if MODE:
        build(VARIANT); kit.studio((0, 0, 0.6), 2.3, top=0.35, key=0.55)
        kit.shot(os.path.join(OUT, f"car{tag}_front.png"), (-5.2, -7.4, 2.5), (0.0, -0.1, 0.55), 60)
        if MODE == "all":
            kit.shot(os.path.join(OUT, f"car{tag}_rear.png"), (5.0, 7.6, 2.3), (0.0, 0.1, 0.55), 60)
            kit.shot(os.path.join(OUT, f"car{tag}_side.png"), (-11.0, -0.2, 1.0), (0.0, 0.0, 0.62), 85)
            OPEN.update({"FL": 62, "RL": 40}); build(VARIANT); kit.studio((0, 0, 0.6), 2.3, top=0.5, key=0.7)   # 문을 연 모습과 실내
            kit.area("cabin_fill", (2.6, -0.4, 1.6), (0.3, 0.2, 0.7), 1.2, 110, (1.0, 0.95, 0.9))
            kit.shot(os.path.join(OUT, f"car{tag}_doors.png"), (5.6, -5.2, 2.6), (0.5, 0.1, 0.60), 60)
            kit.area("cabin_roof", (0.0, 0.3, 1.20), (0.1, -0.2, 0.6), 0.5, 22, (1.0, 0.96, 0.92))
            kit.shot(os.path.join(OUT, f"car{tag}_interior.png"), (-0.46, 0.52, 1.07), (0.34, -0.55, 0.80), 17)
            OPEN.clear()
    build(VARIANT)   # 내보내는 모델은 문을 다 닫은 상태
    kit.export(OUT, "car" + tag, {"variant": VARIANT, "wheel_radius": WR, "driver_side": "+X (왼쪽)", "seats": list(SEATS), "doors": list(DOORS),
                                  "door_glass": "문 유리는 문 부품의 glass 재질 면이다. 가져올 때 window_FL처럼 따로 나눠 창 깨기에 쓴다."})
