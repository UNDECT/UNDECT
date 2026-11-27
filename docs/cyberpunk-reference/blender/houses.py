"""들어갈 수 있는 건물 (자체 제작). 배틀로얄 전장용: 문·창·방·계단·옥상이 있고, 아이템 자리가 정해져 있다.
벽·바닥·가구의 충돌은 전부 축에 맞춘 상자다. 그래서 게임에서는 manifest의 충돌 목록(colliders)을 그대로 보이지 않는 부품으로 놓으면 된다.
창틀, 문틀, 띠 장식, 난간, 가구의 다리 같은 장식은 보이기만 하고 충돌이 없다.
내보내기 전에 '걸어서 갈 수 있는지'를 검사한다: 건물 밖에서 출발해 문과 계단, 사다리만으로 모든 아이템 자리에 닿아야 한다.
실행: python houses.py <출력폴더> [render] [이름...]
건물 원점 = 바닥 가운데, 앞(정문) = -Y, 단위 m.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, numpy as np
from math import atan2, degrees
from mathutils import Matrix, Vector
import kit, street
from kit import finish, box, T, RX
from street import Multi

ARGS = sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/houses"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []
TW = 0.25                      # 바깥벽 두께
DIRS = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}
D = lambda p, w=1.1: (p, w, 0.0, 2.2, "door")             # 문: 시작 위치, 너비
Wn = lambda p, w=1.4: (p, w, 0.9, 1.2, "window")          # 창: 창턱 0.9 m
G = lambda p, w=1.2, h=2.3: (p, w, 0.0, h, "gap")          # 문짝 없는 통로
BIG = lambda p, w, h=2.2, sill=0.5: (p, w, sill, h, "window")

def mats(tex=False):
    street.materials(tex)
    kit.mat_simple("plaster", (0.17, 0.18, 0.165), 0.0, 0.8); kit.mat_simple("floor", (0.055, 0.055, 0.06), 0.0, 0.42); kit.mat_simple("wood", (0.20, 0.11, 0.05), 0.0, 0.6)
    kit.mat_simple("pane", (0.02, 0.03, 0.035), 0.0, 0.04, alpha=0.2); kit.mat_simple("lamp", (0, 0, 0), 0, 0.4, (1.0, 0.84, 0.62), 40.0)
    kit.mat_simple("tread", (0.07, 0.07, 0.08), 0.6, 0.5); kit.mat_simple("mattress", (0.42, 0.41, 0.37), 0.0, 0.9); kit.mat_simple("fabric", (0.08, 0.12, 0.16), 0.0, 0.9)
    kit.mat_simple("screen", (0, 0, 0), 0, 0.3, (0.25, 0.8, 1.0), 3.0)
    kit.mat_simple("door_red", (0.30, 0.035, 0.03), 0.2, 0.5); kit.mat_simple("door_teal", (0.025, 0.15, 0.19), 0.2, 0.5); kit.mat_simple("door_yellow", (0.50, 0.30, 0.02), 0.2, 0.5)
    # 상자·사물함·계산대의 칠: 무늬 없는 단색(게임에서 색이 그대로 나오게)
    kit.mat_simple("paint_teal", (0.035, 0.13, 0.17), 0.1, 0.55); kit.mat_simple("paint_red", (0.26, 0.035, 0.03), 0.1, 0.55); kit.mat_simple("paint_yellow", (0.48, 0.28, 0.025), 0.1, 0.55)

class Bld:
    def __init__(self, name, W, Dp, wall="concrete", inner="plaster", cut=None, door="door_teal", lining=True):
        self.name, self.W, self.D, self.wm, self.im, self.cut, self.dm = name, W, Dp, wall, inner, cut, door
        self.lining, self.trim = lining, ("concrete" if wall == "concrete_dark" else "concrete_dark")
        self.m, self.col, self.loots, self.doors, self.portals, self.levels, self.slabs, self.glass, self.lights = {}, [], [], [], [], [0.0], [], [], []
        self.vis("floor", (W - 2 * TW, Dp - 2 * TW, 0.04), (W / 2, Dp / 2, 0.0))
    # --- 기본 상자
    def box(self, mat, size, c, collide=True):
        if collide: self.col.append({"type": "box", "pos": list(c), "size": list(size), "tag": "structure"})
        if self.cut is not None:          # 단면 그림: 자르는 높이 위는 그리지 않는다
            lo, hi = c[2] - size[2] / 2, c[2] + size[2] / 2
            if lo >= self.cut: return
            if hi > self.cut: size = (size[0], size[1], self.cut - lo); c = (c[0], c[1], (lo + self.cut) / 2)
        self.m.setdefault(mat, Multi()).add(size[0], size[1], size[2], T(*c))
    def vis(self, mat, size, c): self.box(mat, size, c, False)
    def solid(self, size, c, tag="furniture"): self.col.append({"type": "box", "pos": list(c), "size": list(size), "tag": tag})
    def obox(self, mat, sec, p0, p1):
        """p0에서 p1까지 비스듬히 놓인 막대(보이기만 한다). sec = (가로, 세로) 단면."""
        v = p1 - p0; L = v.length; X = v / L; Y = Vector((-X.y, X.x, 0)); Y = Y.normalized() if Y.length > 1e-6 else Vector((0, 1, 0)); Z = X.cross(Y); c = (p0 + p1) / 2
        if self.cut is not None and c.z > self.cut: return
        self.m.setdefault(mat, Multi()).add(L, sec[0], sec[1], Matrix(((X.x, Y.x, Z.x, c.x), (X.y, Y.y, Z.y, c.y), (X.z, Y.z, Z.z, c.z), (0, 0, 0, 1))))
    def _seg(self, ax, c, a, b, z0, h, mat, t, collide=True):
        if b - a < 0.01 or h < 0.01: return
        if ax == "x": self.box(mat, (b - a, t, h), ((a + b) / 2, c, z0 + h / 2), collide)
        else: self.box(mat, (t, b - a, h), (c, (a + b) / 2, z0 + h / 2), collide)
    def wall(self, ax, c, a, b, z0, h, ops=(), mat=None, t=TW, out=0, base=True, ext=0.0):
        """ax = 'x'면 y = c 선을 따라 x가 a~b인 벽. ops = 문·창·통로 목록. out = 바깥벽이면 바깥쪽 방향(-1 또는 +1)."""
        mat = mat or self.wm; cur = a
        V = lambda off, lo, hi, zz, hh, m, tt: self._seg(ax, c + off, lo, hi, zz, hh, m, tt, False)
        E = lambda lo, hi: (lo - (ext if abs(lo - a) < 1e-6 else 0), hi + (ext if abs(hi - b) < 1e-6 else 0))
        def W_(lo, hi, zz, hh):          # 벽 한 조각 + (바깥벽이면) 안쪽 마감
            self._seg(ax, c, lo, hi, zz, hh, mat, t)
            if out and base and self.lining: V(-out * (t / 2 + 0.006), lo, hi, zz, hh, self.im, 0.012)
        def full(lo, hi):
            if hi - lo < 0.01: return
            W_(lo, hi, z0, h)
            if base:
                for s in ((-out,) if out else (-1, 1)): V(s * (t / 2 + 0.008), lo, hi, z0, 0.10, "dark", 0.02)        # 걸레받이
            if out and z0 == 0: l2, h2 = E(lo, hi); V(out * (t / 2 + 0.02), l2, h2, 0, 0.5, self.trim, 0.06)       # 바깥벽 아랫단
        for p, w, sill, oh, kind in sorted(ops):
            full(cur, p); W_(p, p + w, z0, sill); W_(p, p + w, z0 + sill + oh, h - sill - oh); cur = p + w
            if kind == "open": continue
            if sill > 0.4 and out and z0 == 0: V(out * (t / 2 + 0.02), p, p + w, 0, 0.5, self.trim, 0.06)
            fm, ft = "gunmetal", t + 0.06          # 틀: 벽보다 조금 두껍게 해서 양쪽으로 3 cm씩 나온다
            V(0, p - 0.06, p + 0.01, z0 + sill, oh, fm, ft); V(0, p + w - 0.01, p + w + 0.06, z0 + sill, oh, fm, ft); V(0, p - 0.06, p + w + 0.06, z0 + sill + oh - 0.01, 0.07, fm, ft)
            mid = (p + w / 2, c) if ax == "x" else (c, p + w / 2)
            if kind == "window":
                V(out * 0.03, p - 0.1, p + w + 0.1, z0 + sill - 0.05, 0.06, fm, t + 0.16)                           # 창턱
                n = max(1, round(w / 1.3))
                for i in range(1, n): V(0, p + w * i / n - 0.025, p + w * i / n + 0.025, z0 + sill, oh, fm, 0.07)   # 창살
                if oh >= 1.5: V(0, p, p + w, z0 + sill + oh * 0.64, 0.05, fm, 0.07)
                sz = (w, 0.03, oh) if ax == "x" else (0.03, w, oh)
                self.vis("pane", sz, (mid[0], mid[1], z0 + sill + oh / 2)); self.glass.append({"pos": [mid[0], mid[1], z0 + sill + oh / 2], "size": list(sz)})
            elif kind == "door":
                hinge = (p, c, z0) if ax == "x" else (c, p, z0)
                self.doors.append({"hinge": list(hinge), "along": ax, "width": w, "height": oh})
            if out and z0 == 0 and kind in ("door", "gap"):       # 바깥문 위의 등(밤에 입구가 보인다)과 차양
                lw = min(w * 0.6, 1.6); V(out * (t / 2 + 0.03), p + w / 2 - lw / 2, p + w / 2 + lw / 2, z0 + oh + 0.14, 0.07, "lamp", 0.05)
                lp = (mid[0], mid[1] + out * 0.3, z0 + oh + 0.17) if ax == "x" else (mid[0] + out * 0.3, mid[1], z0 + oh + 0.17); self.lights.append({"pos": list(lp), "kind": "door"})
                if kind == "door": V(out * (t / 2 + 0.30), p - 0.2, p + w + 0.2, z0 + oh + 0.30, 0.06, "gunmetal", 0.6)
        full(cur, b)
    def ring(self, z, hh, d=0.05, mat=None):
        """층 사이의 띠 장식(바깥을 한 바퀴)."""
        W, Dp = self.W, self.D; mat = mat or self.trim
        for y in (-d / 2 + 0.005, Dp + d / 2 - 0.005): self.vis(mat, (W + 2 * d, d + 0.01, hh), (W / 2, y, z + hh / 2))
        for x in (-d / 2 + 0.005, W + d / 2 - 0.005): self.vis(mat, (d + 0.01, Dp - 0.02, hh), (x, Dp / 2, z + hh / 2))
    def shell(self, z0, h, front=(), back=(), left=(), right=(), mat=None):
        """바깥벽 네 면. 앞 = y 0, 뒤 = y D, 왼쪽 = x 0, 오른쪽 = x W."""
        W, Dp = self.W, self.D
        self.wall("x", TW / 2, 0, W, z0, h, front, mat, out=-1, ext=0.05); self.wall("x", Dp - TW / 2, 0, W, z0, h, back, mat, out=1, ext=0.05)
        self.wall("y", TW / 2, TW, Dp - TW, z0, h, left, mat, out=-1, ext=TW); self.wall("y", W - TW / 2, TW, Dp - TW, z0, h, right, mat, out=1, ext=TW)
        self.ring(z0 + h - 0.3, 0.3)
    def slab(self, x0, y0, x1, y1, z, holes=(), mat="floor", t=0.25, level=True):
        """윗면이 z인 바닥. holes = 뚫을 사각형들(계단 자리)."""
        rects = [(x0, y0, x1, y1)]
        for hx0, hy0, hx1, hy1 in holes:
            nxt = []
            for a0, b0, a1, b1 in rects:
                if hx0 >= a1 or hx1 <= a0 or hy0 >= b1 or hy1 <= b0: nxt.append((a0, b0, a1, b1)); continue
                for r in ((a0, b0, max(a0, hx0), b1), (min(a1, hx1), b0, a1, b1), (max(a0, hx0), b0, min(a1, hx1), max(b0, hy0)), (max(a0, hx0), min(b1, hy1), min(a1, hx1), b1)):
                    if r[2] - r[0] > 0.01 and r[3] - r[1] > 0.01: nxt.append(r)
            rects = nxt
        for a0, b0, a1, b1 in rects:
            self.box(mat, (a1 - a0, b1 - b0, t), ((a0 + a1) / 2, (b0 + b1) / 2, z - t / 2)); self.slabs.append((z, a0, b0, a1, b1))
        if level and z not in self.levels: self.levels.append(z)
    def stair(self, x, y, z0, z1, d, width=1.2, run=None):
        """(x, y)에서 d 방향으로 올라가는 곧은 계단. 디딤판과 옆판, 난간. 밑은 비어 있다(위아래로 겹쳐 놓을 수 있다). 충돌은 비탈 하나."""
        dx, dy = DIRS[d]; rise = z1 - z0; run = run or rise; n = max(2, round(rise / 0.19))
        for i in range(n):
            cx, cy = x + dx * run * (i + 0.5) / n, y + dy * run * (i + 0.5) / n
            sz = (run / n + 0.02, width, 0.05) if dx else (width, run / n + 0.02, 0.05)
            self.vis("tread", sz, (cx, cy, z0 + rise * (i + 1) / n - 0.025))
        p0, p1, side, up = Vector((x, y, z0)), Vector((x + dx * run, y + dy * run, z1)), Vector((-dy, dx, 0)), Vector((0, 0, 1))
        for s in (-1, 1):
            o = side * (s * (width / 2 + 0.03))
            self.obox("gunmetal", (0.05, 0.26), p0 + o - up * 0.10, p1 + o - up * 0.10); self.obox("gunmetal", (0.05, 0.05), p0 + o + up * 0.95, p1 + o + up * 0.95)
            for u in (0.03, 0.5, 0.97):
                q = p0.lerp(p1, u) + o; self.vis("gunmetal", (0.04, 0.04, 0.95), (q.x, q.y, q.z + 0.475))
        self.col.append({"type": "ramp", "from": [x, y, z0], "to": [x + dx * run, y + dy * run, z1], "width": width, "thickness": 0.15})
        self.portals.append(((x - dx * 0.45, y - dy * 0.45, z0), (x + dx * (run + 0.45), y + dy * (run + 0.45), z1)))
    def ladder(self, x, y, z0, z1, d):
        """벽에 붙은 사다리. d = 사다리에서 벽 쪽(올라가서 내리는 쪽)."""
        dx, dy = DIRS[d]; px, py = -dy, dx
        for s in (-1, 1): self.vis("gunmetal", (0.05, 0.05, z1 - z0 + 1.0), (x + px * 0.22 * s, y + py * 0.22 * s, (z0 + z1 + 1.0) / 2))
        for k in range(int((z1 - z0 + 0.8) / 0.3)):
            self.vis("gunmetal", (0.44, 0.03, 0.03) if px else (0.03, 0.44, 0.03), (x, y, z0 + 0.3 + 0.3 * k))
        for zz in (z0 + 1.2, (z0 + z1) / 2, z1 - 0.3):     # 벽에 고정하는 받침
            self.vis("gunmetal", (0.2, 0.5, 0.04) if dx else (0.5, 0.2, 0.04), (x + dx * 0.1, y + dy * 0.1, zz))
        self.col.append({"type": "ladder", "pos": [x, y, (z0 + z1 + 1.0) / 2], "size": [0.5 if px else 0.1, 0.5 if py else 0.1, z1 - z0 + 1.0]})
        self.portals.append(((x - dx * 0.6, y - dy * 0.6, z0), (x + dx * 0.7, y + dy * 0.7, z1)))
    def roof(self, z, gaps=None, holes=(), h=0.9):
        """옥상 바닥과 난간벽. gaps = {'front': [(시작, 너비)], ...} 사다리가 닿는 곳은 난간벽을 비운다."""
        W, Dp = self.W, self.D; self.slab(TW, TW, W - TW, Dp - TW, z, holes, "concrete_dark"); g = gaps or {}
        for side, ax, c, a, b in (("front", "x", TW / 2, 0, W), ("back", "x", Dp - TW / 2, 0, W), ("left", "y", TW / 2, TW, Dp - TW), ("right", "y", W - TW / 2, TW, Dp - TW)):
            self.wall(ax, c, a, b, z, h, [(p, w, 0.0, h, "open") for p, w in g.get(side, ())], self.wm, out=(-1 if side in ("front", "left") else 1), base=False)
            cur = a
            for p, w in sorted(g.get(side, ())) + [(b, 0)]:
                self._seg(ax, c, cur, p, z + h, 0.05, "gunmetal", TW + 0.08, False); cur = p + w
    def rail(self, ax, c, a, b, z, h=1.0):
        """난간: 충돌은 얇은 판 하나, 보이는 것은 손잡이와 기둥."""
        if ax == "x": self.solid((b - a, 0.06, h), ((a + b) / 2, c, z + h / 2), "rail")
        else: self.solid((0.06, b - a, h), (c, (a + b) / 2, z + h / 2), "rail")
        for zz in (z + h - 0.025, z + h * 0.5): self._seg(ax, c, a, b, zz - 0.02, 0.04, "gunmetal", 0.04, False)
        n = max(1, round((b - a) / 1.0))
        for i in range(n + 1): u = a + (b - a) * i / n; self._seg(ax, c, u - 0.02, u + 0.02, z, h, "gunmetal", 0.04, False)
    def lamp(self, x, y, z):
        self.vis("lamp", (0.7, 0.16, 0.04), (x, y, z - 0.03)); self.vis("dark", (0.8, 0.24, 0.03), (x, y, z - 0.012)); self.lights.append({"pos": [x, y, z - 0.1], "kind": "ceiling"})
    # --- 가구(엄폐물)와 아이템 자리. ax = 긴 쪽의 방향, f = 앞(사람이 서는 쪽)의 방향(+1 또는 -1)
    def part(self, mat, x, y, z, ax, u, v, w, su, sv, sz):
        px, py = (x + u, y + v) if ax == "x" else (x + v, y + u); self.vis(mat, (su, sv, sz) if ax == "x" else (sv, su, sz), (px, py, z + w))
    def body(self, x, y, z, ax, su, sv, sz): self.solid((su, sv, sz) if ax == "x" else (sv, su, sz), (x, y, z + sz / 2))
    def loot(self, x, y, z, kind="floor"): self.loots.append({"pos": [x, y, z], "kind": kind})
    def lootp(self, x, y, z, ax, u, v, w, kind):
        px, py = (x + u, y + v) if ax == "x" else (x + v, y + u); self.loot(px, py, z + w, kind)
    def crate(self, x, y, z, s=0.9, mat="paint_yellow", loot=True):
        self.box(mat, (s, s, s), (x, y, z + s / 2))
        for w in (0.07, s - 0.07): self.vis("dark", (s + 0.03, s + 0.03, 0.06), (x, y, z + w))
        if loot: self.loot(x, y, z + s, "crate_top")
    def table(self, x, y, z, w=1.4, d=0.8, ax="x", loot=True):
        self.part("wood", x, y, z, ax, 0, 0, 0.745, w, d, 0.05)
        for su in (-1, 1):
            for sv in (-1, 1): self.part("gunmetal", x, y, z, ax, su * (w / 2 - 0.06), sv * (d / 2 - 0.06), 0.36, 0.05, 0.05, 0.72)
        self.body(x, y, z, ax, w, d, 0.77)
        if loot: self.loot(x, y, z + 0.79, "table")
    def desk(self, x, y, z, ax="x", f=1):
        """책상 + 화면 + 의자. f = 앉는 쪽."""
        self.table(x, y, z, 1.4, 0.7, ax, False); self.part("dark", x, y, z, ax, 0, -f * 0.2, 0.83, 0.06, 0.06, 0.12); self.part("dark", x, y, z, ax, 0, -f * 0.2, 1.07, 0.62, 0.04, 0.38)
        self.part("screen", x, y, z, ax, 0, -f * 0.2 + f * 0.022, 1.07, 0.56, 0.01, 0.32)
        self.part("fabric", x, y, z, ax, 0, f * 0.7, 0.45, 0.45, 0.45, 0.07); self.part("fabric", x, y, z, ax, 0, f * 0.9, 0.74, 0.45, 0.05, 0.5); self.part("gunmetal", x, y, z, ax, 0, f * 0.7, 0.21, 0.06, 0.06, 0.42)
        self.lootp(x, y, z, ax, 0.45, f * 0.1, 0.79, "table")
    def shelf(self, x, y, z, ax="y", L=1.6, f=1, goods=True):
        for su in (-1, 1): self.part("gunmetal", x, y, z, ax, su * (L / 2 - 0.02), 0, 0.9, 0.04, 0.4, 1.8)
        self.part("gunmetal", x, y, z, ax, 0, -f * 0.19, 0.9, L, 0.02, 1.8); rng = np.random.default_rng(int(x * 131 + y * 17 + z * 7))
        for w in (0.06, 0.5, 0.94, 1.38, 1.78):
            self.part("gunmetal", x, y, z, ax, 0, 0, w, L - 0.08, 0.38, 0.03)
            if goods and w < 1.5:
                u = -L / 2 + 0.1
                while u < L / 2 - 0.3:
                    gw, gh = rng.uniform(0.16, 0.34), rng.uniform(0.14, 0.34)
                    if rng.random() < 0.75: self.part(str(rng.choice(["goods_a", "goods_b", "goods_c", "paint_teal", "titan", "dark"])), x, y, z, ax, u + gw / 2, f * 0.02, w + 0.015 + gh / 2, gw, 0.26, gh)
                    u += gw + rng.uniform(0.03, 0.14)
        self.body(x, y, z, ax, L, 0.4, 1.8); self.lootp(x, y, z, ax, 0, f * 0.5, 0.02, "by_shelf")
    def counter(self, x, y, z, ax="x", L=2.4, mat="paint_teal"):
        self.part(mat, x, y, z, ax, 0, 0, 0.475, L, 0.55, 0.95); self.part("gunmetal", x, y, z, ax, 0, 0, 0.975, L + 0.06, 0.66, 0.05); self.part("dark", x, y, z, ax, 0, 0, 0.05, L + 0.01, 0.56, 0.1)
        self.body(x, y, z, ax, L, 0.6, 1.0); self.loot(x, y, z + 1.02, "counter")
    def bed(self, x, y, z, ax="y", head=-1):
        self.part("dark", x, y, z, ax, 0, 0, 0.125, 2.0, 0.95, 0.25); self.part("mattress", x, y, z, ax, 0, 0, 0.34, 1.94, 0.9, 0.18); self.part("mattress", x, y, z, ax, head * 0.75, 0, 0.48, 0.35, 0.6, 0.1)
        self.part("cloth", x, y, z, ax, -head * 0.4, 0, 0.445, 1.1, 0.92, 0.03); self.part("dark", x, y, z, ax, head * 0.99, 0, 0.4, 0.04, 0.95, 0.8)
        self.body(x, y, z, ax, 2.0, 0.95, 0.45); self.lootp(x, y, z, ax, -head * 0.3, 0, 0.47, "bed")
    def sofa(self, x, y, z, ax="x", f=1):
        self.part("fabric", x, y, z, ax, 0, 0, 0.21, 1.8, 0.8, 0.42); self.part("fabric", x, y, z, ax, 0, -f * 0.29, 0.425, 1.8, 0.22, 0.85)
        for su in (-1, 1): self.part("fabric", x, y, z, ax, su * 0.8, 0, 0.3, 0.2, 0.8, 0.6)
        self.body(x, y, z, ax, 1.8, 0.8, 0.85); self.lootp(x, y, z, ax, 0.3, f * 0.1, 0.44, "sofa")
    def locker(self, x, y, z, ax="x", n=3, f=1, mat="paint_teal"):
        for i in range(n):
            u = (i - (n - 1) / 2) * 0.44
            self.part(mat, x, y, z, ax, u, 0, 0.95, 0.42, 0.5, 1.9); self.part("dark", x, y, z, ax, u, f * 0.252, 1.6, 0.26, 0.01, 0.1); self.part("gunmetal", x, y, z, ax, u + 0.14, f * 0.26, 1.0, 0.03, 0.03, 0.12)
        self.body(x, y, z, ax, n * 0.44, 0.5, 1.9); self.lootp(x, y, z, ax, 0, f * 0.6, 0.02, "by_locker")
    def rack(self, x, y, z, ax="y", f=1):
        """서버 장비함. 앞면에 작은 불빛."""
        self.part("dark", x, y, z, ax, 0, 0, 1.0, 0.7, 0.9, 2.0)
        for k in range(8): self.part("screen", x, y, z, ax, 0.1 * ((k * 3) % 5 - 2), f * 0.452, 0.3 + 0.2 * k, 0.22, 0.01, 0.02)
        self.body(x, y, z, ax, 0.7, 0.9, 2.0)
    def unit(self, x, y, z, s=1.2):
        """옥상 설비(환기 장치). 엄폐물."""
        self.box("titan", (s, s, s * 0.75), (x, y, z + s * 0.375)); self.vis("dark", (s * 0.7, s * 0.7, 0.05), (x, y, z + s * 0.75 + 0.015))
        self.vis("dark", (s * 0.8, 0.02, s * 0.4), (x, y - s / 2 - 0.008, z + s * 0.4)); self.vis("gunmetal", (s + 0.06, s + 0.06, 0.08), (x, y, z + 0.04))
    def container(self, x, y, z, ax="y", L=5.0, mat="paint_teal"):
        self.box(mat, (L, 2.4, 2.5) if ax == "x" else (2.4, L, 2.5), (x, y, z + 1.25)); n = int(L / 0.5)
        for i in range(n):
            for sv in (-1, 1): self.part("dark", x, y, z, ax, -L / 2 + 0.25 + i * 0.5, sv * 1.205, 1.25, 0.05, 0.02, 2.3)
        for su in (-1, 1):
            for sv in (-0.6, 0.6): self.part("gunmetal", x, y, z, ax, su * (L / 2 + 0.01), sv, 1.25, 0.03, 0.05, 2.3)
    # --- 바깥 장식 (보이기만 한다)
    def _side(self, side, pos, off): return {"front": (pos, -off), "back": (pos, self.D + off), "left": (-off, pos), "right": (self.W + off, pos)}[side]
    def ac(self, side, pos, z):
        fb = side in ("front", "back"); x, y = self._side(side, pos, 0.21); self.vis("titan", (0.8, 0.42, 0.55) if fb else (0.42, 0.8, 0.55), (x, y, z))
        x, y = self._side(side, pos, 0.425); self.vis("dark", (0.5, 0.02, 0.4) if fb else (0.02, 0.5, 0.4), (x, y, z))
        x, y = self._side(side, pos, 0.2); self.vis("gunmetal", (0.7, 0.4, 0.04) if fb else (0.4, 0.7, 0.04), (x, y, z - 0.3))
    def pipe(self, side, pos, z0, z1, r=0.09):
        x, y = self._side(side, pos, r / 2 + 0.01); self.vis("gunmetal", (r, r, z1 - z0), (x, y, (z0 + z1) / 2))
        for zz in np.arange(z0 + 0.6, z1, 1.5):
            fb = side in ("front", "back"); self.vis("dark", (r + 0.06, r + 0.03, 0.05) if fb else (r + 0.03, r + 0.06, 0.05), (x, y, float(zz)))
    def sign(self, side, pos, z, w, h, mat="win_pink"):
        """빛나는 간판(글자 없음: 막대 무늬)."""
        fb = side in ("front", "back"); x, y = self._side(side, pos, 0.06); self.vis("dark", (w + 0.12, 0.12, h + 0.12) if fb else (0.12, w + 0.12, h + 0.12), (x, y, z))
        x, y = self._side(side, pos, 0.125)
        for u, bw in ((-0.25, 0.42), (0.14, 0.24), (0.36, 0.12)):
            self.vis(mat, (w * bw, 0.02, h * 0.5) if fb else (0.02, w * bw, h * 0.5), ((x + w * u, y, z) if fb else (x, y + w * u, z)))
        lx, ly = self._side(side, pos, 0.5); self.lights.append({"pos": [lx, ly, z], "kind": "sign"})
    def awning(self, pos, w, z, depth=1.1, mat="cloth"):
        """앞면 가게 위의 차양."""
        if self.cut is not None and z > self.cut: return
        ang = degrees(atan2(0.32, depth)); self.m.setdefault(mat, Multi()).add(w, (depth ** 2 + 0.32 ** 2) ** 0.5, 0.04, T(pos + w / 2, -depth / 2, z - 0.16) @ RX(ang))
        for u in (pos + 0.05, pos + w - 0.05): self.obox("gunmetal", (0.03, 0.03), Vector((u, 0, z - 0.75)), Vector((u, -depth, z - 0.34)))
    # --- 걸어서 갈 수 있는지 검사
    def reach(self, cell=0.1, rad=0.3):
        R = max(2, round(0.45 / cell))
        pad = 3.0; nx, ny = int((self.W + 2 * pad) / cell), int((self.D + 2 * pad) / cell); lv = sorted(self.levels)
        ix = lambda x: int((x + pad) / cell); iy = lambda y: int((y + pad) / cell)
        free, sup = [], []
        for z in lv:
            b = np.zeros((nx, ny), bool); s = np.ones((nx, ny), bool) if z == 0 else np.zeros((nx, ny), bool)
            for c in self.col:
                if c["type"] != "box": continue
                p, q = c["pos"], c["size"]
                if p[2] + q[2] / 2 > z + 0.35 and p[2] - q[2] / 2 < z + 1.7:
                    b[max(0, ix(p[0] - q[0] / 2 - rad)):ix(p[0] + q[0] / 2 + rad) + 1, max(0, iy(p[1] - q[1] / 2 - rad)):iy(p[1] + q[1] / 2 + rad) + 1] = True
            for sz, a0, b0, a1, b1 in self.slabs:
                if abs(sz - z) < 1e-6: s[ix(a0):ix(a1) + 1, iy(b0):iy(b1) + 1] = True
            free.append(~b & s); sup.append(s)
        li = lambda z: min(range(len(lv)), key=lambda k: abs(lv[k] - z))
        seen = [np.zeros((nx, ny), bool) for _ in lv]; todo = [(0, ix(self.W / 2), iy(-2.0))]
        ports = [((li(a[2]), ix(a[0]), iy(a[1])), (li(b[2]), ix(b[0]), iy(b[1]))) for a, b in self.portals]
        def near(k, i, j, r=R):   # 계단 발치·머리 둘레에 닿은 칸이 있는가
            return seen[k][max(0, i - r):i + r + 1, max(0, j - r):j + r + 1].any()
        def freecell(k, i, j, r=R):
            sub = free[k][max(0, i - r):i + r + 1, max(0, j - r):j + r + 1]; w = np.argwhere(sub)
            return None if len(w) == 0 else (k, max(0, i - r) + int(w[0][0]), max(0, j - r) + int(w[0][1]))
        changed = True
        while changed:
            while todo:
                k, i, j = todo.pop()
                if i < 0 or j < 0 or i >= nx or j >= ny or seen[k][i, j] or not free[k][i, j]: continue
                seen[k][i, j] = True; todo += [(k, i + 1, j), (k, i - 1, j), (k, i, j + 1), (k, i, j - 1)]
            changed = False
            for a, b in ports:
                for s0, s1 in ((a, b), (b, a)):
                    if near(*s0):
                        f = freecell(*s1)
                        if f and not seen[f[0]][f[1], f[2]]: todo.append(f); changed = True
        bad = []
        for l in self.loots:
            k = li(max(z for z in lv if z <= l["pos"][2] + 0.05)); i, j = ix(l["pos"][0]), iy(l["pos"][1]); r = int(1.0 / cell)
            if not seen[k][max(0, i - r):i + r + 1, max(0, j - r):j + r + 1].any(): bad.append(l)
        area = [round(float((seen[k] & sup[k]).sum() * cell * cell if lv[k] > 0 else (seen[k][ix(0):ix(self.W), iy(0):iy(self.D)]).sum() * cell * cell), 1) for k in range(len(lv))]
        return bad, area
    # --- 내보내기
    def finish(self):
        sh = T(-self.W / 2, -self.D / 2, 0)
        for mat, mm in self.m.items():
            o = mm.done(self.name + "_" + mat, mat)
            if o: o.data.transform(sh)
        for i, dr in enumerate(self.doors):
            w, h = dr["width"], dr["height"]; hx, hy, hz = dr["hinge"]; ax = dr["along"]
            if self.cut is not None and hz > self.cut: continue
            hh = h if self.cut is None else min(h, self.cut - hz); dm, hm = Multi(), Multi(); o3 = lambda u, v, zz: T(hx + u, hy + v, hz + zz) if ax == "x" else T(hx + v, hy + u, hz + zz)
            sz = lambda su, sv, s3: (su, sv, s3) if ax == "x" else (sv, su, s3)
            dm.add(*sz(w - 0.05, 0.05, hh - 0.04), o3(w / 2, 0, hh / 2)); hm.add(*sz(w - 0.12, 0.062, 0.22), o3(w / 2, 0, 0.16)); hm.add(*sz(0.04, 0.14, 0.14), o3(w - 0.14, 0, 1.05))
            hm.add(*sz(w * 0.5, 0.062, 0.05), o3(w / 2, 0, min(1.62, hh - 0.2)))
            for mm, mat in ((dm, self.dm), (hm, "gunmetal")):
                o = mm.done(f"door_{i}_{mat}", mat, part=f"door_{i}"); o.data.transform(sh)
            kit.pivot(f"door_{i}", (hx - self.W / 2, hy - self.D / 2, hz + h / 2), (0, 0, 1), self.name, f"door_{i}", (0, 100))
        mv = lambda p: [round(p[0] - self.W / 2, 3), round(p[1] - self.D / 2, 3), round(p[2], 3)]
        cols = []
        for c in self.col:
            c = dict(c)
            for k in ("pos", "from", "to"):
                if k in c: c[k] = mv(c[k])
            if "size" in c: c["size"] = [round(v, 3) for v in c["size"]]
            cols.append(c)
        return {"size_m": [self.W, self.D, round(max(self.levels), 2)], "levels_m": sorted(self.levels), "colliders": cols,
                "loot": [{"pos": mv(l["pos"]), "kind": l["kind"]} for l in self.loots], "doors": [{"hinge": mv(d["hinge"]), "along": d["along"], "width": d["width"], "height": d["height"]} for d in self.doors],
                "glass": [{"pos": mv(g["pos"]), "size": g["size"]} for g in self.glass], "lights": [{"pos": mv(l["pos"]), "kind": l["kind"]} for l in self.lights], "origin": "바닥 가운데, 앞(정문) = -Y"}

# ---------------------------------------------------------------- 건물 6종
def shack(cut=None):
    """판잣집: 골진 금속 벽, 방 둘, 옥상."""
    b = Bld("shack", 6.0, 5.0, "shutter", "plaster", cut, "door_red", False); H = 2.8; IH = H - 0.25
    b.shell(0, H, front=[D(0.8), Wn(3.9, 1.2)], back=[Wn(1.2, 1.2)], left=[Wn(1.8, 1.0)], right=[D(3.2)])
    b.wall("y", 3.5, TW, 5.0 - TW, 0, IH, [G(1.2, 1.1)], b.im, 0.12)
    b.table(1.5, 4.1, 0, 1.3, 0.7); b.shelf(0.5, 0.85, 0, "y", 1.0); b.sofa(2.6, 0.75, 0, "x", 1); b.bed(5.25, 1.4, 0); b.crate(4.2, 4.3, 0, 0.7, "paint_yellow"); b.locker(5.45, 2.9, 0, "y", 1, -1, "paint_teal")
    b.loot(2.4, 2.6, 0.02); b.lamp(1.8, 2.5, IH); b.lamp(4.7, 2.5, IH)
    b.roof(H, gaps={"left": [(3.4, 0.9)]}, h=0.5); b.ladder(-0.2, 3.85, 0, H, "+x"); b.crate(4.6, 1.2, H, 0.8, "paint_teal"); b.unit(1.7, 1.5, H, 1.0); b.loot(2.4, 3.6, H + 0.02)
    b.ac("back", 4.2, 1.9); b.pipe("right", 0.5, 0, H + 0.5); b.pipe("back", 5.4, 0, H); b.sign("front", 4.5, H + 0.05, 1.6, 0.5, "win_warm")
    return b

def rowhouse(cut=None):
    """연립 주택: 2층, 안쪽 계단, 뒤쪽 사다리로 옥상."""
    b = Bld("rowhouse", 6.0, 9.0, "concrete_dark", "plaster", cut, "door_teal"); H = 3.0; IH = H - 0.25
    hole = (TW, 5.1, 1.55, 7.3)
    for k in (0, 1):
        z = k * H
        b.shell(z, H, front=[D(0.7), Wn(3.5, 1.6)] if k == 0 else [Wn(0.9), Wn(3.6)], back=[Wn(3.2)] + ([D(1.9)] if k == 0 else []), left=[Wn(2.2, 1.0)], right=[Wn(1.6), Wn(6.2)])
        if k: b.slab(TW, TW, 6.0 - TW, 9.0 - TW, z, [hole])
        b.lamp(3.0, 2.5, z + IH); b.lamp(3.6, 7.0, z + IH)
    b.wall("x", 5.0, TW, 6.0 - TW, 0, IH, [G(3.9, 1.2)], b.im, 0.12)
    b.stair(0.875, 8.1, 0, H, "-y", 1.1, 3.0)
    b.table(4.3, 1.5, 0, 1.3, 0.7); b.sofa(2.3, 4.5, 0, "x", -1); b.shelf(5.5, 3.6, 0, "y", 1.4, -1); b.counter(4.4, 8.35, 0, "x", 2.0); b.crate(2.4, 6.2, 0, 0.7, "paint_red"); b.loot(2.2, 2.6, 0.02)
    b.wall("x", 4.4, 1.6, 6.0 - TW, H, IH, [G(2.6, 1.1)], b.im, 0.12); b.rail("y", 1.6, 5.1, 7.3, H); b.rail("x", 7.3, TW, 1.6, H)
    b.bed(4.8, 1.5, H); b.desk(2.4, 0.75, H, "x", 1); b.bed(4.8, 7.4, H); b.shelf(2.4, 8.5, H, "x", 1.2, -1); b.locker(5.45, 5.2, H, "y", 2, -1, "paint_red"); b.loot(3.0, 6.0, H + 0.02)
    b.roof(2 * H, gaps={"back": [(4.95, 0.9)]}); b.ladder(5.4, 9.2, 0, 2 * H, "-y"); b.crate(1.4, 2.0, 2 * H, 0.9, "paint_teal"); b.unit(4.2, 3.4, 2 * H, 1.1); b.loot(3.0, 6.5, 2 * H + 0.02)
    b.ac("front", 1.6, H + 0.55); b.ac("right", 4.4, H + 0.6); b.ac("right", 4.4, 0.9); b.pipe("front", 5.8, 0, 2 * H + 0.9); b.pipe("left", 6.2, 0, 2 * H); b.sign("front", 2.6, H - 0.15, 0.5, 1.4, "win_pink")
    return b

def shop(cut=None):
    """가게: 큰 진열창, 뒷방, 옥상."""
    b = Bld("shop", 8.0, 7.0, "concrete", "plaster", cut, "door_yellow"); H = 3.4; IH = H - 0.25
    b.shell(0, H, front=[BIG(0.6, 3.8), D(5.6, 1.2)], back=[D(6.2)], left=[Wn(5.2, 1.0)], right=[Wn(1.4)])
    b.wall("x", 4.6, TW, 8.0 - TW, 0, IH, [G(0.9, 1.1)], b.im, 0.12)
    b.counter(5.5, 3.6, 0, "x", 2.6, "paint_red"); b.shelf(0.5, 2.3, 0, "y", 2.2); b.shelf(3.4, 1.9, 0, "y", 1.6); b.shelf(2.9, 4.3, 0, "x", 1.6, -1); b.table(1.9, 1.0, 0, 1.0, 0.6)
    b.shelf(3.6, 6.5, 0, "x", 2.0, -1); b.crate(6.9, 5.4, 0, 0.8, "paint_red"); b.crate(1.0, 5.6, 0, 0.7); b.locker(5.2, 6.45, 0, "x", 2, -1); b.loot(4.4, 5.5, 0.02); b.loot(4.6, 2.2, 0.02)
    b.lamp(2.4, 2.4, IH); b.lamp(5.8, 2.4, IH); b.lamp(4.0, 5.7, IH)
    b.roof(H, gaps={"right": [(4.6, 0.9)]}); b.ladder(8.2, 5.05, 0, H, "-x"); b.crate(2.0, 2.2, H, 1.0, "paint_teal"); b.unit(5.6, 2.0, H, 1.2); b.loot(5.2, 4.6, H + 0.02)
    b.awning(0.4, 4.2, 3.05); b.sign("front", 2.5, H + 0.42, 3.4, 0.6, "win_pink"); b.ac("left", 2.4, 2.4); b.pipe("left", 6.6, 0, H + 0.9); b.pipe("back", 0.5, 0, H)
    return b

def apartment(cut=None):
    """아파트: 3층, 층마다 가운데 복도와 양쪽 집, 가운데 계단, 뒤쪽 사다리."""
    b = Bld("apartment", 12.0, 10.0, "concrete", "plaster", cut, "door_teal"); H = 3.0; n = 3; IH = H - 0.25
    hole = (4.75, 5.6, 6.15, 7.75)
    for k in range(n):
        z = k * H
        b.shell(z, H, front=([Wn(1.6), G(5.45, 1.1), Wn(9.0)] if k == 0 else [Wn(1.6), Wn(5.3), Wn(9.0)]), back=[Wn(1.6), Wn(8.6)] + ([D(6.2, 1.0)] if k == 0 else []), left=[Wn(1.6), Wn(6.6)], right=[Wn(1.6), Wn(6.6)])
        if k: b.slab(TW, TW, 12.0 - TW, 10.0 - TW, z, [hole])
        b.wall("y", 4.6, TW, 10.0 - TW, z, IH, [D(1.6), D(8.6, 1.0)], b.im, 0.14)      # 뒤쪽 문은 계단 발치의 층계참으로 난다
        b.wall("y", 7.4, TW, 10.0 - TW, z, IH, [D(1.6), D(6.9)], b.im, 0.14)
        b.wall("x", 5.0, TW, 4.6, z, IH, [G(2.9, 1.0)], b.im, 0.12); b.wall("x", 5.0, 7.4, 12.0 - TW, z, IH, [G(8.1, 1.0)], b.im, 0.12)
        b.stair(5.45, 8.6, z, z + H, "-y", 1.2, 3.0)
        if k: b.rail("y", 6.15, 5.6, 7.75, z); b.rail("x", 7.75, 4.75, 6.15, z)
        b.bed(1.0, 1.6, z); b.table(2.7, 0.75, z, 1.2, 0.6); b.sofa(1.6, 5.6, z, "x", 1); b.shelf(0.9, 9.5, z, "x", 1.0, -1); b.crate(4.0, 7.2, z, 0.7, "paint_red", k != 1)
        b.bed(11.0, 8.2, z); b.desk(9.7, 0.75, z, "x", 1); b.shelf(11.5, 3.9, z, "y", 1.4, -1); b.counter(9.3, 9.4, z, "x", 1.8, "paint_yellow" if k % 2 else "paint_teal"); b.locker(11.45, 5.7, z, "y", 2, -1, "paint_red")
        b.loot(2.4, 7.4, z + 0.02); b.loot(6.7, 3.0, z + 0.02)
        for lx, ly in ((2.4, 2.5), (2.4, 7.5), (9.6, 2.5), (9.6, 7.5), (6.0, 2.5), (6.7, 8.6)): b.lamp(lx, ly, z + IH)
    b.crate(5.45, 6.3, 0, 0.8, "paint_yellow")                                      # 계단 밑
    b.roof(n * H, gaps={"back": [(10.55, 0.9)]}, holes=[hole]); b.rail("y", 6.15, 5.6, 7.75, n * H); b.rail("x", 7.75, 4.75, 6.15, n * H); b.rail("y", 4.75, 5.6, 7.75, n * H)
    b.ladder(11.0, 10.2, 0, n * H, "-y"); b.crate(2.0, 2.0, n * H, 1.0, "paint_teal"); b.crate(9.6, 6.6, n * H, 0.9, "paint_yellow"); b.unit(9.0, 2.2, n * H, 1.4); b.unit(2.4, 7.6, n * H, 1.2); b.loot(3.0, 5.0, n * H + 0.02)
    for k in (1, 2):
        b.ac("front", 3.5, k * H + 0.6); b.ac("front", 8.4, k * H + 0.6); b.ac("left", 4.2, k * H + 0.6); b.ac("right", 4.2, k * H + 0.6)
    b.pipe("front", 0.3, 0, n * H + 0.9); b.pipe("front", 11.7, 0, n * H + 0.9); b.pipe("left", 9.6, 0, n * H); b.sign("front", 6.0, H - 0.05, 2.2, 0.45, "win_cool"); b.sign("front", 11.2, 2 * H, 0.5, 2.6, "win_pink")
    return b

def warehouse(cut=None):
    """창고: 높은 한 칸, 큰 문, 뒤쪽 위층 발판(메자닌), 컨테이너와 상자."""
    b = Bld("warehouse", 16.0, 12.0, "shutter", "plaster", cut, "door_yellow", False); H = 6.0; M = 3.0
    b.shell(0, H, front=[G(5.0, 6.0, 4.2)], back=[D(13.0)], left=[D(2.0), BIG(6.0, 2.0, 1.2, 3.2)], right=[BIG(3.0, 2.0, 1.2, 3.2), BIG(7.4, 2.0, 1.2, 3.2)])
    b.slab(TW, 8.0, 16.0 - TW, 12.0 - TW, M, mat="tread", t=0.2); b.stair(2.0, 4.6, 0, M, "+y", 1.3, 3.4)
    b.rail("x", 8.0, TW, 1.3, M); b.rail("x", 8.0, 2.7, 16.0 - TW, M)
    for x in (4.0, 8.0, 12.0): b.box("gunmetal", (0.25, 0.25, M - 0.2), (x, 8.1, (M - 0.2) / 2))
    for x, y, s, m in ((5.0, 2.6, 1.2, "paint_yellow"), (6.3, 2.8, 1.0, "paint_red"), (10.4, 5.6, 1.4, "paint_teal"), (8.2, 6.6, 1.0, "paint_red"), (4.4, 6.4, 1.1, "paint_teal")): b.crate(x, y, 0, s, m, s < 1.3)
    b.crate(5.0, 2.6, 1.2, 0.9, "paint_red", False); b.container(13.6, 3.4, 0, "y", 5.0, "paint_teal"); b.crate(13.4, 7.0, 0, 1.0, "paint_yellow")
    b.shelf(15.4, 9.8, 0, "y", 2.4, -1); b.shelf(6.0, 11.4, 0, "x", 2.4, -1); b.shelf(9.0, 11.4, 0, "x", 2.4, -1); b.table(10.6, 9.6, 0); b.locker(0.55, 10.2, 0, "y", 3, 1, "paint_red")
    b.loot(3.2, 10.2, 0.02); b.loot(8.0, 1.4, 0.02); b.loot(10.4, 4.3, 0.02); b.loot(11.6, 2.4, 0.02)
    b.crate(6.0, 10.6, M, 0.9, "paint_yellow"); b.crate(12.6, 10.8, M, 1.0, "paint_teal"); b.desk(9.4, 10.9, M, "x", -1); b.shelf(15.4, 10.2, M, "y", 2.0, -1); b.loot(3.4, 9.6, M + 0.02); b.loot(14.2, 8.8, M + 0.02)
    for lx in (4.0, 8.0, 12.0):
        b.lamp(lx, 4.0, H - 0.25); b.lamp(lx, 10.0, H - 0.25); b.lamp(lx, 10.0, M - 0.2)
    b.roof(H, gaps={"right": [(10.55, 0.9)]}, h=0.6); b.ladder(16.2, 11.0, 0, H, "-x"); b.unit(4.0, 4.0, H, 1.5); b.unit(11.0, 8.0, H, 1.3); b.crate(7.6, 3.0, H, 1.0, "paint_yellow"); b.loot(8.0, 6.0, H + 0.02)
    b.sign("front", 8.0, 5.0, 4.4, 0.7, "win_cool"); b.pipe("front", 0.4, 0, H + 0.6); b.pipe("front", 15.6, 0, H + 0.6); b.pipe("left", 10.0, 0, H); b.ac("left", 4.6, 2.6); b.ac("back", 5.0, 4.4)
    return b

def office(cut=None):
    """사무실: 4층, 뒤쪽 왼편 계단실, 층마다 열린 사무 공간과 회의실."""
    b = Bld("office", 14.0, 12.0, "concrete", "plaster", cut, "door_teal"); H = 3.4; n = 4; IH = H - 0.25
    hole = (0.3, 7.8, 1.75, 10.35)
    for k in range(n):
        z = k * H
        fr = [BIG(1.0, 3.0), G(6.0, 2.0, 2.4), BIG(9.6, 3.2)] if k == 0 else [BIG(1.0, 3.0, 1.6, 0.9), BIG(5.4, 3.0, 1.6, 0.9), BIG(9.8, 3.0, 1.6, 0.9)]
        b.shell(z, H, front=fr, back=[BIG(4.6, 3.0, 1.6, 0.9), BIG(9.6, 3.0, 1.6, 0.9)] + ([D(1.85, 1.0)] if k == 0 else []), left=[BIG(1.6, 3.0, 1.6, 0.9)], right=[BIG(1.6, 3.0, 1.6, 0.9), BIG(7.0, 3.0, 1.6, 0.9)])
        if k: b.slab(TW, TW, 14.0 - TW, 12.0 - TW, z, [hole])
        b.wall("x", 7.0, TW, 3.0, z, IH, (), b.im, 0.14); b.wall("y", 3.0, 7.0, 12.0 - TW, z, IH, [D(7.25)], b.im, 0.14)      # 계단실
        b.stair(1.0, 11.2, z, z + H, "-y", 1.2, 3.4)
        if k: b.rail("y", 1.75, 7.8, 10.35, z); b.rail("x", 10.35, 0.3, 1.75, z)
        b.wall("y", 9.0, TW, 5.0, z, IH, [G(1.6, 1.1)], b.im, 0.12); b.wall("x", 5.0, 9.0, 14.0 - TW, z, IH, (), b.im, 0.12)     # 회의실
        b.table(11.5, 2.6, z, 2.4, 1.1); b.shelf(12.6, 4.7, z, "x", 1.6, -1); b.shelf(0.5, 5.8, z, "y", 1.6); b.shelf(8.6, 11.45, z, "x", 1.6, -1)
        if k == 0:
            b.counter(7.0, 4.4, z, "x", 3.0, "paint_teal"); b.sofa(0.75, 3.0, z, "y", 1); b.sofa(3.6, 0.75, z, "x", 1); b.locker(5.2, 11.4, z, "x", 4, -1, "paint_red"); b.table(11.0, 8.4, z, 1.6, 0.9)
        else:
            for dx_, dy_, f in ((4.4, 1.2, 1), (6.4, 1.2, 1), (4.4, 4.0, -1), (6.4, 4.0, -1), (5.6, 9.2, 1), (10.6, 7.6, 1), (10.6, 9.6, -1)): b.desk(dx_, dy_, z, "x", f)
            if k >= 2: b.rack(13.2, 6.2, z, "y", -1); b.rack(13.2, 7.0, z, "y", -1)
        b.crate(12.8, 10.9, z, 0.7, "paint_yellow", k % 2 == 0); b.loot(8.0, 6.2, z + 0.02); b.loot(2.4, 8.4, z + 0.02)
        for lx, ly in ((3.6, 2.6), (7.0, 2.6), (11.4, 2.6), (6.0, 8.0), (11.0, 9.0), (2.4, 9.5)): b.lamp(lx, ly, z + IH)
    b.roof(n * H, holes=[hole]); b.rail("y", 1.75, 7.8, 10.35, n * H); b.rail("x", 10.35, 0.3, 1.75, n * H)
    for x, y, s in ((5.0, 3.0, 1.5), (9.0, 3.4, 1.2), (10.6, 8.4, 1.6)): b.unit(x, y, n * H, s)
    b.crate(6.0, 9.6, n * H, 1.0, "paint_teal"); b.loot(12.0, 5.0, n * H + 0.02)
    for k in (1, 2, 3): b.ac("back", 8.6, k * H + 0.5); b.ac("right", 5.8, k * H + 0.5)
    b.pipe("front", 0.3, 0, n * H + 0.9); b.pipe("front", 13.7, 0, n * H + 0.9); b.pipe("back", 3.6, 0, n * H); b.sign("front", 7.0, H - 0.1, 3.0, 0.5, "win_cool"); b.sign("front", 0.6, 2.6 * H, 0.5, 3.4, "win_warm")
    return b

KINDS = {"shack": shack, "rowhouse": rowhouse, "shop": shop, "apartment": apartment, "warehouse": warehouse, "office": office}

def stage(fn, cut=None):
    kit.reset(); mats(True); b = fn(cut) if cut is not None else fn(); b.finish()
    finish("stage_ground", box(90, 90, 0.2), "sidewalk", 0, 1, T(0, 0, -0.1), smooth=False)
    for i, l in enumerate(b.lights):          # 확인 그림용 조명(게임에서는 lights 목록 자리에 조명을 단다)
        if cut is not None and l["pos"][2] > cut: continue
        ld = bpy.data.lights.new(f"L{i}", "POINT"); ld.energy = {"ceiling": 45, "door": 14, "sign": 25}[l["kind"]]; ld.color = (1.0, 0.80, 0.58); ld.shadow_soft_size = 0.15
        lo = bpy.data.objects.new(f"L{i}", ld); kit.COL.objects.link(lo); lo.location = (l["pos"][0] - b.W / 2, l["pos"][1] - b.D / 2, l["pos"][2])
    return b

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); street.OUT = OUT
    for name, fn in KINDS.items():
        if ONLY and name not in ONLY: continue
        kit.reset(); mats(); b = fn(); bad, area = b.reach()
        if bad: raise RuntimeError(f"{name}: 걸어서 갈 수 없는 아이템 자리 {len(bad)}곳: {[(l['kind'], [round(v, 2) for v in l['pos']]) for l in bad][:6]}")
        info = b.finish(); info["walkable_m2_by_level"] = area
        if bpy.data.images: raise RuntimeError("그림이 들어갔다: " + str([i.name for i in bpy.data.images]))
        man = kit.export(OUT, "house_" + name, info)
        print(f"HOUSE {name} tris={man['triangles']} colliders={len(info['colliders'])} loot={len(info['loot'])} doors={len(info['doors'])} lights={len(info['lights'])} levels={info['levels_m']} walk={area}", flush=True)
        if RENDER:
            W, Dp, top = b.W, b.D, max(b.levels); r = max(W, Dp); lv = sorted(b.levels)
            stage(fn); street.light_and_shoot(bpy.context.scene, f"house_{name}.png", True, [], cam=((-r * 1.15, -r * 1.6, top * 0.6 + r * 0.55), (0, 0, top * 0.45), 34))
            stage(fn); street.light_and_shoot(bpy.context.scene, f"house_{name}_night.png", False, [("pool_m", (-r * 0.9, -r * 0.9, 5.0), (0, -Dp / 2, 1.5), 600, (1.0, 0.1, 0.5)), ("pool_c", (r * 0.9, -r, 5.0), (0, -Dp / 2, 1.5), 500, (0.1, 0.8, 1.0))],
                                              cam=((-r * 0.75, -r * 1.35, 1.7), (0, 0, top * 0.5), 26))
            for z in lv[:-1][:2]:
                stage(fn, z + 2.3); street.light_and_shoot(bpy.context.scene, f"house_{name}_cut{int(round(z))}.png", True, [], cam=((-r * 0.3, -r * 0.9, z + r * 1.45 + 2), (0, 0.4, z + 0.8), 34))
