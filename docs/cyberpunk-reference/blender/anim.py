"""애니메이션 클립 생성 + Blender 미리보기.
실행: python anim.py <출력폴더> clips            -> 클립 JSON과 검증용 기준값(golden) 생성 (Blender 불필요)
      python anim.py <출력폴더> preview [이름...] -> 클립을 실제 모델에 적용해 연속 사진을 찍는다

클립은 뼈대와 무관한 '의미 관절'로 적는다. 서 있는 기준 자세(앞 = -Y, 위 = +Z)에서:
  flex  앞으로 드는 각(다리·팔)      = +X축 둘레 -θ
  bend  접는 각(무릎은 뒤로, 팔꿈치는 앞으로)  무릎 = +X축 +θ, 팔꿈치 = +X축 -θ
  dorsi 발끝을 드는 각                 = +X축 -θ
  abduct 몸 바깥으로 벌리는 각         = +Y축 둘레 -θ·side (왼쪽 side=+1, 오른쪽 -1)
  yaw   왼쪽으로 도는 각               = +Z축 +θ
  pitch 앞으로 숙이는 각               = +X축 +θ
  roll  왼쪽으로 기우는 각             = +Y축 +θ
  root의 x, y, z는 골반 이동(m). 한 관절의 회전은 Rz · Rx · Ry 순서로 곱한다.
"""
import sys, os, json
from math import sin, cos, pi, exp, radians

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/anim"
MODE = ARGS[1] if len(ARGS) > 1 else "clips"
FPS = 30

def g(ph, mu, sd):
    """주기 1짜리 가우스 봉우리."""
    d = (ph - mu + 0.5) % 1.0 - 0.5
    return exp(-0.5 * (d / sd) ** 2)

def smooth(a, b, u):
    u = max(0.0, min(1.0, u)); u = u * u * (3 - 2 * u); return a + (b - a) * u

def clip(name, dur, loop, fn, speed=0.0, events=(), rig="humanoid"):
    """fn(u) -> {(joint, dof): value}, u = 0..1 진행률. 30fps로 표본을 떠서 직선 보간 키로 저장한다."""
    n = max(2, int(round(dur * FPS)) + 1); tracks = {}
    for i in range(n):
        u = i / (n - 1)
        for k, v in fn(u if not loop else (u % 1.0 if i < n - 1 else 0.0)).items():
            tracks.setdefault(k, []).append([round(u * dur, 5), round(v, 5)])
    return {"name": name, "rig": rig, "duration": dur, "loop": loop, "speed": speed, "fps": FPS,
            "tracks": [{"joint": j, "dof": d, "keys": ks} for (j, d), ks in sorted(tracks.items())],
            "events": [[round(t, 4), e] for t, e in events]}

def gait(ph, hip_amp, hip_off, knee_st, knee_sw, ank=1.0, arm=20.0, elbow=(20.0, 8.0), bob=0.018, sway=0.02, lean=3.0, twist=7.0, hip_h2=3.0):
    out = {}
    for side, s, o in (("L", 1, 0.0), ("R", -1, 0.5)):
        p = (ph + o) % 1.0; c = cos(2 * pi * p)
        out[("hip_" + side, "flex")] = hip_amp * c + hip_off + hip_h2 * cos(4 * pi * p + 0.6)
        out[("knee_" + side, "bend")] = 4 + knee_st * g(p, 0.13, 0.065) + knee_sw * g(p, 0.72, 0.085)
        out[("ankle_" + side, "dorsi")] = ank * (-6 * g(p, 0.06, 0.04) + 9 * g(p, 0.42, 0.10) - 17 * g(p, 0.63, 0.045) + 3 * g(p, 0.85, 0.08))
        out[("shoulder_" + side, "flex")] = -arm * c + 2
        out[("elbow_" + side, "bend")] = elbow[0] - elbow[1] * c
    c0 = cos(2 * pi * ph)
    out[("root", "z")] = -bob * cos(4 * pi * ph); out[("root", "x")] = sway * sin(2 * pi * ph)
    out[("root", "roll")] = -2.5 * sin(2 * pi * ph); out[("root", "yaw")] = -4.0 * c0
    out[("waist", "yaw")] = twist * c0; out[("waist", "pitch")] = lean; out[("neck", "pitch")] = -lean * 0.6
    out[("neck", "yaw")] = -(twist - 4.0) * c0
    return out

def idle(u):
    s = sin(2 * pi * u); b = sin(4 * pi * u)
    return {("root", "roll"): 1.2 * s, ("root", "x"): 0.008 * s, ("root", "z"): -0.003 + 0.003 * b, ("waist", "pitch"): 1.0 + 0.8 * b, ("waist", "roll"): -1.0 * s,
            ("neck", "yaw"): 7.0 * sin(2 * pi * u + 0.8), ("neck", "pitch"): -0.6 * b, ("shoulder_L", "flex"): 1.5 * b, ("shoulder_R", "flex"): -1.5 * b,
            ("elbow_L", "bend"): 8 + 2 * b, ("elbow_R", "bend"): 10 - 2 * b, ("knee_L", "bend"): 2 + 1.5 * s, ("knee_R", "bend"): 3 - 1.5 * s}

def look_around(u):
    yaw = smooth(0, 38, u / 0.2) if u < 0.3 else smooth(38, -32, (u - 0.3) / 0.3) if u < 0.7 else smooth(-32, 0, (u - 0.7) / 0.25)
    return {("neck", "yaw"): yaw * 0.75, ("waist", "yaw"): yaw * 0.25, ("neck", "pitch"): -3 * sin(pi * u), ("root", "roll"): 0.8 * sin(2 * pi * u)}

def talk(u):
    a = sin(4 * pi * u); b = sin(2 * pi * u)
    return {("shoulder_R", "flex"): 26 + 8 * a, ("shoulder_R", "abduct"): 8 + 4 * b, ("elbow_R", "bend"): 78 + 16 * sin(4 * pi * u + 1.2), ("shoulder_L", "flex"): 6 + 3 * b,
            ("elbow_L", "bend"): 24 + 6 * a, ("neck", "pitch"): 3 * a, ("neck", "yaw"): 6 * b, ("waist", "yaw"): 3 * b, ("root", "roll"): 1.0 * b}

def phone(u):
    b = sin(2 * pi * u)
    return {("shoulder_R", "flex"): 34 + 2 * b, ("elbow_R", "bend"): 118 + 4 * b, ("shoulder_R", "abduct"): 4, ("neck", "pitch"): 20 + 2 * b, ("waist", "pitch"): 4,
            ("elbow_L", "bend"): 12, ("root", "roll"): 1.0 * b, ("knee_L", "bend"): 3 + b}

COWER = {("hip_L", "flex"): 82, ("hip_R", "flex"): 78, ("knee_L", "bend"): 98, ("knee_R", "bend"): 94, ("root", "z"): -0.37, ("root", "y"): 0.26, ("waist", "pitch"): 38,
         ("neck", "pitch"): 26, ("shoulder_L", "flex"): 128, ("shoulder_R", "flex"): 124, ("elbow_L", "bend"): 118, ("elbow_R", "bend"): 122, ("shoulder_L", "abduct"): 14, ("shoulder_R", "abduct"): 14}

def cower_enter(u): return {k: smooth(0, v, u) for k, v in COWER.items()}
def cower_loop(u):
    t = sin(2 * pi * u * 3); out = dict(COWER)
    out[("waist", "pitch")] += 1.5 * t; out[("neck", "pitch")] += 2.0 * t; out[("root", "z")] += 0.006 * t; return out

def hit_react(u):
    k = sin(pi * min(1.0, u * 1.6)) * (1 - u)
    return {("waist", "pitch"): -16 * k, ("root", "y"): 0.06 * k, ("neck", "pitch"): -12 * k, ("shoulder_L", "abduct"): 28 * k, ("shoulder_R", "abduct"): 24 * k,
            ("elbow_L", "bend"): 30 * k, ("elbow_R", "bend"): 34 * k, ("knee_L", "bend"): 14 * k, ("knee_R", "bend"): 10 * k, ("waist", "yaw"): 10 * k}

def robot_scan(u):
    yaw = 42 * sin(2 * pi * u) * (0.5 + 0.5 * abs(sin(2 * pi * u)))
    return {("neck", "yaw"): yaw, ("waist", "yaw"): yaw * 0.2, ("root", "roll"): 0.6 * sin(2 * pi * u), ("elbow_L", "bend"): 12 + 3 * sin(4 * pi * u), ("elbow_R", "bend"): 20}

AIM = {("shoulder_R", "flex"): 72, ("elbow_R", "bend"): 16, ("shoulder_R", "abduct"): 4, ("waist", "pitch"): 5, ("waist", "yaw"): -8, ("neck", "yaw"): 8,
       ("knee_L", "bend"): 12, ("knee_R", "bend"): 14, ("hip_L", "flex"): 8, ("hip_R", "flex"): 4, ("root", "z"): -0.012, ("shoulder_L", "flex"): 14, ("elbow_L", "bend"): 40}
def robot_alert(u): return {k: smooth(0, v, u * 1.15) for k, v in AIM.items()}
def robot_aim(u):
    out = dict(AIM); out[("shoulder_R", "flex")] += 0.8 * sin(2 * pi * u); out[("root", "roll")] = 0.4 * sin(2 * pi * u); return out
def robot_fire(u):
    k = exp(-6 * u) * sin(pi * min(1.0, u * 6)); out = dict(AIM)
    out[("shoulder_R", "flex")] += 5 * k; out[("elbow_R", "bend")] += 7 * k; out[("waist", "pitch")] -= 1.5 * k; out[("root", "y")] = 0.012 * k; return out
DOWN = {("knee_L", "bend"): 26, ("knee_R", "bend"): 24, ("hip_L", "flex"): 14, ("hip_R", "flex"): 12, ("waist", "pitch"): 36, ("neck", "pitch"): 42, ("root", "z"): -0.035,
        ("shoulder_L", "flex"): -4, ("shoulder_R", "flex"): -4, ("elbow_L", "bend"): 6, ("elbow_R", "bend"): 6}
def robot_shutdown(u): return {k: smooth(0, v, u) + (2.5 * sin(18 * u) * (1 - u) if k[0] == "waist" else 0) for k, v in DOWN.items()}
def robot_boot(u): return {k: smooth(v, 0, u) for k, v in DOWN.items()}

def all_clips():
    c = []
    c.append(clip("walk", 1.06, True, lambda u: gait(u, 22, -6, 14, 60), 1.35, [(0.0, "foot_L"), (0.53, "foot_R")]))
    c.append(clip("walk_slow", 1.30, True, lambda u: gait(u, 16, -4, 10, 48, arm=12, bob=0.012, twist=5), 0.85, [(0.0, "foot_L"), (0.65, "foot_R")]))
    c.append(clip("run", 0.68, True, lambda u: gait(u, 36, -8, 22, 92, ank=1.3, arm=40, elbow=(88, 8), bob=0.04, sway=0.012, lean=13, twist=12, hip_h2=5), 4.2, [(0.0, "foot_L"), (0.34, "foot_R")]))
    c.append(clip("walk_heavy", 1.34, True, lambda u: gait(u, 19, -5, 12, 50, ank=0.8, arm=8, elbow=(16, 3), bob=0.028, sway=0.03, lean=2, twist=4), 1.0, [(0.0, "foot_L"), (0.67, "foot_R")]))
    c.append(clip("idle", 4.0, True, idle)); c.append(clip("look_around", 5.0, False, look_around))
    c.append(clip("talk", 3.2, True, talk)); c.append(clip("phone", 4.0, True, phone))
    c.append(clip("cower_enter", 0.45, False, cower_enter)); c.append(clip("cower_loop", 1.0, True, cower_loop)); c.append(clip("hit_react", 0.5, False, hit_react))
    c.append(clip("robot_scan", 6.0, True, robot_scan)); c.append(clip("robot_alert", 0.35, False, robot_alert)); c.append(clip("robot_aim", 2.0, True, robot_aim))
    c.append(clip("robot_fire", 0.14, True, robot_fire, events=[(0.0, "shot")])); c.append(clip("robot_shutdown", 1.2, False, robot_shutdown)); c.append(clip("robot_boot", 1.0, False, robot_boot))
    # 무기 부품 (rig = weapon): joint 이름이 부품 이름이다. move_y는 뒤(+Y)로 미는 거리(m), value는 0~1 값.
    w = lambda n, d, f, ev=(), loop=False: c.append(clip(n, d, loop, f, events=ev, rig="weapon"))
    kick = lambda u, a, peak=0.25: a * (u / peak if u < peak else max(0.0, 1 - (u - peak) / (1 - peak)))
    w("pistol_fire", 0.11, lambda u: {("slide", "move_y"): kick(u, 0.034), ("trigger", "pitch"): -kick(u, 14, 0.15), ("hammer", "pitch"): -kick(u, 30, 0.1)}, [(0.0, "muzzle"), (0.03, "eject")])
    w("revolver_fire", 0.16, lambda u: {("cylinder", "roll"): smooth(0, 60, u * 1.6), ("hammer", "pitch"): -kick(u, 38, 0.12), ("trigger", "pitch"): -kick(u, 16, 0.2)}, [(0.0, "muzzle")])
    w("auto_fire", 0.09, lambda u: {("bolt", "move_y"): kick(u, 0.045, 0.3), ("trigger", "pitch"): -10}, [(0.0, "muzzle"), (0.025, "eject")], True)
    w("shotgun_pump", 0.42, lambda u: {("pump", "move_y"): kick(u, 0.085, 0.4)}, [(0.16, "eject"), (0.36, "chamber")])
    w("bolt_cycle", 0.9, lambda u: {("bolt", "roll"): 60 * kick(u, 1, 0.5) if u < 0.2 or u > 0.8 else 60, ("bolt", "move_y"): kick(max(0, (u - 0.2) / 0.6), 0.07, 0.5) if 0.2 <= u <= 0.8 else 0}, [(0.45, "eject")])
    w("mag_reload", 1.6, lambda u: {("mag", "move_z"): -0.16 * (smooth(0, 1, u / 0.18) if u < 0.5 else smooth(1, 0, (u - 0.62) / 0.16)), ("mag", "value"): 0.0 if 0.2 < u < 0.6 else 1.0},
      [(0.05, "mag_out"), (1.0, "mag_in"), (1.35, "chamber")])
    w("charge", 1.2, lambda u: {("coil_glow", "value"): smooth(0, 1, u)}, [(1.2, "charged")])
    return c

def golden(clips):
    """Luau 포팅 검증용: 클립과 시각 -> 기대 값."""
    out = []
    for cl in clips:
        if cl["name"] not in ("walk", "run", "cower_enter", "robot_fire", "mag_reload"): continue
        for t in (0.0, 0.017, 0.2, cl["duration"] * 0.5, cl["duration"] * 0.93, cl["duration"] * 1.7):
            out.append({"clip": cl["name"], "t": round(t, 5), "pose": sample(cl, t)})
    return out

def sample(cl, t):
    d = cl["duration"]; t = t % d if cl["loop"] else max(0.0, min(d, t)); pose = {}
    for tr in cl["tracks"]:
        ks = tr["keys"]; n = len(ks); step = d / (n - 1); i = min(n - 2, int(t / step)); u = (t - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
        pose[tr["joint"] + "." + tr["dof"]] = round(ks[i][1] + (ks[i + 1][1] - ks[i][1]) * u, 6)
    return pose

if MODE == "clips":
    os.makedirs(OUT, exist_ok=True); clips = all_clips()
    for cl in clips: json.dump(cl, open(os.path.join(OUT, cl["name"] + ".json"), "w"), separators=(",", ":"))
    json.dump(golden(clips), open(os.path.join(OUT, "_golden_samples.json"), "w"), separators=(",", ":"))
    json.dump({"clips": [{"name": c["name"], "rig": c["rig"], "duration": c["duration"], "loop": c["loop"], "speed": c["speed"], "events": c["events"]} for c in clips]},
              open(os.path.join(OUT, "_index.json"), "w"), indent=1)
    print("CLIPS", len(clips), [c["name"] for c in clips])
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import bpy, numpy as np
    from mathutils import Matrix, Vector
    import kit
    AX = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
    def joint_rot(joint, dofs):
        side = 1 if joint.endswith("_L") else -1
        rz = dofs.get("yaw", 0.0); rx = dofs.get("pitch", 0.0) - dofs.get("flex", 0.0) - dofs.get("dorsi", 0.0)
        rx += dofs.get("bend", 0.0) * (1 if joint.startswith("knee") else -1)
        ry = dofs.get("roll", 0.0) - dofs.get("abduct", 0.0) * side
        return Matrix.Rotation(radians(rz), 4, "Z") @ Matrix.Rotation(radians(rx), 4, "X") @ Matrix.Rotation(radians(ry), 4, "Y")
    def apply(pose, rest):
        by = {}
        for k, v in pose.items():
            j, d = k.split("."); by.setdefault(j, {})[d] = v
        r = by.get("root", {}); D = {"pelvis": Matrix.Translation((r.get("x", 0), r.get("y", 0), r.get("z", 0))) @ Matrix.Translation((0, 0, 0.95)) @ joint_rot("root", r) @ Matrix.Translation((0, 0, -0.95))}
        pending = dict(kit.PIVOTS)
        while pending:
            done = [n for n, pv in pending.items() if pv["parent"] in D]
            if not done: break
            for n in done:
                pv = pending.pop(n); p = Vector(pv["pos"])
                D[pv["child"]] = D[pv["parent"]] @ Matrix.Translation(p) @ joint_rot(n, by.get(n, {})) @ Matrix.Translation(-p)
        for ob, m in rest.items(): ob.matrix_world = D.get(ob.get("part", "pelvis"), D["pelvis"]) @ m
    def strip(asset, build, clip_name, frames=6, res=(330, 560), cam=((-2.6, -4.6, 1.3), (0, 0, 0.95), 60)):
        cl = json.load(open(os.path.join(OUT, clip_name + ".json"))); build()
        rest = {o: o.matrix_world.copy() for o in kit.asset_objects()}; kit.studio((0, 0, 0.95), 1.0)
        tiles = []
        for i in range(frames):
            t = cl["duration"] * i / (frames if cl["loop"] else frames - 1); apply(sample(cl, t), rest)
            path = os.path.join(OUT, f"_tmp_{i}.png"); kit.shot(path, cam[0], cam[1], cam[2], res=res)
            im = bpy.data.images.load(os.path.abspath(path)); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(res[1], res[0], 4)); os.remove(path)
        sheet = np.concatenate(tiles, axis=1); out = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0]); out.pixels = sheet.ravel()
        out.filepath_raw = os.path.abspath(os.path.join(OUT, f"preview_{asset}_{clip_name}.png")); out.file_format = "PNG"; out.save(); print("PREVIEW", asset, clip_name)
    import npc, security_robot
    jobs = [("npc", lambda: npc.build("techwear"), "walk"), ("npc", lambda: npc.build("techwear"), "run"), ("npc", lambda: npc.build("worker"), "cower_enter"),
            ("robot", security_robot.build, "walk_heavy"), ("robot", security_robot.build, "robot_alert"), ("robot", security_robot.build, "robot_shutdown")]
    only = ARGS[2:]
    for a, b, c in jobs:
        if not only or c in only: strip(a, b, c)
