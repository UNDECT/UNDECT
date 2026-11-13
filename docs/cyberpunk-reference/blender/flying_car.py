"""비행 차량 (자체 디자인). 실행: python flying_car.py <출력폴더> [render|all] [변형]
변형: civil(기본, 흰색), patrol(보안 순찰: 남색 + 경광등), cargo(주황 화물)
앞이 -Y. 길이 6.4 m, 동체 폭 2.3 m, 추진기 포함 폭 4.6 m. 추진기 4개는 X축으로 기울일 수 있다(전진 비행).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, text, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/flying_car"
MODE = ARGS[1] if len(ARGS) > 1 else ""
VARIANT = ARGS[2] if len(ARGS) > 2 else "civil"
VARIANTS = {
    "civil": {"body": (0.66, 0.67, 0.69), "accent": (0.80, 0.30, 0.02), "thrust": "glow_cyan", "bar": None, "word": "KX-AIR"},
    "patrol": {"body": (0.045, 0.07, 0.13), "accent": (0.62, 0.63, 0.64), "thrust": "glow_cyan", "bar": True, "word": "SEC 07"},
    "cargo": {"body": (0.78, 0.36, 0.02), "accent": (0.05, 0.05, 0.055), "thrust": "glow_amber", "bar": None, "word": "HAUL 3"},
}
Z0 = 0.62  # 착륙했을 때 동체 바닥 높이
# 단면: (y, 아래 반폭, 최대 반폭, 지붕 반폭, 바닥 z, 허리 z, 어깨 z, 지붕 z)
STATIONS = [
    (-3.20, 0.30, 0.42, 0.26, 0.42, 0.52, 0.60, 0.66),
    (-2.75, 0.74, 0.92, 0.62, 0.20, 0.42, 0.66, 0.78),
    (-1.90, 0.98, 1.14, 0.84, 0.06, 0.40, 0.84, 0.98),
    (-1.05, 1.02, 1.16, 0.70, 0.00, 0.40, 0.98, 1.56),
    (0.20, 1.02, 1.16, 0.72, 0.00, 0.40, 1.02, 1.66),
    (1.30, 1.00, 1.14, 0.80, 0.04, 0.42, 1.04, 1.52),
    (2.40, 0.86, 1.00, 0.72, 0.20, 0.50, 0.98, 1.22),
    (3.20, 0.56, 0.68, 0.50, 0.46, 0.62, 0.90, 1.02),
]
PODS = {"FL": (1.92, -1.75), "FR": (-1.92, -1.75), "RL": (1.92, 1.95), "RR": (-1.92, 1.95)}

def ring(st):
    y, w0, w1, w2, zf, zm, zb, zr = st
    half = [(0, zf), (w0 - 0.10, zf), (w0, zf + 0.12), (w1, zm), (w1 - 0.05, zb), (w2, zr - 0.05), (0, zr)]
    return [(x, y, z + Z0) for x, z in half + [(-x, z) for x, z in half[-2:0:-1]]]

def hull(v):
    kit.mat_paint("body", v["body"], rough=(0.22, 0.38), wear=0.6, scale=0.10)
    kit.mat_paint("accent", v["accent"], rough=(0.30, 0.46), wear=0.8, scale=0.10)
    kit.mat_paint("under", (0.035, 0.037, 0.042), (0.4, 0.4, 0.4), rough=(0.34, 0.5), wear=0.8, scale=0.10)
    bm = loft([ring(s) for s in STATIONS]); n = 12
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("hull"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("hull", me); kit.COL.objects.link(ob)
    for k in ("body", "glass", "under"): me.materials.append(kit.M[k])
    glass = {2: (4, 5, 6, 7), 3: (4, 5, 6, 7), 4: (4, 7)}
    for p in me.polygons:
        p.use_smooth = True; i, j = divmod(p.index, n)
        if i in glass and j in glass[i]: p.material_index = 1
        elif j in (0, 1, 10, 11): p.material_index = 2
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = 0.02; bv.segments = 3; bv.limit_method = "ANGLE"; bv.angle_limit = radians(18)
    wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = False
    ob["part"] = "body"; kit.PARTS.setdefault("body", []).append(ob)

def details(v):
    p = "body"; z = Z0
    finish("nose_light", box(0.50, 0.03, 0.035), "glow_white", 0, 1, T(0, -3.215, z + 0.555), p)
    for s in (-1, 1):
        finish("headlamp", box(0.34, 0.04, 0.06), "glow_white", 0, 1, T(0.50 * s, -2.93, z + 0.60) @ RZ(-34 * s) @ RX(-30), p)
        finish("door_line", box(0.012, 0.03, 0.80), "black", 0, 1, T(1.13 * s, -0.20, z + 0.72), p)
        finish("door_line2", box(0.012, 0.03, 0.80), "black", 0, 1, T(1.12 * s, 1.20, z + 0.74), p)
        finish("side_stripe", box(0.012, 3.6, 0.10), "accent", 0.003, 1, T(1.166 * s, -0.05, z + 0.42), p)
        finish("side_glow", box(0.008, 3.0, 0.014), v["thrust"], 0, 1, T(1.172 * s, -0.05, z + 0.52), p)
        finish("nav_light", sphere(0.05, 1, 1, 1, 10, 6), "glow_red" if s > 0 else "glow_cyan", 0, 1, T(1.16 * s, 0.9, z + 1.04), p)
        # 추진기 팔 (동체에서 추진기까지)
        for name, (x, y) in PODS.items():
            if (x > 0) == (s > 0):
                finish("pod_arm", box(0.86, 0.46, 0.16, taper=0.8), "body", 0.03, 3, T(1.50 * s, y, z + 0.52) @ (RZ(180) if s < 0 else Matrix.Identity(4)), p)
                finish("pod_arm_under", box(0.70, 0.30, 0.06), "under", 0.01, 2, T(1.48 * s, y, z + 0.42), p)
        # 착륙 다리
        for y in (-1.5, 1.5):
            finish("skid_leg", box(0.07, 0.10, 0.62), "under", 0.01, 2, T(0.72 * s, y, 0.34) @ RY(-10 * s), "skid")
        finish("skid", box(0.12, 3.5, 0.07), "under", 0.02, 2, T(0.78 * s, 0.0, 0.035), "skid")
        finish("tail_fin", prism([(2.30, 1.18), (3.10, 0.98), (3.40, 1.72), (3.05, 1.76)], 0.05, "x"), "body", 0.012, 2, T(0.52 * s, 0, z) @ RY(-16 * s), p)
        finish("tail_fin_tip", prism([(3.02, 1.60), (3.36, 1.58), (3.40, 1.72), (3.05, 1.76)], 0.055, "x"), "accent", 0.008, 2, T(0.52 * s, 0, z) @ RY(-16 * s), p)
        # 뒤 주 추진구
        finish("nozzle", cyl(0.26, 0.21, 0.42, 28, "y"), "gunmetal", 0.012, 2, T(0.34 * s, 3.26, z + 0.70), p)
        finish("nozzle_glow", cyl(0.185, 0.185, 0.02, 28, "y"), "glow_amber", 0, 1, T(0.34 * s, 3.455, z + 0.70), p)
    finish("belly_plate", box(1.5, 3.4, 0.05), "under", 0.02, 2, T(0, 0.0, z + 0.02), p)
    finish("belly_glow", box(1.1, 2.6, 0.012), v["thrust"], 0, 1, T(0, 0.0, z - 0.012), p)
    finish("roof_scoop", prism([(0.2, 1.66), (0.9, 1.60), (0.9, 1.72), (0.35, 1.78)], 0.60, "x"), "under", 0.02, 2, T(0, 0, z), p)
    finish("roof_scoop_in", box(0.50, 0.03, 0.09), "black", 0, 1, T(0, 0.30, z + 1.705) @ RX(34), p)
    finish("searchlight", cyl(0.10, 0.12, 0.14, 18, "y"), "under", 0.01, 2, T(0, -2.72, z + 0.16), p)
    finish("searchlight_lens", cyl(0.085, 0.085, 0.01, 18, "y"), "glow_white", 0, 1, T(0, -2.795, z + 0.16), p)
    for s in (-1, 1):
        text("hull_text", v["word"], 0.26, frame((0, s, 0), (s, 0, 0), (1.172 * s, 0.55, z + 0.76)), "under", p, 0.004)
    if v["bar"]:
        finish("light_bar", box(1.20, 0.26, 0.10), "black", 0.02, 2, T(0, -0.55, z + 1.64), p)
        finish("light_bar_L", box(0.52, 0.27, 0.07), "glow_red", 0, 1, T(0.31, -0.55, z + 1.645), p)
        finish("light_bar_R", box(0.52, 0.27, 0.07), "glow_cyan", 0, 1, T(-0.31, -0.55, z + 1.645), p)

def pods(v):
    for name, (x, y) in PODS.items():
        p = "pod_" + name; Mx = T(x, y, Z0 + 0.52)
        finish("duct", torus(0.50, 0.105, 44, 14, "z"), "body", 0, 1, Mx @ S(1, 1, 1.9), p)
        finish("duct_band", torus(0.600, 0.022, 44, 8, "z"), "accent", 0, 1, Mx @ T(0, 0, 0.06) @ S(1, 1, 2.2), p)
        finish("hub", cyl(0.12, 0.09, 0.34, 20, "z"), "gunmetal", 0.01, 2, Mx, p)
        finish("hub_cap", sphere(0.12, 1, 1, 0.6, 16, 8), "gunmetal", 0, 1, Mx @ T(0, 0, 0.17), p)
        for k in range(3):
            finish("stator", box(0.86, 0.05, 0.10), "under", 0.008, 1, Mx @ RZ(k * 60 + 15) @ T(0, 0, 0.02), p)
        for k in range(9):
            finish("fan_blade", box(0.34, 0.11, 0.012), "steel", 0.002, 1, Mx @ RZ(k * 40) @ T(0.26, 0, -0.06) @ RX(24), "fan_" + name)
        finish("thrust_glow", cyl(0.40, 0.40, 0.012, 36, "z"), v["thrust"], 0, 1, Mx @ T(0, 0, -0.16), p)
        finish("pod_light", box(0.10, 0.03, 0.03), "glow_white" if y < 0 else "glow_red", 0, 1, Mx @ T(0, -0.615 if y < 0 else 0.615, 0.02), p)
        pivot("pod_" + name, (x, y, Z0 + 0.52), (1, 0, 0), "body", p, (-20, 90))
        pivot("fan_" + name, (x, y, Z0 + 0.46), (0, 0, 1), p, "fan_" + name, (-360, 360))

def parts(variant="civil"):
    v = VARIANTS[variant]; hull(v); details(v); pods(v)

def build(variant="civil"):
    kit.reset(); parts(variant)

if __name__ == "__main__":
    build(VARIANT); os.makedirs(OUT, exist_ok=True); tag = "" if VARIANT == "civil" else "_" + VARIANT
    if MODE:
        kit.studio((0, 0, 1.2), 3.2, top=0.4, key=0.5)
        res = tuple(int(c) for c in os.environ.get("FC_RES", "1400,875").split(","))
        kit.shot(os.path.join(OUT, f"flying_car{tag}_front.png"), (-7.6, -10.5, 4.6), (0.0, 0.0, 1.15), 60, res=res)
        if MODE == "all":
            kit.shot(os.path.join(OUT, f"flying_car{tag}_rear.png"), (7.4, 10.8, 3.6), (0.0, 0.0, 1.2), 60, res=res)
            kit.shot(os.path.join(OUT, f"flying_car{tag}_low.png"), (-6.0, -9.0, 0.25), (0.0, 0.0, 1.5), 50, res=res)
    for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
    kit.export(OUT, "flying_car" + tag, {"variant": VARIANT, "landed_floor_z": 0.0})
