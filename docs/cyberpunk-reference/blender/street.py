"""배경: 거리 소품 모듈 + 건물 생성기 + 밤거리 장면(분위기 목표 그림).
실행: python street.py <출력폴더> scene   -> 밤거리 장면 렌더 (street_night.png)
      python street.py <출력폴더> modules -> 소품 모듈을 하나씩 GLB + manifest로 내보내고 모음 사진을 찍는다
간판 규칙: 가게 간판은 가게 위에만 하나, 돌출 간판은 받침대와 함께, 영웅 광고는 한 장면에 하나.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, text, cable, pivot, frame, RX, RY, RZ, T, S

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/street"
MODE = sys.argv[2] if len(sys.argv) > 2 else "scene"
NEON = ["glow_magenta", "glow_cyan", "glow_amber", "glow_red", "glow_white"]
BRANDS = ["KIRO", "ZENTH", "HALO 9", "MIRU", "VANTA", "LUMEN", "ORBIT", "NAMU", "SORA", "TEKKA"]

def materials():
    kit.mat_concrete("concrete", (0.26, 0.25, 0.24)); kit.mat_concrete("concrete_dark", (0.12, 0.12, 0.125))
    kit.mat_concrete("sidewalk", (0.20, 0.20, 0.205), 3.0); kit.mat_wet_asphalt("asphalt")
    kit.mat_paint("prop_paint", (0.10, 0.22, 0.30), scale=0.4, wear=1.5); kit.mat_paint("prop_red", (0.45, 0.03, 0.03), scale=0.4, wear=1.5)
    kit.mat_paint("prop_yellow", (0.80, 0.50, 0.02), scale=0.4, wear=1.5)
    kit.mat_simple("win_dark", (0.006, 0.009, 0.014), 0.0, 0.06)
    kit.mat_simple("win_warm", (0, 0, 0), 0, 0.4, (1.0, 0.58, 0.26), 1.0); kit.mat_simple("win_cool", (0, 0, 0), 0, 0.4, (0.45, 0.78, 1.0), 0.8)
    kit.mat_simple("win_pink", (0, 0, 0), 0, 0.4, (1.0, 0.25, 0.6), 1.2)
    kit.mat_simple("shop_glow", (0, 0, 0), 0, 0.4, (1.0, 0.8, 0.55), 0.55); kit.mat_simple("sodium", (0, 0, 0), 0, 0.4, (1.0, 0.52, 0.16), 14.0)
    kit.mat_simple("paint_line", (0.55, 0.55, 0.5), 0.0, 0.5); kit.mat_simple("cloth", (0.30, 0.05, 0.04), 0.0, 0.8)
    kit.mat_simple("trash", (0.01, 0.01, 0.012), 0.0, 0.35)
    kit.mat_windows("far_windows", ratio=0.20, cell=(4.5, 4.2), strength=2.2)
    kit.mat_windows("tower_glass", wall=(0.01, 0.014, 0.02), lit=(0.6, 0.85, 1.0), lit2=(1.0, 0.75, 0.5), ratio=0.35, cell=(3.0, 3.6), strength=1.2)

class Multi:
    """상자 여러 개를 메시 하나로 모은다 (창문·실외기처럼 수가 많은 것)."""
    def __init__(self): self.bm = bmesh.new()
    def add(self, sx, sy, sz, Mx): bmesh.ops.create_cube(self.bm, size=1.0, matrix=Mx @ S(sx, sy, sz))
    def done(self, name, mat, bevel=0.0, part=None):
        if len(self.bm.verts): return finish(name, self.bm, mat, bevel, 1, part=part, smooth=False)

# ------------------------------------------------------------------ 소품 모듈 (원점 = 바닥 중심, 앞 = -Y)
def lamp(Mx=Matrix.Identity(4), part="lamp", light=False):
    finish("lamp_base", cyl(0.22, 0.16, 0.5, 12, "z"), "gunmetal", 0.01, 1, Mx @ T(0, 0, 0.25), part)
    finish("lamp_pole", cyl(0.09, 0.07, 7.6, 12, "z"), "gunmetal", 0, 1, Mx @ T(0, 0, 4.3), part)
    finish("lamp_arm", box(0.12, 2.4, 0.12), "gunmetal", 0.01, 1, Mx @ T(0, -1.1, 8.0) @ RX(-6), part)
    finish("lamp_head", box(0.42, 1.0, 0.14), "dark", 0.02, 2, Mx @ T(0, -2.1, 8.08), part)
    finish("lamp_glow", box(0.30, 0.8, 0.02), "sodium", 0, 1, Mx @ T(0, -2.1, 8.0), part)
    finish("lamp_box", box(0.3, 0.2, 0.5), "prop_paint", 0.01, 1, Mx @ T(0, 0.12, 1.6), part)
    if light:
        ld = bpy.data.lights.new("lamp_spot", "SPOT"); ld.energy = 1500; ld.color = (1.0, 0.56, 0.2); ld.spot_size = radians(115); ld.spot_blend = 0.6; ld.shadow_soft_size = 0.3
        lo = bpy.data.objects.new("lamp_spot", ld); kit.COL.objects.link(lo); lo.matrix_world = Mx @ T(0, -2.1, 7.9)

def vending(Mx=Matrix.Identity(4), part="vending", col="glow_cyan"):
    finish("vend_body", box(1.1, 0.8, 1.95, z0=True), "prop_paint", 0.03, 2, Mx, part)
    finish("vend_screen", box(0.92, 0.02, 1.05), col, 0, 1, Mx @ T(0, -0.405, 1.28), part)
    finish("vend_slot", box(0.8, 0.03, 0.22), "black", 0.01, 1, Mx @ T(0, -0.40, 0.42), part)
    finish("vend_pay", box(0.14, 0.03, 0.3), "black", 0.01, 1, Mx @ T(0.44, -0.41, 0.95), part)
    for k in range(4): finish("vend_row", box(0.86, 0.03, 0.02), "black", 0, 1, Mx @ T(0, -0.412, 0.9 + 0.25 * k), part)
    text("vend_text", "ORBIT", 0.2, Mx @ frame((1, 0, 0), (0, -1, 0), (0, -0.42, 1.78)), "glow_white", part, 0.004)

def ac_unit(Mx=Matrix.Identity(4), part="ac_unit"):
    finish("ac_body", box(0.95, 0.38, 0.65), "titan", 0.02, 2, Mx, part)
    finish("ac_fan", cyl(0.24, 0.24, 0.02, 20, "y"), "black", 0, 1, Mx @ T(-0.14, -0.195, 0), part)
    finish("ac_grill", torus(0.25, 0.012, 20, 6, "y"), "gunmetal", 0, 1, Mx @ T(-0.14, -0.2, 0), part)
    finish("ac_bracket", box(1.0, 0.45, 0.04), "gunmetal", 0.005, 1, Mx @ T(0, 0.02, -0.35), part)

def barrier(Mx=Matrix.Identity(4), part="barrier"):
    finish("barrier_body", prism([(-0.30, 0), (0.30, 0), (0.12, 0.85), (-0.12, 0.85)], 2.0, "x"), "concrete", 0.03, 2, Mx @ RZ(90), part)
    for k in range(4): finish("barrier_stripe", box(0.30, 0.012, 0.14), "prop_yellow", 0, 1, Mx @ T(-0.75 + 0.5 * k, -0.2, 0.5) @ RX(-12), part)
    finish("barrier_lamp", box(0.12, 0.08, 0.10), "glow_amber", 0, 1, Mx @ T(0, 0, 0.92), part)

def trash(Mx=Matrix.Identity(4), part="trash", seed=1):
    r = random.Random(seed)
    for k in range(6):
        finish("bag", sphere(0.32 + r.random() * 0.14, 1, 1, 0.75, 14, 8), "trash", 0, 1, Mx @ T(r.uniform(-0.8, 0.8), r.uniform(-0.4, 0.4), 0.2 + (0.25 if k > 3 else 0)), part)
    finish("bin", box(1.3, 0.9, 1.15, z0=True), "prop_paint", 0.03, 2, Mx @ T(1.5, 0.1, 0), part)
    finish("bin_lid", box(1.36, 0.96, 0.08), "gunmetal", 0.02, 2, Mx @ T(1.5, 0.1, 1.19) @ RX(5), part)

def stall(Mx=Matrix.Identity(4), part="stall"):
    finish("stall_counter", box(2.6, 1.2, 0.95, z0=True), "prop_red", 0.03, 2, Mx, part)
    finish("stall_top", box(2.7, 1.3, 0.06), "titan", 0.01, 1, Mx @ T(0, 0, 0.98), part)
    for x in (-1.25, 1.25):
        for y in (-0.55, 0.55): finish("stall_post", cyl(0.03, 0.03, 1.6, 8, "z"), "gunmetal", 0, 1, Mx @ T(x, y, 1.8), part)
    finish("stall_awning", box(3.2, 2.2, 0.05), "cloth", 0.01, 1, Mx @ T(0, -0.35, 2.62) @ RX(12), part)
    finish("stall_light", box(2.4, 0.06, 0.06), "glow_white", 0, 1, Mx @ T(0, -0.3, 2.42), part)
    for k in range(7): finish("stall_bulb", sphere(0.05, 1, 1, 1, 8, 6), "glow_amber", 0, 1, Mx @ T(-1.35 + 0.45 * k, -1.38, 2.32 - 0.05 * sin(k * 1.05)), part)
    finish("stall_pot", cyl(0.28, 0.24, 0.3, 16, "z"), "steel", 0.01, 1, Mx @ T(0.6, 0, 1.16), part)
    text("stall_text", "NAMU", 0.26, Mx @ frame((1, 0, 0), (0, -1, 0), (0, -0.61, 0.55)), "glow_amber", part, 0.004)

def blade_sign(Mx=Matrix.Identity(4), part="blade_sign", word="KIRO", col="glow_magenta", h=4.2):
    """벽에서 튀어나온 세로 간판. 원점 = 벽 붙는 점, +X 쪽으로 나온다. 글자는 -Y를 본다."""
    finish("sign_bracket", box(1.5, 0.08, 0.08), "gunmetal", 0.005, 1, Mx @ T(0.7, 0, h / 2 - 0.2), part)
    finish("sign_bracket2", box(1.5, 0.08, 0.08), "gunmetal", 0.005, 1, Mx @ T(0.7, 0, -h / 2 + 0.2), part)
    finish("sign_body", box(1.05, 0.22, h), "black", 0.02, 2, Mx @ T(0.95, 0, 0), part)
    finish("sign_border", box(1.13, 0.10, h + 0.08), col, 0, 1, Mx @ T(0.95, 0, 0), part)
    step = (h - 0.6) / max(1, len(word))
    for i, ch in enumerate(word):
        if ch != " ": text("sign_ch", ch, 0.62, Mx @ frame((1, 0, 0), (0, -1, 0), (0.95, -0.125, h / 2 - 0.55 - i * step)), "glow_white", part, 0.006)

def billboard(Mx=Matrix.Identity(4), part="billboard", w=9.0, h=4.5, word="ZENTH", col=(1.0, 0.1, 0.45), col2=(0.1, 0.6, 1.0)):
    """받침 구조가 있는 중형 광고판. 화면은 -Y를 본다."""
    for x in (-w / 2 + 0.4, 0, w / 2 - 0.4):
        finish("bb_leg", box(0.16, 0.16, 2.6), "gunmetal", 0.01, 1, Mx @ T(x, 0.5, -1.2), part)
        finish("bb_brace", box(0.10, 0.10, 3.2), "gunmetal", 0.01, 1, Mx @ T(x, 1.4, -0.9) @ RX(-38), part)
    finish("bb_frame", box(w + 0.3, 0.35, h + 0.3), "gunmetal", 0.03, 2, Mx @ T(0, 0.2, h / 2 + 0.2), part)
    key = f"ad_{word}"
    if key not in kit.M:
        m, nt, b = kit._nodes(key); tc = nt.nodes.new("ShaderNodeTexCoord"); gr = nt.nodes.new("ShaderNodeTexGradient")
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0.9, 0)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMixRGB"); mix.inputs["Color1"].default_value = (*col, 1); mix.inputs["Color2"].default_value = (*col2, 1)
        nt.links.new(gr.outputs["Fac"], mix.inputs["Fac"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(mix.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.6; kit.M[key] = m
    finish("bb_screen", box(w, 0.05, h), key, 0, 1, Mx @ T(0, 0.0, h / 2 + 0.2), part)
    text("bb_text", word, h * 0.42, Mx @ frame((1, 0, 0), (0, -1, 0), (0, -0.06, h / 2 + 0.35)), "glow_white", part, 0.01)

def monorail(Mx=Matrix.Identity(4), part="monorail", span=44.0, train=True):
    """도로를 가로지르는 고가 선로 (X 방향). 원점 = 선로 중심 바닥."""
    finish("rail_beam", box(span, 2.4, 1.5), "concrete", 0.08, 2, Mx @ T(0, 0, 0.75), part)
    finish("rail_top", box(span, 0.9, 0.5), "concrete_dark", 0.04, 1, Mx @ T(0, 0, 1.75), part)
    for k in range(int(span // 4)): finish("rail_rib", box(0.5, 2.7, 1.1), "concrete_dark", 0.04, 1, Mx @ T(-span / 2 + 2 + 4 * k, 0, 0.55), part)
    finish("rail_cable", box(span, 0.12, 0.12), "gunmetal", 0, 1, Mx @ T(0, 1.35, 0.4), part)
    for s in (-1, 1): finish("rail_strip", box(span, 0.04, 0.06), "glow_cyan", 0, 1, Mx @ T(0, 1.22 * s, 1.45), part)
    if train:
        p = "train"
        finish("train_body", box(16.0, 2.6, 2.7), "titan", 0.25, 3, Mx @ T(3.0, 0, 3.4), p)
        finish("train_skirt", box(15.6, 2.8, 0.7), "gunmetal", 0.1, 2, Mx @ T(3.0, 0, 2.3), p)
        finish("train_windows", box(14.6, 2.64, 0.8), "win_cool", 0, 1, Mx @ T(3.0, 0, 3.75), p)
        finish("train_stripe", box(15.2, 2.66, 0.12), "glow_magenta", 0, 1, Mx @ T(3.0, 0, 2.95), p)

def pillar(Mx=Matrix.Identity(4), part="pillar", h=15.0):
    finish("pillar", cyl(1.0, 0.85, h, 16, "z"), "concrete", 0, 1, Mx @ T(0, 0, h / 2), part)
    finish("pillar_cap", box(3.4, 3.0, 1.2, taper=1.0), "concrete", 0.1, 2, Mx @ T(0, 0, h - 0.6), part)
    finish("pillar_band", cyl(1.04, 1.04, 0.5, 16, "z"), "prop_yellow", 0, 1, Mx @ T(0, 0, 1.3), part)

# ------------------------------------------------------------------ 건물
def building(side, y0, y1, depth, h, seed, style="old", shops=True):
    """side = -1(왼쪽, 벽면이 +X를 봄) 또는 +1(오른쪽). 거리 쪽 벽은 x = 11 * side."""
    r = random.Random(seed); xf = 11.0 * side; xc = xf + side * depth / 2; yc = (y0 + y1) / 2; L = y1 - y0
    wall = "tower_glass" if style == "corp" else ("concrete" if r.random() < 0.6 else "concrete_dark")
    finish("bld_body", box(depth, L, h, z0=True), wall, 0, 1, T(xc, yc, 0), smooth=False)
    if style == "corp":
        for z in range(8, int(h), 12): finish("bld_band", box(depth + 0.6, L + 0.6, 0.5), "gunmetal", 0, 1, T(xc, yc, z), smooth=False)
        finish("bld_crown", box(depth - 3, L - 3, 3.0, z0=True), "gunmetal", 0, 1, T(xc, yc, h), smooth=False)
        finish("bld_logo", box(0.3, 6.0, 2.2), "glow_cyan", 0, 1, T(xf - side * 0.2, yc, h - 3.0), smooth=False)
        return
    dark, warm, cool, pink, bands, fins, acs, mull = Multi(), Multi(), Multi(), Multi(), Multi(), Multi(), Multi(), Multi()
    z = 5.2
    while z < h - 2.0:
        bands.add(0.5, L + 0.3, 0.35, T(xf - side * 0.15, yc, z - 1.25))
        y = y0 + 1.8
        while y < y1 - 1.2:
            k = r.random(); m = warm if k < 0.15 else cool if k < 0.21 else pink if k < 0.235 else dark
            m.add(0.10, 1.7, 1.55, T(xf - side * 0.03, y, z))
            mull.add(0.14, 0.07, 1.6, T(xf - side * 0.05, y, z)); mull.add(0.14, 1.75, 0.07, T(xf - side * 0.05, y, z + 0.25)); mull.add(0.2, 1.95, 0.12, T(xf - side * 0.1, y, z - 0.86))
            if r.random() < 0.16: acs.add(0.45, 0.95, 0.6, T(xf - side * 0.28, y + 0.3, z - 1.15))
            y += 3.2
        z += 3.6
    y = y0 + 0.2
    while y < y1:
        fins.add(0.35, 0.35, h - 4.4, T(xf - side * 0.12, y, 4.4 + (h - 4.4) / 2)); y += 6.4
    # 카메라 쪽(-Y) 옆벽: 위층만 창을 낸다
    z = 5.2
    while z < h - 2.0:
        x = xf + side * 2.0
        while abs(x - xf) < depth - 1.5:
            k = r.random(); m = warm if k < 0.16 else cool if k < 0.22 else dark
            m.add(1.7, 0.10, 1.55, T(x, y0 - 0.03, z)); mull.add(0.07, 0.14, 1.6, T(x, y0 - 0.05, z)); mull.add(1.75, 0.14, 0.07, T(x, y0 - 0.05, z + 0.25)); x += side * 3.4
        z += 3.6
    for mm, nm, mt in ((dark, "win", "win_dark"), (warm, "win_warm", "win_warm"), (cool, "win_cool", "win_cool"), (pink, "win_pink", "win_pink"),
                       (bands, "bands", "concrete_dark"), (fins, "fins", "concrete_dark"), (acs, "acs", "titan"), (mull, "mullions", "gunmetal")):
        mm.done("bld_" + nm, mt)
    # 옥상
    finish("roof_parapet", box(depth + 0.4, L + 0.4, 0.9, z0=True), "concrete_dark", 0, 1, T(xc, yc, h), smooth=False)
    finish("roof_tank", cyl(1.6, 1.6, 2.6, 16, "z"), "titan", 0, 1, T(xc + side * r.uniform(-2, 2), yc + r.uniform(-L / 4, L / 4), h + 2.6))
    finish("roof_mast", cyl(0.08, 0.05, 9.0, 6, "z"), "gunmetal", 0, 1, T(xc, y0 + 2.0, h + 4.5))
    finish("roof_beacon", sphere(0.22, 1, 1, 1, 8, 6), "glow_red", 0, 1, T(xc, y0 + 2.0, h + 9.1))
    # 1층 가게: 가게마다 간판은 하나
    if shops:
        y = y0 + 0.6; i = 0
        while y + 5.6 < y1:
            closed = r.random() < 0.3
            finish("shop_front", box(0.12, 5.0, 3.1), "gunmetal" if closed else "shop_glow", 0, 1, T(xf - side * 0.05, y + 2.8, 1.75), smooth=False)
            finish("shop_frame", box(0.3, 5.4, 0.5), "concrete_dark", 0, 1, T(xf - side * 0.12, y + 2.8, 3.75), smooth=False)
            for q in range(4): finish("shop_mullion", box(0.18, 0.09, 3.1), "gunmetal", 0, 1, T(xf - side * 0.08, y + 0.4 + q * 1.6, 1.75), smooth=False)
            if not closed:
                finish("shop_awning", box(1.7, 5.2, 0.07), "cloth", 0, 1, T(xf - side * 0.95, y + 2.8, 3.25) @ RY(side * 14), smooth=False)
                word = r.choice(BRANDS); colr = r.choice(NEON[:4])
                finish("shop_sign", box(0.16, 4.2, 0.85), "black", 0, 1, T(xf - side * 0.2, y + 2.8, 4.55), smooth=False)
                text("shop_text", word, 0.55, frame((0, -side, 0), (-side, 0, 0), (xf - side * 0.30, y + 2.8, 4.55)), colr, None, 0.01)
            y += 6.2; i += 1

def megastructure(x, y, w, d, h, taper=0.7, logo=None):
    rings = []
    for k, t in enumerate((0, 0.35, 0.36, 0.7, 0.71, 1.0)):
        f = 1.0 - (1.0 - taper) * (k // 2) / 2.0
        rings.append([(x - w / 2 * f, y - d / 2 * f, h * t), (x + w / 2 * f, y - d / 2 * f, h * t), (x + w / 2 * f, y + d / 2 * f, h * t), (x - w / 2 * f, y + d / 2 * f, h * t)])
    finish("mega", loft(rings), "far_windows", 0, 1, smooth=False)
    for sx in (-1, 1): finish("mega_beacon", sphere(1.6, 1, 1, 1, 8, 6), "glow_red", 0, 1, T(x + sx * w * taper * 0.4, y, h + 2))
    if logo: finish("mega_logo", box(w * taper * 0.5, 1.0, h * 0.035), logo, 0, 1, T(x, y - d / 2 * taper - 0.6, h * 0.93), smooth=False)

def place(fn, Mx):
    before = set(kit.COL.objects); fn()
    for o in set(kit.COL.objects) - before: o.matrix_world = Mx @ o.matrix_world

# ------------------------------------------------------------------ 장면
def scene(day=False):
    sc = kit.reset(); materials(); R = random.Random(7)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.010, 0.012, 0.030, 1)
    # 바닥
    finish("road", box(14.0, 520.0, 0.2), "asphalt", 0, 1, T(0, 220, -0.1), smooth=False)
    for s in (-1, 1):
        finish("sidewalk", box(4.0, 520.0, 0.36), "sidewalk", 0, 1, T(9.0 * s, 220, 0.0), smooth=False)
        finish("curb", box(0.3, 520.0, 0.40), "concrete", 0, 1, T(7.05 * s, 220, 0.0), smooth=False)
        finish("ground", box(120.0, 520.0, 0.2), "concrete_dark", 0, 1, T(71.0 * s, 220, -0.1), smooth=False)
    lines = Multi()
    for k in range(40): lines.add(0.16, 3.0, 0.012, T(0, -12 + k * 7.0, 0.006))
    for s in (-1, 1): lines.add(0.14, 300.0, 0.012, T(6.4 * s, 130, 0.006))
    for k in range(9): lines.add(0.55, 4.2, 0.012, T(-5.6 + k * 1.4, 4.0, 0.006))
    lines.done("road_lines", "paint_line")
    # 건물 (가까운 것부터)
    building(-1, -22, 12, 14, 30, 1); building(-1, 13, 36, 16, 44, 2); building(-1, 38, 64, 18, 62, 3, shops=False); building(-1, 66, 100, 22, 118, 4, "corp")
    building(1, -22, 9, 14, 24, 5); building(1, 11, 42, 18, 28, 6); building(1, 44, 72, 16, 25, 7); building(1, 74, 110, 22, 98, 8, shops=False)
    megastructure(-90, 260, 120, 110, 340, 0.62, "glow_magenta"); megastructure(95, 330, 130, 120, 430, 0.6, "glow_cyan")
    megastructure(0, 470, 90, 90, 520, 0.5, "glow_amber"); megastructure(-170, 150, 80, 80, 210, 0.7); megastructure(170, 190, 90, 90, 260, 0.7)
    # 영웅 광고: 한 장면에 하나. 왼쪽 세 번째 건물의 카메라 쪽 벽 위층
    billboard(T(21.5, 73.5, 46.0), "hero_ad", 15.0, 24.0, "LUMEN", (1.0, 0.08, 0.5), (0.15, 0.35, 1.0))
    # 중형 광고판 하나: 오른쪽 첫 건물 옥상
    billboard(T(18.5, 45.0, 27.6) @ RZ(14), "roof_ad", 9.0, 4.4, "ZENTH", (1.0, 0.45, 0.05), (1.0, 0.1, 0.3))
    # 돌출 세로 간판 3개 (받침대 포함)
    blade_sign(T(-11, 6.0, 9.5), "blade1", "KIRO", "glow_magenta"); blade_sign(T(11, 2.0, 8.0) @ RZ(180) @ S(1, -1, 1), "blade2", "MIRU", "glow_cyan", 3.6)
    blade_sign(T(-11, 24.0, 12.0), "blade3", "TEKKA", "glow_amber", 5.0)
    # 고가 선로와 공중 통로
    monorail(T(0, 50, 15.0)); pillar(T(-9.2, 50, 0)); pillar(T(9.2, 50, 0))
    finish("skybridge", box(22.2, 4.5, 4.2), "concrete_dark", 0.1, 1, T(0, 86, 30))
    finish("skybridge_win", box(22.3, 4.56, 1.2), "win_warm", 0, 1, T(0, 86, 30.4), smooth=False)
    # 거리 소품
    for k in range(7):
        lamp(T(-7.6, -4 + 19 * k, 0.18) @ RZ(-90), light=k < 3); lamp(T(7.6, 5 + 19 * k, 0.18) @ RZ(90), light=k < 2)
    vending(T(9.9, -3.4, 0.18) @ RZ(-90), col="glow_cyan"); vending(T(9.9, -2.1, 0.18) @ RZ(-90), "vending2", "glow_magenta")
    stall(T(-9.0, 2.5, 0.18) @ RZ(90)); trash(T(-10.0, -5.5, 0.18)); trash(T(9.6, 13.0, 0.18) @ RZ(160), seed=4)
    barrier(T(4.4, 10.0, 0)); barrier(T(4.9, 12.4, 0) @ RZ(14))
    for k, (y, z) in enumerate(((-2.0, 9.0), (8.0, 11.5), (20.0, 10.0), (30.0, 13.0))):
        cable("street_cable", [Vector((-11, y, z)), Vector((-3, y + 0.6, z - 1.3)), Vector((4, y + 0.2, z - 1.1)), Vector((11, y + 1.0, z + 0.4))], 0.035, "rubber")
    # 차와 로봇
    import car, security_robot
    place(lambda: car.parts("crimson"), T(5.6, 1.5, 0) @ RZ(180)); place(lambda: car.parts("cab"), T(-2.2, 26.0, 0))
    place(lambda: car.parts("teal"), T(-5.6, -6.5, 0)); place(lambda: security_robot.parts(), T(-8.2, -1.2, 0.18) @ RZ(-150))
    light_and_shoot(sc, "street_day.png" if day else "street_night.png", day,
                    [("pool_magenta", (-9.5, 5.5, 6.0), (-6, 4, 0), 700, (1.0, 0.1, 0.5)), ("pool_cyan", (9.5, 0.5, 5.5), (5, -1, 0), 600, (0.1, 0.8, 1.0)), ("pool_amber", (-9.5, 22.0, 7.0), (-4, 20, 0), 550, (1.0, 0.5, 0.1))])

def base_ground():
    finish("road", box(14.0, 520.0, 0.2), "asphalt", 0, 1, T(0, 220, -0.1), smooth=False)
    for s in (-1, 1):
        finish("sidewalk", box(4.0, 520.0, 0.36), "sidewalk", 0, 1, T(9.0 * s, 220, 0.0), smooth=False)
        finish("curb", box(0.3, 520.0, 0.40), "concrete", 0, 1, T(7.05 * s, 220, 0.0), smooth=False)
        finish("ground", box(120.0, 520.0, 0.2), "concrete_dark", 0, 1, T(71.0 * s, 220, -0.1), smooth=False)
    lines = Multi()
    for k in range(40): lines.add(0.16, 3.0, 0.012, T(0, -12 + k * 7.0, 0.006))
    for s in (-1, 1): lines.add(0.14, 300.0, 0.012, T(6.4 * s, 130, 0.006))
    lines.done("road_lines", "paint_line")

def light_and_shoot(sc, fname, day, pools, sky=(0.010, 0.012, 0.030), moon=(0.35, 0.45, 0.8), fog_col=(0.75, 0.82, 1.0), fog=0.0022, exposure=0.3, cam=((2.4, -17.0, 1.75), (-0.5, 40.0, 19.0), 24)):
    """밤: 색 조명 웅덩이 + 달빛 + 안개. 낮: 흐린 하늘 + 해 + 옅은 안개(간판은 켜져 있지만 약하게 보인다)."""
    if not sc.world: sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    if day:
        bg.inputs["Color"].default_value = (0.62, 0.68, 0.76, 1); bg.inputs["Strength"].default_value = 3.0
        sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 8.0; sun.color = (1.0, 0.90, 0.76); sun.angle = radians(6)
        so = bpy.data.objects.new("sun", sun); kit.COL.objects.link(so); so.rotation_euler = (radians(50), 0, radians(-50))
        fog, fog_col, exposure = 0.0006, (1.0, 0.95, 0.88), 0.5
    else:
        bg.inputs["Color"].default_value = (*sky, 1)
        for name, loc, tgt, power, col in pools: kit.area(name, loc, tgt, 3.0, power, col)
        kit.area("moon", (30, -40, 90), (0, 30, 10), 40.0, 5000, moon)
    fm = bpy.data.materials.new("fog"); fm.use_nodes = True; nt = fm.node_tree; nt.nodes.clear()
    vo = nt.nodes.new("ShaderNodeVolumeScatter"); vo.inputs["Density"].default_value = fog; vo.inputs["Anisotropy"].default_value = 0.35
    vo.inputs["Color"].default_value = (*fog_col, 1); out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(vo.outputs[0], out.inputs["Volume"])
    kit.M["fog"] = fm; finish("stage_fog", box(500, 700, 560, z0=True), "fog", 0, 1, T(0, 280, -1), smooth=False)
    sc.cycles.volume_bounces = 0; sc.cycles.max_bounces = 5; sc.view_settings.exposure = exposure
    os.makedirs(OUT, exist_ok=True)
    kit.shot(os.path.join(OUT, fname), cam[0], cam[1], cam[2], res=tuple(int(v) for v in os.environ.get("STREET_RES", "1400,900").split(",")))

def modules():
    """소품을 하나씩 내보내고 모음 사진을 찍는다."""
    mods = {"lamp": lamp, "vending": vending, "ac_unit": lambda: ac_unit(T(0, 0, 0.4)), "barrier": barrier, "trash": trash, "stall": stall,
            "blade_sign": lambda: blade_sign(T(0, 0, 2.2)), "billboard": lambda: billboard(T(0, 0, 2.6)), "monorail_segment": lambda: monorail(span=12.0, train=False), "pillar": pillar}
    for name, fn in mods.items():
        kit.reset(); materials(); fn(); kit.export(os.path.join(OUT, "modules"), name)
    kit.reset(); materials(); kit.studio((0, 0, 2.0), 5.0, top=0.5)
    lamp(T(-9, 2, 0)); vending(T(-6.5, 0, 0)); ac_unit(T(-4.6, 0, 0.5)); barrier(T(-2.2, 0, 0)); trash(T(1.0, 0.5, 0)); stall(T(5.6, 0.5, 0)); blade_sign(T(8.4, 1, 2.4)); billboard(T(-1, 6, 3.0), w=7.0, h=3.4)
    kit.shot(os.path.join(OUT, "street_modules.png"), (-3.0, -21.0, 6.0), (0.0, 1.0, 2.6), 50)

if __name__ == "__main__":
    scene() if MODE == "scene" else scene(True) if MODE == "scene_day" else modules()
