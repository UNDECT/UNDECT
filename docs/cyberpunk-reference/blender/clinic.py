"""시술소 (자체 디자인): 시술 의자, 천장 로봇 팔, 도구 수레, 그리고 시술소 장면.
실행: python clinic.py <출력폴더> modules   -> 의자·로봇 팔·수레를 따로 내보내고 사진을 찍는다
      python clinic.py <출력폴더> scene     -> 시술의와 함께 찍은 시술소 분위기 그림 (시술의는 person.py가 만든다)
앞이 -Y, 위가 +Z. 원점은 의자 받침 가운데 바닥. 누운 사람의 머리가 +Y 쪽, 왼팔이 +X 쪽이다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, bolt, cable, text, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/clinic"
MODE = ARGS[1] if len(ARGS) > 1 else "modules"

def materials():
    kit.mat_paint("c_shell", (0.60, 0.62, 0.62), rough=(0.28, 0.50), wear=1.5, scale=0.5)
    kit.mat_paint("c_dark", (0.045, 0.05, 0.058), (0.45, 0.45, 0.45), rough=(0.34, 0.55), wear=1.3, scale=0.5)
    kit.mat_paint("c_teal", (0.02, 0.16, 0.17), rough=(0.32, 0.52), wear=1.5, scale=0.5)
    kit.mat_paint("c_orange", (0.80, 0.30, 0.02), rough=(0.34, 0.55), wear=1.4, scale=0.5)
    kit.mat_simple("c_pad", (0.018, 0.024, 0.028), 0.0, 0.50)
    kit.mat_simple("c_screen", (0.004, 0.008, 0.010), 0.3, 0.12)
    kit.mat_simple("c_tile", (0.020, 0.024, 0.027), 0.0, 0.16)
    kit.mat_concrete("c_wall", (0.085, 0.095, 0.10), 1.4)
    kit.mat_simple("c_panel_glow", (0.01, 0.02, 0.025), 0.0, 0.3, (0.10, 0.65, 0.85), 1.6)

def seg(name, a, b, w, h, mat, part, bev=0.006, segs=2):
    """두 점 a, b를 잇는 각진 막대."""
    a, b = Vector(a), Vector(b); d = b - a
    up = (0, 0, 1) if abs(d.normalized().z) < 0.95 else (0, 1, 0)
    return finish(name, box(d.length, w, h), mat, bev, segs, T(*((a + b) / 2)) @ frame(d, up), part)

def hinge(name, p, axis, r, L, mat, part):
    up = (0, 0, 1) if abs(Vector(axis).normalized().z) < 0.95 else (0, 1, 0)
    return finish(name, cyl(r, r, L, 24, "x"), mat, min(0.004, r * 0.2), 2, T(*p) @ frame(axis, up), part)

# ------------------------------------------------------------------ 의자
SEAT_Z, RECLINE, LEG = 0.56, 52, 28   # 등받이 각(수평에서), 다리 받침 각

def chair():
    b = "base"
    finish("foot", cyl(0.360, 0.400, 0.050, 8, "z"), "c_dark", 0.010, 2, T(0, 0.05, 0.025) @ RZ(22.5), b)
    for k in range(8): bolt(T(0.340 * cos(radians(k * 45)), 0.05 + 0.340 * sin(radians(k * 45)), 0.051), 0.012, part=b)
    finish("column_outer", cyl(0.130, 0.160, 0.260, 20, "z"), "c_shell", 0.008, 2, T(0, 0.05, 0.180), b)
    finish("column_ring", torus(0.134, 0.008, 28, 6, "z"), "glow_cyan", 0, 1, T(0, 0.05, 0.312), "status_glow")
    finish("column_inner", cyl(0.090, 0.090, 0.180, 20, "z"), "chrome", 0.002, 1, T(0, 0.05, 0.380), "seat")
    finish("pedal", box(0.110, 0.070, 0.016), "c_orange", 0.005, 2, T(-0.300, -0.250, 0.060) @ RX(-14), b)
    cable("power", [(0.250, 0.300, 0.040), (0.600, 0.650, 0.020), (0.900, 1.200, 0.020)], 0.014, "rubber", b)
    pivot("lift", (0, 0.05, 0.31), (0, 0, 1), b, "seat", (0, 0))
    s = "seat"
    finish("seat_frame", box(0.600, 0.580, 0.070), "c_shell", 0.014, 3, T(0, 0, SEAT_Z - 0.075), s)
    finish("seat_under", box(0.420, 0.420, 0.060), "c_dark", 0.010, 2, T(0, 0.02, SEAT_Z - 0.140), s)
    finish("seat_pad", box(0.500, 0.520, 0.070), "c_pad", 0.024, 4, T(0, 0, SEAT_Z - 0.010), s)
    for sx in (-1, 1):
        finish("seat_side", box(0.030, 0.560, 0.110), "c_teal", 0.010, 2, T(0.300 * sx, 0, SEAT_Z - 0.045), s)
        finish("side_glow", box(0.004, 0.400, 0.008), "glow_cyan", 0, 1, T(0.317 * sx, 0, SEAT_Z - 0.030), "status_glow")
    # 등받이
    k = "back"; hb = Vector((0, 0.290, SEAT_Z - 0.020)); Mb = T(*hb) @ RX(RECLINE)
    hinge("back_hinge", hb, (1, 0, 0), 0.050, 0.640, "c_dark", s)
    finish("back_frame", box(0.580, 0.800, 0.060), "c_shell", 0.014, 3, Mb @ T(0, 0.420, -0.045), k)
    finish("back_spine", box(0.160, 0.700, 0.050), "c_dark", 0.010, 2, Mb @ T(0, 0.400, -0.092), k)
    for i in range(3): finish("back_pad", box(0.480 - i * 0.03, 0.230, 0.070), "c_pad", 0.024, 4, Mb @ T(0, 0.150 + i * 0.245, 0.012), k)
    for sx in (-1, 1):
        finish("back_wing", box(0.050, 0.520, 0.110), "c_pad", 0.020, 3, Mb @ T(0.262 * sx, 0.330, 0.030) @ RY(-14 * sx), k)
        finish("back_glow", box(0.004, 0.560, 0.008), "glow_cyan", 0, 1, Mb @ T(0.2925 * sx, 0.420, -0.045), "status_glow")
    for i in range(5): finish("spine_port", box(0.050, 0.030, 0.010), "glow_amber" if i == 2 else "gunmetal", 0.002, 1, Mb @ T(0, 0.180 + i * 0.110, -0.121), k)
    pivot("recline", hb, (1, 0, 0), s, k, (-40, 30))
    # 머리 받침 + 목 접속 장치
    h = "headrest"; Mh = Mb @ T(0, 0.860, 0.000)
    finish("head_post", box(0.070, 0.140, 0.030), "chrome", 0.004, 1, Mh @ T(0, -0.040, -0.040), h)
    finish("head_pad", box(0.300, 0.200, 0.080), "c_pad", 0.030, 4, Mh @ T(0, 0.060, 0.010), h)
    finish("head_shell", box(0.340, 0.220, 0.040), "c_shell", 0.012, 3, Mh @ T(0, 0.060, -0.045), h)
    for sx in (-1, 1):
        finish("neural_clamp", box(0.030, 0.090, 0.110), "c_teal", 0.008, 2, Mh @ T(0.175 * sx, 0.040, 0.050), h)
        finish("neural_pin", cyl(0.006, 0.004, 0.050, 10, "x"), "chrome", 0, 1, Mh @ T(0.140 * sx, 0.040, 0.070), h)
        finish("neural_led", box(0.004, 0.060, 0.010), "glow_amber", 0, 1, Mh @ T(0.1915 * sx, 0.040, 0.080), "status_glow")
    pivot("headrest", tuple(Mh.translation), (1, 0, 0), k, h, (-20, 20))
    # 다리 받침
    l = "legrest"; hl = Vector((0, -0.290, SEAT_Z - 0.030)); Ml = T(*hl) @ RX(LEG)
    hinge("leg_hinge", hl, (1, 0, 0), 0.045, 0.600, "c_dark", s)
    finish("leg_frame", box(0.520, 0.560, 0.050), "c_shell", 0.012, 3, Ml @ T(0, -0.300, -0.040), l)
    for i in range(2): finish("leg_pad", box(0.440, 0.250, 0.060), "c_pad", 0.022, 4, Ml @ T(0, -0.160 - i * 0.270, 0.010), l)
    finish("foot_plate", box(0.460, 0.030, 0.200), "c_dark", 0.008, 2, Ml @ T(0, -0.590, 0.060), l)
    for i in range(5): finish("foot_grip", box(0.400, 0.006, 0.014), "c_orange", 0.001, 1, Ml @ T(0, -0.573, 0.000 + i * 0.034), l)
    for sx in (-1, 1): finish("ankle_cuff", torus(0.060, 0.012, 20, 8, "y"), "c_teal", 0, 1, Ml @ T(0.120 * sx, -0.470, 0.080) @ S(1, 1, 0.9), l)
    pivot("legrest", hl, (1, 0, 0), s, l, (-60, 30))
    # 팔걸이: 오른쪽은 일반, 왼쪽(+X)은 팔 시술용 받침
    for sx, name in ((-1, "armrest_R"), (1, "armrest_L")):
        x = 0.400 * sx
        seg("arm_post", (0.315 * sx, 0.120, SEAT_Z - 0.060), (x, 0.120, SEAT_Z + 0.170), 0.060, 0.050, "c_dark", name, 0.010)
        finish("arm_beam", box(0.110, 0.560, 0.040), "c_shell", 0.012, 3, T(x, -0.060, SEAT_Z + 0.190), name)
        finish("arm_pad", box(0.090, 0.480, 0.040), "c_pad", 0.016, 3, T(x, -0.060, SEAT_Z + 0.222), name)
        finish("wrist_cuff", torus(0.052, 0.012, 20, 8, "y"), "c_teal", 0, 1, T(x, -0.250, SEAT_Z + 0.270), name)
        finish("cuff_led", box(0.030, 0.014, 0.006), "glow_cyan", 0, 1, T(x, -0.250, SEAT_Z + 0.332), "status_glow")
        pivot(name, (0.315 * sx, 0.120, SEAT_Z - 0.060), (0, 1, 0), s, name, (0, 80))
    c = "armrest_L"; x = 0.400
    finish("cradle_tray", box(0.200, 0.620, 0.016), "c_dark", 0.006, 2, T(x + 0.050, -0.080, SEAT_Z + 0.176), c)
    for y in (-0.320, -0.100, 0.120):
        finish("cradle_clamp", torus(0.060, 0.010, 20, 8, "y"), "chrome", 0, 1, T(x, y, SEAT_Z + 0.280), c)
        finish("clamp_base", box(0.150, 0.030, 0.060), "c_orange", 0.006, 2, T(x, y, SEAT_Z + 0.212), c)
    finish("cradle_light", box(0.012, 0.560, 0.012), "glow_white", 0, 1, T(x + 0.145, -0.080, SEAT_Z + 0.200), "work_light")
    finish("drip_pan", box(0.240, 0.300, 0.030), "chrome", 0.006, 2, T(x + 0.060, -0.200, SEAT_Z + 0.120), c)

# ------------------------------------------------------------------ 천장 로봇 팔
ARMS = [  # 이름, 어깨, 팔꿈치, 손목, 끝, 도구
    ("arm_A", (-0.380, 0.150, 2.480), (-0.760, -0.100, 1.880), (-0.420, -0.300, 1.360), (-0.300, -0.330, 1.130), "laser"),
    ("arm_B", (0.300, 0.420, 2.480), (0.820, 0.560, 1.900), (0.620, 0.140, 1.380), (0.500, 0.000, 1.170), "grip"),
    ("arm_C", (0.000, 0.560, 2.480), (0.000, 1.060, 2.050), (0.000, 0.980, 1.560), (0.000, 0.900, 1.400), "scan"),
]

def surgery_rig():
    b = "mount"; c = Vector((0, 0.280, 2.560))
    finish("ceiling_plate", cyl(0.620, 0.620, 0.040, 8, "z"), "c_dark", 0.010, 2, T(c.x, c.y, 2.620) @ RZ(22.5), b)
    finish("ring", torus(0.470, 0.050, 40, 10, "z"), "c_shell", 0, 1, T(c.x, c.y, 2.540) @ S(1, 1, 0.8), b)
    finish("ring_glow", torus(0.470, 0.010, 40, 6, "z"), "glow_cyan", 0, 1, T(c.x, c.y, 2.498), "status_glow")
    for k in range(4): seg("ring_strut", (c.x + 0.47 * cos(radians(k * 90 + 45)), c.y + 0.47 * sin(radians(k * 90 + 45)), 2.540), (c.x, c.y, 2.600), 0.050, 0.030, "c_dark", b, 0.006)
    finish("hub", cyl(0.140, 0.110, 0.120, 20, "z"), "c_teal", 0.010, 2, T(c.x, c.y, 2.540), b)
    # 수술등
    lm = "lamp"
    seg("lamp_arm", (c.x, c.y, 2.480), (0, -0.050, 2.200), 0.050, 0.040, "c_dark", lm, 0.008)
    finish("lamp_head", cyl(0.260, 0.220, 0.070, 32, "z"), "c_shell", 0.012, 3, T(0, -0.060, 2.160), lm)
    finish("lamp_ring", torus(0.180, 0.022, 36, 8, "z"), "glow_white", 0, 1, T(0, -0.060, 2.124), "work_light")
    for k in range(6): finish("lamp_cell", cyl(0.034, 0.034, 0.006, 16, "z"), "glow_white", 0, 1, T(0.090 * cos(radians(k * 60)), -0.060 + 0.090 * sin(radians(k * 60)), 2.124), "work_light")
    finish("lamp_handle", cyl(0.016, 0.016, 0.070, 12, "z"), "c_orange", 0.003, 1, T(0, -0.060, 2.095), lm)
    pivot("lamp", (c.x, c.y, 2.480), (0, 0, 1), b, lm, (-90, 90))
    for name, sh, el, wr, tip, tool in ARMS:
        sh, el, wr, tip = Vector(sh), Vector(el), Vector(wr), Vector(tip); u, f, t = name + "_upper", name + "_fore", name + "_tool"
        finish("shoulder_base", cyl(0.085, 0.085, 0.080, 22, "z"), "c_dark", 0.006, 2, T(sh.x, sh.y, sh.z + 0.040), b)
        finish("shoulder_ball", sphere(0.075), "c_shell", 0, 1, T(*sh), u)
        seg("upper", sh, el, 0.085, 0.070, "c_shell", u, 0.014, 3); seg("upper_inlay", sh.lerp(el, 0.2), sh.lerp(el, 0.8), 0.090, 0.030, "c_dark", u, 0.004)
        seg("upper_glow", sh.lerp(el, 0.3), sh.lerp(el, 0.7), 0.093, 0.006, "glow_cyan", "status_glow", 0)
        hinge("elbow", el, (el - sh).cross(wr - el), 0.060, 0.130, "c_teal", u)
        seg("fore", el, wr, 0.060, 0.050, "c_dark", f, 0.010, 3); seg("fore_piston", el.lerp(wr, 0.15), el.lerp(wr, 0.75), 0.022, 0.022, "chrome", f, 0.002)
        hinge("wrist", wr, (wr - el).cross(tip - wr) if (wr - el).cross(tip - wr).length > 1e-4 else (1, 0, 0), 0.040, 0.090, "c_orange", f)
        d = (tip - wr).normalized(); Mt = T(*wr) @ frame(d, (0, 1, 0) if abs(d.y) < 0.9 else (0, 0, 1)); L = (tip - wr).length
        finish("tool_body", box(L * 0.6, 0.050, 0.050), "c_shell", 0.008, 2, Mt @ T(L * 0.35, 0, 0), t)
        if tool == "laser":
            finish("emitter", cyl(0.016, 0.006, L * 0.4, 14, "x"), "chrome", 0.001, 1, Mt @ T(L * 0.82, 0, 0), t)
            finish("emitter_tip", sphere(0.007), "glow_red", 0, 1, Mt @ T(L * 1.03, 0, 0), "tool_glow")
            for k in range(3): finish("emitter_fin", box(0.040, 0.004, 0.030), "c_orange", 0.001, 1, Mt @ T(L * 0.62, 0, 0) @ RX(k * 60), t)
        elif tool == "grip":
            for k in range(3):
                Mf = Mt @ T(L * 0.66, 0, 0) @ RX(k * 120)
                finish("finger", box(0.070, 0.010, 0.014), "chrome", 0.002, 1, Mf @ T(0.030, 0, 0.022) @ RY(18), t)
                finish("finger_tip", box(0.050, 0.008, 0.010), "chrome", 0.002, 1, Mf @ T(0.080, 0, 0.022) @ RY(-28), t)
            finish("grip_led", torus(0.028, 0.004, 18, 6, "x"), "glow_amber", 0, 1, Mt @ T(L * 0.66, 0, 0), "tool_glow")
        else:
            finish("scan_bar", box(0.050, 0.320, 0.040), "c_dark", 0.008, 2, Mt @ T(L * 0.80, 0, 0), t)
            finish("scan_glow", box(0.004, 0.290, 0.016), "glow_cyan", 0, 1, Mt @ T(L * 0.80 + 0.026, 0, 0), "tool_glow")
        cable(name + "_hose", [tuple(sh + Vector((0, 0.05, -0.05))), tuple(sh.lerp(el, 0.5) + Vector((0, 0.10, 0.06))), tuple(el + Vector((0, 0.08, 0.02))), tuple(el.lerp(wr, 0.6) + Vector((0, 0.06, 0.03)))], 0.011, "rubber", f)
        pivot(name + "_shoulder", tuple(sh), (0, 0, 1), b, u, (-180, 180)); pivot(name + "_elbow", tuple(el), tuple((el - sh).cross(wr - el).normalized()), u, f, (-120, 120))
        pivot(name + "_wrist", tuple(wr), (1, 0, 0), f, t, (-90, 90)); pivot(name + "_tip", tuple(tip), tuple(d), t, "fx")

# ------------------------------------------------------------------ 도구 수레
def cart(o=(0, 0, 0)):
    b = "cart"; O = T(*o)
    for sx in (-1, 1):
        for sy in (-1, 1):
            finish("leg", box(0.026, 0.026, 0.800), "chrome", 0.004, 1, O @ T(0.250 * sx, 0.180 * sy, 0.470), b)
            finish("wheel", cyl(0.036, 0.036, 0.024, 16, "x"), "rubber", 0.004, 1, O @ T(0.250 * sx, 0.180 * sy, 0.036), b)
    for z, m in ((0.250, "c_dark"), (0.560, "c_dark"), (0.870, "c_shell")):
        finish("shelf", box(0.560, 0.420, 0.024), m, 0.006, 2, O @ T(0, 0, z), b)
        for sy in (-1, 1): finish("shelf_rail", box(0.540, 0.010, 0.030), "chrome", 0.002, 1, O @ T(0, 0.200 * sy, z + 0.026), b)
    finish("tray", box(0.360, 0.260, 0.012), "chrome", 0.004, 1, O @ T(-0.070, -0.040, 0.888), b)
    for i in range(6):
        finish("tool", box(0.008, 0.150 + (i % 3) * 0.020, 0.006), "chrome", 0.001, 1, O @ T(-0.200 + i * 0.040, -0.040, 0.897) @ RZ(i * 3 - 6), b)
        finish("tool_grip", box(0.012, 0.050, 0.010), "c_teal" if i % 2 else "c_orange", 0.002, 1, O @ T(-0.200 + i * 0.040, 0.040, 0.899) @ RZ(i * 3 - 6), b)
    for i in range(3):
        finish("vial", cyl(0.016, 0.016, 0.080, 14, "z"), "glass", 0.002, 1, O @ T(0.170 + i * 0.040, 0.120, 0.922), b)
        finish("vial_fluid", cyl(0.012, 0.012, 0.050, 12, "z"), ("glow_cyan", "glow_amber", "glow_magenta")[i], 0, 1, O @ T(0.170 + i * 0.040, 0.120, 0.912), "vial_glow")
    finish("chip_case", box(0.140, 0.100, 0.030), "c_dark", 0.006, 2, O @ T(0.180, -0.090, 0.897), b)
    for i in range(3): finish("chip", box(0.030, 0.050, 0.004), "glow_amber", 0, 1, O @ T(0.140 + i * 0.040, -0.090, 0.914), "vial_glow")
    finish("box_low", box(0.300, 0.260, 0.160), "c_orange", 0.010, 2, O @ T(-0.080, 0, 0.342), b); finish("box_low2", box(0.160, 0.220, 0.120), "c_teal", 0.010, 2, O @ T(0.170, 0.020, 0.632), b)
    finish("coil", torus(0.080, 0.016, 24, 8, "z"), "rubber", 0, 1, O @ T(-0.120, 0.000, 0.590), b)
    # 화면
    m = "monitor"
    finish("monitor_pole", cyl(0.014, 0.014, 0.520, 12, "z"), "chrome", 0.002, 1, O @ T(0.250, 0.180, 1.130), b)
    Mm = O @ T(0.170, 0.150, 1.380) @ RZ(-22) @ RX(-8)
    finish("monitor_case", box(0.420, 0.036, 0.280), "c_dark", 0.010, 2, Mm, m)
    finish("monitor_screen", box(0.390, 0.004, 0.250), "c_screen", 0, 1, Mm @ T(0, -0.019, 0), m)
    pts = [(-0.180, 0.060), (-0.110, 0.060), (-0.090, 0.100), (-0.070, 0.010), (-0.050, 0.060), (0.020, 0.060), (0.040, 0.100), (0.060, 0.010), (0.080, 0.060), (0.180, 0.060)]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]): seg("pulse", Mm @ Vector((x0, -0.022, z0)), Mm @ Vector((x1, -0.022, z1)), 0.002, 0.005, "glow_cyan", "screen_glow", 0)
    for i in range(4): finish("bar", box(0.030 + 0.025 * ((i * 7) % 4), 0.002, 0.014), ("glow_amber", "glow_cyan", "glow_magenta", "glow_cyan")[i], 0, 1, Mm @ T(-0.150 + 0.012 * ((i * 7) % 4), -0.022, -0.020 - i * 0.026), "screen_glow")
    finish("ring_gauge", torus(0.040, 0.006, 24, 6, "y"), "glow_amber", 0, 1, Mm @ T(0.110, -0.022, -0.050), "screen_glow")
    pivot("monitor", tuple((O @ Vector((0.250, 0.180, 1.380)))), (0, 0, 1), b, m, (-90, 90))

MODULES = {"chair": (chair, (0, 0, 0.75), 1.25), "surgery_rig": (surgery_rig, (0, 0.2, 1.9), 1.45), "cart": (cart, (0, 0, 0.75), 1.0)}

# ------------------------------------------------------------------ 장면
def room():
    r = "room"
    finish("floor", box(7.0, 7.0, 0.02), "c_tile", 0, 1, T(0, 0.5, -0.01), r)
    for i in range(-5, 6):
        finish("tile_x", box(0.008, 7.0, 0.002), "black", 0, 1, T(i * 0.6, 0.5, 0.001), r); finish("tile_y", box(7.0, 0.008, 0.002), "black", 0, 1, T(0, 0.5 + i * 0.6, 0.001), r)
    finish("wall_back", box(7.0, 0.1, 3.0), "c_wall", 0, 1, T(0, 2.45, 1.5), r); finish("wall_side", box(0.1, 7.0, 3.0), "c_wall", 0, 1, T(2.75, 0.5, 1.5), r)
    finish("ceiling", box(7.0, 7.0, 0.05), "c_wall", 0, 1, T(0, 0.5, 2.67), r)
    for i in range(6):
        x = -2.4 + i * 0.95
        finish("wall_panel", box(0.86, 0.04, 1.30), "c_dark", 0.01, 2, T(x, 2.38, 0.70), r)
        finish("panel_strip", box(0.86, 0.02, 0.03), ("glow_cyan", "glow_magenta")[i % 2], 0, 1, T(x, 2.36, 1.40), r)
    finish("sign_box", box(1.50, 0.06, 0.42), "c_dark", 0.01, 2, T(-0.70, 2.36, 2.10), r)
    text("sign", "CLINIC  24H", 0.20, T(-0.70, 2.32, 2.10) @ RX(90), "glow_magenta", r, 0.004)
    for i in range(3):
        finish("shelf", box(1.30, 0.34, 0.03), "c_dark", 0.006, 1, T(1.55, 2.22, 1.05 + i * 0.42), r)
        for k in range(5): finish("shelf_box", box(0.18, 0.22, 0.14 + 0.05 * ((k + i) % 3)), ("c_orange", "c_teal", "c_shell", "c_dark")[(k + i) % 4], 0.008, 1, T(1.05 + k * 0.25, 2.20, 1.14 + i * 0.42 + 0.025 * ((k + i) % 3)), r)
    finish("cabinet", box(0.50, 1.60, 0.95), "c_shell", 0.012, 2, T(2.42, 1.20, 0.475), r)
    for k in range(3): finish("drawer", box(0.02, 0.46, 0.24), "c_dark", 0.006, 1, T(2.165, 0.66 + k * 0.52, 0.62), r)
    finish("wall_screen", box(0.05, 1.10, 0.62), "c_dark", 0.008, 2, T(2.67, 1.20, 1.75), r); finish("wall_screen_glow", box(0.01, 1.00, 0.52), "c_panel_glow", 0, 1, T(2.64, 1.20, 1.75), r)
    for k in range(5): finish("wall_screen_bar", box(0.012, 0.20 + 0.12 * ((k * 3) % 4), 0.03), "glow_amber" if k == 1 else "glow_cyan", 0, 1, T(2.636, 0.95 + 0.06 * ((k * 3) % 4), 1.92 - k * 0.08), r)
    for k in range(3): cable("pipe", [(-3.2, 2.20 - k * 0.12, 2.56 - k * 0.02), (0, 2.20 - k * 0.12, 2.58 - k * 0.02), (2.6, 2.20 - k * 0.12, 2.56 - k * 0.02)], 0.035, "gunmetal", r)
    finish("vent", box(0.9, 0.9, 0.06), "c_dark", 0.01, 1, T(-1.8, 0.6, 2.62), r)

def scene():
    doc = None
    try:
        import person
        rig, meshes, joints, rest, made, B, k = person.build("doctor")
        pose = {"shoulder_L.flex": 38, "shoulder_R.flex": 30, "shoulder_L.abduct": 6, "shoulder_R.abduct": 10, "elbow_L.bend": 62, "elbow_R.bend": 78,
                "waist.pitch": 10, "neck.pitch": 14, "neck.yaw": -8, "hip_L.flex": 4, "hip_R.flex": -3}
        pose.update(person.hand_pose("relaxed")); person.apply_pose(rig, joints, rest, pose)
        rig.location = (0.98, -0.10, 0); rig.rotation_euler = (0, 0, radians(-96)); doc = rig
    except Exception as e:
        print("doctor skipped:", repr(e)[:160]); kit.reset()
    materials(); chair(); surgery_rig(); cart((-0.95, 0.55, 0)); room()
    sc = bpy.context.scene; w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.002, 0.003, 0.004, 1)
    kit.area("lamp", (0, -0.06, 2.10), (0.15, -0.05, 0.8), 0.36, 300, (1.0, 0.97, 0.92))
    kit.area("cyan", (-2.6, -1.2, 1.9), (0, 0.2, 1.0), 1.6, 110, (0.15, 0.8, 1.0)); kit.area("magenta", (2.2, 2.0, 2.2), (0.3, 0.3, 1.0), 1.2, 130, (1.0, 0.12, 0.5))
    kit.area("front", (-0.6, -3.4, 1.6), (0.3, 0, 1.0), 2.2, 18, (1.0, 0.9, 0.8))
    res = tuple(int(v) for v in os.environ.get("CL_RES", "1600,900").split(","))
    kit.shot(os.path.join(OUT, "clinic_scene.png"), (-2.25, -3.05, 1.55), (0.25, 0.35, 1.12), 32, res=res)
    kit.shot(os.path.join(OUT, "clinic_scene_close.png"), (-0.55, -2.05, 1.50), (0.60, 0.05, 1.12), 40, res=res)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if MODE == "scene":
        scene()
    else:
        for name, (fn, c, k) in MODULES.items():
            if len(ARGS) > 2 and name not in ARGS[2:]: continue
            kit.reset(); materials(); fn()
            if "norender" not in ARGS:
                kit.studio(c, k, top=0.7, key=0.8); res = tuple(int(v) for v in os.environ.get("CL_RES", "1200,900").split(","))
                kit.shot(os.path.join(OUT, f"{name}_front.png"), (c[0] - 1.9 * k, c[1] - 2.6 * k, c[2] + 0.75 * k), c, 60, res=res)
                kit.shot(os.path.join(OUT, f"{name}_rear.png"), (c[0] + 2.1 * k, c[1] + 2.3 * k, c[2] + 0.6 * k), c, 60, res=res)
                for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
            kit.export(os.path.join(OUT, name), name)
