"""무기 (자체 디자인): 권총, 리볼버, 기관단총, 돌격소총, 산탄총, 저격총, 장검, 단검.
실행: python weapons.py <출력폴더> [render] [이름...]
앞(총구·칼끝)이 -Y, 위가 +Z. 원점은 방아쇠 뒤 손잡이 윗부분(쥐는 손 위치).
움직이는 부품(slide, bolt, mag, trigger, cylinder, pump)은 따로 나뉜다. 붙임점(muzzle, eject, grip, support, sight, mag)은 manifest의 pivots에 기록된다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, text, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/weapons"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []

def materials():
    kit.mat_paint("w_black", (0.028, 0.03, 0.034), (0.5, 0.5, 0.5), rough=(0.34, 0.52), wear=1.5)
    kit.mat_paint("w_tan", (0.36, 0.28, 0.17), rough=(0.42, 0.6), wear=1.4)
    kit.mat_paint("w_white", (0.62, 0.63, 0.64), rough=(0.26, 0.42), wear=1.2)
    kit.mat_paint("w_orange", (0.80, 0.20, 0.02), rough=(0.36, 0.55), wear=1.6)
    kit.mat_paint("w_olive", (0.10, 0.13, 0.08), rough=(0.42, 0.6), wear=1.5)
    kit.mat_simple("w_grip", (0.016, 0.016, 0.018), 0.0, 0.78)
    kit.mat_simple("w_wood", (0.16, 0.07, 0.03), 0.0, 0.45)
    kit.mat_simple("w_wrap", (0.05, 0.012, 0.014), 0.0, 0.85)

def pl(name, pts, w, mat, part, x=0.0, bev=0.0015, segs=2):
    """옆모습 다각형 pts = [(y, z)...]을 폭 w로 민 판."""
    return finish(name, prism(pts, w, "x"), mat, bev, segs, T(x, 0, 0), part)

def bar(name, y0, y1, z, r, mat, part, segs=20, x=0.0, r2=None):
    return finish(name, cyl(r, r2 or r, abs(y1 - y0), segs, "y"), mat, min(0.001, r * 0.2), 1, T(x, (y0 + y1) / 2, z), part)

def rail(y0, y1, z, part, w=0.021, mat="gunmetal"):
    finish("rail_base", box(w * 0.7, abs(y1 - y0), 0.004), mat, 0.0006, 1, T(0, (y0 + y1) / 2, z + 0.002), part)
    m = bmesh.new(); n = int(abs(y1 - y0) / 0.010)
    for k in range(n): bmesh.ops.create_cube(m, size=1.0, matrix=T(0, min(y0, y1) + 0.005 + k * 0.010, z + 0.0065) @ S(w, 0.0052, 0.005))
    finish("rail_teeth", m, mat, 0.0005, 1, part=part)

def guard(y0, y1, z0, part, w=0.012, mat="w_black"):
    """방아쇠울: 앞 기둥, 아래 막대, 뒤 연결."""
    finish("guard_front", box(w, 0.005, abs(z0) + 0.004), mat, 0.0012, 1, T(0, y0, z0 / 2) @ RX(-12), part)
    finish("guard_bottom", box(w, abs(y1 - y0) + 0.006, 0.005), mat, 0.0012, 1, T(0, (y0 + y1) / 2 + 0.003, z0), part)
    finish("trigger", prism([(-0.004, 0.0), (0.004, 0.0), (0.001, -0.022), (-0.005, -0.024)], 0.007, "x"), "steel", 0.001, 1, T(0, (y0 + y1) / 2 - 0.004, -0.004), "trigger")

def glow_sight(y, z, part, col="glow_cyan", s=1.0):
    finish("sight_body", box(0.034 * s, 0.060 * s, 0.012 * s), "w_black", 0.002, 2, T(0, y, z + 0.006 * s), part)
    for sx in (-1, 1): finish("sight_wall", box(0.004 * s, 0.050 * s, 0.034 * s), "w_black", 0.0015, 1, T(0.015 * s * sx, y, z + 0.026 * s), part)
    finish("sight_top", box(0.034 * s, 0.050 * s, 0.004 * s), "w_black", 0.0015, 1, T(0, y, z + 0.043 * s), part)
    finish("sight_lens", box(0.026 * s, 0.002, 0.028 * s), col, 0, 1, T(0, y - 0.018 * s, z + 0.026 * s), part)

def attach(mz, ej=None, grip=(0, 0.02, -0.06), sup=None, sight=None, mag=None):
    pivot("muzzle", mz, (0, -1, 0), "body", "fx")
    if ej: pivot("eject", ej, (1, 0, 0.4), "body", "fx")
    pivot("grip", grip, (0, 0, 1), "body", "hand_R")
    if sup: pivot("support", sup, (0, 0, 1), "body", "hand_L")
    if sight: pivot("sight", sight, (0, -1, 0), "body", "attachment")
    if mag: pivot("mag", mag, (0, 0, -1), "body", "mag", (0, 0))

# ------------------------------------------------------------------ 총
def pistol():
    """자동 권총 (군용 각진 양식)."""
    b = "body"
    pl("slide", [(-0.152, 0.024), (-0.152, 0.057), (-0.142, 0.064), (0.048, 0.064), (0.056, 0.054), (0.056, 0.024)], 0.029, "w_black", "slide", bev=0.002)
    for k in range(7):
        for sx in (-1, 1): finish("serration", box(0.002, 0.004, 0.026), "black", 0, 1, T(0.0146 * sx, 0.010 + k * 0.0062, 0.043) @ RX(-10), "slide")
    finish("eject_port", box(0.016, 0.034, 0.004), "black", 0.001, 1, T(0.006, -0.036, 0.0632), "slide")
    finish("chamber", box(0.012, 0.030, 0.003), "steel", 0.001, 1, T(0.006, -0.036, 0.0622), "slide")
    pl("frame", [(-0.146, 0.000), (-0.146, 0.023), (0.057, 0.023), (0.062, 0.004), (0.040, -0.010), (-0.030, -0.010), (-0.030, 0.000)], 0.026, "gunmetal", b, bev=0.002)
    pl("dust_cover", [(-0.144, -0.008), (-0.144, 0.001), (-0.040, 0.001), (-0.040, -0.008)], 0.022, "gunmetal", b)
    rail(-0.140, -0.050, -0.0085 - 0.011, b, 0.019)
    pl("grip", [(-0.028, -0.010), (0.041, -0.010), (0.064, -0.112), (0.014, -0.120)], 0.030, "w_grip", b, bev=0.004, segs=3)
    pl("grip_panel", [(-0.012, -0.022), (0.036, -0.022), (0.053, -0.100), (0.016, -0.106)], 0.0335, "w_tan", b, bev=0.002)
    for k in range(6): finish("grip_groove", box(0.035, 0.030, 0.0016), "w_grip", 0, 1, T(0, 0.020 + k * 0.004, -0.036 - k * 0.012) @ RX(13), b)
    pl("mag_base", [(0.012, -0.120), (0.066, -0.112), (0.069, -0.124), (0.014, -0.133)], 0.032, "titan", "mag", bev=0.002)
    guard(-0.088, -0.028, -0.042, b)
    bar("barrel", -0.160, -0.140, 0.045, 0.0075, "steel", b); bar("bore", -0.1612, -0.1598, 0.045, 0.0048, "black", b, 14)
    finish("front_sight", box(0.004, 0.010, 0.006), "w_black", 0.0008, 1, T(0, -0.140, 0.067), "slide")
    finish("front_dot", box(0.0022, 0.001, 0.0022), "glow_cyan", 0, 1, T(0, -0.1345, 0.0685), "slide")
    for sx in (-1, 1): finish("rear_sight", box(0.006, 0.010, 0.007), "w_black", 0.0008, 1, T(0.0075 * sx, 0.044, 0.0675), "slide")
    finish("hammer", box(0.008, 0.012, 0.014), "steel", 0.002, 1, T(0, 0.060, 0.046) @ RX(20), b)
    finish("slide_stop", box(0.003, 0.030, 0.005), "steel", 0.001, 1, T(-0.0142, -0.020, 0.020), b)
    finish("light_module", box(0.024, 0.060, 0.024), "w_black", 0.003, 2, T(0, -0.112, -0.034), b)
    finish("light_lens", cyl(0.008, 0.008, 0.002, 14, "y"), "glow_white", 0, 1, T(0, -0.143, -0.034), b)
    attach((0, -0.162, 0.045), (0.016, -0.036, 0.064), (0, 0.022, -0.062), None, (0, -0.02, 0.066), (0, 0.040, -0.120))

def revolver():
    """대구경 리볼버 (거리 개조 양식)."""
    b = "body"
    pl("frame", [(-0.075, 0.012), (-0.075, 0.066), (0.050, 0.066), (0.066, 0.046), (0.060, 0.000), (0.030, -0.012), (-0.030, -0.012), (-0.030, 0.012)], 0.030, "steel", b, bev=0.003, segs=3)
    finish("cylinder", cyl(0.0265, 0.0265, 0.058, 30, "y"), "gunmetal", 0.002, 2, T(0, -0.020, 0.038), "cylinder")
    for k in range(6):
        a = 2 * pi * k / 6
        finish("flute", cyl(0.007, 0.007, 0.040, 10, "y"), "black", 0, 1, T(0.0245 * cos(a), -0.028, 0.038 + 0.0245 * sin(a)), "cylinder")
        finish("chamber_hole", cyl(0.0058, 0.0058, 0.002, 10, "y"), "black", 0, 1, T(0.0155 * cos(a + 0.52), -0.0495, 0.038 + 0.0155 * sin(a + 0.52)), "cylinder")
    pivot("cylinder", (0, -0.020, 0.038), (0, 1, 0), b, "cylinder", (-360, 360))
    pl("barrel_shroud", [(-0.250, 0.018), (-0.250, 0.070), (-0.240, 0.076), (-0.075, 0.076), (-0.075, 0.018)], 0.026, "gunmetal", b, bev=0.003, segs=3)
    pl("underlug", [(-0.236, 0.004), (-0.236, 0.020), (-0.075, 0.020), (-0.075, 0.004)], 0.020, "steel", b, bev=0.002)
    for k in range(4): finish("vent", box(0.028, 0.020, 0.008), "black", 0.001, 1, T(0, -0.215 + k * 0.036, 0.066), b)
    bar("barrel", -0.262, -0.248, 0.047, 0.0105, "steel", b); bar("bore", -0.2632, -0.2618, 0.047, 0.0064, "black", b, 14)
    finish("comp", box(0.030, 0.026, 0.040), "w_orange", 0.003, 2, T(0, -0.238, 0.050), b)
    for sx in (-1, 1): finish("comp_port", box(0.002, 0.012, 0.010), "black", 0, 1, T(0.0155 * sx, -0.238, 0.058), b)
    pl("grip", [(0.020, -0.010), (0.062, 0.004), (0.094, -0.100), (0.070, -0.124), (0.036, -0.112)], 0.032, "w_wood", b, bev=0.006, segs=3)
    pl("grip_wrap", [(0.040, -0.040), (0.078, -0.034), (0.088, -0.074), (0.050, -0.082)], 0.0345, "w_wrap", b, bev=0.003)
    guard(-0.036, 0.022, -0.046, b)
    finish("hammer", prism([(0.058, 0.060), (0.072, 0.082), (0.080, 0.078), (0.070, 0.054)], 0.010, "x"), "steel", 0.002, 1, part="hammer")
    finish("front_sight", prism([(-0.246, 0.076), (-0.226, 0.076), (-0.230, 0.088)], 0.004, "x"), "w_orange", 0.0006, 1, part=b)
    finish("rear_sight", box(0.016, 0.012, 0.006), "w_black", 0.001, 1, T(0, 0.044, 0.069), b)
    finish("tape", cyl(0.0125, 0.0125, 0.018, 14, "y"), "w_wrap", 0, 1, T(0, -0.150, 0.047), b)
    attach((0, -0.264, 0.047), None, (0, 0.058, -0.060), None, (0, -0.10, 0.078))

def smg():
    """기관단총 (매끈한 기업 양식, 유도형)."""
    b = "body"
    pl("receiver", [(-0.210, 0.006), (-0.220, 0.040), (-0.200, 0.074), (0.110, 0.074), (0.130, 0.050), (0.130, 0.006)], 0.042, "w_white", b, bev=0.005, segs=3)
    pl("side_inlay", [(-0.180, 0.022), (-0.186, 0.052), (0.080, 0.052), (0.080, 0.022)], 0.0445, "w_black", b, bev=0.002)
    for sx in (-1, 1): finish("glow_line", box(0.001, 0.220, 0.003), "glow_cyan", 0, 1, T(0.0226 * sx, -0.050, 0.037), b)
    pl("shroud", [(-0.300, 0.016), (-0.300, 0.062), (-0.210, 0.066), (-0.210, 0.012)], 0.036, "w_black", b, bev=0.004, segs=3)
    for k in range(5):
        for sx in (-1, 1): finish("shroud_slot", box(0.002, 0.010, 0.022), "black", 0, 1, T(0.0182 * sx, -0.288 + k * 0.017, 0.040), b)
    bar("barrel", -0.318, -0.300, 0.040, 0.009, "steel", b); bar("bore", -0.3192, -0.3178, 0.040, 0.0052, "black", b, 14)
    pl("grip", [(-0.006, 0.006), (0.050, 0.006), (0.074, -0.098), (0.026, -0.104)], 0.034, "w_grip", b, bev=0.005, segs=3)
    pl("magwell", [(-0.118, -0.020), (-0.118, 0.008), (-0.066, 0.008), (-0.062, -0.020)], 0.034, "w_white", b, bev=0.003)
    pl("mag", [(-0.115, -0.150), (-0.115, -0.020), (-0.066, -0.020), (-0.060, -0.150)], 0.026, "gunmetal", "mag", bev=0.003)
    finish("mag_window", box(0.027, 0.010, 0.090), "glow_cyan", 0, 1, T(0, -0.0905, -0.080), "mag")
    guard(-0.056, -0.010, -0.038, b)
    pl("stock_arm", [(0.130, 0.040), (0.130, 0.060), (0.250, 0.060), (0.250, 0.040)], 0.014, "gunmetal", b)
    pl("stock_pad", [(0.250, -0.010), (0.250, 0.076), (0.268, 0.076), (0.272, -0.010)], 0.032, "w_grip", b, bev=0.004, segs=3)
    rail(-0.190, 0.090, 0.074, b)
    glow_sight(-0.050, 0.083, b, "glow_cyan")
    finish("bolt", box(0.006, 0.050, 0.012), "steel", 0.001, 1, T(0.022, -0.110, 0.060), "bolt")
    finish("smart_link", box(0.030, 0.050, 0.010), "w_black", 0.003, 2, T(0, 0.080, 0.079), b)
    finish("smart_led", box(0.012, 0.004, 0.004), "glow_cyan", 0, 1, T(0, 0.106, 0.080), b)
    attach((0, -0.320, 0.040), (0.024, -0.110, 0.066), (0, 0.034, -0.050), (0, -0.250, 0.010), (0, -0.05, 0.085), (0, -0.090, -0.020))

def rifle():
    """돌격소총 (군용 각진 양식)."""
    b = "body"
    pl("upper", [(-0.200, 0.030), (-0.200, 0.076), (0.150, 0.076), (0.166, 0.060), (0.166, 0.030)], 0.044, "w_black", b, bev=0.003)
    pl("lower", [(-0.125, -0.012), (-0.125, 0.030), (0.166, 0.030), (0.166, 0.004), (0.070, -0.012)], 0.040, "gunmetal", b, bev=0.003)
    pl("magwell", [(-0.122, -0.058), (-0.122, -0.012), (-0.056, -0.012), (-0.050, -0.058)], 0.038, "gunmetal", b, bev=0.003)
    pl("mag", [(-0.118, -0.058), (-0.054, -0.058), (-0.082, -0.205), (-0.146, -0.192)], 0.027, "w_tan", "mag", bev=0.003)
    for k in range(4): finish("mag_rib", box(0.029, 0.058, 0.004), "w_tan", 0.001, 1, T(0, -0.092 - k * 0.006, -0.085 - k * 0.030) @ RX(-10), "mag")
    pl("grip", [(0.022, -0.012), (0.068, -0.008), (0.098, -0.108), (0.052, -0.114)], 0.034, "w_grip", b, bev=0.005, segs=3)
    guard(-0.044, 0.024, -0.042, b)
    pl("handguard", [(-0.520, 0.020), (-0.520, 0.070), (-0.200, 0.076), (-0.200, 0.012)], 0.048, "w_olive", b, bev=0.004, segs=3)
    for k in range(7):
        for sx in (-1, 1): finish("hg_slot", box(0.002, 0.030, 0.010), "black", 0, 1, T(0.0242 * sx, -0.490 + k * 0.040, 0.046), b)
    rail(-0.510, 0.140, 0.076, b); rail(-0.500, -0.300, 0.012 - 0.011, b, 0.019)
    bar("barrel", -0.640, -0.520, 0.048, 0.0105, "steel", b); bar("gas_tube", -0.600, -0.520, 0.066, 0.004, "steel", b, 10)
    finish("gas_block", box(0.026, 0.030, 0.040), "gunmetal", 0.003, 2, T(0, -0.575, 0.056), b)
    bar("brake", -0.700, -0.640, 0.048, 0.0165, "gunmetal", b)
    for k in range(3):
        for sx in (-1, 1): finish("brake_port", box(0.004, 0.010, 0.016), "black", 0, 1, T(0.0155 * sx, -0.688 + k * 0.018, 0.048), b)
    bar("bore", -0.7012, -0.6998, 0.048, 0.0056, "black", b, 14)
    pl("foregrip", [(-0.405, -0.090), (-0.405, 0.000), (-0.370, 0.000), (-0.364, -0.090)], 0.030, "w_grip", b, bev=0.005, segs=3)
    bar("buffer", 0.166, 0.330, 0.050, 0.0155, "gunmetal", b)
    pl("stock", [(0.210, -0.040), (0.210, 0.074), (0.392, 0.078), (0.404, -0.058), (0.350, -0.066)], 0.040, "w_olive", b, bev=0.005, segs=3)
    pl("butt_pad", [(0.392, -0.058), (0.392, 0.078), (0.410, 0.074), (0.418, -0.056)], 0.042, "w_grip", b, bev=0.004)
    finish("eject_port", box(0.003, 0.060, 0.020), "black", 0.001, 1, T(0.0215, -0.050, 0.056), b)
    finish("bolt", box(0.004, 0.054, 0.016), "steel", 0.001, 1, T(0.0200, -0.050, 0.056), "bolt")
    finish("charging_handle", box(0.050, 0.020, 0.008), "gunmetal", 0.002, 1, T(0, 0.150, 0.072), "bolt")
    finish("selector", cyl(0.006, 0.006, 0.004, 12, "x"), "w_orange", 0, 1, T(-0.0205, 0.050, 0.012), b)
    glow_sight(-0.020, 0.085, b, "glow_red", 1.15)
    finish("front_sight", prism([(-0.500, 0.085), (-0.480, 0.085), (-0.486, 0.110), (-0.494, 0.110)], 0.008, "x"), "gunmetal", 0.001, 1, part=b)
    finish("laser_box", box(0.024, 0.060, 0.024), "w_black", 0.003, 2, T(0.036, -0.440, 0.046), b)
    finish("laser_lens", cyl(0.006, 0.006, 0.002, 12, "y"), "glow_red", 0, 1, T(0.036, -0.471, 0.046), b)
    attach((0, -0.702, 0.048), (0.024, -0.050, 0.062), (0, 0.060, -0.060), (0, -0.385, -0.045), (0, -0.02, 0.087), (0, -0.088, -0.058))

def shotgun():
    """펌프 산탄총 (거리 개조 양식)."""
    b = "body"
    pl("receiver", [(-0.170, 0.000), (-0.170, 0.072), (0.110, 0.072), (0.130, 0.044), (0.130, 0.000)], 0.046, "gunmetal", b, bev=0.004, segs=3)
    bar("barrel", -0.640, -0.170, 0.052, 0.0135, "steel", b); bar("bore", -0.6412, -0.6398, 0.052, 0.0105, "black", b, 16)
    bar("mag_tube", -0.600, -0.170, 0.018, 0.0125, "gunmetal", b); bar("tube_cap", -0.612, -0.600, 0.018, 0.0140, "steel", b)
    for y in (-0.590, -0.380): finish("clamp", box(0.034, 0.016, 0.062), "gunmetal", 0.003, 2, T(0, y, 0.036), b)
    pl("pump", [(-0.500, -0.012), (-0.500, 0.040), (-0.300, 0.040), (-0.300, -0.012)], 0.050, "w_orange", "pump", bev=0.006, segs=3)
    for k in range(8): finish("pump_rib", box(0.052, 0.008, 0.046), "w_grip", 0.002, 1, T(0, -0.485 + k * 0.024, 0.014), "pump")
    pivot("pump", (0, -0.400, 0.014), (0, 1, 0), b, "pump", (0, 0))
    pl("heat_shield", [(-0.620, 0.062), (-0.620, 0.074), (-0.200, 0.074), (-0.200, 0.062)], 0.032, "w_black", b, bev=0.002)
    for k in range(13): finish("shield_hole", box(0.034, 0.014, 0.004), "black", 0, 1, T(0, -0.600 + k * 0.031, 0.0745), b)
    pl("grip", [(0.060, 0.000), (0.110, 0.004), (0.150, -0.096), (0.104, -0.106)], 0.036, "w_grip", b, bev=0.005, segs=3)
    guard(-0.006, 0.062, -0.044, b)
    pl("stock", [(0.130, -0.004), (0.130, 0.050), (0.380, 0.040), (0.396, -0.090), (0.340, -0.100), (0.180, -0.030)], 0.040, "w_wood", b, bev=0.006, segs=3)
    pl("butt_pad", [(0.386, -0.094), (0.384, 0.042), (0.402, 0.040), (0.412, -0.090)], 0.042, "w_grip", b, bev=0.004)
    finish("shell_holder", box(0.010, 0.120, 0.030), "w_black", 0.003, 1, T(0.027, -0.030, 0.040), b)
    for k in range(5):
        finish("shell", cyl(0.0085, 0.0085, 0.050, 12, "z"), "w_orange" if k % 2 else "prop_red" if "prop_red" in kit.M else "w_orange", 0.001, 1, T(0.036, -0.078 + k * 0.024, 0.044), b)
        finish("shell_brass", cyl(0.0088, 0.0088, 0.012, 12, "z"), "titan", 0, 1, T(0.036, -0.078 + k * 0.024, 0.064), b)
    finish("eject_port", box(0.003, 0.070, 0.022), "black", 0.001, 1, T(0.0225, -0.090, 0.050), b)
    finish("bead", sphere(0.004, 1, 1, 1, 10, 6), "glow_amber", 0, 1, T(0, -0.612, 0.078), b)
    finish("tape", cyl(0.0150, 0.0150, 0.030, 14, "y"), "w_wrap", 0, 1, T(0, -0.250, 0.052), b)
    attach((0, -0.642, 0.052), (0.026, -0.090, 0.056), (0, 0.105, -0.056), (0, -0.400, -0.012), (0, -0.10, 0.076), None)

def sniper():
    """정밀 소총 (충전 관통형). 총열의 코일 고리가 충전량에 따라 빛난다."""
    b = "body"
    pl("receiver", [(-0.260, 0.010), (-0.260, 0.082), (0.170, 0.082), (0.190, 0.056), (0.190, 0.010)], 0.050, "w_white", b, bev=0.004, segs=3)
    pl("receiver_inlay", [(-0.230, 0.024), (-0.230, 0.064), (0.140, 0.064), (0.140, 0.024)], 0.0525, "w_black", b, bev=0.002)
    pl("capacitor", [(-0.200, -0.050), (-0.200, 0.010), (-0.020, 0.010), (-0.030, -0.050)], 0.058, "gunmetal", b, bev=0.005, segs=3)
    for k in range(4): finish("cap_cell", box(0.060, 0.030, 0.040), "glow_amber", 0, 1, T(0, -0.176 + k * 0.042, -0.022), b)
    for k in range(5): finish("cap_rib", box(0.064, 0.010, 0.050), "gunmetal", 0.002, 1, T(0, -0.197 + k * 0.042, -0.022), b)
    bar("barrel", -0.930, -0.260, 0.050, 0.014, "steel", b)
    pl("barrel_frame", [(-0.860, 0.020), (-0.860, 0.030), (-0.260, 0.034), (-0.260, 0.016)], 0.030, "w_black", b, bev=0.003)
    for k in range(9):
        y = -0.820 + k * 0.064
        finish("coil", torus(0.0235, 0.0065, 26, 8, "y"), "gunmetal", 0, 1, T(0, y, 0.050), b)
        finish("coil_glow", torus(0.0205, 0.0030, 26, 6, "y"), "glow_amber", 0, 1, T(0, y, 0.050), "coil_glow")
    bar("muzzle", -0.990, -0.930, 0.050, 0.022, "gunmetal", b)
    for k in range(3): finish("muzzle_slot", box(0.050, 0.010, 0.012), "black", 0, 1, T(0, -0.975 + k * 0.018, 0.050), b)
    bar("bore", -0.9912, -0.9898, 0.050, 0.0075, "black", b, 14)
    pl("grip", [(0.040, 0.010), (0.092, 0.012), (0.124, -0.098), (0.076, -0.106)], 0.036, "w_grip", b, bev=0.005, segs=3)
    guard(-0.020, 0.044, -0.034, b)
    pl("stock", [(0.190, 0.014), (0.190, 0.074), (0.460, 0.078), (0.470, -0.060), (0.420, -0.070), (0.300, 0.000)], 0.044, "w_white", b, bev=0.006, segs=3)
    pl("cheek_rest", [(0.260, 0.078), (0.260, 0.100), (0.400, 0.100), (0.410, 0.078)], 0.038, "w_grip", b, bev=0.004)
    pl("butt_pad", [(0.458, -0.062), (0.458, 0.080), (0.478, 0.076), (0.486, -0.060)], 0.046, "w_grip", b, bev=0.004)
    rail(-0.240, 0.150, 0.082, b)
    # 조준경
    for y in (-0.110, 0.040):
        finish("scope_ring", box(0.040, 0.016, 0.052), "w_black", 0.003, 2, T(0, y, 0.114), b)
    bar("scope_tube", -0.190, 0.130, 0.128, 0.0165, "w_black", b, 24); bar("scope_bell", -0.290, -0.190, 0.128, 0.0165, "w_black", b, 24, r2=0.027)
    bar("scope_eye", 0.130, 0.175, 0.128, 0.0165, "w_black", b, 24, r2=0.021)
    bar("scope_lens", -0.2915, -0.2895, 0.128, 0.024, "glow_cyan", b, 24)
    finish("scope_turret", cyl(0.012, 0.012, 0.022, 16, "z"), "gunmetal", 0.001, 1, T(0, -0.030, 0.152), b)
    finish("scope_turret_side", cyl(0.012, 0.012, 0.022, 16, "x"), "gunmetal", 0.001, 1, T(0.026, -0.030, 0.128), b)
    # 양각대
    for sx in (-1, 1):
        finish("bipod_leg", cyl(0.006, 0.005, 0.260, 10, "z"), "gunmetal", 0, 1, T(0.075 * sx, -0.640, -0.100) @ RY(-26 * sx), b)
        finish("bipod_foot", box(0.030, 0.040, 0.008), "w_grip", 0.002, 1, T(0.132 * sx, -0.640, -0.220), b)
    finish("bipod_mount", box(0.050, 0.040, 0.026), "gunmetal", 0.003, 2, T(0, -0.640, 0.014), b)
    finish("bolt_handle", cyl(0.006, 0.006, 0.050, 10, "x"), "steel", 0, 1, T(0.050, 0.060, 0.050), "bolt")
    finish("bolt_knob", sphere(0.012, 1, 1, 1, 12, 8), "w_black", 0, 1, T(0.078, 0.060, 0.050), "bolt")
    attach((0, -0.992, 0.050), (0.028, 0.000, 0.070), (0, 0.082, -0.050), (0, -0.330, 0.010), (0, -0.05, 0.13), None)

# ------------------------------------------------------------------ 칼
def blade_geo(P, Q, th, mat, part, name="blade"):
    """P = 날 끝선(z=0... 두께 0), Q = 두꺼운 등 부분. 좌표 (y, z): 날이 아래(-Z)를 본다."""
    bm = bmesh.new(); n = len(P)
    pv = [bm.verts.new((0, y, z)) for y, z in P]; qa = [bm.verts.new((th / 2, y, z)) for y, z in Q]; qb = [bm.verts.new((-th / 2, y, z)) for y, z in Q]
    bm.faces.new(qa); bm.faces.new(qb[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((qa[i], pv[i], pv[j], qa[j])); bm.faces.new((qb[i], qb[j], pv[j], pv[i]))
    return finish(name, bm, mat, 0, 1, part=part)

def katana(hot=False):
    """장검. 손잡이가 +Y, 칼끝이 -Y. hot=True면 날이 달아오른 변형."""
    b = "body"
    P = [(-0.030, -0.016), (-0.700, -0.016), (-0.760, 0.004), (-0.740, 0.013), (-0.030, 0.013)]
    Q = [(-0.030, -0.006), (-0.690, -0.006), (-0.742, 0.008), (-0.736, 0.0115), (-0.030, 0.0115)]
    blade_geo(P, Q, 0.0056, "steel", b)
    pl("fuller", [(-0.060, 0.002), (-0.640, 0.002), (-0.660, 0.008), (-0.060, 0.008)], 0.0062, "dark", b, bev=0.0004)
    e = 0.0012
    pl("edge_glow", [(-0.040, -0.016 - e), (-0.701, -0.016 - e), (-0.762, 0.004), (-0.760, 0.0052), (-0.699, -0.0150), (-0.040, -0.0150)], 0.0010, "glow_amber" if hot else "glow_cyan", "edge_glow", bev=0)
    pl("habaki", [(-0.045, -0.018), (-0.045, 0.015), (-0.008, 0.015), (-0.008, -0.018)], 0.011, "titan", b, bev=0.0015)
    finish("guard", box(0.016, 0.014, 0.078), "gunmetal", 0.004, 3, T(0, 0.000, -0.001), b)
    finish("guard_plate", box(0.050, 0.008, 0.050), "gunmetal", 0.004, 3, T(0, 0.002, -0.001), b)
    finish("guard_led", box(0.018, 0.0085, 0.006), "glow_amber" if hot else "glow_cyan", 0, 1, T(0, 0.002, 0.018), b)
    bar("handle", 0.008, 0.270, -0.001, 0.0150, "w_grip", b, 18)
    for k in range(9):
        finish("wrap", torus(0.0150, 0.0034, 18, 6, "y"), "w_wrap", 0, 1, T(0, 0.028 + k * 0.027, -0.001) @ RX(0) @ RZ(0) @ S(1, 1.6, 1), b)
    bar("pommel", 0.270, 0.292, -0.001, 0.0170, "titan", b, 18)
    finish("power_cell", box(0.022, 0.050, 0.012), "gunmetal", 0.003, 2, T(0, 0.045, 0.016), b)
    pivot("grip", (0, 0.10, 0), (0, -1, 0), b, "hand_R"); pivot("tip", (0, -0.76, 0.004), (0, -1, 0), b, "fx"); pivot("support", (0, 0.22, 0), (0, -1, 0), b, "hand_L")

def knife():
    """전투 단검."""
    b = "body"
    P = [(-0.012, -0.018), (-0.150, -0.018), (-0.205, 0.006), (-0.170, 0.016), (-0.012, 0.016)]
    Q = [(-0.012, -0.007), (-0.146, -0.007), (-0.190, 0.008), (-0.168, 0.0145), (-0.012, 0.0145)]
    blade_geo(P, Q, 0.0048, "steel", b)
    for k in range(6): finish("serration", box(0.0052, 0.006, 0.004), "dark", 0, 1, T(0, -0.040 - k * 0.012, 0.0155), b)
    pl("fuller", [(-0.030, 0.002), (-0.130, 0.002), (-0.140, 0.008), (-0.030, 0.008)], 0.0054, "dark", b, bev=0.0004)
    finish("guard", box(0.018, 0.012, 0.062), "gunmetal", 0.004, 3, T(0, -0.006, -0.002), b)
    pl("handle", [(0.000, -0.020), (0.000, 0.016), (0.112, 0.014), (0.120, -0.006), (0.104, -0.022)], 0.022, "w_grip", b, bev=0.005, segs=3)
    pl("handle_inlay", [(0.014, -0.010), (0.014, 0.008), (0.096, 0.007), (0.096, -0.010)], 0.0245, "w_orange", b, bev=0.002)
    for k in range(5): finish("handle_groove", box(0.026, 0.004, 0.030), "w_grip", 0.001, 1, T(0, 0.022 + k * 0.017, -0.003), b)
    finish("lanyard", torus(0.006, 0.002, 14, 6, "x"), "steel", 0, 1, T(0, 0.118, -0.002), b)
    pivot("grip", (0, 0.055, -0.002), (0, -1, 0), b, "hand_R"); pivot("tip", (0, -0.205, 0.006), (0, -1, 0), b, "fx")

WEAPONS = {"pistol": (pistol, 0.46), "revolver": (revolver, 0.54), "smg": (smg, 0.72), "rifle": (rifle, 1.15), "shotgun": (shotgun, 1.10),
           "sniper": (sniper, 1.50), "katana": (katana, 1.10), "knife": (knife, 0.36)}

def build(name):
    kit.reset(); materials(); WEAPONS[name][0]()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, (fn, size) in WEAPONS.items():
        if ONLY and name not in ONLY: continue
        build(name)
        if RENDER:
            objs = kit.asset_objects(); dg = bpy.context.evaluated_depsgraph_get()
            ys = [(o.matrix_world @ Vector(c)).y for o in objs for c in o.bound_box]; zs = [(o.matrix_world @ Vector(c)).z for o in objs for c in o.bound_box]
            cy, cz = (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2; k = size
            kit.studio((0, cy, cz), k * 0.42, floor_z=min(zs) - 0.02 * k)
            kit.shot(os.path.join(OUT, f"{name}.png"), (2.25 * k, cy - 0.85 * k, cz + 0.70 * k), (0, cy, cz), 85, dof=None, res=tuple(int(v) for v in os.environ.get("WPN_RES", "1400,800").split(",")))
            for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
        kit.export(os.path.join(OUT, name), name)
