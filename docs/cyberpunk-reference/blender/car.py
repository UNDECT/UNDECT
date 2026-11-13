"""도시형 세단 (자체 디자인, 각진 쐐기형). 실행: python car.py <출력폴더> [render|all] [변형]
변형: crimson(기본), cab(택시: 자체 도색 + 지붕 표시등), corp(흰색 기업 차량), teal
앞이 -Y. 길이 4.7 m, 폭 1.92 m, 높이 1.30 m. 바퀴 4개는 따로 도는 부품이다.
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
}
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

def build_body(v):
    kit.mat_paint("body", v["body"], rough=(0.20, 0.36), wear=0.35, scale=0.10)
    kit.mat_paint("body_dark", (0.03, 0.032, 0.036), (0.4, 0.4, 0.4), rough=(0.30, 0.5), wear=0.6, scale=0.12)
    bm = loft([ring(s) for s in STATIONS]); n = 12
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("body"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("body", me); kit.COL.objects.link(ob)
    for k in ("body", "glass", "black"): me.materials.append(kit.M[k])
    glass = {3: (4, 5, 6, 7), 4: (4, 7), 5: (4, 5, 6, 7)}
    for p in me.polygons:
        p.use_smooth = True; i, j = divmod(p.index, n)
        if i in glass and j in glass[i]: p.material_index = 1
    # 바퀴집: 원통으로 파낸다 (파낸 면은 검은색)
    for name, (x, y) in WHEELS.items():
        cb = cyl(WR + 0.050, WR + 0.050, 0.50, 36, "x"); cm = bpy.data.meshes.new("cut"); cb.to_mesh(cm); cb.free()
        co = bpy.data.objects.new("stage_cut_" + name, cm); kit.COL.objects.link(co); cm.materials.append(kit.M["black"])
        co.location = (x + (0.10 if x > 0 else -0.10), y, WR); co.hide_render = True; co.display_type = "WIRE"
        md = ob.modifiers.new("arch_" + name, "BOOLEAN"); md.operation = "DIFFERENCE"; md.object = co
        try: md.solver = "EXACT"; md.material_mode = "TRANSFER"
        except Exception as e: print("bool:", e)
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = 0.014; bv.segments = 3; bv.limit_method = "ANGLE"; bv.angle_limit = radians(18)
    wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = False
    ob["part"] = "body"; kit.PARTS.setdefault("body", []).append(ob)

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
        finish("side_line", box(0.006, 1.90, 0.010), v["trim"], 0, 1, T(0.9635 * s, -0.02, 0.452), p)
        finish("mirror_stalk", box(0.090, 0.022, 0.016), "body_dark", 0.004, 1, T(0.935 * s, -0.640, 0.862), p)
        finish("mirror_cam", box(0.045, 0.110, 0.042, taper=1.0), "body", 0.010, 3, T(0.990 * s, -0.625, 0.872), p)
        finish("mirror_lens", box(0.030, 0.006, 0.026), "glow_cyan", 0, 1, T(0.990 * s, -0.568, 0.872), p)
        for y in (-0.36, 0.72):
            finish("door_handle", box(0.008, 0.130, 0.020), "black", 0.003, 1, T(0.9500 * s, y, 0.760), p)
        finish("intake_side", prism([(0.95, 0.30), (1.22, 0.30), (1.22, 0.52), (1.05, 0.52)], 0.012, "x"), "black", 0.003, 1, T(0.966 * s, 0, 0), p)
        finish("pillar_b", box(0.020, 0.075, 0.42), "black", 0.004, 2, T(0.795 * s, 0.50, 1.07) @ RY(-27 * s), p)
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
    if v["roof"]:
        finish("cab_sign", box(0.78, 0.20, 0.105), "black", 0.012, 2, T(0, 0.66, 1.345), p)
        finish("cab_sign_face_f", box(0.70, 0.006, 0.070), "glow_amber", 0, 1, T(0, 0.557, 1.348), p)
        finish("cab_sign_face_r", box(0.70, 0.006, 0.070), "glow_amber", 0, 1, T(0, 0.763, 1.348), p)
        text("cab_text", v["roof"], 0.060, frame((1, 0, 0), (0, -1, 0), (0, 0.5525, 1.348)), "black", p)
        for s in (-1, 1):
            for k in range(7):
                if k % 2 == 0: finish("cab_check", box(0.006, 0.11, 0.055), "black", 0, 1, T(0.9605 * s, -0.42 + 0.11 * k, 0.61), p)
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
    v = VARIANTS[variant]; build_body(v); details(v); wheels()

if __name__ == "__main__":
    build(VARIANT); os.makedirs(OUT, exist_ok=True); tag = "" if VARIANT == "crimson" else "_" + VARIANT
    if MODE:
        kit.studio((0, 0, 0.6), 2.3, top=0.35, key=0.55)
        kit.shot(os.path.join(OUT, f"car{tag}_front.png"), (-5.2, -7.4, 2.5), (0.0, -0.1, 0.55), 60)
        if MODE == "all":
            kit.shot(os.path.join(OUT, f"car{tag}_rear.png"), (5.0, 7.6, 2.3), (0.0, 0.1, 0.55), 60)
            kit.shot(os.path.join(OUT, f"car{tag}_side.png"), (-11.0, -0.2, 1.0), (0.0, 0.0, 0.62), 85)
    for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
    kit.export(OUT, "car" + tag, {"variant": VARIANT, "wheel_radius": WR})
