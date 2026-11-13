"""사이버웨어 팔 3종 (자체 디자인): 파워암, 나노와이어, 런처. 블레이드 팔은 samples/cyber-arm에 있다.
실행: python cyber_arms.py <출력폴더> [render] [이름...]
좌표는 블레이드 팔과 같다: X = 팔꿈치 -> 손끝, Y = 엄지 쪽, Z = 손등 쪽. 단위 m. 팔꿈치가 원점, 손목이 x = 0.27.
내보내는 모델은 접힌(기본) 상태다. 펼친 상태는 사진으로 보여 주고, 움직임은 manifest의 pivots와 deploy에 적는다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, shell, tube, bolt, cable, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/cyber_arms"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []
WRIST = 0.27

def materials():
    kit.mat_paint("a_yellow", (0.78, 0.52, 0.02), rough=(0.34, 0.55), wear=1.6, scale=1.6)
    kit.mat_paint("a_white", (0.62, 0.63, 0.64), rough=(0.24, 0.40), wear=1.1, scale=1.6)
    kit.mat_paint("a_black", (0.03, 0.032, 0.036), (0.5, 0.5, 0.5), rough=(0.30, 0.50), wear=1.4, scale=1.6)
    kit.mat_paint("a_olive", (0.11, 0.14, 0.085), rough=(0.42, 0.60), wear=1.6, scale=1.6)
    kit.mat_simple("a_wire", (0.02, 0.0, 0.01), 0.0, 0.3, (1.0, 0.10, 0.55), 9.0)

def hand(scale, skin, joint, glow, curls=(8, 10, 8), thumb=(20, 20), tips=False):
    """손: 손바닥 + 손가락 4개(3마디) + 엄지(2마디). curls = 마디별 굽힘 각."""
    h = "hand"; k = scale
    finish("wrist_ball", sphere(0.026 * k, 1.0, 1.15, 0.9), "gunmetal", 0, 1, T(WRIST, 0, 0), h)
    finish("wrist_ring", torus(0.030 * k, 0.006 * k, 28, 8, "x"), joint, 0, 1, T(WRIST - 0.004, 0, 0) @ S(1, 1.12, 0.92), h)
    finish("palm", box(0.086 * k, 0.086 * k, 0.026 * k), skin, 0.006 * k, 3, T(WRIST + 0.060 * k, 0, 0), h)
    finish("palm_back", box(0.070 * k, 0.072 * k, 0.008 * k), "a_black", 0.003, 2, T(WRIST + 0.058 * k, 0, 0.015 * k), h)
    finish("palm_pad", box(0.060 * k, 0.066 * k, 0.006 * k), "rubber", 0.003, 2, T(WRIST + 0.062 * k, 0, -0.015 * k), h)
    finish("palm_led", box(0.030 * k, 0.004, 0.003), glow, 0, 1, T(WRIST + 0.050 * k, 0, 0.0195 * k), "glow")
    pivot("wrist", (WRIST, 0, 0), (0, 1, 0), "forearm", h, (-70, 70))
    lens = ((0.040, 0.026, 0.020), (0.044, 0.029, 0.021), (0.041, 0.027, 0.020), (0.033, 0.022, 0.018))
    for i, y in enumerate((0.033, 0.011, -0.011, -0.033)):
        Mx = T(WRIST + 0.104 * k, y * k, 0.001); par = h
        for j, L in enumerate(lens[i]):
            L *= k; Mx = Mx @ RY(curls[j]); p = f"finger{i + 1}_{'abc'[j]}"; w = (0.0185 - j * 0.0015) * k
            finish("knuckle", cyl(w * 0.56, w * 0.56, w * 1.04, 14, "y"), joint, 0.001, 1, Mx, p)
            finish("phalanx", box(L - 0.006 * k, w, w * 0.92), skin, 0.003 * k, 2, Mx @ T(L / 2 + 0.002 * k, 0, 0), p)
            finish("phalanx_pad", box(L * 0.6, w * 0.8, 0.003), "rubber", 0.001, 1, Mx @ T(L / 2 + 0.002 * k, 0, -w * 0.47), p)
            if tips and j == 2: finish("tip_glow", box(0.004, w * 0.7, w * 0.5), glow, 0, 1, Mx @ T(L - 0.001, 0, 0), "glow")
            pivot(p, tuple(Mx.translation), tuple((Mx.to_3x3() @ Vector((0, 1, 0)))), par, p, (0, 95)); par = p; Mx = Mx @ T(L, 0, 0)
    Mx = T(WRIST + 0.036 * k, 0.046 * k, -0.004) @ RZ(42) @ RX(-30); par = h
    for j, L in enumerate((0.036, 0.028)):
        L *= k; Mx = Mx @ RY(thumb[j]); p = f"thumb_{'ab'[j]}"; w = 0.020 * k
        finish("knuckle", cyl(w * 0.56, w * 0.56, w * 1.04, 14, "y"), joint, 0.001, 1, Mx, p)
        finish("phalanx", box(L - 0.006 * k, w, w * 0.92), skin, 0.003 * k, 2, Mx @ T(L / 2 + 0.002 * k, 0, 0), p)
        pivot(p, tuple(Mx.translation), tuple((Mx.to_3x3() @ Vector((0, 1, 0)))), par, p, (0, 80)); par = p; Mx = Mx @ T(L, 0, 0)

def elbow(r, mat):
    f = "forearm"
    finish("elbow_hinge", cyl(r, r, r * 2.5, 28, "y"), "titan", 0.003, 2, T(0, 0, 0), f)
    for s in (-1, 1):
        finish("elbow_cap", cyl(r * 0.72, r * 0.6, 0.010, 24, "y"), mat, 0.002, 1, T(0, s * r * 1.30, 0), f); bolt(T(0, s * (r * 1.30 + 0.006), 0) @ RX(90 * s), 0.006, part=f)
    finish("bellows", tube(lambda x: (r * 0.86 + 0.004 * sin(x * 900), r * 0.80 + 0.004 * sin(x * 900)), -0.060, -0.012, 0.0, 24, 28), "rubber", 0, 1, part=f)
    pivot("elbow", (0, 0, 0), (0, 1, 0), "upperarm", f, (0, 140))

def about_edge(prof, a, off, ang, x=0.13):
    """손등 판을 가장자리(각 a)를 축으로 ang만큼 여는 변환."""
    ry, rz = prof(x); p = Vector((0, (ry + off) * cos(radians(a)), (rz + off) * sin(radians(a))))
    return T(*p) @ RX(ang) @ T(*(-p)), p

# ------------------------------------------------------------------ 파워암
def power(deployed=False):
    """파워암: 유압 피스톤과 충전 코일. 펼치면 주먹을 쥐고 너클 판이 앞으로 나오며 코일이 빛난다."""
    f = "forearm"; prof = lambda x: (0.050 - 0.030 * x, 0.046 - 0.028 * x)
    elbow(0.040, "a_yellow")
    finish("core", tube(prof, 0.010, WRIST - 0.010, -0.010), "fiber", 0, 1, part=f)
    finish("dorsal", shell(prof, 0.020, 0.215, 28, 152, 0.0, 0.012), "a_yellow", 0.004, 3, part=f)
    finish("dorsal_inlay", shell(prof, 0.050, 0.185, 62, 118, 0.008, 0.006, 10, 6), "a_black", 0.002, 2, part=f)
    for k in range(5): finish("vent", shell(prof, 0.066 + k * 0.024, 0.078 + k * 0.024, 70, 110, 0.012, 0.003, 2, 6), "black", 0, 1, part=f)
    finish("ventral", shell(prof, 0.030, 0.230, 208, 332, -0.002, 0.010), "a_black", 0.003, 2, part=f)
    for s, a in ((1, 0), (-1, 180)):
        finish("side_rail", shell(prof, 0.030, 0.240, a - 22, a + 22, 0.004, 0.008, 12, 4), "gunmetal", 0.002, 2, part=f)
        ry0, _ = prof(0.03); ry1, _ = prof(0.24); p0 = Vector((0.030, s * (ry0 + 0.026), 0.004)); p1 = Vector((0.238, s * (ry1 + 0.022), 0.004)); d = p1 - p0
        finish("piston_body", cyl(0.0120, 0.0120, d.length * 0.55, 16, "x"), "a_black", 0.002, 1, T(*p0.lerp(p1, 0.30)) @ frame(d, (0, 0, 1)), f)
        finish("piston_rod", cyl(0.0065, 0.0065, d.length * 0.50, 12, "x"), "chrome", 0, 1, T(*p0.lerp(p1, 0.74)) @ frame(d, (0, 0, 1)), "piston")
        for q in (p0, p1): finish("piston_eye", cyl(0.0110, 0.0110, 0.018, 14, "z"), "titan", 0.002, 1, T(*q), f)
        finish("hazard", shell(prof, 0.200, 0.214, a + s * 30, a + s * 60, 0.0125, 0.001, 2, 4), "a_black", 0, 1, part=f)
    for k in range(4):
        x = 0.226 + k * 0.012
        finish("coil", torus(prof(x)[0] + 0.010, 0.0050, 32, 8, "x"), "gunmetal", 0, 1, T(x, 0, 0) @ S(1, 1, prof(x)[1] / prof(x)[0]), f)
        finish("coil_glow", torus(prof(x)[0] + 0.0125, 0.0018, 32, 6, "x"), "glow_amber", 0, 1, T(x + 0.006, 0, 0) @ S(1, 1, prof(x)[1] / prof(x)[0]), "charge_glow")
    finish("cell", box(0.070, 0.034, 0.016), "a_black", 0.004, 2, T(0.120, 0, 0.060), f); finish("cell_led", box(0.050, 0.010, 0.003), "glow_amber", 0, 1, T(0.120, 0, 0.0685), "charge_glow")
    hand(1.22, "a_yellow", "titan", "glow_amber", (70, 82, 60) if deployed else (10, 12, 8), (40, 40) if deployed else (18, 18))
    kx = WRIST + 0.104 * 1.22 + (0.020 if deployed else 0.0); kp = "knuckle_plate"
    finish("plate", box(0.040, 0.112, 0.014), "a_black", 0.004, 3, T(kx - 0.018, 0, 0.026), kp)
    for i in range(4):
        finish("stud", prism([(0.0, -0.011), (0.022, 0.0), (0.0, 0.011)], 0.020, "y"), "steel", 0.002, 1, T(kx + 0.002, (0.040 - i * 0.0268), 0.024), kp)
        finish("stud_glow", box(0.004, 0.016, 0.003), "glow_amber", 0, 1, T(kx - 0.006, (0.040 - i * 0.0268), 0.0335), "charge_glow")
    pivot("knuckle_plate", (kx, 0, 0.026), (1, 0, 0), "hand", kp, (0, 0))
    return {"deploy": [{"part": "finger*", "do": "주먹 쥐기", "time": 0.12}, {"part": "knuckle_plate", "slide_x": 0.020, "time": 0.08}, {"part": "piston", "slide_x": 0.018, "time": 0.10}, {"part": "charge_glow", "emissive": "0 -> 1", "time": 0.25}]}

# ------------------------------------------------------------------ 나노와이어
def nanowire(deployed=False):
    """나노와이어: 손목 안쪽 감개에서 빛나는 실이 나온다. 펼치면 덮개가 뒤로 밀리고 실이 뻗는다."""
    f = "forearm"; prof = lambda x: (0.038 - 0.036 * x, 0.034 - 0.030 * x)
    elbow(0.031, "a_white")
    finish("core", tube(prof, 0.010, WRIST - 0.008, -0.008), "fiber", 0, 1, part=f)
    finish("dorsal", shell(prof, 0.018, 0.240, 20, 160, 0.0, 0.007), "a_white", 0.003, 3, part=f)
    finish("dorsal_inlay", shell(prof, 0.040, 0.220, 76, 104, 0.005, 0.004, 12, 4), "a_black", 0.0015, 2, part=f)
    finish("dorsal_line", shell(prof, 0.046, 0.214, 88.5, 91.5, 0.0095, 0.001, 12, 2), "glow_magenta", 0, 1, part="glow")
    finish("ventral", shell(prof, 0.026, 0.190, 204, 336, -0.001, 0.006), "a_black", 0.002, 2, part=f)
    for s, a in ((1, 0), (-1, 180)): finish("side_strip", shell(prof, 0.030, 0.236, a - 16, a + 16, 0.003, 0.004, 12, 4), "gunmetal", 0.0015, 2, part=f)
    # 감개 (손목 안쪽)
    finish("spool_housing", cyl(0.030, 0.030, 0.018, 28, "z"), "gunmetal", 0.003, 2, T(0.226, 0, -0.030), f)
    finish("spool", cyl(0.024, 0.024, 0.010, 28, "z"), "a_black", 0.002, 1, T(0.226, 0, -0.040), "spool")
    finish("spool_glow", torus(0.018, 0.0030, 28, 6, "z"), "glow_magenta", 0, 1, T(0.226, 0, -0.0455), "glow")
    for k in range(6): finish("spool_tooth", box(0.006, 0.004, 0.010), "titan", 0.001, 1, T(0.226, 0, -0.040) @ RZ(k * 60) @ T(0.024, 0, 0), "spool")
    pivot("spool", (0.226, 0, -0.040), (0, 0, 1), f, "spool", (-360, 360))
    cv = "spool_cover"; dx = -0.034 if deployed else 0.0
    finish("cover", shell(prof, 0.196 + dx, 0.262 + dx, 232, 308, 0.016, 0.004, 6, 8), "a_white", 0.002, 2, part=cv)
    finish("cover_tab", box(0.010, 0.020, 0.004), "glow_magenta", 0, 1, T(0.202 + dx, 0, -0.0505), cv)
    pivot("spool_cover", (0.229, 0, -0.050), (1, 0, 0), f, cv, (0, 0))
    finish("nozzle", cyl(0.0060, 0.0040, 0.022, 12, "x"), "chrome", 0.001, 1, T(WRIST + 0.006, 0, -0.022), f)
    pivot("wire_out", (WRIST + 0.018, 0, -0.022), (1, 0, 0), f, "fx")
    hand(0.96, "a_white", "gunmetal", "glow_magenta", (26, 34, 24) if deployed else (8, 10, 8), (30, 24) if deployed else (18, 18), tips=True)
    if deployed:
        pts = [(WRIST + 0.018, 0, -0.022), (0.40, -0.02, -0.06), (0.58, -0.12, -0.02), (0.74, -0.30, 0.10), (0.80, -0.52, 0.24), (0.70, -0.70, 0.30)]
        cable("wire", pts, 0.0012, "a_wire", "wire"); finish("wire_weight", sphere(0.006), "a_wire", 0, 1, T(*pts[-1]), "wire")
    return {"deploy": [{"part": "spool_cover", "slide_x": -0.034, "time": 0.10}, {"part": "spool", "spin_deg": 720, "time": 0.25}, {"part": "glow", "emissive": "0.4 -> 1", "time": 0.2}],
            "wire": "실은 모델에 없다. 게임에서 wire_out 붙임점부터 Beam/Trail로 그린다. 굵기 약 2 mm, 발광 자홍. 길이 2.5~3 m."}

# ------------------------------------------------------------------ 런처
def launcher(deployed=False):
    """런처: 손등 문 2장이 양옆으로 열리고 발사관이 올라온다."""
    f = "forearm"; prof = lambda x: (0.046 - 0.040 * x, 0.042 - 0.030 * x)
    elbow(0.036, "a_olive")
    finish("core", tube(prof, 0.010, WRIST - 0.008, -0.009), "fiber", 0, 1, part=f)
    finish("ventral", shell(prof, 0.024, 0.236, 200, 340, -0.001, 0.009), "a_olive", 0.003, 2, part=f)
    for s, a in ((1, 0), (-1, 180)):
        finish("side_plate", shell(prof, 0.022, 0.244, a - 34, a + 34, 0.002, 0.009, 12, 6), "a_black", 0.003, 2, part=f)
        for k in range(3): finish("ammo_led", shell(prof, 0.090 + k * 0.022, 0.104 + k * 0.022, a - 5, a + 5, 0.0115, 0.001, 2, 2), "glow_red", 0, 1, part="glow")
    finish("bay_floor", shell(prof, 0.040, 0.230, 44, 136, -0.016, 0.004, 10, 8), "black", 0, 1, part=f)
    finish("collar_rear", shell(prof, 0.016, 0.044, 36, 144, 0.002, 0.012, 3, 10), "a_olive", 0.003, 2, part=f)
    finish("collar_front", shell(prof, 0.228, 0.252, 36, 144, 0.002, 0.011, 3, 10), "a_olive", 0.003, 2, part=f)
    ang = 72 if deployed else 0
    for s, a0, a1, name in ((1, 37, 90, "hatch_L"), (-1, 90, 143, "hatch_R")):
        edge = a0 if s > 0 else a1; Mh, p = about_edge(prof, edge, 0.004, -ang * s)
        finish("hatch", shell(prof, 0.046, 0.226, a0 + 0.6, a1 - 0.6, 0.003, 0.008, 10, 8), "a_olive", 0.003, 2, Mh, name)
        finish("hatch_stripe", shell(prof, 0.120, 0.150, a0 + 8, a1 - 8, 0.0112, 0.001, 3, 6), "a_yellow", 0, 1, Mh, name)
        pivot(name, tuple(p + Vector((0.136, 0, 0))), (1, 0, 0), f, name, (0, 72))
    tb = "tube"; lift = 0.030 if deployed else 0.0; Mt = T(0.136, 0, 0.022 + lift) @ RY(-6 if deployed else 0)
    finish("tube_body", cyl(0.0190, 0.0190, 0.170, 22, "x"), "gunmetal", 0.002, 2, Mt, tb)
    for x in (-0.070, 0.0, 0.070): finish("tube_band", cyl(0.0210, 0.0210, 0.012, 22, "x"), "a_black", 0.002, 1, Mt @ T(x, 0, 0), tb)
    finish("tube_mouth", torus(0.0165, 0.0035, 22, 8, "x"), "steel", 0, 1, Mt @ T(0.086, 0, 0), tb)
    finish("rocket_tip", cyl(0.0125, 0.0030, 0.022, 16, "x"), "a_yellow", 0.001, 1, Mt @ T(0.088, 0, 0), "rocket")
    finish("rocket_band", cyl(0.0128, 0.0128, 0.004, 16, "x"), "glow_red", 0, 1, Mt @ T(0.076, 0, 0), "rocket")
    finish("tube_sight", box(0.030, 0.008, 0.010), "a_black", 0.002, 1, Mt @ T(0.030, 0, 0.024), tb); finish("sight_lens", box(0.002, 0.005, 0.006), "glow_red", 0, 1, Mt @ T(0.046, 0, 0.024), "glow")
    for s in (-1, 1): finish("tube_strut", box(0.010, 0.006, 0.030 + lift), "chrome", 0.001, 1, T(0.136 + 0.050 * s, 0, 0.004 + lift / 2), tb)
    pivot("tube", (0.136, 0, 0.022), (0, 1, 0), f, tb, (-6, 0)); pivot("muzzle", tuple(Mt @ Vector((0.100, 0, 0))), (1, 0, 0), tb, "fx"); pivot("backblast", tuple(Mt @ Vector((-0.090, 0, 0))), (-1, 0, 0), tb, "fx")
    hand(1.05, "a_olive", "gunmetal", "glow_red", (58, 70, 50) if deployed else (8, 10, 8), (36, 30) if deployed else (18, 18))
    return {"deploy": [{"part": "hatch_L / hatch_R", "open_deg": 72, "time": 0.15}, {"part": "tube", "lift_z": 0.030, "pitch_deg": -6, "time": 0.15}, {"part": "glow", "emissive": "0.3 -> 1", "time": 0.1}]}

ARMS = {"power": power, "nanowire": nanowire, "launcher": launcher}

def build(name, deployed=False):
    kit.reset(); materials(); return ARMS[name](deployed)

def shoot(path):
    kit.studio((0.22, 0, 0), 0.34, floor_z=-0.11, top=0.7, key=0.9)
    kit.shot(path, (0.90, -0.74, 0.46), (0.250, -0.03, -0.01), 70, res=tuple(int(v) for v in os.environ.get("ARM_RES", "1400,900").split(",")))
    for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name in ARMS:
        if ONLY and name not in ONLY: continue
        if RENDER:
            build(name, True); shoot(os.path.join(OUT, f"arm_{name}_deployed.png"))
        extra = build(name, False)
        if RENDER: shoot(os.path.join(OUT, f"arm_{name}.png"))
        kit.export(os.path.join(OUT, name), "arm_" + name, extra)
