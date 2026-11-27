"""보안 로봇 (자체 디자인). 실행: python security_robot.py <출력폴더> [render]
-Y를 바라보고 선다. 키 약 1.95 m. 부품은 관절 단위로 나뉘고 manifest.json에 관절 위치·축이 기록된다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, shell, tube, bolt, cable, text, pivot, frame, RX, RY, RZ, T, S

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/security_robot"
RENDER = len(sys.argv) > 2

def materials():
    kit.mat_paint("armor", (0.58, 0.60, 0.61), rough=(0.30, 0.52), wear=1.4, scale=0.35)
    kit.mat_paint("armor2", (0.055, 0.085, 0.14), (0.5, 0.5, 0.5), rough=(0.30, 0.50), wear=1.6, scale=0.35)
    kit.mat_paint("accent", (0.86, 0.50, 0.015), rough=(0.34, 0.55), scale=0.35)
    kit.mat_paint("frame", (0.05, 0.053, 0.06), (0.45, 0.45, 0.45), rough=(0.36, 0.55), scale=0.35)

def superring(w, d, z, n=28, e=3.2, yoff=0.0):
    """둥근 사각형 단면 고리 (가로 w, 앞뒤 d)."""
    pts = []
    for i in range(n):
        a = 2 * pi * i / n; c, s = cos(a), sin(a)
        pts.append((w / 2 * abs(c) ** (2 / e) * (1 if c >= 0 else -1), yoff + d / 2 * abs(s) ** (2 / e) * (1 if s >= 0 else -1), z))
    return pts

def dome(r, sx, sy, sz, cut=-0.12):
    bm = sphere(r, 1, 1, 1, 28, 16)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut * r], context="VERTS")
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    return bm

def solid(ob, th):
    md = ob.modifiers.new("solid", "SOLIDIFY"); md.thickness = th; md.offset = -1
    ob.modifiers.move(len(ob.modifiers) - 1, 0); return ob

# ------------------------------------------------------------------ 다리
def leg(s):
    side = "L" if s > 0 else "R"; out_a = 0.0 if s > 0 else 180.0
    hip = Vector((0.128 * s, 0.0, 1.012))
    Mx = T(*hip) @ frame((0, 0, -1), (0, -1, 0)) @ RY(-3)
    p = f"thigh_{side}"; L = 0.455
    pt = lambda x: (0.100 - 0.022 * x / L, 0.108 - 0.026 * x / L)
    finish("hip_ball", sphere(0.078), "frame", 0, 1, Mx, p)
    finish("hip_cap", cyl(0.05, 0.045, 0.03, 24, "y"), "titan", 0.004, 2, Mx @ T(0, 0.085 * s, 0), p)
    finish("thigh_core", tube(pt, 0.05, L - 0.03, -0.030), "fiber", 0, 1, Mx, p)
    finish("thigh_front", shell(pt, 0.06, L - 0.07, 14, 166, 0.0, 0.013), "armor2", 0.004, 3, Mx, p)
    finish("thigh_front_inlay", shell(pt, 0.11, L - 0.14, 58, 122, 0.006, 0.006, 8, 6), "frame", 0.002, 2, Mx, p)
    finish("thigh_back", shell(pt, 0.09, L - 0.10, 198, 342, -0.004, 0.011), "frame", 0.003, 2, Mx, p)
    finish("thigh_stripe", shell(pt, 0.10, 0.27, out_a - 13, out_a + 13, 0.004, 0.006, 6, 4), "accent", 0.002, 2, Mx, p)
    for bx in (0.075, L - 0.085):
        for ba in (24, 156): bolt(Mx @ T(bx, (pt(bx)[0]) * cos(radians(ba)), (pt(bx)[1]) * sin(radians(ba))) @ RX(ba - 90), 0.006, part=p)
    pivot(f"hip_{side}", hip, (1, 0, 0), "pelvis", p, (-70, 40))
    # 무릎
    Mk = Mx @ T(L, 0, 0) @ RY(6)
    p = f"shin_{side}"; L2 = 0.445
    ps = lambda x: (0.082 - 0.022 * x / L2 + 0.014 * sin(pi * x / L2), 0.086 - 0.022 * x / L2 + 0.024 * sin(pi * min(1.0, 1.3 * x / L2)))
    finish("knee_hinge", cyl(0.064, 0.064, 0.176, 28, "y"), "titan", 0.004, 3, Mk, p)
    finish("knee_pin", cyl(0.024, 0.024, 0.192, 16, "y"), "chrome", 0.002, 1, Mk, p)
    finish("knee_cap", box(0.15, 0.135, 0.034, taper=0.80), "accent", 0.008, 3, Mk @ T(0.0, 0, 0.082) @ RY(-4), p)
    finish("shin_core", tube(ps, 0.05, L2 - 0.02, -0.026), "fiber", 0, 1, Mk, p)
    finish("shin_front", shell(ps, 0.075, L2 - 0.035, 16, 164, 0.004, 0.015), "armor", 0.005, 3, Mk, p)
    finish("shin_inlay", shell(ps, 0.12, 0.31, 62, 118, 0.011, 0.007, 8, 6), "frame", 0.002, 2, Mk, p)
    finish("shin_glow", shell(ps, 0.33, 0.39, 76, 104, 0.0105, 0.004, 3, 4), "glow_cyan", 0, 1, Mk, p)
    finish("calf", shell(ps, 0.06, 0.33, 204, 336, 0.0, 0.012), "armor2", 0.004, 3, Mk, p)
    for y in (-0.028, 0.028):
        finish("achilles_sleeve", cyl(0.011, 0.011, 0.09, 14, "x", True), "frame", 0.001, 1, Mk @ T(0.30, y, -0.052), p)
        finish("achilles_rod", cyl(0.006, 0.006, 0.075, 12, "x", True), "chrome", 0, 1, Mk @ T(0.37, y, -0.052), p)
    pivot(f"knee_{side}", Mk.translation, (1, 0, 0), f"thigh_{side}", p, (0, 130))
    # 발 (월드 기준으로 평평하게)
    ank = (Mk @ T(L2, 0, 0)).translation; p = f"foot_{side}"
    finish("ankle", cyl(0.044, 0.044, 0.125, 24, "x"), "titan", 0.003, 2, T(*ank), p)
    Fx = T(ank.x, ank.y, 0)
    finish("sole", box(0.150, 0.330, 0.036, z0=True), "rubber", 0.008, 2, Fx @ T(0, -0.070, 0), p)
    finish("foot_upper", prism([(-0.100, 0.034), (-0.100, 0.118), (0.020, 0.150), (0.105, 0.118), (0.105, 0.034)], 0.132, "x"), "frame", 0.008, 3, Fx @ T(0, -0.035, 0), p)
    finish("toe_cap", prism([(-0.225, 0.034), (-0.225, 0.066), (-0.150, 0.098), (-0.098, 0.098), (-0.098, 0.034)], 0.144, "x"), "armor2", 0.008, 3, Fx, p)
    finish("heel", box(0.128, 0.060, 0.090, z0=True), "armor2", 0.008, 3, Fx @ T(0, 0.105, 0.034), p)
    pivot(f"ankle_{side}", ank, (1, 0, 0), f"shin_{side}", p, (-40, 40))

# ------------------------------------------------------------------ 몸통
def body():
    p = "pelvis"
    finish("pelvis_block", loft([superring(0.30, 0.19, 0.950), superring(0.35, 0.21, 1.03), superring(0.31, 0.19, 1.10)]), "frame", 0.006, 3, part=p)
    finish("crotch_plate", prism([(-0.075, 1.085), (0.075, 1.085), (0.050, 0.945), (-0.050, 0.945)], 0.030), "armor", 0.006, 3, T(0, -0.098, 0), p)
    for s in (-1, 1):
        finish("tasset", box(0.034, 0.185, 0.215), "armor2", 0.008, 3, T(0.222 * s, 0.0, 1.020) @ RY(-10 * s), p)
        finish("tasset_stripe", box(0.008, 0.12, 0.034), "accent", 0.002, 2, T(0.239 * s, 0.0, 1.080) @ RY(-10 * s), p)
    finish("belt", cyl(0.158, 0.150, 0.040, 40, "z"), "titan", 0.004, 2, T(0, 0, 1.118) @ S(1, 0.66, 1), p)
    for k in range(4):
        finish("waist_bellows", torus(0.100, 0.021, 40, 10, "z"), "rubber", 0, 1, T(0, 0, 1.158 + 0.033 * k) @ S(1, 0.70, 1), "torso")
    for s in (-1, 1):
        finish("spine_piston", cyl(0.011, 0.011, 0.15, 14, "z"), "chrome", 0, 1, T(0.128 * s, 0.035, 1.205), "torso")
    pivot("waist", (0, 0, 1.14), (0, 0, 1), "pelvis", "torso", (-45, 45))
    p = "torso"
    finish("chest", loft([superring(0.29, 0.20, 1.265), superring(0.40, 0.25, 1.37), superring(0.475, 0.275, 1.515), superring(0.45, 0.25, 1.60), superring(0.30, 0.19, 1.645)]), "frame", 0.006, 3, part=p)
    for s in (-1, 1):
        finish("pec", prism([(0.012, 1.585), (0.212, 1.560), (0.200, 1.425), (0.060, 1.385), (0.012, 1.400)] if s > 0 else [(-0.012, 1.585), (-0.012, 1.400), (-0.060, 1.385), (-0.200, 1.425), (-0.212, 1.560)], 0.030), "armor", 0.007, 3, T(0, -0.134, 0), p)
        finish("rib", prism([(0.035 * s, 1.365), (0.170 * s, 1.395), (0.150 * s, 1.300), (0.035 * s, 1.285)][::s], 0.022), "frame", 0.005, 2, T(0, -0.118, 0), p)
        finish("collar_plate", box(0.15, 0.20, 0.022), "armor", 0.007, 3, T(0.135 * s, 0.0, 1.640) @ RY(14 * s), p)
    finish("core_ring", cyl(0.040, 0.040, 0.030, 28, "y"), "titan", 0.004, 2, T(0, -0.150, 1.495), p)
    finish("core_glow", cyl(0.026, 0.026, 0.006, 24, "y"), "glow_cyan", 0, 1, T(0, -0.167, 1.495), p)
    for k in range(3):
        finish("abdomen_slat", box(0.185 - 0.02 * k, 0.020, 0.024), "armor", 0.004, 2, T(0, -0.108 + 0.004 * k, 1.345 - 0.037 * k), p)
    text("unit_text", "SEC 112", 0.034, frame((1, 0, 0), (0, -1, 0), (0.108, -0.1505, 1.535)), "frame", p)
    finish("collar", torus(0.082, 0.022, 36, 10, "z"), "titan", 0, 1, T(0, 0.0, 1.655), p)
    # 등 장비 (약점: 가운데 주황 발광판)
    finish("backpack", box(0.30, 0.115, 0.30, taper=1.0), "armor", 0.012, 3, T(0, 0.180, 1.445), p)
    finish("backpack_frame", box(0.33, 0.06, 0.20), "frame", 0.008, 2, T(0, 0.145, 1.445), p)
    for k in range(5):
        finish("back_vent", box(0.20, 0.012, 0.014), "black", 0.002, 1, T(0, 0.238, 1.545 - 0.024 * k), p)
    finish("weak_point", box(0.115, 0.010, 0.062), "glow_amber", 0, 1, T(0, 0.2385, 1.375), p)
    finish("weak_frame", box(0.14, 0.014, 0.085), "frame", 0.004, 2, T(0, 0.234, 1.375), p)
    for s in (-1, 1):
        finish("exhaust", cyl(0.028, 0.032, 0.11, 20, "z"), "titan", 0.003, 2, T(0.105 * s, 0.205, 1.640), p)
        finish("exhaust_hole", cyl(0.022, 0.022, 0.006, 20, "z"), "black", 0, 1, T(0.105 * s, 0.205, 1.6935), p)
    finish("antenna", cyl(0.004, 0.003, 0.30, 8, "z"), "frame", 0, 1, T(-0.135, 0.215, 1.765), p)
    finish("antenna_tip", sphere(0.008), "glow_red", 0, 1, T(-0.135, 0.215, 1.918), p)

# ------------------------------------------------------------------ 팔
def arm(s, pose):
    side = "L" if s > 0 else "R"
    sh = Vector((0.305 * s, 0.0, 1.560))
    Mx = T(*sh) @ frame((0, 0, -1), (s, 0, 0)) @ RY(pose["abduct"]) @ RZ(-s * pose["swing"])
    p = f"upperarm_{side}"; L = 0.315
    pu = lambda x: (0.072 - 0.012 * x / L, 0.072 - 0.012 * x / L)
    finish("shoulder_ball", sphere(0.072), "frame", 0, 1, Mx, p)
    finish("pauldron_cap", box(0.070, 0.225, 0.175, taper=0.9), "frame", 0.012, 3, Mx @ T(-0.062, 0, 0.012), p)
    finish("pauldron_top", box(0.185, 0.235, 0.030, taper=0.86), "armor", 0.010, 3, Mx @ T(0.010, 0, 0.098) @ RY(-24), p)
    finish("pauldron_low", box(0.120, 0.200, 0.024, taper=0.84), "armor2", 0.008, 3, Mx @ T(0.118, 0, 0.118) @ RY(-10), p)
    finish("pauldron_trim", box(0.022, 0.205, 0.012), "accent", 0.003, 2, Mx @ T(0.060, 0, 0.133) @ RY(-24), p)
    finish("status_lamp", box(0.034, 0.060, 0.010), "glow_cyan", 0, 1, Mx @ T(-0.040, 0, 0.120) @ RY(-24), p)
    finish("upperarm_core", tube(pu, 0.05, L - 0.02, -0.020), "fiber", 0, 1, Mx, p)
    finish("upperarm_outer", shell(pu, 0.105, L - 0.045, 28, 152, 0.002, 0.012), "armor2", 0.004, 3, Mx, p)
    finish("upperarm_inner", shell(pu, 0.09, L - 0.06, 205, 335, -0.002, 0.009), "frame", 0.003, 2, Mx, p)
    pivot(f"shoulder_{side}", sh, (1, 0, 0), "torso", p, (-170, 60))
    Me = Mx @ T(L, 0, 0) @ RZ(-s * pose["elbow"])
    p = f"forearm_{side}"; L2 = 0.300
    pf = lambda x: (0.064 - 0.014 * x / L2 + 0.012 * sin(pi * x / L2), 0.064 - 0.014 * x / L2 + 0.012 * sin(pi * x / L2))
    finish("elbow_hinge", cyl(0.056, 0.056, 0.146, 26, "z"), "titan", 0.004, 3, Me, p)
    finish("elbow_pin", cyl(0.021, 0.021, 0.160, 14, "z"), "chrome", 0.002, 1, Me, p)
    finish("forearm_core", tube(pf, 0.04, L2 - 0.01, -0.020), "fiber", 0, 1, Me, p)
    finish("forearm_outer", shell(pf, 0.060, L2 - 0.03, 18, 162, 0.003, 0.013), "armor", 0.004, 3, Me, p)
    finish("forearm_inner", shell(pf, 0.070, L2 - 0.05, 200, 340, 0.0, 0.010), "frame", 0.003, 2, Me, p)
    finish("wrist", cyl(0.036, 0.034, 0.034, 24, "x", True), "titan", 0.003, 2, Me @ T(L2 - 0.012, 0, 0), p)
    pivot(f"elbow_{side}", Me.translation, tuple((Me.to_3x3() @ Vector((0, 0, 1)))), f"upperarm_{side}", p, (0, 140))
    if s < 0:
        # 오른팔: 전완 일체형 2연장 총
        finish("gun_pod", box(0.270, 0.072, 0.066, True, 0.9, 0.9), "frame", 0.008, 3, Me @ T(0.035, 0, 0.100), p)
        finish("gun_pod_top", box(0.160, 0.050, 0.012, True), "armor", 0.004, 2, Me @ T(0.060, 0, 0.138), p)
        finish("gun_feed", cyl(0.034, 0.034, 0.060, 20, "y"), "titan", 0.004, 2, Me @ T(0.085, -0.050 * s, 0.098), p)
        for y in (-0.017, 0.017):
            finish("gun_barrel", cyl(0.0125, 0.0125, 0.150, 16, "x", True), "steel", 0.001, 1, Me @ T(0.290, y, 0.100), p)
            finish("gun_bore", cyl(0.0075, 0.0075, 0.004, 12, "x", True), "black", 0, 1, Me @ T(0.4385, y, 0.100), p)
        finish("gun_shroud", box(0.060, 0.070, 0.050, True), "titan", 0.005, 2, Me @ T(0.300, 0, 0.100), p)
        finish("gun_sight", box(0.030, 0.008, 0.006), "glow_red", 0, 1, Me @ T(0.250, 0, 0.1365), p)
    else:
        # 왼팔: 탐조등과 신분 스캐너
        finish("lamp_body", cyl(0.030, 0.034, 0.090, 20, "x", True), "frame", 0.004, 2, Me @ T(0.150, 0, 0.094), p)
        finish("lamp_lens", cyl(0.027, 0.027, 0.005, 20, "x", True), "glow_white", 0, 1, Me @ T(0.2405, 0, 0.094), p)
        finish("scanner", box(0.085, 0.050, 0.014, True), "frame", 0.004, 2, Me @ T(0.050, 0, 0.084), p)
        finish("scanner_glow", box(0.060, 0.030, 0.003, True), "glow_cyan", 0, 1, Me @ T(0.062, 0, 0.0915), p)
    # 손: 손바닥이 몸 쪽(-Z)을 본다
    Mh = Me @ T(L2 + 0.022, 0, 0) @ RY(8); p = f"hand_{side}"
    finish("palm", box(0.090, 0.082, 0.030, True, 1.04, 0.85), "frame", 0.008, 3, Mh, p)
    finish("hand_plate", box(0.066, 0.068, 0.010, True), "armor", 0.004, 3, Mh @ T(0.010, 0, 0.018), p)
    for i, y in enumerate((-0.028, 0.0, 0.028)):
        Mf = Mh @ T(0.092, y, 0) @ RY(16)
        for k, Lf in enumerate((0.044, 0.034)):
            finish("finger_joint", cyl(0.012, 0.012, 0.024, 14, "y"), "titan", 0.001, 1, Mf, p)
            finish("finger", box(Lf - 0.006, 0.021, 0.021, True, 0.9), "frame", 0.004, 2, Mf @ T(0.006, 0, 0), p)
            finish("finger_plate", box((Lf - 0.006) * 0.8, 0.018, 0.005, True), "armor", 0.002, 2, Mf @ T(0.009, 0, 0.012), p)
            Mf = Mf @ T(Lf, 0, 0) @ RY(24)
    Mt = Mh @ T(0.020, -0.046 * s, -0.006) @ RZ(-34 * s) @ RY(28)
    for Lf in (0.040, 0.032):
        finish("thumb_joint", cyl(0.013, 0.013, 0.026, 14, "y"), "titan", 0.001, 1, Mt, p)
        finish("thumb", box(Lf - 0.006, 0.023, 0.023, True, 0.9), "frame", 0.004, 2, Mt @ T(0.006, 0, 0), p)
        Mt = Mt @ T(Lf, 0, 0) @ RY(18)
    pivot(f"wrist_{side}", Mh.translation, tuple((Mh.to_3x3() @ Vector((0, 1, 0)))), f"forearm_{side}", p, (-60, 60))

# ------------------------------------------------------------------ 머리 (사람 얼굴이 아닌 센서 모듈)
def head():
    p = "head"
    finish("neck", cyl(0.048, 0.044, 0.085, 24, "z"), "frame", 0.003, 2, T(0, 0.005, 1.690), p)
    for k in range(3): finish("neck_ring", torus(0.049, 0.008, 28, 8, "z"), "rubber", 0, 1, T(0, 0.005, 1.668 + 0.020 * k), p)
    side = [(0.105, 1.722), (0.118, 1.868), (0.060, 1.918), (-0.050, 1.925), (-0.118, 1.878), (-0.128, 1.795), (-0.085, 1.722)]
    finish("skull", prism(side, 0.205, "x"), "frame", 0.012, 3, part=p)
    finish("cap", prism([(0.122, 1.875), (0.062, 1.930), (-0.054, 1.938), (-0.126, 1.888), (-0.118, 1.868), (-0.048, 1.905), (0.056, 1.898), (0.110, 1.852)], 0.222, "x"), "armor2", 0.006, 3, part=p)
    finish("visor_frame", box(0.214, 0.030, 0.062), "black", 0.006, 2, T(0, -0.118, 1.833) @ RX(6), p)
    finish("visor", box(0.186, 0.008, 0.026), "glow_cyan", 0, 1, T(0, -0.1345, 1.835) @ RX(6), p)
    finish("jaw", prism([(-0.128, 1.795), (-0.085, 1.722), (-0.020, 1.722), (-0.060, 1.800)], 0.214, "x"), "armor", 0.006, 3, part=p)
    for k in range(3): finish("grill", box(0.085, 0.006, 0.008), "black", 0.001, 1, T(0, -0.1185 + 0.011 * k, 1.770 - 0.016 * k) @ RX(-28), p)
    for s in (-1, 1):
        finish("ear_pod", cyl(0.038, 0.034, 0.030, 22, "x"), "titan", 0.004, 2, T(0.116 * s, 0.025, 1.818), p)
        finish("ear_lens", cyl(0.014, 0.014, 0.006, 16, "x"), "glow_cyan", 0, 1, T(0.133 * s, 0.025, 1.818), p)
        finish("cheek", box(0.010, 0.085, 0.060), "armor", 0.004, 2, T(0.108 * s, -0.060, 1.775), p)
    finish("fin", prism([(0.030, 1.925), (0.118, 1.900), (0.128, 2.010), (0.085, 2.010)], 0.012, "x"), "frame", 0.003, 2, T(0.050, 0, 0), p)
    pivot("neck", (0, 0.005, 1.66), (0, 0, 1), "torso", p, (-80, 80))

def build(pose=None):
    kit.reset(); parts(pose)

def parts(pose=None):
    """kit.reset() 없이 부품만 만든다 (다른 장면에 넣을 때 쓴다)."""
    materials()
    pose = pose or {"L": {"abduct": -9, "swing": 4, "elbow": 14}, "R": {"abduct": -9, "swing": 6, "elbow": 22}}
    body(); head()
    for s in (1, -1):
        leg(s); arm(s, pose["L" if s > 0 else "R"])

if __name__ == "__main__":
    build()
    os.makedirs(OUT, exist_ok=True)
    if RENDER:
        kit.studio((0, 0, 1.0), 1.0)
        kit.shot(os.path.join(OUT, "robot_front.png"), (-2.3, -4.6, 1.55), (0, 0, 1.02), 70, res=(1000, 1400))
        if sys.argv[2] == "all":
            kit.shot(os.path.join(OUT, "robot_back.png"), (2.6, 4.2, 1.7), (0, 0, 1.05), 70, res=(1000, 1400))
            kit.shot(os.path.join(OUT, "robot_bust.png"), (-0.95, -1.75, 1.72), (0.0, 0, 1.62), 70, dof=5.6)
    for o in [o for o in kit.COL.objects if o.name.startswith("stage_") or o.type in ("LIGHT",)]:
        import bpy; bpy.data.objects.remove(o)
    kit.export(OUT, "security_robot")
