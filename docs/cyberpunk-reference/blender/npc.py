"""거리 NPC (자체 디자인). 얼굴을 가린 미래 도시 거리 사람들: 우비, 테크웨어, 작업자, 배달부, 회사원.
맨얼굴 사람은 사람 생성 도구(MPFB)가 필요해서 이 스크립트는 후드·헬멧·마스크·바이저로 얼굴을 덮은 유형만 만든다.
실행: python npc.py <출력폴더> [render] [이름...]
-Y를 바라보고 선다. 키 약 1.75 m. 부품: pelvis, torso, head, upperarm_L/R, forearm_L/R, thigh_L/R, shin_L/R (+ skirt, prop).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, tube, text, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/npc"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []

def mat_cloth(key, color, rough=0.8, wrinkle=0.6):
    """천: 고운 짜임 + 큰 주름 요철. rough가 낮으면 비닐 우비처럼 번들거린다."""
    m, nt, b = kit._nodes(key)
    var = kit._noise(nt, 7.0, detail=5.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Color1"].default_value = (*color, 1)
    mix.inputs["Color2"].default_value = (0.6, 0.6, 0.62, 1); nt.links.new(kit._ramp(nt, var.outputs["Fac"], 0.35, 0.75, 0.0, 0.6), mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(kit._ramp(nt, var.outputs["Fac"], 0.3, 0.7, rough - 0.08, rough + 0.08), b.inputs["Roughness"])
    w = kit._noise(nt, 14.0, (1, 1, 0.35), 3.0); f = kit._noise(nt, 420.0, detail=2.0)
    h = kit._math(nt, "ADD", kit._math(nt, "MULTIPLY", w.outputs["Fac"], wrinkle), kit._math(nt, "MULTIPLY", f.outputs["Fac"], 0.08))
    kit._bump(nt, b, h, 0.9, 0.012)
    kit.M[key] = m; return m

def soft(ob, lv=2, wrinkle=0.0):
    """부드럽게 다듬고(면 나누기) 주름을 조금 준다."""
    md = ob.modifiers.new("sub", "SUBSURF"); md.levels = lv; md.render_levels = lv
    ob.modifiers.move(len(ob.modifiers) - 1, 0)
    for m in list(ob.modifiers):
        if m.type == "BEVEL": ob.modifiers.remove(m)
    if wrinkle:
        tx = bpy.data.textures.new("wr", "CLOUDS"); tx.noise_scale = 0.09
        d = ob.modifiers.new("wr", "DISPLACE"); d.texture = tx; d.strength = wrinkle; d.mid_level = 0.5
    return ob

def ring(w, d, z, yoff=0.0, n=14, e=2.5):
    pts = []
    for i in range(n):
        a = 2 * pi * i / n; c, s = cos(a), sin(a)
        pts.append((w / 2 * abs(c) ** (2 / e) * (1 if c >= 0 else -1), yoff + d / 2 * abs(s) ** (2 / e) * (1 if s >= 0 else -1), z))
    return pts

SPEC = {
    # 이름: 겉옷 색, 바지 색, 겉옷 길이(z), 겉옷 재질 거칠기, 머리 종류, 발광색, 소품
    "raincoat": {"coat": (0.55, 0.42, 0.03), "pants": (0.02, 0.022, 0.028), "hem": 0.56, "rough": 0.22, "head": "hood", "glow": "glow_cyan", "prop": "umbrella", "pose": "walk"},
    "techwear": {"coat": (0.022, 0.024, 0.030), "pants": (0.17, 0.18, 0.12), "hem": 0.90, "rough": 0.7, "head": "helmet", "glow": "glow_magenta", "prop": "sling", "pose": "stand"},
    "worker": {"coat": (0.75, 0.30, 0.02), "pants": (0.06, 0.08, 0.13), "hem": 0.88, "rough": 0.75, "head": "hardhat", "glow": "glow_amber", "prop": "toolbox", "pose": "walk"},
    "courier": {"coat": (0.10, 0.36, 0.34), "pants": (0.03, 0.03, 0.034), "hem": 0.92, "rough": 0.55, "head": "helmet", "glow": "glow_amber", "prop": "box", "pose": "walk"},
    "office": {"coat": (0.09, 0.085, 0.10), "pants": (0.035, 0.035, 0.04), "hem": 0.50, "rough": 0.85, "head": "cap", "glow": "glow_cyan", "prop": "case", "pose": "stand"},
}
POSES = {
    "stand": {"hipL": -2, "kneeL": 4, "hipR": 4, "kneeR": 8, "armL": (-6, 4, 12), "armR": (-7, -3, 18)},
    "walk": {"hipL": -24, "kneeL": 8, "hipR": 16, "kneeR": 38, "armL": (-5, -20, 22), "armR": (-6, 24, 30)},
}

def leg(s, sp, po):
    side = "L" if s > 0 else "R"; hip = Vector((0.092 * s, 0.0, 0.925))
    Mx = T(*hip) @ frame((0, 0, -1), (0, -1, 0)) @ RY(po["hip" + side])
    p = f"thigh_{side}"; L = 0.43
    pt = lambda x: (0.092 - 0.022 * x / L, 0.098 - 0.026 * x / L)
    soft(finish("thigh", tube(pt, -0.03, L + 0.02, 0.0, 6, 12), "pants", 0, 1, Mx, p), 2, 0.012)
    pivot(f"hip_{side}", hip, (1, 0, 0), "pelvis", p, (-80, 40))
    Mk = Mx @ T(L, 0, 0) @ RY(po["knee" + side]); p = f"shin_{side}"; L2 = 0.42
    ps = lambda x: (0.066 - 0.016 * x / L2 + 0.006 * sin(pi * x / L2), 0.070 - 0.018 * x / L2 + 0.012 * sin(pi * min(1.0, 1.3 * x / L2)))
    soft(finish("shin", tube(ps, -0.03, L2 - 0.10, 0.004, 6, 12), "pants", 0, 1, Mk, p), 2, 0.010)
    finish("knee_pad", box(0.10, 0.095, 0.022, taper=0.85), "gear", 0.008, 3, Mk @ T(0.0, 0, 0.066), p)
    soft(finish("boot_shaft", tube(lambda x: (0.058, 0.062), L2 - 0.17, L2 - 0.01, 0.0, 3, 12), "boot", 0, 1, Mk, p), 2)
    for k in range(3): finish("boot_strap", torus(0.061, 0.006, 16, 6, "x"), "gear", 0, 1, Mk @ T(L2 - 0.15 + 0.045 * k, 0, 0), p)
    pivot(f"knee_{side}", Mk.translation, (1, 0, 0), f"thigh_{side}", p, (0, 140))
    # 발: 정강이 방향을 따라 기울인다
    Ma = Mk @ T(L2, 0, 0)
    Fm = Ma @ frame((0, 0, -1), (0, -1, 0)).inverted()
    finish("boot", prism([(-0.185, -0.070), (-0.185, -0.030), (-0.120, 0.012), (-0.050, 0.030), (0.075, 0.030), (0.085, -0.070)], 0.100, "x"), "boot", 0.014, 3, Fm, p)
    finish("boot_sole", prism([(-0.190, -0.086), (-0.190, -0.066), (0.090, -0.066), (0.090, -0.086)], 0.106, "x"), "sole", 0.006, 2, Fm, p)
    finish("boot_toe", prism([(-0.188, -0.066), (-0.188, -0.036), (-0.140, -0.012), (-0.120, -0.066)], 0.104, "x"), "gear", 0.008, 2, Fm, p)

def arm(s, sp, po):
    side = "L" if s > 0 else "R"; sh = Vector((0.205 * s, 0.0, 1.425)); ab, sw, el = po["arm" + side]
    Mx = T(*sh) @ frame((0, 0, -1), (s, 0, 0)) @ RY(ab) @ RZ(-s * sw)
    p = f"upperarm_{side}"; L = 0.285
    soft(finish("sleeve_upper", tube(lambda x: (0.068 - 0.010 * x / L, 0.068 - 0.010 * x / L), -0.04, L + 0.02, 0.0, 5, 12), "coat", 0, 1, Mx, p), 2, 0.012)
    finish("shoulder_patch", box(0.07, 0.06, 0.004), sp["glow"], 0, 1, Mx @ T(0.085, 0, 0.066), p)
    pivot(f"shoulder_{side}", sh, (1, 0, 0), "torso", p, (-170, 60))
    Me = Mx @ T(L, 0, 0) @ RZ(-s * el); p = f"forearm_{side}"; L2 = 0.255
    soft(finish("sleeve_lower", tube(lambda x: (0.058 - 0.010 * x / L2, 0.058 - 0.010 * x / L2), -0.03, L2 - 0.01, 0.0, 5, 12), "coat", 0, 1, Me, p), 2, 0.010)
    finish("cuff", torus(0.050, 0.010, 18, 8, "x"), "gear", 0, 1, Me @ T(L2 - 0.02, 0, 0), p)
    Mh = Me @ T(L2 + 0.005, 0, 0) @ RY(10)
    finish("glove", box(0.095, 0.078, 0.032, True, 0.95, 0.8), "glove", 0.012, 3, Mh, p)
    finish("glove_fingers", box(0.070, 0.074, 0.026, True, 0.9, 0.8), "glove", 0.010, 3, Mh @ T(0.092, 0, -0.004) @ RY(28), p)
    finish("glove_thumb", box(0.055, 0.024, 0.024, True, 0.85), "glove", 0.008, 2, Mh @ T(0.025, -0.044 * s, -0.006) @ RZ(-30 * s) @ RY(20), p)
    finish("glove_plate", box(0.050, 0.055, 0.008, True), "gear", 0.004, 2, Mh @ T(0.014, 0, 0.018), p)
    pivot(f"elbow_{side}", Me.translation, tuple(Me.to_3x3() @ Vector((0, 0, 1))), f"upperarm_{side}", p, (0, 145))
    return Mh

def torso(sp):
    soft(finish("pelvis", loft([ring(0.30, 0.20, 0.84), ring(0.35, 0.225, 0.93), ring(0.31, 0.20, 1.02)]), "pants", 0, 1, part="pelvis"), 2, 0.008)
    finish("belt", loft([ring(0.335, 0.225, 0.995), ring(0.335, 0.225, 1.035)], False), "gear", 0, 1, part="pelvis")
    finish("buckle", box(0.06, 0.02, 0.045), "titan", 0.004, 2, T(0, -0.114, 1.015), "pelvis")
    hem = sp["hem"]; rings = [ring(0.20, 0.17, 1.535, 0.005), ring(0.44, 0.23, 1.465), ring(0.46, 0.265, 1.33), ring(0.40, 0.25, 1.10), ring(0.42, 0.26, 0.96)]
    soft(finish("jacket", loft(rings), "coat", 0, 1, part="torso"), 2, 0.016)
    finish("zip", box(0.014, 0.012, 0.50), "gear", 0.002, 1, T(0, -0.134, 1.22) @ RX(-2), "torso")
    finish("collar", torus(0.085, 0.028, 20, 8, "z"), "coat", 0, 1, T(0, 0.005, 1.525) @ S(1, 0.9, 1.5), "torso")
    for s in (-1, 1):
        finish("chest_pocket", box(0.10, 0.02, 0.085), "coat", 0.008, 2, T(0.115 * s, -0.128, 1.30) @ RZ(8 * s), "torso")
        finish("pocket_flap", box(0.105, 0.022, 0.028), "gear", 0.004, 2, T(0.115 * s, -0.132, 1.335) @ RZ(8 * s), "torso")
    if hem < 0.85:
        # 긴 옷자락: 따로 흔들 수 있게 부품을 나눈다
        soft(finish("skirt", loft([ring(0.42, 0.26, 0.97), ring(0.47, 0.30, 0.80), ring(0.52, 0.34, hem + 0.02), ring(0.50, 0.33, hem)], False), "coat", 0, 1, part="skirt"), 2, 0.02)
        pivot("skirt", (0, 0, 0.97), (1, 0, 0), "torso", "skirt", (-25, 25))
    pivot("waist", (0, 0, 1.02), (0, 0, 1), "pelvis", "torso", (-40, 40))

def head(sp):
    p = "head"; g = sp["glow"]
    finish("neck", cyl(0.052, 0.058, 0.09, 14, "z"), "under", 0, 1, T(0, 0.01, 1.535), p)
    soft(finish("head_base", sphere(0.105, 0.92, 1.05, 1.12, 16, 10), "under", 0, 1, T(0, 0.0, 1.635), p), 1)
    kind = sp["head"]
    if kind == "hood":
        soft(finish("hood", sphere(0.135, 1.0, 1.12, 1.14, 16, 10), "coat", 0, 1, T(0, 0.022, 1.640), p), 1, 0.01)
        finish("hood_open", sphere(0.098, 1.0, 0.55, 1.05, 16, 10), "black", 0, 1, T(0, -0.098, 1.628), p)
        finish("respirator", box(0.095, 0.050, 0.064), "gear", 0.012, 3, T(0, -0.128, 1.588), p)
        for s in (-1, 1):
            finish("filter", cyl(0.030, 0.026, 0.040, 16, "x"), "gunmetal", 0.004, 2, T(0.062 * s, -0.112, 1.582), p)
            finish("goggle_frame", cyl(0.032, 0.032, 0.022, 18, "y"), "gear", 0.003, 2, T(0.038 * s, -0.132, 1.652), p)
            finish("goggle_lens", cyl(0.025, 0.025, 0.004, 18, "y"), g, 0, 1, T(0.038 * s, -0.144, 1.652), p)
    elif kind == "helmet":
        soft(finish("helmet", sphere(0.128, 0.96, 1.10, 1.06, 16, 10), "helmet", 0, 1, T(0, 0.0, 1.650), p), 2)
        finish("visor", box(0.196, 0.030, 0.078), "glass", 0.012, 3, T(0, -0.120, 1.650) @ RX(8), p)
        finish("visor_line", box(0.150, 0.004, 0.006), g, 0, 1, T(0, -0.1365, 1.668) @ RX(8), p)
        finish("chin", box(0.13, 0.07, 0.05), "helmet", 0.014, 3, T(0, -0.098, 1.572), p)
        for s in (-1, 1): finish("ear_cup", cyl(0.036, 0.032, 0.022, 16, "x"), "gear", 0.004, 2, T(0.118 * s, 0.01, 1.640), p)
        finish("helmet_ridge", box(0.03, 0.22, 0.02), "gear", 0.006, 2, T(0, 0.01, 1.778) @ RX(-4), p)
    elif kind == "hardhat":
        soft(finish("hat", sphere(0.125, 1.0, 1.12, 0.78, 16, 10), "helmet", 0, 1, T(0, 0.0, 1.705), p), 2)
        finish("hat_brim", cyl(0.150, 0.150, 0.012, 24, "z"), "helmet", 0.003, 2, T(0, -0.025, 1.700) @ S(1, 1.15, 1), p)
        finish("hat_lamp", box(0.05, 0.03, 0.035), "gear", 0.006, 2, T(0, -0.130, 1.735), p)
        finish("hat_lamp_lens", box(0.036, 0.004, 0.022), "glow_white", 0, 1, T(0, -0.146, 1.735), p)
        finish("goggles", box(0.170, 0.026, 0.046), "gear", 0.010, 3, T(0, -0.098, 1.655), p)
        finish("goggles_lens", box(0.150, 0.004, 0.028), g, 0, 1, T(0, -0.112, 1.655), p)
        finish("half_mask", box(0.11, 0.05, 0.07), "gear", 0.014, 3, T(0, -0.092, 1.582), p)
    else:
        finish("cap", cyl(0.108, 0.100, 0.06, 20, "z"), "coat", 0.012, 3, T(0, 0.0, 1.740) @ S(1, 1.1, 1), p)
        finish("cap_brim", box(0.15, 0.10, 0.010), "coat", 0.004, 2, T(0, -0.135, 1.722) @ RX(-8), p)
        finish("ar_visor", box(0.176, 0.018, 0.036), "glass", 0.008, 3, T(0, -0.102, 1.660), p)
        finish("ar_line", box(0.150, 0.004, 0.005), g, 0, 1, T(0, -0.112, 1.668), p)
        soft(finish("scarf", torus(0.105, 0.045, 18, 8, "z"), "scarf", 0, 1, T(0, -0.005, 1.545) @ S(1, 1.0, 1.25), p), 1, 0.012)
        finish("mask", box(0.12, 0.04, 0.075), "scarf", 0.016, 3, T(0, -0.088, 1.590), p)
    pivot("neck", (0, 0.01, 1.52), (0, 0, 1), "torso", p, (-80, 80))

def prop(sp, MhL, MhR):
    k = sp["prop"]; p = "prop"
    if k == "umbrella": pivot("prop", MhR.translation, (1, 0, 0), "forearm_R", "prop", (0, 0))
    elif k in ("toolbox", "case"): pivot("prop", MhL.translation, (1, 0, 0), "forearm_L", "prop", (0, 0))
    if k == "umbrella":
        Mu = MhR @ T(0.05, 0, 0) @ MhR.to_3x3().to_4x4().inverted()
        finish("umbrella_pole", cyl(0.008, 0.008, 0.95, 8, "z"), "gunmetal", 0, 1, Mu @ T(0, 0, 0.42), p)
        finish("umbrella_canopy", cyl(0.56, 0.03, 0.17, 10, "z"), "umbrella", 0, 1, Mu @ T(0, 0, 0.93), p, smooth=False)
        finish("umbrella_rim", torus(0.56, 0.008, 10, 6, "z"), sp["glow"], 0, 1, Mu @ T(0, 0, 0.845), p)
        finish("umbrella_handle", cyl(0.014, 0.014, 0.10, 10, "z"), "gear", 0, 1, Mu @ T(0, 0, -0.03), p)
    elif k == "box":
        finish("pack_box", box(0.36, 0.30, 0.40), "helmet", 0.02, 3, T(0, 0.28, 1.30), "torso")
        finish("pack_logo", box(0.20, 0.006, 0.20), sp["glow"], 0, 1, T(0, 0.433, 1.30), "torso")
        text("pack_text", "TEKKA", 0.06, frame((-1, 0, 0), (0, 1, 0), (0, 0.437, 1.30)), "black", "torso", 0.002)
        for s in (-1, 1): finish("pack_strap", box(0.04, 0.26, 0.30), "gear", 0.008, 2, T(0.12 * s, 0.0, 1.36) @ RX(0), "torso")
    elif k == "toolbox":
        Mt = MhL @ T(0.07, 0, 0) @ MhL.to_3x3().to_4x4().inverted()
        finish("toolbox", box(0.16, 0.34, 0.16), "helmet", 0.015, 3, Mt @ T(0, 0, -0.14), p)
        finish("toolbox_handle", box(0.02, 0.14, 0.05), "gear", 0.006, 2, Mt @ T(0, 0, -0.035), p)
        for z in (1.12, 1.30):
            finish("hivis", loft([ring(0.47, 0.275, z), ring(0.47, 0.275, z + 0.045)], False), "glow_strip", 0, 1, part="torso")
    elif k == "case":
        Mt = MhL @ T(0.07, 0, 0) @ MhL.to_3x3().to_4x4().inverted()
        finish("case", box(0.09, 0.42, 0.30), "gear", 0.015, 3, Mt @ T(0, 0, -0.20), p)
        finish("case_handle", box(0.02, 0.12, 0.04), "gunmetal", 0.006, 2, Mt @ T(0, 0, -0.03), p)
        finish("case_light", box(0.092, 0.06, 0.008), sp["glow"], 0, 1, Mt @ T(0, 0.10, -0.10), p)
    else:
        finish("sling_bag", box(0.20, 0.10, 0.28), "gear", 0.03, 3, T(-0.12, 0.17, 1.18) @ RY(18), "torso")
        finish("sling_strap", box(0.05, 0.02, 0.62), "gear", 0.006, 2, T(0.02, -0.138, 1.27) @ RY(-38), "torso")
        finish("sling_light", box(0.06, 0.006, 0.012), sp["glow"], 0, 1, T(-0.12, 0.222, 1.25) @ RY(18), "torso")

def parts(name):
    sp = SPEC[name]; po = POSES[sp["pose"]]
    mat_cloth("coat", sp["coat"], sp["rough"]); mat_cloth("pants", sp["pants"], 0.82, 0.5); mat_cloth("under", (0.015, 0.015, 0.018), 0.85, 0.3)
    mat_cloth("scarf", (0.40, 0.05, 0.08), 0.9, 0.8); mat_cloth("glove", (0.02, 0.02, 0.022), 0.6, 0.2)
    kit.mat_simple("boot", (0.014, 0.014, 0.016), 0.0, 0.42); kit.mat_simple("sole", (0.02, 0.02, 0.02), 0.0, 0.8)
    kit.mat_paint("gear", (0.05, 0.052, 0.058), (0.45, 0.45, 0.45), rough=(0.36, 0.55), wear=1.5, scale=0.6)
    kit.mat_paint("helmet", tuple(min(1, c * 1.15 + 0.02) for c in sp["coat"]), rough=(0.20, 0.36), wear=1.3, scale=0.6)
    kit.mat_simple("umbrella", (0.01, 0.012, 0.016), 0.0, 0.12); kit.mat_simple("glow_strip", (0.4, 0.4, 0.38), 0.0, 0.3, (0.9, 0.9, 0.7), 1.2)
    torso(sp); head(sp); hands = {}
    for s in (1, -1):
        leg(s, sp, po); hands[s] = arm(s, sp, po)
    prop(sp, hands[1], hands[-1])

def build(name):
    kit.reset(); parts(name)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name in SPEC:
        if ONLY and name not in ONLY: continue
        build(name)
        if RENDER:
            kit.studio((0, 0, 0.95), 1.0)
            res = tuple(int(c) for c in os.environ.get("NPC_RES", "900,1350").split(","))
            kit.shot(os.path.join(OUT, f"npc_{name}.png"), (-2.0, -4.3, 1.45), (0, 0, 0.98), 70, res=res)
            for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
        kit.export(os.path.join(OUT, name), "npc_" + name)
