"""건물 벽 재질(자체 제작). 이어 붙여도 이음매가 보이지 않는 그림 세 벌을 수식으로 만든다: 색, 요철(노멀), 거칠기.
  concrete_panel : 밝은 콘크리트 패널. 줄눈, 거푸집 구멍, 패널마다 조금 다른 색, 빗물 얼룩
  concrete_board : 어두운 콘크리트. 널빤지 거푸집 자국(가로줄), 진한 얼룩
  metal_ribbed   : 골이 진 금속 외장. 세로 골, 가로 이음, 리벳
한 장이 3.6 m × 3.6 m를 덮는다(층고와 같다). 글자나 그림은 없고 무늬뿐이다.
실행: python wall_textures.py <출력폴더> [preview]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np

N = 1024; TILE = 3.6
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "out", "street", "materials")

def fnoise(beta, seed, ay=1.0, ax=1.0):
    """이어지는(주기적인) 잡음. ay, ax가 크면 그 방향으로 길게 늘어진다."""
    rng = np.random.default_rng(seed); f = np.fft.fft2(rng.standard_normal((N, N)))
    ky = np.fft.fftfreq(N)[:, None] * ay; kx = np.fft.fftfreq(N)[None, :] * ax
    k = np.sqrt(kx ** 2 + ky ** 2); k[0, 0] = 1.0; f *= k ** (-beta / 2.0); f[0, 0] = 0
    x = np.real(np.fft.ifft2(f)); return (x - x.mean()) / x.std()

def srgb(lin): return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def normal_from(height, strength):
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength; dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    # 초록 = 그림의 위쪽(OpenGL 방식). 그림은 위에서 아래로 저장되므로 세로 기울기의 부호를 뒤집는다
    n = np.stack([-dx, dy, np.ones_like(height)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True); return n * 0.5 + 0.5

def save(path, arr):
    """arr: (N, N) 또는 (N, N, 3), 0~1. 값 그대로 8비트 PNG로 쓴다(색 그림은 이미 sRGB로 바꾼 값)."""
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, -1)
    px = np.concatenate([np.clip(arr, 0, 1), np.ones((N, N, 1))], -1)[::-1].astype(np.float32)
    im = bpy.data.images.new(os.path.basename(path), N, N, alpha=False); im.colorspace_settings.name = "Non-Color"
    im.pixels = px.ravel(); im.filepath_raw = path; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)

def grids():
    v, u = np.meshgrid((np.arange(N) + 0.5) / N * TILE, (np.arange(N) + 0.5) / N * TILE, indexing="ij"); return u, v   # v = 세로(m), u = 가로(m)

def concrete_panel():
    u, v = grids(); rh, pw = 0.9, 1.8
    row = np.floor(v / rh).astype(int); uo = (u + (row % 2) * pw / 2) % TILE; col = np.floor(uo / pw).astype(int)
    dj = np.minimum(np.minimum(v % rh, rh - v % rh), np.minimum(uo % pw, pw - uo % pw)); groove = 1 - smooth(dj / 0.006)
    hx = (uo % pw) / pw; hy = (v % rh) / rh
    holes = np.maximum(1 - smooth(np.hypot((hx - 0.25) * pw, (hy - 0.5) * rh) / 0.014), 1 - smooth(np.hypot((hx - 0.75) * pw, (hy - 0.5) * rh) / 0.014))
    rng = np.random.default_rng(3); tint = rng.uniform(-0.08, 0.08, (4, 2))[row % 4, col % 2]
    mottle = fnoise(2.4, 1); grain = fnoise(0.9, 2); streak = np.clip(fnoise(2.0, 4, ay=14.0) * 0.6 + fnoise(2.2, 5, ay=40.0) * 0.4, -2, 2)
    under = smooth((rh - v % rh) / 0.25) * 0.5                                   # 줄눈 바로 아래는 물이 고여 더 얼룩진다
    shade = 1 + tint + 0.11 * mottle + 0.03 * grain - 0.20 * np.clip(streak, 0, 2) * (0.6 + under) - 0.50 * groove - 0.6 * holes
    base = np.array([0.26, 0.25, 0.24]); warm = np.array([1.03, 1.0, 0.95])
    colr = base[None, None] * shade[..., None] * (1 + 0.04 * np.clip(-mottle, 0, 2)[..., None] * (warm - 1)[None, None])
    height = -groove * 1.0 - holes * 1.2 + 0.10 * grain + 0.25 * mottle
    rough = np.clip(0.78 + 0.05 * grain - 0.10 * np.clip(streak, 0, 2) + 0.08 * groove, 0.3, 1)
    return srgb(colr), normal_from(height, 2.2), rough

def concrete_board():
    u, v = grids(); bh = 0.15
    board = np.floor(v / bh).astype(int); rng = np.random.default_rng(7); tint = rng.uniform(-0.07, 0.07, 24)[board % 24]
    dj = np.minimum(v % bh, bh - v % bh); line = 1 - smooth(dj / 0.004)
    woodg = fnoise(1.6, 11, ax=30.0); mottle = fnoise(2.4, 12); grain = fnoise(0.9, 13)
    streak = np.clip(fnoise(2.0, 14, ay=16.0) * 0.6 + fnoise(2.2, 15, ay=50.0) * 0.5, -2, 2)
    shade = 1 + tint + 0.12 * mottle + 0.06 * woodg + 0.03 * grain - 0.26 * np.clip(streak, 0, 2) - 0.38 * line + 0.14 * np.clip(-streak, 0, 2) * 0.5
    colr = np.array([0.12, 0.12, 0.125])[None, None] * shade[..., None]
    height = -line * 0.8 + 0.22 * woodg + 0.08 * grain + 0.2 * mottle
    rough = np.clip(0.80 + 0.05 * grain - 0.14 * np.clip(streak, 0, 2), 0.3, 1)
    return srgb(colr), normal_from(height, 2.0), rough

def metal_ribbed():
    u, v = grids(); rw = 0.3
    rib = 0.5 + 0.5 * np.cos(2 * np.pi * u / rw); rib = smooth(rib) ** 1.5                     # 세로 골
    sh = 1.8; ds = np.minimum(v % sh, sh - v % sh); seam = 1 - smooth(ds / 0.008)
    rx = (u % rw) / rw; rivet = (1 - smooth(np.hypot((rx - 0.5) * rw, ds - 0.035) / 0.010)) * (ds < 0.08)
    grain = fnoise(0.8, 21); streak = np.clip(fnoise(2.0, 22, ay=24.0), -2, 2); mottle = fnoise(2.4, 23)
    shade = 1 + 0.10 * (rib - 0.5) + 0.05 * mottle + 0.02 * grain - 0.12 * np.clip(streak, 0, 2) - 0.4 * seam + 0.15 * rivet
    colr = np.array([0.11, 0.115, 0.125])[None, None] * shade[..., None] + np.array([0.05, 0.02, 0.0])[None, None] * (0.25 * np.clip(streak - 1.0, 0, 1) * seam)[..., None]
    height = rib * 1.2 - seam * 0.8 + rivet * 1.0 + 0.04 * grain
    rough = np.clip(0.42 + 0.06 * grain + 0.16 * np.clip(streak, 0, 2) + 0.2 * seam, 0.15, 1)
    return srgb(colr), normal_from(height, 1.6), rough

SETS = {"concrete_panel": concrete_panel, "concrete_board": concrete_board, "metal_ribbed": metal_ribbed}

def generate(out):
    os.makedirs(out, exist_ok=True)
    for name, fn in SETS.items():
        c, n, r = fn()
        save(os.path.join(out, name + "_Color.png"), c); save(os.path.join(out, name + "_Normal.png"), n); save(os.path.join(out, name + "_Roughness.png"), r)
        print("TEXTURE", name, "mean sRGB", tuple(int(x) for x in (c.reshape(-1, 3).mean(0) * 255)))

def material(key, name, metallic=0.0, folder=DEFAULT_DIR):
    """그림 세 장을 상자 투영(세계 좌표, 3.6 m마다 반복)으로 입힌 재질을 kit.M[key]에 넣는다. 그림이 없으면 False."""
    import kit
    paths = [os.path.join(folder, f"{name}_{s}.png") for s in ("Color", "Normal", "Roughness")]
    if not all(os.path.exists(p) for p in paths): return False
    m, nt, b = kit._nodes(key); tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / TILE, 1 / TILE, 1 / TILE); nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(path, data):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.projection = "BOX"; t.projection_blend = 0.15
        if data: t.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"]); return t
    nt.links.new(tex(paths[0], False).outputs["Color"], b.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0; nt.links.new(tex(paths[1], True).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(tex(paths[2], True).outputs["Color"], b.inputs["Roughness"]); b.inputs["Metallic"].default_value = metallic
    kit.M[key] = m; return True

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    generate(out)
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        import kit, street
        from kit import T
        sc = kit.reset(); street.materials(); street.base_ground()
        street.building(1, 0, 34, 14, 30, 1, full=True); street.building(1, 36, 59, 16, 44, 2, full=True)
        street.light_and_shoot(sc, "wall_preview.png", True, [], cam=((-7.0, -6.0, 1.75), (12.5, 16.0, 9.0), 30))
