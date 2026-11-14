"""맨얼굴 사람 (전부 자체 제작). 머리·얼굴·손·옷·머리카락·신발·뼈대를 이 스크립트가 처음부터 만든다.
외부 에셋, 사람 생성 도구, 그림 파일(텍스처)을 하나도 쓰지 않는다. 재질은 색과 수치뿐이다.
실행: python person.py <출력폴더> [render|export|heads] [이름...]
-Y를 바라보고 선다. 단위 m.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from math import sin, cos, pi, radians, sqrt
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, sphere, torus, loft, RX, RY, RZ, T, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/person"
MODE = ARGS[1] if len(ARGS) > 1 else "export"
ONLY = ARGS[2:] if len(ARGS) > 2 else []

# ---------------------------------------------------------------- 재질 (그림 없이 색과 수치만)
def mat_skin(key, color):
    m, nt, b = kit._nodes(key)
    var = kit._noise(nt, 30.0, detail=3.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Color1"].default_value = (*color, 1)
    mix.inputs["Color2"].default_value = (0.86, 0.80, 0.80, 1); nt.links.new(kit._ramp(nt, var.outputs["Fac"], 0.35, 0.75, 0.0, 0.35), mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.46
    for nm, val in (("Subsurface Weight", 0.35), ("Subsurface Scale", 0.006)):
        if nm in b.inputs: b.inputs[nm].default_value = val
    if "Subsurface Radius" in b.inputs: b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    pore = kit._noise(nt, 900.0, detail=2.0); kit._bump(nt, b, pore.outputs["Fac"], 0.12, 0.0004)
    kit.M[key] = m; return m

# ---------------------------------------------------------------- 머리: 공을 수식으로 빚는다
FACE = dict(   # 얼굴 생김새 수치. 사람마다 일부를 바꾼다
    wide=1.0, deep=1.0,              # 머리통 가로·앞뒤 배율
    jaw=1.0, chin_w=1.0, chin=0.004, # 턱 너비 배율, 턱끝 너비 배율, 턱끝이 나온 정도
    cheekbone=1.0,                   # 광대 너비 배율
    brow=0.0030,                     # 눈썹뼈가 나온 정도
    eye_x=0.0315, eye_w=0.0176, eye_h=0.0082, eye_in=0.0086, eye_tilt=0.06,   # 눈 간격의 절반, 눈구멍 크기, 깊이, 눈꼬리 기울기
    nose_len=0.046, nose_out=0.021, nose_w=0.0060, nose_tip=0.0100, wing=0.0125,   # 코 길이, 높이, 콧등 너비, 코끝 너비, 콧방울 벌어짐
    cheek=0.0030,                    # 볼살
    mouth_z=-0.070, mouth_w=0.0245, lip_up=0.0026, lip_low=0.0034, mound=0.0045,   # 입 높이, 너비, 입술 두께, 입 주변이 나온 정도
)

def _curve(pts):
    """(z, 값) 조절점을 부드럽게 잇는 함수."""
    zs = np.array([p[0] for p in pts]); vs = np.array([p[1] for p in pts]); o = np.argsort(zs); zs, vs = zs[o], vs[o]
    fine = np.linspace(zs[0], zs[-1], 400); v = np.interp(fine, zs, vs)
    k = np.exp(-np.linspace(-2, 2, 31) ** 2); k /= k.sum(); v2 = np.convolve(np.pad(v, 15, mode="edge"), k, mode="valid")
    v2[0], v2[-1] = v[0], v[-1]
    return lambda z: np.interp(z, fine, v2)

def head_mesh(f, cols=76):
    """머리 메시(눈 높이가 z=0, 얼굴이 -Y). 높이마다 앞·뒤·옆 윤곽을 정해 가로 단면을 쌓고, 그 위에 눈·코·입을 빚는다.
    돌려주는 값: bmesh, 면별 입술 여부, 눈알 중심 둘."""
    W, D, J = f["wide"], f["deep"], f["jaw"]
    front = _curve([(0.120, -0.004), (0.108, -0.040), (0.085, -0.070), (0.055, -0.086), (0.022, -0.091), (0.0, -0.0895), (-0.030, -0.0885), (-0.052, -0.0890),
                    (-0.072, -0.0880), (-0.092, -0.0850), (-0.106, -0.0800), (-0.114, -0.0690), (-0.119, -0.0450)])
    back = _curve([(0.120, 0.008), (0.108, 0.058), (0.080, 0.092), (0.040, 0.104), (0.0, 0.103), (-0.030, 0.094), (-0.055, 0.076), (-0.080, 0.058), (-0.100, 0.050), (-0.119, 0.046)])
    half = _curve([(0.120, 0.006), (0.108, 0.040), (0.085, 0.063), (0.050, 0.0755), (0.015, 0.0765), (-0.018, 0.0735 * f["cheekbone"]), (-0.045, 0.0680), (-0.070, 0.0610 * J),
                   (-0.088, 0.0500 * J), (-0.102, 0.0340 * f["chin_w"]), (-0.112, 0.0220 * f["chin_w"]), (-0.119, 0.0120)])
    zs = np.concatenate([np.linspace(0.120, 0.100, 5)[:-1], np.linspace(0.100, 0.030, 9)[:-1], np.linspace(0.030, 0.012, 5)[:-1], np.linspace(0.012, -0.012, 11)[:-1], np.linspace(-0.012, -0.056, 13)[:-1],
                         np.linspace(-0.056, -0.086, 16)[:-1], np.linspace(-0.086, -0.119, 9)])
    u = (np.arange(cols) + 0.5) / cols - 0.5; psi = 2 * pi * u - 0.62 * np.sin(2 * pi * u)       # 얼굴 쪽에 점을 몰아 준다
    se = lambda t, e: np.sign(t) * np.abs(t) ** (2.0 / e)
    P = np.zeros((len(zs), cols, 3))
    for k, z in enumerate(zs):
        fr, bk, hw = front(z) * D, back(z) * D, half(z) * W
        c, hd = (fr + bk) / 2, (bk - fr) / 2
        e = 2.25 + 0.5 * np.clip((0.03 - z) / 0.08, 0, 1) * (np.cos(psi) > 0)                      # 얼굴 아래쪽 앞면은 조금 더 네모지게
        P[k, :, 0] = hw * se(np.sin(psi), e); P[k, :, 1] = c - hd * se(np.cos(psi), e); P[k, :, 2] = z
    shape = P.shape; P = P.reshape(-1, 3)

    def surf(x, zz):
        m = P[:, 1] < 0.0; d2 = (P[m, 0] - x) ** 2 + (P[m, 2] - zz) ** 2
        return P[m][np.argmin(d2), 1]
    def push(c, r, vec, power=2.0):
        d = ((P[:, 0] - c[0]) / r[0]) ** 2 + ((P[:, 1] - c[1]) / r[1]) ** 2 + ((P[:, 2] - c[2]) / r[2]) ** 2
        w = np.exp(-d ** (power / 2)); P[:] += np.outer(w, vec); return w

    # 눈썹뼈, 눈구멍
    for s in (-1, 1):
        ex = s * f["eye_x"]; push((ex * 1.05, surf(ex, 0.0), 0.018), (0.030, 0.03, 0.0075), (0, -f["brow"], 0))
    eyes = []
    for s in (-1, 1):
        ex = s * f["eye_x"]; ys = surf(ex, 0.0)
        eyes.append(Vector((ex, ys + 0.0122 + 0.0026, 0.0)))                     # 눈알 앞이 원래 피부보다 3 mm 뒤
        zz = P[:, 2] - (P[:, 0] - ex) * s * f["eye_tilt"]
        d = ((P[:, 0] - ex) / f["eye_w"]) ** 2 + (zz / f["eye_h"]) ** 2 + ((P[:, 1] - ys) / 0.03) ** 2
        P[:, 1] += np.exp(-d ** 1.5) * f["eye_in"]                               # 가로로 긴 구멍 -> 눈알이 아몬드 모양으로 드러난다
        push((ex, ys, 0.0085), (0.019, 0.03, 0.0028), (0, -0.0012, -0.0006))     # 윗눈꺼풀이 살짝 덮는다
        push((ex, ys, -0.015), (0.020, 0.03, 0.007), (0, 0.0012, 0))             # 눈 밑
    # 코
    yb = surf(0.0, 0.0)
    for i in range(9):
        t = i / 8.0; zc = 0.006 - f["nose_len"] * t
        push((0, yb, zc), (f["nose_w"] + (f["nose_tip"] - f["nose_w"]) * t ** 1.5, 0.04, 0.0095), (0, -(0.0030 + f["nose_out"] * t ** 1.7) / 3.1, -0.0005 * t))
    zt = 0.006 - f["nose_len"]
    for s in (-1, 1): push((s * f["wing"], yb - 0.005, zt + 0.0035), (0.0058, 0.02, 0.0055), (s * 0.0012, -0.0048, 0))
    push((0, yb - 0.004, zt - 0.0105), (0.017, 0.03, 0.0040), (0, 0.0042, 0.0012))     # 코 밑을 판다
    for s in (-1, 1): push((s * 0.0052, yb - 0.014, zt - 0.0030), (0.0030, 0.010, 0.0024), (0, 0.0032, 0.0022))   # 콧구멍
    push((0, yb, 0.013), (0.011, 0.03, 0.009), (0, 0.0018, 0))                  # 미간은 살짝 들어간다
    # 볼
    for s in (-1, 1):
        cx = s * 0.046; push((cx, surf(cx, -0.024), -0.024), (0.020, 0.03, 0.015), (s * 0.001, -f["cheek"], 0))
        push((s * 0.030, surf(s * 0.030, -0.052), -0.052), (0.010, 0.03, 0.016), (0, 0.0016, 0))   # 팔자 주름 자리
    # 입
    mz = f["mouth_z"]; ym = surf(0.0, mz)
    push((0, ym, mz), (0.030, 0.035, 0.016), (0, -f["mound"], 0))
    ym = surf(0.0, mz); xs = P[:, 0]; mw = f["mouth_w"]
    curve = mz + 0.0020 * (np.abs(xs) / mw) ** 2 - 0.0006                        # 입꼬리가 살짝 올라간 선
    near = np.exp(-((P[:, 1] - ym) / 0.03) ** 2) * (P[:, 1] < 0)
    inx = np.exp(-(np.abs(xs) / (mw * 1.04)) ** 6) * near
    taper = np.clip(1 - (np.abs(xs) / mw) ** 2.2, 0, 1)
    bow = 1 - 0.28 * np.exp(-(xs / 0.0042) ** 2)                                 # 윗입술 가운데 패임
    up = np.exp(-((P[:, 2] - (curve + 0.0040 * bow)) / 0.0034) ** 2) * inx * taper
    lo = np.exp(-((P[:, 2] - (curve - 0.0048)) / 0.0042) ** 2) * inx * taper
    cr = np.exp(-((P[:, 2] - curve) / 0.0019) ** 2) * inx
    P[:, 1] -= up * f["lip_up"] + lo * f["lip_low"]; P[:, 1] += cr * 0.0046
    lipw = np.clip(np.maximum(up, lo), 0, 1)
    push((0, ym, mz - 0.0160), (0.015, 0.03, 0.0042), (0, 0.0028, 0))            # 아랫입술 밑
    push((0, ym, mz + 0.0100), (0.0032, 0.03, 0.0055), (0, 0.0011, 0))           # 인중
    for s in (-1, 1): push((s * (mw + 0.002), ym + 0.003, mz), (0.0040, 0.02, 0.0045), (0, 0.0016, 0))   # 입꼬리
    push((0, surf(0.0, -0.103), -0.103), (0.019 * f["chin_w"], 0.03, 0.012), (0, -f["chin"], -0.001))
    for s in (-1, 1): push((s * 0.072, -0.030, 0.020), (0.012, 0.030, 0.028), (-s * 0.0030, 0, 0))   # 관자놀이

    P = P.reshape(shape); lipw = lipw.reshape(shape[:2])
    bm = bmesh.new(); vs = [[bm.verts.new(P[k, j]) for j in range(cols)] for k in range(shape[0])]
    lips = []
    for k in range(shape[0] - 1):
        for j in range(cols):
            j2 = (j + 1) % cols
            bm.faces.new((vs[k][j], vs[k][j2], vs[k + 1][j2], vs[k + 1][j]))
            lips.append((lipw[k, j] + lipw[k, j2] + lipw[k + 1, j] + lipw[k + 1, j2]) / 4 > 0.40)
    bm.faces.new(vs[0][::-1]); lips.append(False); bm.faces.new(vs[-1]); lips.append(False)
    return bm, lips, eyes, (shape[0], cols)

def ear_mesh(s, f):
    """귀 한쪽(자체 모양): 납작한 타원 + 귓바퀴 테두리 + 안쪽 홈."""
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=18, radius=1.0)
    P = np.array([v.co[:] for v in bm.verts]); zn = np.sign(P[:, 2]) * np.abs(P[:, 2]) ** 0.7; yn = P[:, 1].copy()
    rr = np.sqrt(np.clip(1 - zn ** 2, 0, 1)) / np.maximum(np.sqrt(np.clip(1 - P[:, 2] ** 2, 1e-9, 1)), 1e-4)
    P[:, 0] *= rr * 0.0036; P[:, 1] *= rr * 0.0155; P[:, 2] = zn * 0.0300                 # 위아래 끝이 뾰족하지 않게 둥글린다
    P[:, 1] *= 0.70 + 0.30 * np.clip((zn + 1) / 1.1, 0, 1)                                # 귓불 쪽이 좁다
    P[:, 1] -= 0.0030 * zn ** 2
    outer = P[:, 0] * s > 0
    d = ((yn + 0.10) / 0.60) ** 2 + ((zn - 0.10) / 0.62) ** 2
    P[outer, 0] -= s * 0.0042 * np.exp(-d[outer] ** 2)                                    # 귓바퀴 안쪽 홈(테두리는 남는다)
    for v, p in zip(bm.verts, P): v.co = p
    Mx = T(s * (0.0765 * f["wide"] - 0.0025), 0.0190, -0.0150) @ RZ(s * 9) @ RY(s * -6) @ RX(-8)
    bmesh.ops.transform(bm, matrix=Mx, verts=bm.verts)
    return bm

def cap(r, ang, segs=24, rings=5):
    """공의 앞쪽(-Y) 뚜껑: 홍채와 동공을 눈알 위에 얹을 때 쓴다."""
    bm = bmesh.new(); c = bm.verts.new((0, -r, 0)); prev = None
    for i in range(1, rings + 1):
        a = radians(ang) * i / rings
        ring = [bm.verts.new((r * sin(a) * cos(2 * pi * j / segs), -r * cos(a), r * sin(a) * sin(2 * pi * j / segs))) for j in range(segs)]
        for j in range(segs):
            j2 = (j + 1) % segs
            if prev: bm.faces.new((prev[j], prev[j2], ring[j2], ring[j]))
            else: bm.faces.new((c, ring[j2], ring[j]))
        prev = ring
    return bm

def eye_parts(c, iris, part):
    """눈알: 흰자, 홍채, 동공. 그림 없이 도형으로만."""
    r = 0.0122
    finish("eye_white", sphere(r, u=24, v=16), "eye_white", 0, 1, T(*c), part)
    finish("eye_iris", cap(r * 1.012, 27), iris, 0, 1, T(*c), part)
    finish("eye_pupil", cap(r * 1.022, 11, 18, 3), "eye_pupil", 0, 1, T(*c), part)

def brow_mesh(s, f, thick=1.0, arch=0.004):
    """눈썹: 얇은 띠를 얼굴 곡면 위에 얹는다."""
    rings = []
    for i in range(9):
        t = i / 8.0; x = s * (f["eye_x"] - 0.019 + 0.040 * t)
        z = 0.0150 + arch * sin(pi * min(1.0, t * 1.15)) - 0.004 * t ** 2
        hw = 0.0036 * thick * (1.0 - 0.75 * t ** 2) + 0.0005
        rings.append((x, z, hw))
    return rings

def build_head(name, f, skin, iris="iris_brown", part="head", brow=(0.03, 0.02, 0.015), brow_thick=1.0):
    bm, lips, eyes, grid = head_mesh(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name + "_head"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name + "_head", me); kit.COL.objects.link(ob)
    me.materials.append(kit.M[skin]); me.materials.append(kit.M["lip_" + skin])
    for p, lp in zip(me.polygons, lips):
        p.use_smooth = True; p.material_index = 1 if lp else 0
    ob["part"] = part; kit.PARTS.setdefault(part, []).append(ob)
    # 눈썹은 머리 곡면에 붙여야 하므로 머리 메시에서 y를 찾는다
    co = np.array([v.co[:] for v in me.vertices]); fr = co[co[:, 1] < 0]
    ysurf = lambda x, z: fr[np.argmin((fr[:, 0] - x) ** 2 + (fr[:, 2] - z) ** 2), 1]
    kit.mat_simple("brow_" + name, brow, 0.0, 0.75)
    for s in (-1, 1):
        bb = bmesh.new(); prev = None
        for x, z, hw in brow_mesh(s, f, brow_thick):
            y = ysurf(x, z) - 0.0011
            ring = [bb.verts.new((x, y + 0.0012, z - hw)), bb.verts.new((x, y - 0.0004, z)), bb.verts.new((x, y + 0.0012, z + hw))]
            if prev:
                for a in range(2): bb.faces.new((prev[a], prev[a + 1], ring[a + 1], ring[a]))
            prev = ring
        bmesh.ops.recalc_face_normals(bb, faces=bb.faces)
        finish("brow", bb, "brow_" + name, 0, 1, None, part)
        finish("ear", ear_mesh(s, f), skin, 0, 1, None, part)
    for c in eyes: eye_parts(c, iris, part)
    return ob, eyes, grid

def base_mats():
    kit.base_materials()
    kit.mat_simple("eye_white", (0.80, 0.78, 0.76), 0.0, 0.25)
    kit.mat_simple("eye_pupil", (0.004, 0.004, 0.004), 0.0, 0.15)
    for k, c in (("iris_brown", (0.10, 0.045, 0.018)), ("iris_dark", (0.03, 0.016, 0.01)), ("iris_blue", (0.10, 0.20, 0.32)), ("iris_green", (0.12, 0.20, 0.09)), ("iris_gray", (0.20, 0.23, 0.26))):
        kit.mat_simple(k, c, 0.0, 0.3)

SKINS = {"light": (0.62, 0.40, 0.31), "tan": (0.50, 0.30, 0.20), "olive": (0.44, 0.29, 0.19), "brown": (0.25, 0.135, 0.085), "dark": (0.115, 0.062, 0.042), "pale": (0.70, 0.50, 0.42)}
def skin_mats(tone):
    c = SKINS[tone]; mat_skin("skin_" + tone, c)
    lip = (c[0] * 0.92 + 0.05, c[1] * 0.55, c[2] * 0.55)
    m = mat_skin("lip_skin_" + tone, lip); m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.34

if __name__ == "__main__" and MODE == "heads":
    os.makedirs(OUT, exist_ok=True)
    tests = [("a", {}, "light"), ("b", dict(jaw=0.90, chin_w=0.85, brow=0.0012, nose_out=0.018, nose_tip=0.0088, wing=0.0108, lip_up=0.0034, lip_low=0.0044, eye_h=0.0068), "tan"),
             ("c", dict(wide=1.03, jaw=1.06, nose_tip=0.0130, wing=0.0155, nose_out=0.019, lip_up=0.0040, lip_low=0.0050, brow=0.0038), "dark")]
    for nm, over, tone in tests:
        kit.reset(); base_mats(); skin_mats(tone)
        f = dict(FACE); f.update(over); build_head(nm, f, "skin_" + tone)
        kit.studio((0, 0, 0), 0.22, floor_z=-0.16)
        kit.area("fill", (-0.4, -0.9, 0.25), (0, 0, 0), 0.6, 14, (1.0, 0.95, 0.9))
        kit.shot(os.path.join(OUT, f"head_{nm}_front.png"), (0, -0.95, 0.0), (0, 0, -0.02), 85, res=(520, 620))
        kit.shot(os.path.join(OUT, f"head_{nm}_34.png"), (-0.55, -0.78, 0.04), (0, 0, -0.02), 85, res=(520, 620))
        kit.shot(os.path.join(OUT, f"head_{nm}_side.png"), (-0.95, 0.0, 0.0), (0, 0, -0.02), 85, res=(520, 620))

# ================================================================ 몸, 옷, 손, 머리카락, 뼈대 (전부 자체 제작)
V = Vector
H0 = 1.75   # 기준 키. 사람마다 마지막에 통째로 늘이거나 줄인다

def mat_cloth(key, color, rough=0.8, wrinkle=0.5):
    m, nt, b = kit._nodes(key)
    var = kit._noise(nt, 7.0, detail=5.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Color1"].default_value = (*color, 1)
    mix.inputs["Color2"].default_value = (0.62, 0.62, 0.64, 1); nt.links.new(kit._ramp(nt, var.outputs["Fac"], 0.35, 0.75, 0.0, 0.55), mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(kit._ramp(nt, var.outputs["Fac"], 0.3, 0.7, rough - 0.08, rough + 0.08), b.inputs["Roughness"])
    w = kit._noise(nt, 16.0, (1, 1, 0.4), 3.0); fz = kit._noise(nt, 420.0, detail=2.0)
    h = kit._math(nt, "ADD", kit._math(nt, "MULTIPLY", w.outputs["Fac"], wrinkle), kit._math(nt, "MULTIPLY", fz.outputs["Fac"], 0.08))
    kit._bump(nt, b, h, 0.9, 0.010)
    kit.M[key] = m; return m

def mat_hair(key, color):
    m, nt, b = kit._nodes(key)
    st = kit._noise(nt, 260.0, (1, 1, 0.03), 2.0)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Color1"].default_value = (*color, 1)
    mix.inputs["Color2"].default_value = (0.45, 0.45, 0.45, 1); nt.links.new(kit._ramp(nt, st.outputs["Fac"], 0.3, 0.7, 0.0, 0.7), mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.42
    kit._bump(nt, b, st.outputs["Fac"], 0.5, 0.002)
    kit.M[key] = m; return m

def ring(w, d, z, yoff=0.0, n=24, e=2.4):
    pts = []
    for i in range(n):
        a = 2 * pi * i / n; c, s = cos(a), sin(a)
        pts.append((w / 2 * abs(c) ** (2 / e) * (1 if c >= 0 else -1), yoff + d / 2 * abs(s) ** (2 / e) * (1 if s >= 0 else -1), z))
    return pts

def tube(pts, radii, u=None, flat=1.0, n=14, cap=True):
    """점들을 따라가는 관. radii = 점마다의 반지름. u = 단면의 가로 방향(없으면 X에 가깝게), flat = 세로/가로 비."""
    pts = [V(p) for p in pts]; rings = []
    for i, p in enumerate(pts):
        t = ((pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])).normalized()
        uu = V(u) if u is not None else V((1, 0, 0))
        uu = (uu - t * uu.dot(t)).normalized(); vv = t.cross(uu)
        r = radii[i]; rings.append([p + uu * (r * cos(2 * pi * j / n)) + vv * (r * flat * sin(2 * pi * j / n)) for j in range(n)])
    return loft(rings, cap)

def lerp_path(a, b, ts): return [V(a).lerp(V(b), t) for t in ts]

def obj(name, bm, mat, wb, part="body", bevel=0, soft=0):
    o = finish(name, bm, mat, bevel, 1, None, part); o["wb"] = wb
    if soft:
        md = o.modifiers.new("sub", "SUBSURF"); md.levels = soft; md.render_levels = soft; o.modifiers.move(len(o.modifiers) - 1, 0)
    return o

def skeleton(sex):
    """관절 위치(기준 키 1.75 m). L이 +x, 얼굴이 -Y."""
    sx = 0.176 if sex == "m" else 0.158
    J = {"pelvis": V((0, 0.010, 0.955)), "spine": V((0, 0.010, 1.085)), "chest": V((0, 0.004, 1.270)), "neck": V((0, 0.012, 1.500)), "head": V((0, 0.004, 1.585)), "crown": V((0, 0.004, 1.770))}
    for S, sg in (("L", 1), ("R", -1)):
        J["hip_" + S] = V((sg * 0.092, 0.006, 0.935)); J["knee_" + S] = V((sg * 0.097, -0.004, 0.505)); J["ankle_" + S] = V((sg * 0.098, 0.014, 0.088)); J["toe_" + S] = V((sg * 0.106, -0.180, 0.020))
        nu = V((sg * 0.10, 0.0, -1)).normalized(); nf = V((sg * 0.07, -0.03, -1)).normalized()
        J["shoulder_" + S] = V((sg * sx, 0.004, 1.425)); J["elbow_" + S] = J["shoulder_" + S] + nu * 0.285
        J["wrist_" + S] = J["elbow_" + S] + nf * 0.255; J["knuckle_" + S] = J["wrist_" + S] + nf * 0.092
        a = nf; n = V((-sg, 0, 0)); n = (n - a * n.dot(a)).normalized(); t = n.cross(a) * sg     # a = 손끝 쪽, n = 손바닥이 보는 쪽, t = 엄지 쪽
        J["hand_axes_" + S] = (a, n, t)
        for f, off, ln, r in (("index", 0.030, 0.074, 0.0088), ("middle", 0.010, 0.082, 0.0090), ("ring", -0.010, 0.076, 0.0086), ("pinky", -0.029, 0.060, 0.0078)):
            p = J["knuckle_" + S] + t * off - a * 0.004; d = (a + t * (off * 1.2)).normalized()
            J[f"{f}_{S}"] = [p, p + d * ln * 0.45, p + d * ln * 0.75, p + d * ln, r]
        p = J["wrist_" + S] + a * 0.026 + t * 0.034 + n * 0.008; d = (a * 0.66 + t * 0.70 + n * 0.22).normalized()
        J["thumb_" + S] = [p, p + d * 0.038, p + d * 0.070, p + d * 0.096, 0.0110]
    return J

BONES = [("pelvis", "pelvis", "spine", None), ("spine", "spine", "chest", "pelvis"), ("chest", "chest", "neck", "spine"), ("neck", "neck", "head", "chest"), ("head", "head", "crown", "neck")]
for _S in "LR":
    BONES += [("thigh_" + _S, "hip_" + _S, "knee_" + _S, "pelvis"), ("shin_" + _S, "knee_" + _S, "ankle_" + _S, "thigh_" + _S), ("foot_" + _S, "ankle_" + _S, "toe_" + _S, "shin_" + _S),
              ("upperarm_" + _S, "shoulder_" + _S, "elbow_" + _S, "chest"), ("forearm_" + _S, "elbow_" + _S, "wrist_" + _S, "upperarm_" + _S), ("hand_" + _S, "wrist_" + _S, "knuckle_" + _S, "forearm_" + _S)]
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
SEM = [("waist", "spine"), ("neck", "neck")] + [(f"{j}_{S}", f"{b}_{S}") for S in "LR" for j, b in (("hip", "thigh"), ("knee", "shin"), ("ankle", "foot"), ("shoulder", "upperarm"), ("elbow", "forearm"), ("wrist", "hand"))]

def bone_table(J):
    """뼈 이름 -> (머리, 꼬리, 부모)."""
    B = {n: (J[a], J[b], p) for n, a, b, p in BONES}
    for S in "LR":
        for f in FINGERS:
            c = J[f"{f}_{S}"]
            for k in (1, 2, 3): B[f"{f}_{k}_{S}"] = (c[k - 1], c[k], f"{f}_{k - 1}_{S}" if k > 1 else "hand_" + S)
    return B

def hands(J, skin):
    for S in "LR":
        a, n, t = J["hand_axes_" + S]; w, k = J["wrist_" + S], J["knuckle_" + S]
        pts = [w - a * 0.012, w + a * 0.004, w + a * 0.030, w + a * 0.066, k + a * 0.004, k + a * 0.012]
        obj("palm_" + S, tube(pts, [0.020, 0.030, 0.040, 0.043, 0.041, 0.030], u=t, flat=0.36, n=16), skin, "hand_" + S)
        for f in FINGERS:
            c = J[f"{f}_{S}"]; r = c[4]
            for i in (1, 2, 3):
                p0, p1 = c[i - 1], c[i]; d = (p1 - p0).normalized(); r0 = r * (1.0 - 0.07 * (i - 1)); r1 = r * (1.0 - 0.07 * i)
                pts = [p0 - d * r0 * 0.7, p0 - d * r0 * 0.2, p0.lerp(p1, 0.5), p1 + d * r1 * 0.2, p1 + d * r1 * 0.75]
                obj(f"{f}_{i}_{S}", tube(pts, [r0 * 0.55, r0, (r0 + r1) / 2, r1, r1 * 0.5], u=t, flat=0.92, n=10), skin, f"{f}_{i}_{S}")

def arm_skin(J, skin, sex, from_t):
    """맨팔: from_t = 위팔에서 드러나기 시작하는 위치(0 어깨 ~ 1 팔꿈치). 긴소매면 손목만 만든다."""
    k = 1.0 if sex == "m" else 0.86
    for S in "LR":
        s, e, w = J["shoulder_" + S], J["elbow_" + S], J["wrist_" + S]
        if from_t is None:
            obj("wrist_" + S, tube([e.lerp(w, 0.80), w, w.lerp(J["knuckle_" + S], 0.12)], [0.031 * k, 0.029 * k, 0.027 * k], n=12), skin, "forearm_" + S); continue
        ts = [from_t + (1 - from_t) * i / 3 for i in range(4)]
        pts = lerp_path(s, e, ts) + lerp_path(e, w, (0.12, 0.3, 0.55, 0.8, 1.0)) + [w.lerp(J["knuckle_" + S], 0.12)]
        rad = [(0.052 - 0.006 * t) * k for t in ts] + [x * k for x in (0.045, 0.046, 0.040, 0.033, 0.029, 0.027)]
        obj("arm_" + S, tube(pts, rad, n=14), skin, f"upperarm_{S},forearm_{S}")

def neck(J, skin, sex):
    r = 0.061 if sex == "m" else 0.049
    obj("neck", tube([(0, 0.016, 1.430), (0, 0.014, 1.490), (0, 0.010, 1.540), (0, 0.012, 1.585)], [r * 1.25, r * 1.02, r, r * 1.02], flat=1.05, n=18), skin, "chest,neck,head")

TORSO = {"m": [(0.90, 0.360, 0.232, 0.0), (0.98, 0.350, 0.224, 0.0), (1.08, 0.332, 0.212, 0.0), (1.20, 0.350, 0.224, -0.004), (1.32, 0.374, 0.240, -0.008), (1.40, 0.384, 0.222, -0.004),
               (1.452, 0.346, 0.186, 0.004), (1.492, 0.226, 0.152, 0.008), (1.522, 0.140, 0.138, 0.010)],
         "f": [(0.90, 0.372, 0.232, 0.0), (0.98, 0.352, 0.216, 0.0), (1.08, 0.276, 0.184, 0.0), (1.20, 0.304, 0.210, -0.010), (1.31, 0.332, 0.246, -0.022), (1.39, 0.344, 0.208, -0.006),
               (1.442, 0.308, 0.170, 0.004), (1.482, 0.200, 0.140, 0.008), (1.512, 0.128, 0.128, 0.010)]}

def torso(sex, mat, hem=0.90, grow=0.0, build=1.0, name="top", wb="pelvis,spine,chest", zmax=9.0):
    """윗옷 몸통. hem = 밑단 높이, grow = 몸에서 뜨는 두께."""
    prof = TORSO[sex]; rings = []
    if hem < prof[0][0]:
        z0, w0, d0, y0 = prof[0]; n = max(1, int((z0 - hem) / 0.08))
        for i in range(n): rings.append(ring((w0 + 2 * grow) * build * 1.02, (d0 + 2 * grow) * build * 1.02, hem + (z0 - hem) * i / n, y0))
    for z, w, d, y in prof:
        if z < hem - 1e-6 or z > zmax: continue
        g = grow * (1.0 if z < 1.46 else 0.5)
        rings.append(ring((w + 2 * g) * (build if z < 1.44 else 1.0), (d + 2 * g) * (build if z < 1.44 else 1.0), z, y))
    return obj(name, loft(rings), mat, wb if hem >= 0.80 else wb + ",thigh_L,thigh_R", soft=1)

def sleeves(J, mat, length=1.0, r=1.0, cuff=None):
    """소매. length = 1.0 손목까지, 0.45 반소매."""
    for S in "LR":
        s, e, w = J["shoulder_" + S], J["elbow_" + S], J["wrist_" + S]; yoke = V((s.x * 0.60, s.y, s.z + 0.026))
        if length < 0.5:
            rad = [0.046, 0.056, 0.056, 0.055, 0.056]
            obj("sleeve_" + S, tube([yoke] + lerp_path(s, e, (0.0, 0.20, 0.36, 0.44)), [x * r for x in rad], n=16), mat, "upperarm_" + S, soft=1)
        else:
            pts = [yoke] + lerp_path(s, e, (0.0, 0.25, 0.55, 0.85)) + lerp_path(e, w, (0.0, 0.2, 0.5, 0.8, 0.96))
            rad = [0.046, 0.056, 0.054, 0.051, 0.048, 0.048, 0.046, 0.042, 0.038, 0.036]
            obj("sleeve_" + S, tube(pts, [x * r for x in rad], n=16), mat, f"upperarm_{S},forearm_{S}", soft=1)
            if cuff: obj("cuff_" + S, tube(lerp_path(e, w, (0.93, 0.99)), [0.040 * r, 0.040 * r], n=16), cuff, "forearm_" + S)

def collar(mat, sex, z=1.500, h=0.030, r=0.070, open_front=True):
    zz = z if sex == "m" else z - 0.010; rr = r if sex == "m" else r * 0.88; bm = bmesh.new(); n = 28; lo, hi = [], []
    a0 = radians(24 if open_front else 0)
    for i in range(n + 1):
        a = a0 + (2 * pi - 2 * a0) * i / n; x, y = rr * sin(a), -rr * cos(a) * 0.92 + 0.012
        lo.append(bm.verts.new((x * 1.10, y * 1.10 + 0.002, zz))); hi.append(bm.verts.new((x, y, zz + h)))
    for i in range(n): bm.faces.new((lo[i], lo[i + 1], hi[i + 1], hi[i]))
    o = obj("collar", bm, mat, "chest,neck"); md = o.modifiers.new("s", "SOLIDIFY"); md.thickness = 0.004; return o

def pants(J, sex, mat, cuff_r=0.060, build=1.0, cargo=False):
    k = 1.0
    hip = [(1.075, 0.304 if sex == "m" else 0.270, 0.196), (1.02, 0.324, 0.208), (0.94, 0.344 * k, 0.222), (0.87, 0.338 * k, 0.218), (0.825, 0.270, 0.190)]
    obj("hips", loft([ring(w * build, d * build, z) for z, w, d in hip[::-1]]), mat, "pelvis", soft=1)
    for S in "LR":
        h, kn, an = J["hip_" + S], J["knee_" + S], J["ankle_" + S]; top = V((h.x * 1.02, h.y, 0.905))
        pts = [top, top.lerp(kn, 0.25), top.lerp(kn, 0.6), top.lerp(kn, 0.9), kn, kn.lerp(an, 0.25), kn.lerp(an, 0.6), kn.lerp(an, 0.93)]
        rad = [0.086 * k, 0.084 * k, 0.072, 0.062, 0.059, 0.058, 0.054, cuff_r]
        obj("leg_" + S, tube(pts, [x * build for x in rad], flat=1.06, n=18), mat, f"thigh_{S},shin_{S}", soft=1)
        if cargo:
            sg = 1 if S == "L" else -1; c = top.lerp(kn, 0.62) + V((sg * 0.066, 0.0, 0))
            obj("pocket_" + S, box(0.022, 0.105, 0.125), mat, "thigh_" + S, bevel=0.006).matrix_world = T(*c) @ RY(sg * -4)
    obj("belt", loft([ring(hip[0][1] * build + 0.008, hip[0][2] * build + 0.008, z) for z in (1.045, 1.075)], cap=False), "belt", "pelvis")

def shoes(J, mat, boot=True):
    for S in "LR":
        an = J["ankle_" + S]; x0 = an.x + (0.006 if S == "L" else -0.006)
        sec = [(0.092, 0.050, 0.060), (0.070, 0.082, 0.098), (0.020, 0.096, 0.112), (-0.050, 0.102, 0.084), (-0.110, 0.104, 0.062), (-0.165, 0.094, 0.050), (-0.196, 0.064, 0.036)]
        rings = []
        for y, w, hh in sec:
            pts = []
            for i in range(16):
                a = 2 * pi * i / 16; c, s = cos(a), sin(a)
                zz = hh / 2 + hh / 2 * (abs(s) ** (2 / 2.2 if s > 0 else 2 / 6.0)) * (1 if s >= 0 else -1)
                pts.append((x0 + w / 2 * abs(c) ** (2 / 2.6) * (1 if c >= 0 else -1), an.y + y, 0.012 + zz))
            rings.append(pts)
        obj("shoe_" + S, loft(rings), mat, "foot_" + S)
        sole = bmesh.new(); lo, hi = [], []
        outline = [(x0 + sx * w / 2 * 1.06, an.y + y * 1.02) for sx, seq in ((1, sec), (-1, sec[::-1])) for y, w, hh in seq]
        for x, y in outline: lo.append(sole.verts.new((x, y, 0.0))); hi.append(sole.verts.new((x, y, 0.024)))
        m = len(outline)
        for i in range(m): sole.faces.new((lo[i], lo[(i + 1) % m], hi[(i + 1) % m], hi[i]))
        sole.faces.new(lo[::-1]); sole.faces.new(hi)
        obj("sole_" + S, sole, "rubber", "foot_" + S)
        if boot: obj("shaft_" + S, tube([V((an.x, an.y + 0.012, 0.070)), V((an.x, an.y + 0.008, 0.140)), V((an.x, an.y + 0.004, 0.215))], [0.052, 0.056, 0.062], flat=1.12, n=16), mat, "foot_" + S)

# ---------------------------------------------------------------- 머리카락
HAIRLINE = [(0.0, 0.066), (0.55, 0.062), (0.95, 0.034), (1.30, 0.020), (1.75, 0.018), (2.10, -0.030), (2.60, -0.060), (pi, -0.064)]
def hair(head, grid, style, mat, part="head"):
    """머리 메시의 격자를 바깥으로 밀어 머리카락 껍질을 만든다. style: buzz, short, slick, bob, long, afro, bun (bald는 만들지 않는다)."""
    if style == "bald": return None
    rows, cols = grid; me = head.data
    P = np.array([v.co[:] for v in me.vertices[:rows * cols]]).reshape(rows, cols, 3)
    me.calc_loop_triangles(); N = np.array([v.normal[:] for v in me.vertices[:rows * cols]]).reshape(rows, cols, 3)
    u = (np.arange(cols) + 0.5) / cols - 0.5; psi = np.abs(2 * pi * u - 0.62 * np.sin(2 * pi * u))
    hl = np.interp(psi, [p[0] for p in HAIRLINE], [p[1] for p in HAIRLINE])
    if style in ("bob", "long", "bun"): hl = np.where(psi > 0.9, np.minimum(hl, 0.02), hl)
    TH = {"buzz": (0.0022, 0.0022), "short": (0.016, 0.007), "slick": (0.010, 0.006), "bob": (0.016, 0.014), "long": (0.015, 0.014), "afro": (0.052, 0.040), "bun": (0.011, 0.008)}[style]
    bm = bmesh.new(); vid = {}
    for k in range(rows):
        for j in range(cols):
            z = P[k, j, 2]
            if z < hl[j] - 0.014: continue
            edge = np.clip((z - hl[j]) / 0.022, 0.0, 1.0); top = np.clip((z - 0.03) / 0.07, 0, 1)
            th = (TH[1] + (TH[0] - TH[1]) * top) * (0.12 + 0.88 * edge ** 0.7)
            th *= 1.0 + (0.10 * sin(j * 2.4 + k * 0.3) if style != "afro" else 0.22 * sin(j * 1.9 + k * 2.3) * sin(k * 1.1 + j))
            n = N[k, j].copy()
            if style == "slick": n[1] += 0.25 * top
            q = P[k, j] + n * th
            if z < hl[j]: q[2] = hl[j] + 0.0005                       # 경계는 머리선 높이에 맞춘다
            vid[(k, j)] = bm.verts.new(q)
    for k in range(rows - 1):
        for j in range(cols):
            q = [(k, j), (k, (j + 1) % cols), (k + 1, (j + 1) % cols), (k + 1, j)]
            if all(c in vid for c in q): bm.faces.new([vid[c] for c in q])
    if all((0, j) in vid for j in range(cols)): bm.faces.new([vid[(0, j)] for j in range(cols)][::-1])
    if style in ("bob", "long"):                                   # 옆과 뒤로 내려오는 머리
        zend = -0.105 if style == "bob" else -0.250
        zs = np.arange(0.030, zend, -0.012); prev = None
        for z in zs:
            k = int(np.argmin(np.abs(P[:, 0, 2] - max(z, -0.112)))); cur = {}
            for j in range(cols):
                if psi[j] < 0.92 or (psi[j] < 1.55 and z < -0.110): continue
                p = P[k, j]; c = np.array([0.0, 0.012]); out = p[:2] - c; out /= np.linalg.norm(out)
                drop = max(0.0, -0.112 - z)
                near = 0.25 + 0.75 * min(1.0, (psi[j] - 0.92) / 0.40)                 # 얼굴 옆 가장자리는 머리에 붙인다
                xy = p[:2] + out * ((0.015 + 0.0016 * sin(j * 2.4)) * near + 0.10 * drop) + np.array([0, 0.25 * drop])
                cur[j] = bm.verts.new((xy[0], xy[1], z))
            if prev:
                for j in range(cols):
                    j2 = (j + 1) % cols
                    if j in cur and j2 in cur and j in prev and j2 in prev: bm.faces.new((prev[j], prev[j2], cur[j2], cur[j]))
            prev = cur
    o = finish("hair", bm, mat, 0, 1, None, part); o["wb"] = "head"
    md = o.modifiers.new("s", "SOLIDIFY"); md.thickness = 0.003; md.offset = -1
    if style == "bun": obj("bun", sphere(0.036, 1, 0.9, 0.9, 18, 12), mat, "head", part).matrix_world = T(0, 0.098, 0.050)
    return o

def band(r, thick, h, half_deg, n=28):
    """얼굴을 감싸는 휜 띠(바이저)."""
    bm = bmesh.new(); rows = []
    for i in range(n + 1):
        a = radians(-half_deg + 2 * half_deg * i / n); row = []
        for rr, zz in ((r, -h / 2), (r + thick, -h / 2), (r + thick, h / 2), (r, h / 2)): row.append(bm.verts.new((rr * sin(a), -rr * cos(a), zz)))
        rows.append(row)
    for i in range(n):
        for k in range(4): bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][(k + 1) % 4], rows[i][(k + 1) % 4]))
    bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1]); return bm

def cyberware(kinds, f, eyes, glow):
    """얼굴 장식(머리 좌표, 눈 높이 z=0). 전부 이 스크립트가 만든 도형이다."""
    made = []
    def add(name, bm, mat, Mx=None, wb="head"):
        o = finish(name, bm, mat, 0.0004, 1, Mx, "cyber_head"); o["wb"] = wb; made.append(o.name); return o
    ey = eyes[0].y - 0.0122
    for c in kinds:
        if c in ("visor", "visor_thin"):
            h = 0.032 if c == "visor" else 0.016; r = 0.084 * f["wide"]; yc = ey - 0.017 + r
            kit.mat_simple("visor_lens", (0.012, 0.03, 0.04), 0.9, 0.06)
            add("visor_lens", band(r, 0.0025, h, 78), "visor_lens", T(0, yc, 0.004)); add("visor_frame", band(r + 0.0008, 0.004, 0.004, 80), "gunmetal", T(0, yc, 0.004 + h / 2))
            add("visor_line", band(r + 0.0030, 0.0012, 0.0022, 62), glow, T(0, yc, 0.004 - h / 2 + 0.004))
        elif c == "ear":
            x = -(0.0765 * f["wide"] + 0.006)
            add("ear_disc", cyl(0.011, 0.011, 0.006, 20, "x"), "gunmetal", T(x, 0.016, 0.004)); add("ear_led", cyl(0.004, 0.004, 0.002, 14, "x"), glow, T(x - 0.004, 0.016, 0.004))
            add("ear_bar", box(0.004, 0.030, 0.005), "titan", T(x, -0.004, 0.000) @ RZ(-10))
        elif c == "cheek":
            for s in (-1, 1):
                for i in range(3): add("cheek_line", box(0.0012, 0.0012, 0.010 - i * 0.002), glow, T(s * (0.040 + i * 0.006), ey + 0.006 + i * 0.006, -0.026))
        elif c == "eye":
            e = eyes[1]; add("eye_ring", torus(0.015, 0.0022, 28, 8, "y"), "gunmetal", T(e.x, e.y - 0.0125, e.z)); add("eye_lens", cyl(0.013, 0.013, 0.0015, 24, "y"), glow, T(e.x, e.y - 0.0135, e.z))
            add("eye_arm", box(0.030, 0.004, 0.004), "titan", T(e.x + (0.020 if e.x > 0 else -0.020), e.y - 0.004, e.z + 0.012))
        elif c == "neck":
            add("neck_port", cyl(0.010, 0.010, 0.005, 18, "x"), "gunmetal", T(0.052, 0.020, -0.135), "neck"); add("neck_led", cyl(0.0035, 0.0035, 0.002, 12, "x"), glow, T(0.056, 0.020, -0.135), "neck")
    return made

# ---------------------------------------------------------------- 옷 앞판, 뼈대, 가중치, 자세
def _prof(sex, z):
    pr = TORSO[sex]; zs = [p[0] for p in pr]
    return [float(np.interp(z, zs, [p[i] for p in pr])) for i in (1, 2, 3)]

def front_y(sex, z, x, grow=0.0, build=1.0, e=2.4):
    w, d, y = _prof(sex, z); w = (w + 2 * grow) * build; d = (d + 2 * grow) * build
    t = min(0.999, abs(x) / (w / 2)); return y - d / 2 * (1 - t ** e) ** (1 / e)

def plate(name, sex, mat, z0, z1, half, off=0.004, grow=0.0, build=1.0, nz=14, nx=7, wb="pelvis,spine,chest"):
    """윗옷 앞면을 따라 붙는 판(셔츠 앞섶, 넥타이, 멜빵바지 가슴판). half(z) = 그 높이에서의 반너비."""
    bm = bmesh.new(); rows = []
    for i in range(nz + 1):
        z = z0 + (z1 - z0) * i / nz; hw = half(z)
        rows.append([bm.verts.new((x, front_y(sex, z, x, grow, build) - off, z)) for x in np.linspace(-hw, hw, nx)])
    for i in range(nz):
        for j in range(nx - 1): bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    o = obj(name, bm, mat, wb); md = o.modifiers.new("s", "SOLIDIFY"); md.thickness = 0.004; md.offset = 1; return o

def make_rig(B):
    arm = bpy.data.armatures.new("rig"); rig = bpy.data.objects.new("rig", arm); kit.COL.objects.link(rig)
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode="EDIT")
    for n, (h, t, p) in B.items():
        eb = arm.edit_bones.new(n); eb.head = h; eb.tail = t
    for n, (h, t, p) in B.items():
        if p: arm.edit_bones[n].parent = arm.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT"); return rig

def category(o):
    n = o.name; m = o.data.materials[0].name if o.data.materials else ""
    if o.get("part") == "cyber_head": return "cyber"
    if n.startswith(("eye_white", "eye_iris", "eye_pupil")): return "eyes"
    if n.startswith(("hair", "brow", "bun")): return "hair"
    if n.startswith("cap"): return "hat"
    if m.startswith(("skin_", "lip_")): return "skin"
    if n.startswith(("shoe", "sole", "shaft")): return "shoes"
    if n.startswith(("hips", "leg", "pocket", "belt")): return "bottom"
    return "top"

def skin_to(rig, B, k):
    """메시마다 뼈 가중치를 주고(뼈 선분까지의 거리로), 종류별로 합친 뒤 뼈대에 건다. k = 키 배율."""
    dg = bpy.context.evaluated_depsgraph_get(); groups = {}
    for o in [o for o in kit.COL.objects if o.type == "MESH" and o.get("wb")]:
        me = o.data; me.transform(Matrix.Diagonal((k, k, k, 1)) @ o.matrix_world); o.matrix_world = Matrix.Identity(4)
        names = o["wb"].split(","); co = np.array([v.co[:] for v in me.vertices]); W = np.zeros((len(co), len(names)))
        for i, b in enumerate(names):
            h, t = np.array(B[b][0]), np.array(B[b][1]); ab = t - h; u = np.clip(((co - h) @ ab) / (ab @ ab), 0, 1)
            W[:, i] = 1.0 / (np.linalg.norm(co - (h + np.outer(u, ab)), axis=1) + 0.004 * k) ** 4
        W /= W.sum(axis=1, keepdims=True); W[W < 0.04] = 0; W /= W.sum(axis=1, keepdims=True)
        for i, b in enumerate(names):
            vg = o.vertex_groups.new(name=b)
            for vi in np.nonzero(W[:, i])[0]: vg.add([int(vi)], float(W[vi, i]), "REPLACE")
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    for o in [o for o in kit.COL.objects if o.type == "MESH" and o.get("wb")]:
        if o.modifiers:
            nm = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg); o.modifiers.clear(); o.data = nm
        groups.setdefault(category(o), []).append(o)
    out = {}
    for cat, objs in groups.items():
        if len(objs) > 1:
            with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_editable_objects=objs, selected_objects=objs): bpy.ops.object.join()
        o = objs[0]; o.name = cat; o.data.name = cat
        for p in o.data.polygons: p.use_smooth = True
        md = o.modifiers.new("arm", "ARMATURE"); md.object = rig; o.parent = rig; out[cat] = o
    return out

def rig_joints(rig, B):
    """의미 관절 대응표(runtime의 RigAnimator가 읽는다). 이 뼈대는 기본 자세가 곧 중립 자세(팔을 내린 자세)라서 neutral이 전부 단위 행렬이다."""
    I = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]; R = lambda v: [round(c, 5) for c in v]
    driven = {b for _, b in SEM} | {f"{f}_{k}_{S}" for f in FINGERS for k in (1, 2, 3) for S in "LR"}
    def anc(b):
        p = B[b][2]
        while p and p not in driven and p != "pelvis": p = B[p][2]
        return p or "pelvis"
    joints = {"root": {"bone": "pelvis", "pos": R(B["pelvis"][0])}}
    for j, b in SEM: joints[j] = {"bone": b, "parent": anc(b), "pos": R(B[b][0]), "neutral": I}
    for S in "LR":
        hb = B["hand_" + S][0]; n = (B[f"index_1_{S}"][0] - hb).cross(B[f"pinky_1_{S}"][0] - hb).normalized()
        if n.dot(B[f"thumb_2_{S}"][0] - hb) < 0: n = -n                          # n = 손바닥이 보는 쪽
        for f in FINGERS:
            for k in (1, 2, 3):
                b = f"{f}_{k}_{S}"; d = (B[b][1] - B[b][0]).normalized()
                v = (B[f"index_1_{S}"][0] - B[f"thumb_1_{S}"][0]).normalized() + n * 0.6 if f == "thumb" else n
                joints[f"{f}_{S}_{k}"] = {"bone": b, "parent": anc(b), "pos": R(B[b][0]), "neutral": I, "axis": R(d.cross(v).normalized())}
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    return joints, rest

def jrot(joint, d, axis=None):
    side = 1 if "_L" in joint else -1
    rz = d.get("yaw", 0.0); rx = d.get("pitch", 0.0) - d.get("flex", 0.0) - d.get("dorsi", 0.0) + d.get("bend", 0.0) * (1 if joint.startswith("knee") else -1)
    ry = d.get("roll", 0.0) - d.get("abduct", 0.0) * side
    Rm = Matrix.Rotation(radians(rz), 4, "Z") @ Matrix.Rotation(radians(rx), 4, "X") @ Matrix.Rotation(radians(ry), 4, "Y")
    return Matrix.Rotation(radians(d.get("curl", 0.0)), 4, Vector(axis)) @ Rm if axis else Rm

def solve(joints, pose):
    """자세 {"hip_L.flex": 20, ...} -> 뼈 이름별 변환(기본 자세 기준, 세계 좌표). runtime/RigSolver.luau와 같은 계산."""
    by = {}
    for kk, v in pose.items():
        j, d = kk.split("."); by.setdefault(j, {})[d] = v
    r = by.get("root", {}); p = Vector(joints["root"]["pos"]); TR = Matrix.Translation
    D = {"pelvis": TR((r.get("x", 0), r.get("y", 0), r.get("z", 0))) @ TR(p) @ jrot("root", r) @ TR(-p)}; N = {"pelvis": Matrix.Identity(4)}
    pend = [j for j in joints if j != "root"]
    while pend:
        for j in [j for j in pend if joints[j]["parent"] in D]:
            Jn = joints[j]; n = Jn["neutral"]; Nj = Matrix((n[0:3], n[3:6], n[6:9])).to_4x4(); q = Vector(Jn["pos"])
            D[Jn["bone"]] = D[Jn["parent"]] @ TR(q) @ N[Jn["parent"]].inverted() @ jrot(j, by.get(j, {}), Jn.get("axis")) @ Nj @ TR(-q); N[Jn["bone"]] = Nj; pend.remove(j)
    return D

def hand_pose(name, sides="LR"):
    hp = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "anim", "hand_poses.json")))[name]
    return {f"{f}_{S}_{k + 1}.curl": a for S in sides for f, v in hp.items() for k, a in enumerate(v)}

def apply_pose(rig, joints, rest, pose):
    D = solve(joints, pose)
    for pb in rig.pose.bones:   # 부모가 먼저 온다
        b = rig.data.bones[pb.name]
        while b and b.name not in D: b = b.parent
        pb.matrix = (D[b.name] if b else Matrix.Identity(4)) @ rest[pb.name]; bpy.context.view_layer.update()

STAND = {"shoulder_L.abduct": 5, "shoulder_R.abduct": 5, "shoulder_L.flex": -3, "shoulder_R.flex": 4, "elbow_L.bend": 14, "elbow_R.bend": 20, "neck.yaw": 6, "waist.yaw": -3,
         "hip_L.flex": 3, "hip_R.flex": -2, "knee_R.bend": 4}

def sample(cl, t):
    d = cl["duration"]; t = t % d if cl["loop"] else max(0.0, min(d, t)); pose = {}
    for tr in cl["tracks"]:
        ks = tr["keys"]; n = len(ks); step = d / (n - 1); i = min(n - 2, int(t / step)); u = (t - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
        pose[tr["joint"] + "." + tr["dof"]] = ks[i][1] + (ks[i + 1][1] - ks[i][1]) * u
    return pose

# ---------------------------------------------------------------- 사람 표 (전부 성인)
INK, CHAR, OLIVE, NAVY, RUST, BONE, TEAL, WINE, DENIM, GRAY = (0.012, 0.012, 0.015), (0.045, 0.045, 0.052), (0.075, 0.085, 0.04), (0.02, 0.035, 0.095), (0.28, 0.085, 0.03), (0.45, 0.42, 0.36), (0.018, 0.085, 0.085), (0.16, 0.02, 0.03), (0.03, 0.05, 0.11), (0.16, 0.16, 0.17)
PEOPLE = {
    "man_a": dict(role="행인", sex="m", age=30, h=1.78, build=1.0, tone="light", face=dict(), iris="iris_brown", hair=("short", (0.015, 0.012, 0.010)),
                  top=("jacket", CHAR, INK), bottom=(CHAR, False), shoes=(INK, True), cyber=["visor", "ear"], glow="glow_cyan"),
    "woman_a": dict(role="행인", sex="f", age=27, h=1.64, build=0.94, tone="pale", face=dict(jaw=0.90, chin_w=0.84, brow=0.0012, nose_out=0.017, nose_tip=0.0086, wing=0.0106, lip_up=0.0034, lip_low=0.0044, eye_h=0.0090),
                    iris="iris_gray", hair=("bob", (0.02, 0.22, 0.24)), top=("tee", INK, None), bottom=(DENIM, False), shoes=(INK, True), cyber=["cheek", "ear"], glow="glow_magenta"),
    "man_b": dict(role="노동자", sex="m", age=45, h=1.84, build=1.08, tone="dark", face=dict(wide=1.03, jaw=1.06, nose_tip=0.0130, wing=0.0155, nose_out=0.019, lip_up=0.0040, lip_low=0.0050, brow=0.0038),
                  iris="iris_dark", hair=("buzz", (0.02, 0.018, 0.016)), top=("overall", RUST, (0.55, 0.20, 0.12)), bottom=(RUST, False), shoes=(INK, True), cyber=["ear", "neck"], glow="glow_amber"),
    "woman_b": dict(role="회사원", sex="f", age=34, h=1.72, build=0.96, tone="light", face=dict(jaw=0.92, chin_w=0.88, brow=0.0015, nose_out=0.019, nose_tip=0.0090, wing=0.0110, lip_up=0.0030, lip_low=0.0040),
                    iris="iris_blue", hair=("bun", (0.010, 0.008, 0.008)), top=("suit", INK, (0.30, 0.31, 0.33)), bottom=(INK, False), shoes=(INK, False), cyber=["visor_thin", "ear"], glow="glow_cyan"),
    "man_c": dict(role="임원", sex="m", age=58, h=1.74, build=1.04, tone="light", face=dict(jaw=1.04, cheek=0.0040, nose_out=0.023, nose_tip=0.0112, brow=0.0036, lip_up=0.0020, lip_low=0.0028),
                  iris="iris_gray", hair=("slick", (0.36, 0.36, 0.38)), top=("suit", INK, (0.42, 0.43, 0.46)), bottom=(INK, False), shoes=((0.16, 0.06, 0.025), False), cyber=["eye", "neck"], glow="glow_red"),
    "woman_c": dict(role="행인", sex="f", age=29, h=1.76, build=0.98, tone="brown", face=dict(jaw=0.94, chin_w=0.90, nose_tip=0.0118, wing=0.0140, nose_out=0.018, lip_up=0.0042, lip_low=0.0054, brow=0.0016, eye_h=0.0088),
                    iris="iris_dark", hair=("afro", (0.20, 0.03, 0.12)), top=("tee", WINE, None), bottom=(CHAR, True), shoes=(INK, True), cyber=["visor", "cheek"], glow="glow_magenta"),
    "man_d": dict(role="행인", sex="m", age=24, h=1.69, build=0.96, tone="tan", face=dict(jaw=0.96, eye_tilt=0.12, eye_h=0.0068, nose_out=0.017, nose_tip=0.0108, wing=0.0132, brow=0.0020, cheekbone=1.03),
                  iris="iris_dark", hair=("short", (0.46, 0.38, 0.14)), top=("tee", INK, None), bottom=(OLIVE, True), shoes=(INK, True), cyber=["cheek", "ear"], glow="glow_amber"),
    "woman_d": dict(role="회사원", sex="f", age=47, h=1.68, build=1.0, tone="light", face=dict(jaw=0.94, chin_w=0.90, brow=0.0014, cheek=0.0038, nose_out=0.020, lip_up=0.0028, lip_low=0.0038),
                    iris="iris_green", hair=("long", (0.42, 0.43, 0.48)), top=("suit", WINE, (0.50, 0.20, 0.22)), bottom=(WINE, False), shoes=(INK, False), cyber=["cheek", "ear"], glow="glow_cyan"),
    "merchant": dict(role="상인", sex="m", age=60, h=1.64, build=1.10, tone="olive", face=dict(wide=1.04, jaw=1.08, cheek=0.0048, eye_tilt=0.10, eye_h=0.0066, nose_out=0.017, nose_tip=0.0116, wing=0.0138),
                     iris="iris_dark", hair=("short", (0.40, 0.40, 0.41)), top=("polo", OLIVE, None), bottom=(INK, False), shoes=(INK, False), cap=CHAR, cyber=["ear"], glow="glow_amber"),
    "doctor": dict(role="시술의", sex="m", age=41, h=1.70, build=0.98, tone="tan", face=dict(jaw=0.98, nose_out=0.022, brow=0.0030, cheek=0.0022),
                   iris="iris_brown", hair=("slick", (0.02, 0.016, 0.014)), top=("coat", (0.30, 0.33, 0.34), TEAL), bottom=(CHAR, False), shoes=(INK, True), cyber=["eye", "ear", "neck"], glow="glow_cyan"),
    "fp_sleeve": dict(role="1인칭 팔(긴소매)", sex="m", age=30, h=1.78, build=1.0, tone="light", top=("shirt", CHAR, None), fp=True, glow="glow_cyan"),
    "fp_bare": dict(role="1인칭 팔(맨팔)", sex="m", age=30, h=1.78, build=1.0, tone="light", top=("tee", INK, None), fp=True, glow="glow_cyan"),
}

def build(name):
    sp = PEOPLE[name]
    if sp["age"] < 20: raise RuntimeError("성인만 만든다: " + name)
    kit.reset(); base_mats(); skin_mats(sp["tone"]); skin = "skin_" + sp["tone"]; sex = sp["sex"]; bld = sp["build"]; k = sp["h"] / H0
    J = skeleton(sex); kind, col, col2 = sp["top"]
    mat_cloth("top", col, 0.82 if kind in ("suit", "coat") else 0.78, 0.35 if kind == "suit" else 0.55)
    if col2: mat_cloth("top2", col2, 0.7, 0.4)
    kit.mat_simple("belt", (0.02, 0.018, 0.016), 0.0, 0.5)
    fp = sp.get("fp"); made = []; eyes = None
    # 윗옷
    if kind in ("tee", "polo", "overall"):
        tm = "top2" if kind == "overall" else "top"
        if not fp: torso(sex, tm, 0.90, 0.004, bld)
        sleeves(J, tm, 0.45, bld); arm_skin(J, skin, sex, 0.36)
        if kind == "polo" and not fp: collar("top", sex, h=0.026)
        if kind == "overall" and not fp:
            torso(sex, "top", 0.88, 0.010, bld, name="bib", zmax=1.33)
            for sg in (-1, 1):
                obj("strap", tube([(sg * 0.080, front_y(sex, 1.32, sg * 0.080, 0.010, bld) - 0.004, 1.31), (sg * 0.092, -0.085, 1.43), (sg * 0.098, 0.005, 1.485), (sg * 0.088, 0.105, 1.42), (sg * 0.070, 0.128, 1.31)],
                                  [0.019] * 5, u=(1, 0, 0), flat=0.3, n=10), "top", "chest")
    else:
        grow, hem, r = {"shirt": (0.006, 0.88, 1.0), "jacket": (0.013, 0.86, 1.10), "suit": (0.010, 0.84, 1.05), "coat": (0.016, 0.52, 1.10)}[kind]
        if not fp:
            torso(sex, "top", hem, grow, bld)
            collar("top", sex, h=0.034 if kind != "suit" else 0.022, r=0.074 if kind != "shirt" else 0.066)
            if kind in ("jacket", "coat"):
                plate("front", sex, "top2", max(hem + 0.02, 0.60), 1.49, lambda z: 0.026 + 0.026 * min(1.0, max(0.0, (z - 0.9) / 0.5)), 0.0012, grow, bld, wb="pelvis,spine,chest" if hem > 0.8 else "pelvis,spine,chest,thigh_L,thigh_R")
            if kind == "suit":
                plate("shirt_front", sex, "top2", 1.16, 1.49, lambda z: 0.006 + 0.075 * max(0.0, (z - 1.16) / 0.33), 0.003, grow, bld)
                kit.mat_simple("tie", (0.03, 0.03, 0.035) if sex == "m" else (0.35, 0.05, 0.08), 0.0, 0.5)
                plate("tie", sex, "tie", 1.20, 1.475, lambda z: 0.012 + 0.010 * (1 - abs((z - 1.30) / 0.17)), 0.008, grow, bld, nx=3)
                for z in (1.06, 1.12): obj("button", cyl(0.007, 0.007, 0.004, 14, "y"), "belt", "spine").matrix_world = T(0.0, front_y(sex, z, 0, grow, bld) - 0.002, z)
        sleeves(J, "top", 1.0, bld * r, cuff="top2" if kind == "suit" else None); arm_skin(J, skin, sex, None)
    hands(J, skin)
    if not fp:
        neck(J, skin, sex)
        bc, cargo = sp["bottom"]; mat_cloth("bottom", bc, 0.8, 0.5); pants(J, sex, "bottom", 0.060 if cargo else 0.052, bld, cargo)
        sc, boot = sp["shoes"]; kit.mat_simple("shoe", sc, 0.0, 0.42); shoes(J, "shoe", boot)
        # 머리(눈 높이가 z=0인 좌표에서 만든 뒤 제자리로 옮긴다)
        before = set(kit.COL.objects); f = dict(FACE); f.update(sp["face"])
        if sex == "f": f.setdefault("_", 0); f["wide"] = f["wide"] * 0.965
        hc = sp["hair"][1]; head, eyes, grid = build_head(name, f, skin, sp["iris"], brow=tuple(c * 0.8 for c in hc) if max(hc) < 0.3 else (0.05, 0.04, 0.035), brow_thick=1.0 if sex == "m" else 0.75)
        mat_hair("hair", hc); hair(head, grid, sp["hair"][0], "hair")
        if sp.get("cap"):
            mat_cloth("cap", sp["cap"], 0.8, 0.3)
            obj("cap_top", sphere(0.090, 1.0, 1.12, 0.42, 24, 12), "cap", "head", "head").matrix_world = T(0, 0.004, 0.092) @ RX(-6)
            obj("cap_brim", sphere(0.060, 1.15, 1.0, 0.10, 20, 8), "cap", "head", "head").matrix_world = T(0, -0.085, 0.066) @ RX(-10)
        made = cyberware(sp["cyber"], f, eyes, sp["glow"])
        Mh = T(0, 0.0, 1.650) @ (S(0.96, 0.96, 0.96) if sex == "f" else Matrix.Identity(4))
        for o in set(kit.COL.objects) - before:
            o["wb"] = o.get("wb") or "head"; o.matrix_world = Mh @ o.matrix_world
    for o in kit.COL.objects:
        if o.type == "MESH" and not o.get("wb"): o["wb"] = "head"
    Jk = {n: (v * k if isinstance(v, Vector) else ([p * k for p in v[:4]] + [v[4] * k] if isinstance(v, list) else v)) for n, v in J.items()}
    B = bone_table(Jk); rig = make_rig(B); meshes = skin_to(rig, B, k)
    joints, rest = rig_joints(rig, B)
    return rig, meshes, joints, rest, made, B, k

def export(name, rig, meshes, joints, made, B, k, extra=None):
    sp = PEOPLE[name]
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update(); d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True); tris = {}
    for c, o in meshes.items():
        o.data.calc_loop_triangles(); tris[c] = len(o.data.loop_triangles)
    objs = list(meshes.values()) + [rig]
    for o in bpy.context.scene.objects: o.select_set(o in objs)
    imgs = [i.name for i in bpy.data.images if i.type not in ("RENDER_RESULT", "COMPOSITING")]
    if imgs: raise RuntimeError("그림 파일이 들어 있다: " + ", ".join(imgs))
    try: bpy.ops.export_scene.gltf(filepath=os.path.join(d, f"human_{name}.glb"), export_apply=False, use_selection=True, export_extras=True)
    except Exception as e: print("gltf:", repr(e)[:200])
    man = {"name": "human_" + name, "role": sp.get("role"), "made_by": "person.py (자체 제작, 외부 에셋·그림 파일 없음)", "units": "m", "forward": "-Y", "up": "+Z", "rig": "person", "height": round(sp["h"], 3),
           "bones": [b.name for b in rig.data.bones], "joints": joints, "triangles": sum(tris.values()), "triangles_by_mesh": tris, "meshes": sorted(meshes), "images": 0,
           "materials": sorted({s.material.name for o in meshes.values() for s in o.material_slots if s.material}), "cyberware": sorted(made), "glow": sp["glow"],
           "attach": {"cyber_head": "head", "hand_R": "hand_R", "hand_L": "hand_L"}}
    man.update(extra or {})
    json.dump(man, open(os.path.join(d, f"human_{name}.manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(f"EXPORT human_{name} tris={man['triangles']} meshes={len(tris)} bones={len(man['bones'])} h={man['height']}", flush=True)

def golden(joints, clips_dir):
    """Luau 쪽 RigSolver 검증용: 사람 뼈대에 클립을 적용했을 때 뼈별 행렬."""
    cases = []; fmt = lambda Dm: {b: [round(m[r][c], 6) for r in range(3) for c in range(3)] + [round(m[r][3], 6) for r in range(3)] for b, m in Dm.items()}
    for cn in ("walk", "run", "cower_enter"):
        cl = json.load(open(os.path.join(clips_dir, cn + ".json")))
        for t in (0.0, 0.21, cl["duration"] * 0.6): cases.append({"clip": cn, "t": round(t, 5), "parts": fmt(solve(joints, sample(cl, t)))})
    hp = dict(sample(json.load(open(os.path.join(clips_dir, "walk.json"))), 0.3)); hp.update(hand_pose("grip_pistol", "R")); hp.update(hand_pose("fist", "L")); hp["wrist_R.flex"] = 20
    json.dump({"manifest": {"joints": joints}, "cases": cases, "hand_case": {"pose": hp, "parts": fmt(solve(joints, hp))}}, open(os.path.join(clips_dir, "_golden_human.json"), "w"), separators=(",", ":"))
    print("GOLDEN human", len(cases))

if __name__ == "__main__" and MODE in ("render", "export"):
    os.makedirs(OUT, exist_ok=True); clips = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "anim"); RENDER = MODE == "render"
    for name in PEOPLE:
        if ONLY and name not in ONLY: continue
        rig, meshes, joints, rest, made, B, k = build(name); sp = PEOPLE[name]; extra = {}
        res = tuple(int(c) for c in os.environ.get("HUMAN_RES", "800,1200").split(","))
        if sp.get("fp"):
            eye = [0.0, round(-0.075 * k, 4), round(1.650 * k, 4)]; extra["eye"] = eye
            if RENDER:
                pose = {"shoulder_L.flex": 62, "shoulder_R.flex": 62, "shoulder_L.abduct": -4, "shoulder_R.abduct": -4, "elbow_L.bend": 46, "elbow_R.bend": 46}
                pose.update(hand_pose("grip_pistol", "R")); pose.update(hand_pose("relaxed", "L")); apply_pose(rig, joints, rest, pose)
                kit.studio((0, -0.35, 1.25), 0.7, floor_z=0.6)
                kit.shot(os.path.join(OUT, f"{name}_view.png"), (eye[0], eye[1] + 0.06, eye[2] + 0.02), (0, -0.60, 1.20), 20, res=(res[1], res[0]))
                kit.shot(os.path.join(OUT, f"{name}.png"), (-1.55, -1.95, 1.95), (0, -0.32, 1.22), 60, res=(res[1], res[0]))
        elif RENDER:
            pose = dict(STAND); pose.update(hand_pose("relaxed")); apply_pose(rig, joints, rest, pose); kit.studio((0, 0, 0.9), 1.0)
            kit.shot(os.path.join(OUT, f"human_{name}.png"), (-1.5, -4.3, 1.45), (0, 0, 0.90), 70, res=res)
            hz = 1.650 * k
            fill = kit.area("face_fill", (-0.5, -1.6, hz + 0.25), (0, 0, hz), 0.8, 26, (1.0, 0.95, 0.9))
            kit.shot(os.path.join(OUT, f"human_{name}_face.png"), (-0.42, -1.05, hz + 0.03), (0, -0.02, hz - 0.01), 85, res=(res[0], res[0]))
            strips = os.environ.get("HUMAN_STRIPS", "")
            if strips:
                bpy.data.objects.remove(fill)
                for cn in strips.split(","):
                    cl = json.load(open(os.path.join(clips, cn + ".json")))
                    for i in range(6):
                        apply_pose(rig, joints, rest, sample(cl, cl["duration"] * i / (6 if cl["loop"] else 5)))
                        kit.shot(os.path.join(OUT, f"_{cn}_{name}_{i}.png"), (-2.9, -4.4, 1.3), (0, 0.1, 0.80), 60, res=(330, 560))
        for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
        export(name, rig, meshes, joints, made, B, k, extra)
        if name == "man_a" and os.environ.get("HUMAN_GOLDEN"): golden(joints, clips)
