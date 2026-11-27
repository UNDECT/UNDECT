"""보안 기계 (자체 디자인): 드론, 포탑, 감시 카메라.
실행: python machines.py <출력폴더> [render] [이름...]
앞이 -Y, 위가 +Z. 드론 원점은 몸통 가운데, 포탑과 카메라 원점은 설치면 가운데.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, prism, loft, bolt, cable, text, pivot, frame, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/machines"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []

def materials():
    kit.mat_paint("m_armor", (0.055, 0.085, 0.14), (0.5, 0.5, 0.5), rough=(0.30, 0.50), wear=1.5, scale=0.6)
    kit.mat_paint("m_light", (0.58, 0.60, 0.61), rough=(0.30, 0.52), wear=1.4, scale=0.6)
    kit.mat_paint("m_accent", (0.86, 0.50, 0.015), rough=(0.34, 0.55), scale=0.6)
    kit.mat_paint("m_frame", (0.05, 0.053, 0.06), (0.45, 0.45, 0.45), rough=(0.36, 0.55), scale=0.6)

def wedge(pts, w, mat, part, name="plate", bev=0.004, x=0.0, segs=2):
    """옆모습 다각형 pts = [(y, z)...]을 폭 w로 민 판."""
    return finish(name, prism(pts, w, "x"), mat, bev, segs, T(x, 0, 0), part)

def stripes(n, w, y, z, Mx, part, step=0.03):
    for k in range(n): finish("warn", box(w, 0.002, 0.012), "m_accent" if k % 2 == 0 else "black", 0, 1, Mx @ T(0, y, z + k * step * 0) @ T((k - (n - 1) / 2) * w, 0, 0), part)

# ------------------------------------------------------------------ 드론
def drone():
    """감시·전투 드론. 폭 약 1.0 m. 추진기 4개, 배 아래 회전 총좌."""
    b = "body"
    wedge([(-0.300, -0.010), (-0.330, 0.020), (-0.250, 0.070), (0.180, 0.085), (0.300, 0.050), (0.300, -0.020), (0.200, -0.050), (-0.200, -0.050)], 0.240, "m_armor", b, "hull", 0.012, segs=3)
    wedge([(-0.240, 0.070), (-0.150, 0.110), (0.120, 0.115), (0.180, 0.085)], 0.170, "m_light", b, "top_cover", 0.010, segs=3)
    wedge([(-0.330, 0.006), (-0.330, 0.030), (-0.262, 0.064), (-0.262, 0.006)], 0.150, "m_frame", b, "nose", 0.006)
    finish("eye_ring", torus(0.034, 0.008, 24, 8, "y"), "gunmetal", 0, 1, T(0, -0.332, 0.026), b)
    finish("eye", cyl(0.030, 0.030, 0.006, 24, "y"), "glow_red", 0, 1, T(0, -0.333, 0.026), "eye")
    finish("eye_core", cyl(0.012, 0.012, 0.008, 16, "y"), "black", 0, 1, T(0, -0.336, 0.026), b)
    for sx in (-1, 1):
        finish("side_sensor", box(0.016, 0.030, 0.016), "glow_white", 0, 1, T(0.090 * sx, -0.300, 0.012), b)
        finish("side_vent", box(0.004, 0.160, 0.040), "black", 0.001, 1, T(0.121 * sx, 0.060, 0.020), b)
        for k in range(5): finish("vent_fin", box(0.006, 0.004, 0.040), "m_frame", 0, 1, T(0.122 * sx, -0.004 + k * 0.032, 0.020), b)
        finish("nav", box(0.006, 0.030, 0.008), "glow_red" if sx < 0 else "glow_cyan", 0, 1, T(0.121 * sx, -0.180, 0.030), b)
    finish("stripe", box(0.172, 0.050, 0.002), "m_accent", 0, 1, T(0, -0.060, 0.1135) @ RX(-1.2), b)
    text("id", "SEC-07", 0.030, T(0, 0.060, 0.1150), "m_frame", b)
    finish("tail_fin", prism([(0.180, 0.085), (0.300, 0.150), (0.330, 0.150), (0.300, 0.050)], 0.012, "x"), "m_armor", 0.003, 1, part=b)
    finish("tail_light", box(0.014, 0.004, 0.030), "glow_red", 0, 1, T(0, 0.317, 0.140) @ RX(-20), b)
    finish("antenna", cyl(0.003, 0.002, 0.160, 6, "z"), "gunmetal", 0, 1, T(0.060, 0.160, 0.180), b)
    # 추진기: 팔 + 덕트 + 팬
    for name, sx, sy in (("FL", -1, -1), ("FR", 1, -1), ("RL", -1, 1), ("RR", 1, 1)):
        c = Vector((0.330 * sx, 0.250 * sy, 0.050))
        root = Vector((0.110 * sx, 0.120 * sy, 0.030)); d = c - root; L = d.length
        finish("arm", box(L, 0.040, 0.030), "m_frame", 0.006, 2, T(*((root + c) / 2)) @ frame(d, (0, 0, 1)), b)
        finish("arm_glow", box(L * 0.6, 0.006, 0.004), "glow_cyan", 0, 1, T(*((root + c) / 2 + Vector((0, 0, 0.0165)))) @ frame(d, (0, 0, 1)), b)
        finish("duct", torus(0.150, 0.022, 36, 10, "z"), "m_armor", 0, 1, T(*c) @ S(1, 1, 1.9), b)
        finish("duct_lip", torus(0.150, 0.008, 36, 8, "z"), "m_accent", 0, 1, T(c.x, c.y, c.z + 0.040), b)
        for k in range(3): finish("strut", box(0.300, 0.010, 0.008), "gunmetal", 0.001, 1, T(c.x, c.y, c.z - 0.020) @ RZ(k * 60), b)
        finish("motor", cyl(0.030, 0.026, 0.050, 18, "z"), "gunmetal", 0.003, 2, T(c.x, c.y, c.z - 0.004), b)
        p = "fan_" + name
        finish("hub", cyl(0.022, 0.016, 0.020, 16, "z"), "titan", 0.002, 1, T(c.x, c.y, c.z + 0.030), p)
        for k in range(5):
            finish("blade", prism([(0.018, -0.003), (0.132, -0.010), (0.136, 0.004), (0.020, 0.006)], 0.034, "y"), "m_light", 0.001, 1, T(c.x, c.y, c.z + 0.030) @ RZ(k * 72) @ RX(24), p)
        finish("thrust_glow", torus(0.128, 0.006, 32, 6, "z"), "glow_cyan", 0, 1, T(c.x, c.y, c.z - 0.044), "thrust_glow")
        pivot(p, (c.x, c.y, c.z + 0.030), (0, 0, 1), b, p, (-360, 360))
    # 총좌
    g = "gimbal"
    finish("gimbal_ring", cyl(0.060, 0.060, 0.020, 24, "z"), "gunmetal", 0.003, 2, T(0, -0.060, -0.058), b)
    finish("gimbal_body", cyl(0.050, 0.044, 0.050, 22, "z"), "m_frame", 0.004, 2, T(0, -0.060, -0.092), g)
    for sx in (-1, 1): finish("gimbal_ear", box(0.012, 0.050, 0.060), "m_armor", 0.004, 2, T(0.048 * sx, -0.060, -0.118), g)
    pivot("gimbal_yaw", (0, -0.060, -0.068), (0, 0, 1), b, g, (-180, 180))
    q = "gun"
    finish("gun_block", box(0.076, 0.130, 0.050), "m_armor", 0.006, 2, T(0, -0.080, -0.130), q)
    for sx in (-1, 1):
        finish("gun_barrel", cyl(0.009, 0.009, 0.200, 14, "y"), "steel", 0.001, 1, T(0.018 * sx, -0.230, -0.130), q)
        finish("gun_bore", cyl(0.0055, 0.0055, 0.002, 10, "y"), "black", 0, 1, T(0.018 * sx, -0.331, -0.130), q)
    finish("gun_shroud", box(0.060, 0.080, 0.034), "m_frame", 0.004, 2, T(0, -0.180, -0.130), q)
    finish("gun_laser", cyl(0.006, 0.006, 0.004, 10, "y"), "glow_red", 0, 1, T(0, -0.222, -0.108), q)
    finish("gun_feed", box(0.030, 0.060, 0.050), "m_accent", 0.004, 2, T(0, -0.020, -0.146), q)
    pivot("gun_pitch", (0, -0.060, -0.126), (1, 0, 0), g, q, (-60, 20)); pivot("muzzle", (0, -0.334, -0.130), (0, -1, 0), q, "fx"); pivot("eye", (0, -0.336, 0.026), (0, -1, 0), b, "fx")
    for sx in (-1, 1):
        for sy in (-1, 1): finish("skid", box(0.012, 0.012, 0.060), "gunmetal", 0.002, 1, T(0.090 * sx, 0.160 * sy + 0.02, -0.076), b)
        finish("skid_bar", box(0.014, 0.380, 0.012), "rubber", 0.003, 1, T(0.090 * sx, 0.020, -0.108), b)

# ------------------------------------------------------------------ 포탑
def turret():
    """보안 포탑. 바닥 설치형, 높이 약 1.15 m. 뒤집어 천장에 달 수 있다. 받침 -> 몸(좌우) -> 머리(상하) -> 총열(반동)."""
    b = "base"
    finish("plate", cyl(0.300, 0.320, 0.030, 8, "z"), "m_frame", 0.008, 2, T(0, 0, 0.015) @ RZ(22.5), b)
    for k in range(8):
        a = radians(k * 45); bolt(T(0.270 * cos(a), 0.270 * sin(a), 0.031), 0.012, part=b)
    finish("pedestal", cyl(0.150, 0.190, 0.420, 8, "z"), "m_armor", 0.012, 3, T(0, 0, 0.240) @ RZ(22.5), b)
    for k in range(4):
        a = radians(k * 90 + 45)
        finish("rib", box(0.030, 0.060, 0.360), "m_frame", 0.006, 2, T(0.172 * cos(a), 0.172 * sin(a), 0.230) @ RZ(k * 90 + 45 + 90), b)
        finish("warn", box(0.090, 0.004, 0.024), "m_accent", 0.001, 1, T(0.158 * cos(a - pi / 4), 0.158 * sin(a - pi / 4), 0.110) @ RZ(k * 90 + 90), b)
    finish("status_ring", torus(0.156, 0.007, 32, 6, "z"), "glow_red", 0, 1, T(0, 0, 0.452), "status_glow")
    finish("yaw_ring", cyl(0.170, 0.170, 0.036, 32, "z"), "gunmetal", 0.005, 2, T(0, 0, 0.474), b)
    y = "yoke"
    finish("turntable", cyl(0.160, 0.150, 0.050, 32, "z"), "m_frame", 0.006, 2, T(0, 0, 0.517), y)
    for sx in (-1, 1):
        wedge([(-0.090, 0.540), (-0.070, 0.900), (0.070, 0.900), (0.110, 0.540)], 0.040, "m_armor", y, "yoke_arm", 0.010, 0.210 * sx, 3)
        finish("yoke_cap", cyl(0.060, 0.060, 0.020, 24, "x"), "gunmetal", 0.004, 2, T(0.236 * sx, 0, 0.820), y)
        finish("yoke_led", cyl(0.020, 0.020, 0.004, 16, "x"), "glow_red", 0, 1, T(0.248 * sx, 0, 0.820), "status_glow")
    finish("yoke_bridge", box(0.420, 0.120, 0.050), "m_frame", 0.008, 2, T(0, 0.040, 0.565), y)
    pivot("yaw", (0, 0, 0.492), (0, 0, 1), b, y, (-170, 170))
    h = "head"
    wedge([(-0.260, 0.740), (-0.300, 0.800), (-0.260, 0.900), (0.200, 0.920), (0.280, 0.860), (0.280, 0.760), (0.200, 0.720)], 0.340, "m_light", h, "head_shell", 0.014, segs=3)
    wedge([(-0.300, 0.780), (-0.306, 0.820), (-0.270, 0.880), (-0.270, 0.760)], 0.250, "m_frame", h, "face", 0.006)
    finish("eye", box(0.150, 0.006, 0.026), "glow_red", 0, 1, T(0, -0.306, 0.850) @ RX(-8), "eye")
    finish("eye_frame", box(0.170, 0.010, 0.044), "gunmetal", 0.003, 1, T(0, -0.300, 0.850) @ RX(-8), h)
    finish("top_plate", box(0.240, 0.300, 0.016), "m_armor", 0.006, 2, T(0, -0.020, 0.920) @ RX(-2.5), h)
    text("id", "T-12", 0.050, T(0, 0.000, 0.9295) @ RX(-2.5), "m_light", h)
    for sx in (-1, 1):
        finish("ammo_box", box(0.070, 0.220, 0.130), "m_accent", 0.008, 2, T(0.208 * sx - 0.020 * sx, 0.120, 0.800), h)
        finish("ammo_window", box(0.004, 0.120, 0.030), "glow_amber", 0, 1, T(0.2245 * sx, 0.120, 0.820), h)
        finish("trunnion", cyl(0.040, 0.040, 0.070, 20, "x"), "titan", 0.004, 2, T(0.180 * sx, 0, 0.820), h)
    finish("sensor_mast", box(0.050, 0.070, 0.060), "m_frame", 0.006, 2, T(0.090, 0.120, 0.955), h)
    finish("sensor_lens", cyl(0.018, 0.018, 0.006, 16, "y"), "glow_cyan", 0, 1, T(0.090, 0.083, 0.958), h)
    finish("antenna", cyl(0.004, 0.002, 0.220, 6, "z"), "gunmetal", 0, 1, T(-0.090, 0.180, 1.030), h)
    pivot("pitch", (0, 0, 0.820), (1, 0, 0), y, h, (-35, 45))
    g = "barrels"
    finish("barrel_block", box(0.170, 0.160, 0.090), "m_frame", 0.008, 2, T(0, -0.340, 0.812), g)
    for sx in (-1, 1):
        finish("barrel", cyl(0.018, 0.018, 0.420, 18, "y"), "steel", 0.002, 1, T(0.046 * sx, -0.620, 0.812), g)
        finish("jacket", cyl(0.030, 0.030, 0.220, 18, "y"), "m_armor", 0.003, 2, T(0.046 * sx, -0.520, 0.812), g)
        for k in range(5): finish("jacket_slot", box(0.062, 0.022, 0.010), "black", 0, 1, T(0.046 * sx, -0.600 + k * 0.040, 0.812), g)
        finish("brake", cyl(0.026, 0.026, 0.060, 16, "y"), "gunmetal", 0.003, 1, T(0.046 * sx, -0.840, 0.812), g)
        finish("bore", cyl(0.011, 0.011, 0.002, 12, "y"), "black", 0, 1, T(0.046 * sx, -0.871, 0.812), g)
    finish("laser", cyl(0.008, 0.008, 0.006, 12, "y"), "glow_red", 0, 1, T(0, -0.423, 0.840), g)
    pivot("recoil", (0, -0.340, 0.812), (0, 1, 0), h, g, (0, 0)); pivot("muzzle", (0, -0.874, 0.812), (0, -1, 0), g, "fx"); pivot("eye", (0, -0.310, 0.850), (0, -1, 0), h, "fx")
    cable("feed_cable", [(0.150, 0.230, 0.800), (0.150, 0.300, 0.700), (0.100, 0.200, 0.580)], 0.012, "rubber", h)

# ------------------------------------------------------------------ 감시 카메라
def camera():
    """감시 카메라. 벽 설치형. 원점은 벽면(벽은 +Y 쪽), 렌즈가 -Y를 본다. 받침 -> 팔(좌우) -> 몸(상하)."""
    b = "base"
    finish("wall_plate", box(0.140, 0.014, 0.180), "m_frame", 0.006, 2, T(0, -0.007, 0), b)
    for sx in (-1, 1):
        for sz in (-1, 1): bolt(T(0.052 * sx, -0.015, 0.070 * sz) @ RX(90), 0.007, part=b)
    finish("bracket", box(0.050, 0.120, 0.040), "m_armor", 0.008, 2, T(0, -0.070, 0.000), b)
    finish("yaw_joint", cyl(0.034, 0.034, 0.050, 20, "z"), "gunmetal", 0.004, 2, T(0, -0.130, -0.020), b)
    a = "arm"
    finish("arm_post", cyl(0.022, 0.022, 0.060, 16, "z"), "m_frame", 0.003, 1, T(0, -0.130, -0.070), a)
    for sx in (-1, 1): finish("arm_fork", box(0.012, 0.040, 0.090), "m_armor", 0.004, 2, T(0.066 * sx, -0.130, -0.130), a)
    finish("arm_bar", box(0.144, 0.040, 0.016), "m_armor", 0.004, 2, T(0, -0.130, -0.094), a)
    pivot("pan", (0, -0.130, -0.045), (0, 0, 1), b, a, (-90, 90))
    h = "head"
    wedge([(-0.330, -0.180), (-0.330, -0.100), (-0.300, -0.084), (-0.060, -0.084), (-0.040, -0.110), (-0.040, -0.180)], 0.108, "m_light", h, "housing", 0.010, segs=3)
    wedge([(-0.372, -0.092), (-0.372, -0.082), (-0.250, -0.076), (-0.250, -0.086)], 0.124, "m_frame", h, "visor", 0.002)
    finish("lens_ring", cyl(0.040, 0.040, 0.020, 24, "y"), "gunmetal", 0.003, 2, T(0, -0.338, -0.136), h)
    finish("lens", cyl(0.032, 0.032, 0.004, 24, "y"), "glass", 0, 1, T(0, -0.349, -0.136), h)
    finish("lens_glow", torus(0.026, 0.004, 24, 6, "y"), "glow_red", 0, 1, T(0, -0.350, -0.136), "eye")
    finish("status_led", box(0.010, 0.004, 0.010), "glow_red", 0, 1, T(0.040, -0.332, -0.098), "eye")
    finish("stripe", box(0.110, 0.050, 0.002), "m_accent", 0, 1, T(0, -0.120, -0.0835), h)
    for sx in (-1, 1): finish("trunnion", cyl(0.018, 0.018, 0.012, 14, "x"), "titan", 0.002, 1, T(0.056 * sx, -0.130, -0.140), h)
    cable("cable", [(0, -0.050, -0.130), (0, -0.030, -0.060), (0, -0.020, 0.040)], 0.006, "rubber", h)
    pivot("tilt", (0, -0.130, -0.140), (1, 0, 0), a, h, (-50, 20)); pivot("eye", (0, -0.352, -0.136), (0, -1, 0), h, "fx")

MACHINES = {"drone": (drone, 1.0, (0, 0, 0.02)), "turret": (turret, 1.3, (0, -0.15, 0.55)), "camera": (camera, 0.5, (0, -0.19, -0.06))}

def build(name):
    kit.reset(); materials(); MACHINES[name][0]()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, (fn, k, c) in MACHINES.items():
        if ONLY and name not in ONLY: continue
        build(name)
        if RENDER:
            zs = [(o.matrix_world @ Vector(v)).z for o in kit.asset_objects() for v in o.bound_box]
            kit.studio(c, k * 0.75, floor_z=min(zs) - (0.25 * k if name != "turret" else 0.0), top=0.6, key=0.8)
            res = tuple(int(v) for v in os.environ.get("MC_RES", "1200,900").split(","))
            kit.shot(os.path.join(OUT, f"{name}_front.png"), (c[0] - 1.25 * k, c[1] - 1.75 * k, c[2] + 0.75 * k), c, 60, res=res)
            kit.shot(os.path.join(OUT, f"{name}_rear.png"), (c[0] + 1.35 * k, c[1] + 1.65 * k, c[2] + 0.55 * k), c, 60, res=res)
            for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
        kit.export(os.path.join(OUT, name), name)
