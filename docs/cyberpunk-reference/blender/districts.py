"""구역별 건물 양식 (자체 디자인): 빈민·재활용풍, 기업·군사풍, 부유층 고급풍. '싸구려 화려풍'(번화가)은 street.py의 밤거리 장면이다.
실행: python districts.py <출력폴더> [slum|corp|rich|all]
거리 뼈대(도로 14 m, 인도 4 m, 건물 벽 x = ±11)는 street.py와 같다. 구역마다 건물 생성 함수, 소품, 조명, 간판 양이 다르다.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, text, cable, frame, RX, RY, RZ, T, S
import street
from street import Multi, place

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/street"
WHICH = sys.argv[2] if len(sys.argv) > 2 else "all"
street.OUT = OUT

def materials():
    street.materials()
    kit.mat_paint("rust", (0.22, 0.075, 0.03), (0.30, 0.16, 0.08), rough=(0.55, 0.85), wear=3.0, scale=0.12)
    kit.mat_paint("box_blue", (0.04, 0.12, 0.20), (0.30, 0.16, 0.08), rough=(0.5, 0.8), wear=2.6, scale=0.12)
    kit.mat_paint("box_green", (0.05, 0.13, 0.08), (0.30, 0.16, 0.08), rough=(0.5, 0.8), wear=2.6, scale=0.12)
    kit.mat_paint("box_yellow", (0.50, 0.33, 0.03), (0.30, 0.16, 0.08), rough=(0.5, 0.8), wear=2.6, scale=0.12)
    kit.mat_simple("tarp_blue", (0.02, 0.10, 0.28), 0.0, 0.55); kit.mat_simple("tarp_orange", (0.45, 0.14, 0.02), 0.0, 0.6); kit.mat_simple("plywood", (0.23, 0.15, 0.08), 0.0, 0.8)
    kit.mat_concrete("brutal", (0.17, 0.17, 0.175), 0.6); kit.mat_simple("black_glass", (0.004, 0.005, 0.008), 0.6, 0.04)
    kit.mat_simple("hazard", (0.75, 0.50, 0.02), 0.0, 0.5); kit.mat_simple("strip_white", (0, 0, 0), 0, 0.4, (0.80, 0.90, 1.0), 5.0)
    kit.mat_concrete("stone_white", (0.62, 0.60, 0.56), 0.5); kit.mat_simple("clear_glass", (0.02, 0.035, 0.04), 0.3, 0.03); kit.mat_simple("gold", (0.80, 0.56, 0.20), 1.0, 0.22)
    kit.mat_simple("gold_glow", (0, 0, 0), 0, 0.4, (1.0, 0.70, 0.34), 1.6); kit.mat_simple("lobby_glow", (0.02, 0.015, 0.01), 0, 0.3, (1.0, 0.72, 0.40), 0.35); kit.mat_simple("leaf", (0.03, 0.12, 0.04), 0.0, 0.6); kit.mat_simple("leaf2", (0.05, 0.16, 0.05), 0.0, 0.6)
    kit.mat_simple("bark", (0.06, 0.04, 0.03), 0.0, 0.8); kit.mat_simple("water", (0.01, 0.03, 0.04), 0.0, 0.02); kit.mat_simple("holo", (0, 0, 0), 0, 0.4, (0.55, 0.90, 1.0), 2.4)

# ------------------------------------------------------------------ 빈민·재활용풍
def slum_block(side, y0, y1, seed):
    """컨테이너와 덧댄 방을 쌓은 블록. 층마다 조금씩 어긋난다."""
    r = random.Random(seed); xf = 11.0 * side; cols = ("rust", "box_blue", "box_green", "box_yellow", "concrete_dark", "rust")
    warm, cool, dark, ribs, acs = Multi(), Multi(), Multi(), Multi(), Multi(); y = y0
    while y < y1 - 3.0:
        L = r.choice((6.1, 6.1, 12.2)) if y + 12.2 < y1 else 6.1; n = r.randint(3, 8)
        for k in range(n):
            off = r.uniform(-0.5, 0.9) if k else 0.0; d = r.choice((2.5, 2.5, 5.0)); z = k * 2.75
            finish("unit", box(d, L - 0.1, 2.6, z0=True), r.choice(cols), 0.04, 1, T(xf + side * (d / 2 - off), y + L / 2, z), smooth=False)
            for q in range(int(L / 0.42)): ribs.add(0.06, 0.12, 2.3, T(xf - side * (off + 0.02), y + 0.3 + q * 0.42, z + 1.3))
            if r.random() < 0.75:
                m = warm if r.random() < 0.45 else cool if r.random() < 0.15 else dark
                m.add(0.10, r.choice((1.0, 1.4, 2.0)), 1.1, T(xf - side * (off + 0.06), y + r.uniform(1.2, L - 1.2), z + 1.45))
            if r.random() < 0.35: acs.add(0.5, 0.9, 0.6, T(xf - side * (off + 0.30), y + r.uniform(0.8, L - 0.8), z + 0.6))
            if k and r.random() < 0.30:   # 발코니와 빨래
                finish("balcony", box(1.1, L * 0.6, 0.08), "plywood", 0, 1, T(xf - side * (off + 0.55), y + L / 2, z + 0.05), smooth=False)
                finish("rail", box(0.05, L * 0.6, 0.9), "gunmetal", 0, 1, T(xf - side * (off + 1.08), y + L / 2, z + 0.5), smooth=False)
                for q in range(4): finish("laundry", box(0.02, 0.5, 0.7), r.choice(("cloth", "tarp_blue", "paint_line", "tarp_orange")), 0, 1, T(xf - side * (off + 1.12), y + L * 0.25 + q * 0.7, z + 0.45), smooth=False)
        if r.random() < 0.6: finish("tank", cyl(0.9, 0.9, 1.6, 12, "z"), "titan", 0, 1, T(xf + side * 1.4, y + L / 2, n * 2.75 + 0.8))
        if r.random() < 0.7:  # 인도 위 천막
            finish("tarp", box(3.4, L * 0.8, 0.05), r.choice(("tarp_blue", "tarp_orange", "cloth")), 0, 1, T(xf - side * 1.75, y + L / 2, 3.0) @ RY(side * 12), smooth=False)
            for q in (-1, 1): finish("tarp_pole", cyl(0.04, 0.04, 2.7, 6, "z"), "gunmetal", 0, 1, T(xf - side * 3.3, y + L / 2 + q * L * 0.36, 1.5))
        if r.random() < 0.5:  # 손으로 만든 작은 간판
            c = r.choice(street.NEON[:3]); z = r.uniform(3.4, 5.0)
            finish("hand_sign", box(0.08, 1.8, 0.6), "plywood", 0, 1, T(xf - side * 0.3, y + L / 2, z), smooth=False)
            text("hand_text", r.choice(("NOODLE", "FIX", "PARTS", "24", "TEA", "CHIPS")), 0.36, frame((0, -side, 0), (-side, 0, 0), (xf - side * 0.36, y + L / 2, z)), c, None, 0.008)
        y += L + r.choice((0.0, 0.0, 1.2))
    for mm, nm, mt in ((warm, "win_warm", "win_warm"), (cool, "win_cool", "win_cool"), (dark, "win_dark", "win_dark"), (ribs, "ribs", "gunmetal"), (acs, "acs", "titan")): mm.done("slum_" + nm, mt)

def slum():
    sc = kit.reset(); materials(); R = random.Random(11); street.base_ground()
    slum_block(-1, -22, 110, 21); slum_block(1, -22, 110, 22)
    for k in range(4): street.megastructure((-150, 130, -40, 60)[k], (300, 340, 520, 560)[k], 100, 100, (330, 420, 520, 460)[k], 0.6, (None, "glow_magenta", None, "glow_cyan")[k])
    for k in range(14):   # 길을 가로지르는 전선과 빨랫줄
        y = -6 + k * 5.5; z = R.uniform(5.5, 13.0)
        cable("wire", [Vector((-11, y, z)), Vector((-3, y + R.uniform(-1, 1), z - R.uniform(0.8, 2.2))), Vector((4, y + R.uniform(-1, 1), z - R.uniform(0.6, 1.8))), Vector((11, y + R.uniform(-2, 2), z + R.uniform(-1, 1)))], 0.03, "rubber")
    for k in range(5): street.lamp(T(-7.6, -2 + 24 * k, 0.18) @ RZ(-90), light=k < 2)
    street.stall(T(-9.0, 1.0, 0.18) @ RZ(90)); street.stall(T(9.0, 7.5, 0.18) @ RZ(-90), "stall2"); street.stall(T(-9.0, 15.0, 0.18) @ RZ(90), "stall3")
    for k, (x, y) in enumerate(((-10.0, -5.0), (9.6, -1.5), (-9.8, 8.0), (9.9, 14.0), (6.2, 3.0), (-6.4, 11.0))): street.trash(T(x, y, 0.18 if abs(x) > 7 else 0.0) @ RZ(k * 50), "trash%d" % k, seed=k + 2)
    for k in range(3): finish("barrel", cyl(0.30, 0.30, 0.88, 14, "z"), ("rust", "box_blue", "box_yellow")[k], 0.02, 1, T(8.0 + 0.7 * k, -4.4 + 0.3 * k, 0.62))
    finish("barrel_fire", cyl(0.24, 0.24, 0.05, 12, "z"), "sodium", 0, 1, T(8.0, -4.4, 1.07))
    street.barrier(T(3.6, 9.0, 0) @ RZ(30)); street.vending(T(-9.9, 5.0, 0.18) @ RZ(90), col="glow_amber")
    import car; place(lambda: car.parts("teal"), T(5.4, 16.0, 0) @ RZ(184))
    street.light_and_shoot(sc, "district_slum.png", False,
        [("fire", (8.0, -4.4, 1.6), (6, -4, 0), 260, (1.0, 0.45, 0.10)), ("sodium1", (-8.5, 4.0, 6.5), (-5, 5, 0), 900, (1.0, 0.50, 0.14)), ("sodium2", (8.5, 12.0, 6.0), (5, 12, 0), 700, (1.0, 0.50, 0.14)),
         ("neon", (-9.0, 16.0, 4.5), (-5, 16, 0), 260, (0.1, 0.8, 1.0))], sky=(0.016, 0.012, 0.012), moon=(0.5, 0.42, 0.36), fog_col=(1.0, 0.80, 0.62), fog=0.0030, exposure=0.5)

# ------------------------------------------------------------------ 기업·군사풍
def corp_block(side, y0, y1, depth, h, seed):
    """브루탈 콘크리트 기단 + 검은 유리 탑. 간판은 꼭대기 로고 하나."""
    r = random.Random(seed); xf = 11.0 * side; xc = xf + side * depth / 2; yc = (y0 + y1) / 2; L = y1 - y0
    finish("podium", box(depth, L, 14.0, z0=True), "brutal", 0, 1, T(xc, yc, 0), smooth=False)
    slots, strips = Multi(), Multi()
    for z in (5.0, 8.4, 11.8):
        slots.add(0.3, L - 4.0, 1.1, T(xf - side * 0.02, yc, z)); strips.add(0.12, L - 4.0, 0.08, T(xf - side * 0.10, yc, z - 0.75))
    slots.done("slots", "black_glass"); strips.done("strips", "strip_white")
    for y in (y0 + 0.4, y1 - 0.4): finish("buttress", box(1.6, 0.8, 14.0, z0=True), "brutal", 0, 1, T(xf - side * 0.6, y, 0), smooth=False)
    finish("gate", box(0.4, 7.0, 3.6, z0=True), "black_glass", 0, 1, T(xf - side * 0.1, yc, 0), smooth=False)
    finish("gate_frame", box(1.0, 8.0, 0.6), "brutal", 0, 1, T(xf - side * 0.4, yc, 3.9), smooth=False)
    for q in range(8): finish("hazard", box(1.02, 0.5, 0.62), "hazard" if q % 2 else "black", 0, 1, T(xf - side * 0.4, yc - 3.5 + q * 1.0, 3.9), smooth=False)
    text("gate_text", "SECTOR %02d  AUTHORIZED ONLY" % (seed % 20), 0.34, frame((0, -side, 0), (-side, 0, 0), (xf - side * 0.93, yc, 4.75)), "glow_white", None, 0.008)
    finish("setback", box(depth - 4, L - 4, 2.0, z0=True), "gunmetal", 0, 1, T(xc + side * 2, yc, 14.0), smooth=False)
    finish("tower", box(depth - 6, L - 6, h - 16, z0=True), "tower_glass", 0, 1, T(xc + side * 3, yc, 16.0), smooth=False)
    fins = Multi(); y = y0 + 3.2
    while y < y1 - 3: fins.add(0.5, 0.25, h - 16, T(xf + side * 2.9, y, 16 + (h - 16) / 2)); y += 3.0
    fins.done("tower_fins", "gunmetal")
    finish("crown", box(depth - 8, L - 8, 4.0, z0=True), "gunmetal", 0, 1, T(xc + side * 3, yc, h), smooth=False)
    finish("logo", box(0.3, min(9.0, L * 0.4), 2.6), "glow_cyan" if seed % 2 else "glow_white", 0, 1, T(xf + side * 2.8, yc, h - 4.0), smooth=False)
    for q in (-1, 1): finish("beacon", sphere(0.3, 1, 1, 1, 8, 6), "glow_red", 0, 1, T(xc + side * 3, yc + q * (L / 2 - 5), h + 4.3))

def bollard(x, y):
    finish("bollard", cyl(0.16, 0.16, 0.9, 12, "z"), "gunmetal", 0.02, 1, T(x, y, 0.63)); finish("bollard_led", cyl(0.165, 0.165, 0.06, 12, "z"), "strip_white", 0, 1, T(x, y, 0.95))

def corp():
    sc = kit.reset(); materials(); street.base_ground()
    corp_block(-1, -22, 14, 22, 120, 3); corp_block(-1, 18, 62, 24, 190, 4); corp_block(-1, 66, 120, 26, 150, 9)
    corp_block(1, -22, 20, 22, 90, 6); corp_block(1, 24, 70, 24, 230, 7); corp_block(1, 74, 130, 26, 170, 8)
    street.megastructure(0, 420, 140, 120, 560, 0.5, "glow_cyan"); street.megastructure(-160, 300, 100, 100, 380, 0.6); street.megastructure(170, 320, 110, 110, 420, 0.6)
    for s in (-1, 1):
        for k in range(14): bollard(7.5 * s, -8 + k * 3.0)
        finish("ground_strip", box(0.10, 200.0, 0.02), "strip_white", 0, 1, T(10.6 * s, 90, 0.19), smooth=False)
    finish("checkpoint_bar", box(13.0, 0.25, 0.25), "hazard", 0.02, 1, T(0.4, 14.0, 1.1)); finish("checkpoint_post", box(0.5, 0.5, 1.3, z0=True), "brutal", 0.03, 1, T(-6.3, 14.0, 0))
    finish("booth", box(2.2, 2.6, 2.8, z0=True), "brutal", 0.05, 1, T(-9.0, 15.5, 0.18)); finish("booth_glass", box(2.24, 1.8, 1.0), "black_glass", 0, 1, T(-9.0, 15.3, 1.95), smooth=False)
    finish("booth_strip", box(2.26, 2.66, 0.08), "strip_white", 0, 1, T(-9.0, 15.5, 2.80), smooth=False)
    for k in range(3): street.barrier(T(-3.0 + k * 3.0, 9.5, 0), "barrier%d" % k)
    import car, security_robot, machines, flying_car
    machines.materials()
    place(lambda: security_robot.parts(), T(-8.3, 6.0, 0.18) @ RZ(-160)); place(lambda: security_robot.parts(), T(8.2, 9.0, 0.18) @ RZ(170))
    place(machines.turret, T(8.9, 15.5, 0.18) @ RZ(170) @ S(1.25, 1.25, 1.25)); place(machines.camera, T(-10.98, 3.0, 5.2) @ RZ(90) @ S(1.6, 1.6, 1.6))
    place(lambda: car.parts("corp"), T(3.2, 2.0, 0) @ RZ(180)); place(lambda: flying_car.parts("patrol"), T(-2.0, 60.0, 34.0) @ RZ(170) @ RY(8))
    place(machines.drone, T(3.5, 20.0, 9.0) @ RZ(160) @ S(1.6, 1.6, 1.6))
    street.light_and_shoot(sc, "district_corp.png", False,
        [("gate_l", (-8.0, 2.0, 7.0), (-6, 4, 0), 900, (0.75, 0.88, 1.0)), ("gate_r", (8.0, 8.0, 7.0), (5, 8, 0), 900, (0.75, 0.88, 1.0)), ("check", (0, 13.0, 6.0), (0, 14, 0), 600, (1.0, 0.92, 0.8))],
        sky=(0.008, 0.012, 0.022), moon=(0.45, 0.60, 0.95), fog_col=(0.72, 0.84, 1.0), fog=0.0018, exposure=0.5)

# ------------------------------------------------------------------ 부유층 고급풍
def tree(x, y, z=0.18, k=1.0, seed=0):
    r = random.Random(seed)
    finish("trunk", cyl(0.14 * k, 0.09 * k, 2.6 * k, 8, "z"), "bark", 0, 1, T(x, y, z + 1.3 * k))
    for q in range(6): finish("crown", sphere(r.uniform(0.9, 1.4) * k, 1, 1, 0.8, 10, 7), "leaf" if q % 2 else "leaf2", 0, 1, T(x + r.uniform(-0.8, 0.8) * k, y + r.uniform(-0.8, 0.8) * k, z + (3.0 + r.uniform(0, 1.2)) * k))

def rich_block(side, y0, y1, depth, floors, seed):
    """흰 석재 테라스 건물. 층마다 뒤로 물러나고 유리 난간과 녹지가 있다."""
    r = random.Random(seed); xf = 11.0 * side; yc = (y0 + y1) / 2; L = y1 - y0; glass, glow, slabs, rails, plants = Multi(), Multi(), Multi(), Multi(), Multi()
    for k in range(floors):
        back = 0.9 * max(0, k - 2) if k < 12 else 0.9 * 10; z = k * 4.2; d = depth - back
        finish("mass", box(d, L - back * 0.4, 4.2, z0=True), "stone_white", 0, 1, T(xf + side * (back + d / 2), yc, z), smooth=False)
        slabs.add(d + 1.6, L - back * 0.4 + 0.6, 0.28, T(xf + side * (back + d / 2 - 0.6), yc, z + 4.2))
        if k:
            glass.add(0.08, L - back * 0.4 - 1.2, 3.1, T(xf + side * (back - 0.02), yc, z + 1.9)); glow.add(0.06, (L - back * 0.4 - 1.2) * r.uniform(0.25, 0.7), 2.9, T(xf + side * (back + 0.06), yc + r.uniform(-L / 6, L / 6), z + 1.9))
            rails.add(0.04, L - back * 0.4 + 0.4, 1.0, T(xf + side * (back - 1.35), yc, z + 0.65))
            for q in range(int(L / 5)):
                if r.random() < 0.6: plants.add(0.7, 1.6, 0.7, T(xf + side * (back - 0.9), y0 + 2.5 + q * 5 + r.uniform(-1, 1), z + 0.6))
    for mm, nm, mt in ((glass, "glass", "clear_glass"), (glow, "glow", "gold_glow"), (slabs, "slabs", "stone_white"), (rails, "rails", "clear_glass"), (plants, "plants", "leaf")): mm.done("rich_" + nm, mt)
    finish("lobby", box(0.3, L * 0.5, 3.6, z0=True), "lobby_glow", 0, 1, T(xf - side * 0.05, yc, 0.2), smooth=False)
    finish("canopy", box(3.4, L * 0.5 + 1.0, 0.16), "stone_white", 0.03, 1, T(xf - side * 1.6, yc, 3.95)); finish("canopy_trim", box(3.44, L * 0.5 + 1.04, 0.05), "gold", 0, 1, T(xf - side * 1.6, yc, 3.84), smooth=False)
    text("mark", r.choice(("AUREA", "SOLENNE", "VELA", "MIRAE")), 0.42, frame((0, -side, 0), (-side, 0, 0), (xf - side * 3.34, yc, 3.96)), "gold", None, 0.012)
    finish("roof_garden", box(depth * 0.4, L * 0.5, 0.5, z0=True), "leaf2", 0, 1, T(xf + side * (depth * 0.6), yc, floors * 4.2), smooth=False)

def rich():
    sc = kit.reset(); materials(); street.base_ground()
    rich_block(-1, -22, 16, 22, 9, 31); rich_block(-1, 20, 60, 24, 14, 32); rich_block(-1, 64, 120, 26, 22, 33)
    rich_block(1, -22, 22, 22, 11, 34); rich_block(1, 26, 70, 24, 16, 35); rich_block(1, 74, 130, 26, 26, 36)
    street.megastructure(0, 460, 120, 110, 540, 0.5, "gold_glow"); street.megastructure(-170, 320, 100, 100, 400, 0.6); street.megastructure(160, 300, 100, 100, 360, 0.6, "holo")
    for s in (-1, 1):
        for k in range(9):
            y = -10 + k * 9.0
            finish("planter", box(1.4, 3.2, 0.5, z0=True), "stone_white", 0.04, 1, T(8.0 * s, y, 0.18)); finish("planter_soil", box(1.2, 3.0, 0.06), "leaf", 0, 1, T(8.0 * s, y, 0.70), smooth=False)
            tree(8.0 * s, y, 0.6, 1.0 + 0.15 * (k % 3), k * 2 + (s > 0))
            finish("path_light", box(0.08, 3.2, 0.04), "gold_glow", 0, 1, T(8.0 * s - s * 0.72, y, 0.50), smooth=False)
    finish("median", box(1.6, 90.0, 0.3, z0=True), "stone_white", 0.04, 1, T(0, 45, 0)); finish("median_water", box(1.2, 89.0, 0.04), "water", 0, 1, T(0, 45, 0.30), smooth=False)
    for k in range(8): finish("median_light", box(1.22, 0.06, 0.03), "gold_glow", 0, 1, T(0, 6 + k * 11.0, 0.325), smooth=False)
    # 큰 고급 홀로그램 하나
    finish("holo_base", cyl(1.4, 1.6, 0.5, 24, "z"), "stone_white", 0.05, 1, T(0, 34.0, 0.55)); finish("holo_ring", torus(1.2, 0.05, 32, 6, "z"), "holo", 0, 1, T(0, 34.0, 0.86))
    for k in range(5): finish("holo_band", torus(2.6 - 0.25 * k, 0.03, 40, 4, "z"), "holo", 0, 1, T(0, 34.0, 3.0 + k * 1.9) @ RX(12 * (k % 2 * 2 - 1)))
    text("holo_text", "AUREA", 2.2, frame((1, 0, 0), (0, -1, 0), (0, 33.9, 8.0)), "holo", None, 0.02)
    finish("skybridge", box(22.2, 5.0, 3.6), "clear_glass", 0.1, 1, T(0, 96, 44)); finish("skybridge_glow", box(22.0, 4.6, 0.1), "gold_glow", 0, 1, T(0, 96, 42.4), smooth=False)
    import car, flying_car
    place(lambda: car.parts("corp"), T(4.6, 2.0, 0) @ RZ(180)); place(lambda: car.parts("crimson"), T(-4.4, 20.0, 0))
    place(lambda: flying_car.parts("civil"), T(3.0, 52.0, 26.0) @ RZ(175) @ RY(-6))
    street.light_and_shoot(sc, "district_rich.png", False,
        [("lobby_l", (-8.0, -2.0, 5.0), (-6, 0, 0), 500, (1.0, 0.78, 0.50)), ("lobby_r", (8.0, 2.0, 5.0), (6, 2, 0), 500, (1.0, 0.78, 0.50)), ("holo", (0, 28.0, 9.0), (0, 22, 0), 500, (0.6, 0.9, 1.0)),
         ("wash_l", (-4.0, 10.0, 1.0), (-11, 30, 30), 2600, (1.0, 0.86, 0.70)), ("wash_r", (4.0, 10.0, 1.0), (11, 30, 30), 2600, (1.0, 0.86, 0.70))],
        sky=(0.035, 0.040, 0.075), moon=(0.75, 0.78, 1.0), fog_col=(0.90, 0.88, 1.0), fog=0.0012, exposure=0.9)

if __name__ == "__main__":
    for name, fn in (("slum", slum), ("corp", corp), ("rich", rich)):
        if WHICH in ("all", name): fn()
