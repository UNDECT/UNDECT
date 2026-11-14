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
    assert all(len(ks) == n for ks in tracks.values()), name + ": 프레임마다 관절 목록이 다르다"
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

# ------------------------------------------------------------------ 추가 동작 (사람)
def seq(u, *stages):
    """stages = (끝 시각 0~1, 자세)... 사이를 부드럽게 잇는다. 첫 단계의 시각이 0이면 그 자세에서 시작하고, 아니면 선 자세에서 시작한다.
    어느 시각에나 같은 관절 목록을 돌려준다(트랙마다 키 개수가 같아야 한다)."""
    keys = set().union(*[p.keys() for _, p in stages]); prev_t, prev = 0.0, {}
    if stages[0][0] <= 0.001: prev = stages[0][1]; stages = stages[1:]
    for t, pose in stages:
        if u <= t:
            w = (u - prev_t) / max(1e-6, t - prev_t); return {k: smooth(prev.get(k, 0.0), pose.get(k, 0.0), w) for k in keys}
        prev_t, prev = t, pose
    return {k: prev.get(k, 0.0) for k in keys}

SIT = {("hip_L", "flex"): 86, ("hip_R", "flex"): 86, ("knee_L", "bend"): 88, ("knee_R", "bend"): 88, ("root", "z"): -0.40, ("root", "y"): 0.16, ("waist", "pitch"): 4,
       ("shoulder_L", "flex"): 24, ("shoulder_R", "flex"): 24, ("elbow_L", "bend"): 58, ("elbow_R", "bend"): 58, ("neck", "pitch"): 2}
SIT_MID = {("hip_L", "flex"): 62, ("hip_R", "flex"): 62, ("knee_L", "bend"): 60, ("knee_R", "bend"): 60, ("root", "z"): -0.20, ("root", "y"): 0.14, ("waist", "pitch"): 34,
           ("shoulder_L", "flex"): 30, ("shoulder_R", "flex"): 30, ("elbow_L", "bend"): 40, ("elbow_R", "bend"): 40, ("neck", "pitch"): -10}
def sit_down(u): return seq(u, (0.55, SIT_MID), (1.0, SIT))
def stand_up(u): return seq(u, (0.001, SIT), (0.45, SIT_MID), (1.0, {}))
def sit_loop(u):
    b = sin(2 * pi * u); out = dict(SIT); out[("waist", "pitch")] += 1.2 * b; out[("neck", "yaw")] = 6 * sin(2 * pi * u + 1.0); out[("elbow_R", "bend")] += 2 * b; return out

LIE = {("root", "pitch"): -86, ("root", "z"): -0.80, ("root", "y"): 0.42, ("hip_L", "flex"): 6, ("hip_R", "flex"): 14, ("knee_L", "bend"): 10, ("knee_R", "bend"): 26,
       ("shoulder_L", "abduct"): 48, ("shoulder_R", "abduct"): 36, ("elbow_L", "bend"): 26, ("elbow_R", "bend"): 44, ("neck", "pitch"): -6}
FALL_MID = {("root", "pitch"): -38, ("root", "z"): -0.30, ("root", "y"): 0.26, ("hip_L", "flex"): 44, ("hip_R", "flex"): 30, ("knee_L", "bend"): 62, ("knee_R", "bend"): 40,
            ("shoulder_L", "abduct"): 70, ("shoulder_R", "abduct"): 64, ("shoulder_L", "flex"): 40, ("shoulder_R", "flex"): 50, ("elbow_L", "bend"): 50, ("elbow_R", "bend"): 40, ("waist", "pitch"): 14, ("neck", "pitch"): 22}
GETUP_SIT = {("root", "pitch"): -22, ("root", "z"): -0.66, ("root", "y"): 0.30, ("hip_L", "flex"): 96, ("hip_R", "flex"): 80, ("knee_L", "bend"): 110, ("knee_R", "bend"): 70,
             ("shoulder_L", "flex"): -30, ("shoulder_R", "flex"): -24, ("elbow_L", "bend"): 20, ("elbow_R", "bend"): 30, ("waist", "pitch"): 30, ("neck", "pitch"): 6}
GETUP_CROUCH = {("root", "z"): -0.36, ("root", "y"): 0.10, ("hip_L", "flex"): 92, ("hip_R", "flex"): 84, ("knee_L", "bend"): 108, ("knee_R", "bend"): 100, ("waist", "pitch"): 36,
                ("shoulder_L", "flex"): 30, ("shoulder_R", "flex"): 36, ("elbow_L", "bend"): 50, ("elbow_R", "bend"): 44, ("neck", "pitch"): -14}
def knockdown(u): return seq(u, (0.42, FALL_MID), (0.80, LIE), (1.0, LIE))
def lie_loop(u):
    out = dict(LIE); out[("elbow_R", "bend")] += 2 * sin(2 * pi * u); return out
def get_up(u): return seq(u, (0.001, LIE), (0.38, GETUP_SIT), (0.68, GETUP_CROUCH), (1.0, {}))
COLLAPSE = {("root", "z"): -0.52, ("root", "y"): -0.06, ("root", "pitch"): 30, ("hip_L", "flex"): 40, ("hip_R", "flex"): 52, ("knee_L", "bend"): 118, ("knee_R", "bend"): 126,
            ("waist", "pitch"): 44, ("neck", "pitch"): 34, ("shoulder_L", "flex"): 8, ("shoulder_R", "flex"): 4, ("elbow_L", "bend"): 14, ("elbow_R", "bend"): 10}
def collapse(u): return seq(u, (0.35, {("knee_L", "bend"): 50, ("knee_R", "bend"): 56, ("root", "z"): -0.12, ("waist", "pitch"): 16, ("neck", "pitch"): 20, ("hip_L", "flex"): 26, ("hip_R", "flex"): 30}), (1.0, COLLAPSE))

# 3인칭 무기 자세 (적·다른 플레이어)
AIM_PISTOL = {("shoulder_R", "flex"): 80, ("shoulder_R", "abduct"): -14, ("elbow_R", "bend"): 14, ("shoulder_L", "flex"): 74, ("shoulder_L", "abduct"): -22, ("elbow_L", "bend"): 30,
              ("waist", "pitch"): 6, ("neck", "pitch"): 2, ("knee_L", "bend"): 10, ("knee_R", "bend"): 12, ("root", "z"): -0.012, ("hip_L", "flex"): 8, ("hip_R", "flex"): 2}
AIM_RIFLE = {("shoulder_R", "flex"): 46, ("shoulder_R", "abduct"): 26, ("elbow_R", "bend"): 104, ("shoulder_L", "flex"): 66, ("shoulder_L", "abduct"): -30, ("elbow_L", "bend"): 46,
             ("waist", "yaw"): -22, ("waist", "pitch"): 8, ("neck", "yaw"): 20, ("neck", "pitch"): 4, ("knee_L", "bend"): 14, ("knee_R", "bend"): 10, ("root", "z"): -0.015, ("hip_L", "flex"): 10}
LOW_READY = {("shoulder_R", "flex"): 18, ("shoulder_R", "abduct"): 10, ("elbow_R", "bend"): 86, ("shoulder_L", "flex"): 34, ("shoulder_L", "abduct"): -24, ("elbow_L", "bend"): 62, ("waist", "yaw"): -14, ("neck", "yaw"): 12}
def hold(base, amp=0.8): return lambda u: {**base, ("shoulder_R", "flex"): base[("shoulder_R", "flex")] + amp * sin(2 * pi * u), ("root", "roll"): 0.5 * sin(2 * pi * u)}
def fire_3p(base, kick_deg):
    def f(u):
        k = exp(-7 * u) * sin(pi * min(1.0, u * 7)); out = dict(base)
        out[("shoulder_R", "flex")] += kick_deg * k; out[("elbow_R", "bend")] += kick_deg * 1.4 * k; out[("waist", "pitch")] = out.get(("waist", "pitch"), 0) - 1.5 * k; out[("root", "y")] = 0.010 * k; return out
    return f

# 근접 공격 (오른손). 이벤트 hit에서 판정한다.
def melee_slash(u):
    return seq(u, (0.30, {("shoulder_R", "flex"): 70, ("shoulder_R", "abduct"): 62, ("elbow_R", "bend"): 70, ("waist", "yaw"): -38, ("root", "yaw"): -10, ("neck", "yaw"): 26, ("knee_L", "bend"): 12, ("root", "z"): -0.02}),
               (0.52, {("shoulder_R", "flex"): 62, ("shoulder_R", "abduct"): -34, ("elbow_R", "bend"): 14, ("waist", "yaw"): 40, ("root", "yaw"): 12, ("neck", "yaw"): -22, ("hip_L", "flex"): 18, ("knee_L", "bend"): 24, ("root", "z"): -0.05, ("root", "y"): -0.10, ("waist", "pitch"): 12}),
               (0.70, {("shoulder_R", "flex"): 40, ("shoulder_R", "abduct"): -40, ("elbow_R", "bend"): 30, ("waist", "yaw"): 46, ("root", "yaw"): 12, ("hip_L", "flex"): 14, ("knee_L", "bend"): 18, ("root", "z"): -0.04, ("root", "y"): -0.08}), (1.0, {}))
def melee_stab(u):
    return seq(u, (0.28, {("shoulder_R", "flex"): 10, ("elbow_R", "bend"): 116, ("waist", "yaw"): -24, ("shoulder_R", "abduct"): 12, ("root", "y"): 0.04, ("knee_R", "bend"): 12}),
               (0.48, {("shoulder_R", "flex"): 82, ("elbow_R", "bend"): 6, ("waist", "yaw"): 26, ("waist", "pitch"): 14, ("hip_L", "flex"): 26, ("knee_L", "bend"): 30, ("root", "y"): -0.16, ("root", "z"): -0.06}),
               (0.66, {("shoulder_R", "flex"): 78, ("elbow_R", "bend"): 14, ("waist", "yaw"): 24, ("waist", "pitch"): 12, ("hip_L", "flex"): 22, ("knee_L", "bend"): 24, ("root", "y"): -0.14, ("root", "z"): -0.05}), (1.0, {}))
def melee_heavy(u):
    up = {("shoulder_R", "flex"): 158, ("shoulder_L", "flex"): 154, ("elbow_R", "bend"): 70, ("elbow_L", "bend"): 74, ("shoulder_L", "abduct"): -16, ("shoulder_R", "abduct"): -16, ("waist", "pitch"): -12, ("neck", "pitch"): -8, ("root", "z"): 0.01}
    down = {("shoulder_R", "flex"): 42, ("shoulder_L", "flex"): 40, ("elbow_R", "bend"): 16, ("elbow_L", "bend"): 20, ("shoulder_L", "abduct"): -18, ("shoulder_R", "abduct"): -18, ("waist", "pitch"): 40, ("neck", "pitch"): -16,
            ("hip_L", "flex"): 34, ("hip_R", "flex"): 30, ("knee_L", "bend"): 46, ("knee_R", "bend"): 40, ("root", "z"): -0.14, ("root", "y"): -0.06}
    return seq(u, (0.42, up), (0.58, down), (0.76, down), (1.0, {}))
def punch(u):
    return seq(u, (0.30, {("shoulder_R", "flex"): 30, ("elbow_R", "bend"): 124, ("waist", "yaw"): -22, ("shoulder_L", "flex"): 44, ("elbow_L", "bend"): 110, ("knee_L", "bend"): 10}),
               (0.50, {("shoulder_R", "flex"): 86, ("elbow_R", "bend"): 8, ("waist", "yaw"): 30, ("shoulder_L", "flex"): 40, ("elbow_L", "bend"): 118, ("hip_L", "flex"): 16, ("knee_L", "bend"): 20, ("root", "y"): -0.08, ("waist", "pitch"): 6}), (1.0, {}))
def throw(u):
    return seq(u, (0.40, {("shoulder_R", "flex"): 150, ("shoulder_R", "abduct"): 30, ("elbow_R", "bend"): 96, ("waist", "yaw"): -34, ("waist", "pitch"): -10, ("shoulder_L", "flex"): 60, ("elbow_L", "bend"): 20, ("hip_R", "flex"): -10, ("root", "y"): 0.05}),
               (0.58, {("shoulder_R", "flex"): 96, ("shoulder_R", "abduct"): -6, ("elbow_R", "bend"): 10, ("waist", "yaw"): 30, ("waist", "pitch"): 20, ("shoulder_L", "flex"): -10, ("hip_L", "flex"): 24, ("knee_L", "bend"): 26, ("root", "y"): -0.14, ("root", "z"): -0.05}),
               (0.74, {("shoulder_R", "flex"): 40, ("shoulder_R", "abduct"): -20, ("elbow_R", "bend"): 24, ("waist", "yaw"): 38, ("waist", "pitch"): 24, ("hip_L", "flex"): 22, ("knee_L", "bend"): 24, ("root", "y"): -0.14, ("root", "z"): -0.05}), (1.0, {}))

# ------------------------------------------------------------------ 1인칭 (rig = fp)
# view = 팔과 무기 뭉치 전체를 카메라 기준으로 옮기는 값. x 오른쪽, y 뒤(+)·앞(-), z 위 (m). pitch 총구가 위로(+), yaw 왼쪽(+), roll 왼쪽으로 기움(+) (도).
# 걷기 흔들림(보브)은 만들지 않는다. 멈춰 있을 때의 숨쉬기 흔들림만 있다.
def fp_idle(u):
    a, b = sin(2 * pi * u), sin(4 * pi * u + 0.7)
    return {("view", "z"): 0.0030 * a, ("view", "x"): 0.0016 * b, ("view", "pitch"): 0.35 * a, ("view", "roll"): 0.25 * b}
def fp_raise(u):
    k = 1 - smooth(0, 1, u); o = sin(pi * u) * 0.12
    return {("view", "z"): -0.26 * k, ("view", "y"): 0.06 * k, ("view", "pitch"): -34 * k + 5 * o, ("view", "roll"): 14 * k}
def fp_lower(u):
    k = smooth(0, 1, u); return {("view", "z"): -0.26 * k, ("view", "y"): 0.06 * k, ("view", "pitch"): -34 * k, ("view", "roll"): 14 * k}
def fp_recoil(back, up, side=0.0):
    def f(u):
        k = exp(-9 * u) * min(1.0, u * 22); w = exp(-5 * u) * sin(26 * u)
        return {("view", "y"): back * k, ("view", "pitch"): up * k + up * 0.10 * w, ("view", "z"): 0.004 * k, ("view", "yaw"): side * k, ("view", "roll"): side * 0.8 * w}
    return f
def fp_reload(u):
    d = sin(pi * min(1.0, u / 0.25)) if u < 0.25 else 1.0 if u < 0.72 else 1 - smooth(0, 1, (u - 0.72) / 0.28)
    j = 0.012 * exp(-40 * (u - 0.60) ** 2) + 0.008 * exp(-60 * (u - 0.84) ** 2)
    return {("view", "z"): -0.070 * d + j, ("view", "x"): -0.030 * d, ("view", "roll"): 26 * d, ("view", "pitch"): 14 * d, ("view", "yaw"): 8 * d,
            ("support", "z"): -0.22 * (smooth(0, 1, (u - 0.10) / 0.12) if u < 0.40 else 1 - smooth(0, 1, (u - 0.48) / 0.14)), ("support", "value"): 0.0 if 0.14 < u < 0.52 else 1.0}
def fp_ads(u):
    k = smooth(0, 1, u); return {("view", "x"): -0.085 * k, ("view", "z"): 0.032 * k, ("view", "y"): 0.030 * k, ("view", "roll"): -1.5 * sin(pi * u), ("view", "value"): k}
def fp_slash(u):
    return seq(u, (0.26, {("view", "x"): 0.16, ("view", "z"): 0.10, ("view", "yaw"): -30, ("view", "roll"): -34, ("view", "pitch"): 12}),
               (0.46, {("view", "x"): -0.30, ("view", "z"): -0.10, ("view", "yaw"): 46, ("view", "roll"): 38, ("view", "pitch"): -10, ("view", "y"): -0.10}),
               (0.64, {("view", "x"): -0.34, ("view", "z"): -0.16, ("view", "yaw"): 52, ("view", "roll"): 40, ("view", "pitch"): -14, ("view", "y"): -0.06}), (1.0, {}))
def fp_stab(u):
    return seq(u, (0.26, {("view", "y"): 0.14, ("view", "z"): -0.03, ("view", "pitch"): 6, ("view", "roll"): -8}), (0.44, {("view", "y"): -0.34, ("view", "z"): 0.02, ("view", "pitch"): -3, ("view", "x"): -0.05}),
               (0.60, {("view", "y"): -0.30, ("view", "z"): 0.01, ("view", "x"): -0.05}), (1.0, {}))
def fp_punch(u):
    return seq(u, (0.24, {("view", "y"): 0.12, ("view", "x"): 0.04, ("view", "roll"): -10}), (0.42, {("view", "y"): -0.38, ("view", "x"): -0.10, ("view", "z"): 0.04, ("view", "roll"): 14, ("view", "yaw"): 10}), (1.0, {}))
def fp_heavy(u):
    return seq(u, (0.40, {("view", "z"): 0.26, ("view", "y"): 0.10, ("view", "pitch"): 58, ("view", "roll"): -6}), (0.56, {("view", "z"): -0.22, ("view", "y"): -0.22, ("view", "pitch"): -48}),
               (0.74, {("view", "z"): -0.24, ("view", "y"): -0.20, ("view", "pitch"): -50}), (1.0, {}))
def fp_throw(u):
    return seq(u, (0.38, {("view", "z"): 0.14, ("view", "y"): 0.18, ("view", "x"): 0.06, ("view", "pitch"): 40, ("view", "roll"): -16}), (0.54, {("view", "z"): 0.02, ("view", "y"): -0.34, ("view", "pitch"): -24, ("view", "x"): -0.06}),
               (0.70, {("view", "z"): -0.16, ("view", "y"): -0.20, ("view", "pitch"): -40, ("view", "value"): 1.0}), (1.0, {("view", "z"): -0.26, ("view", "pitch"): -34, ("view", "value"): 1.0}))
def fp_inspect(u):
    a = sin(pi * u); t = sin(2 * pi * u)
    return {("view", "x"): -0.06 * a, ("view", "z"): 0.05 * a, ("view", "y"): 0.05 * a, ("view", "roll"): (50 * t) * a, ("view", "yaw"): 30 * a - 20 * t * a, ("view", "pitch"): 12 * a}
def fp_sprint(u):
    return {("view", "z"): -0.10, ("view", "x"): -0.05, ("view", "roll"): 22, ("view", "pitch"): -16, ("view", "yaw"): 24}
def fp_land(u):
    k = exp(-7 * u) * sin(pi * min(1.0, u * 5)); return {("view", "z"): -0.045 * k, ("view", "pitch"): -4 * k}

# ------------------------------------------------------------------ 죽는 동작, 맞는 동작 (사람)
# 죽는 클립은 반복하지 않는다. 끝 자세가 시체 자세이므로 마지막 프레임에서 멈춘 채로 둔다.
def plus(pose, extra):
    out = dict(pose)
    for k, v in extra.items(): out[k] = out.get(k, 0.0) + v
    return out

LIE_OPEN = {("root", "pitch"): -88, ("root", "z"): -0.81, ("root", "y"): 0.46, ("hip_L", "flex"): 4, ("hip_R", "flex"): 10, ("knee_L", "bend"): 6, ("knee_R", "bend"): 30, ("hip_L", "abduct"): 0,
            ("shoulder_L", "abduct"): 62, ("shoulder_R", "abduct"): 28, ("elbow_L", "bend"): 18, ("elbow_R", "bend"): 70, ("neck", "yaw"): 28, ("neck", "pitch"): -8, ("waist", "roll"): 4}
LIE_TIGHT = {("root", "pitch"): -88, ("root", "z"): -0.81, ("root", "y"): 0.30, ("hip_L", "flex"): 16, ("hip_R", "flex"): 2, ("knee_L", "bend"): 44, ("knee_R", "bend"): 8,
             ("shoulder_L", "abduct"): 18, ("shoulder_R", "abduct"): 22, ("elbow_L", "bend"): 40, ("elbow_R", "bend"): 24, ("neck", "yaw"): -34, ("neck", "pitch"): -4}
PRONE = {("root", "pitch"): 86, ("root", "z"): -0.80, ("root", "y"): -0.46, ("hip_L", "flex"): -4, ("hip_R", "flex"): -8, ("knee_L", "bend"): 10, ("knee_R", "bend"): 26,
         ("shoulder_L", "flex"): 150, ("shoulder_R", "flex"): 60, ("shoulder_L", "abduct"): 34, ("shoulder_R", "abduct"): 40, ("elbow_L", "bend"): 62, ("elbow_R", "bend"): 96, ("neck", "yaw"): 52, ("neck", "pitch"): -10}
def side(s):
    """옆으로 누운 자세. s = +1 왼쪽으로, -1 오른쪽으로 쓰러진다."""
    return {("root", "roll"): 84 * s, ("root", "z"): -0.76, ("root", "x"): -0.40 * s, ("root", "yaw"): 30 * s, ("hip_L", "flex"): 36, ("hip_R", "flex"): 22, ("knee_L", "bend"): 58, ("knee_R", "bend"): 36,
            ("shoulder_L", "flex"): 46, ("shoulder_R", "flex"): 30, ("elbow_L", "bend"): 64, ("elbow_R", "bend"): 50, ("waist", "pitch"): 16, ("neck", "pitch"): 14, ("neck", "yaw"): -10 * s}
KNEEL = {("root", "z"): -0.46, ("root", "y"): -0.04, ("hip_L", "flex"): 6, ("hip_R", "flex"): 10, ("knee_L", "bend"): 104, ("knee_R", "bend"): 108, ("waist", "pitch"): 10, ("neck", "pitch"): 22,
         ("shoulder_L", "flex"): 4, ("shoulder_R", "flex"): 6, ("elbow_L", "bend"): 10, ("elbow_R", "bend"): 12}
JOLT_BACK = {("waist", "pitch"): -20, ("neck", "pitch"): -14, ("root", "y"): 0.10, ("shoulder_L", "abduct"): 44, ("shoulder_R", "abduct"): 40, ("shoulder_L", "flex"): 20, ("shoulder_R", "flex"): 26,
             ("elbow_L", "bend"): 36, ("elbow_R", "bend"): 30, ("knee_L", "bend"): 18, ("knee_R", "bend"): 26, ("hip_R", "flex"): -8}
CRAWL = {("root", "pitch"): 76, ("root", "z"): -0.70, ("root", "y"): -0.40, ("hip_L", "flex"): 30, ("hip_R", "flex"): 6, ("knee_L", "bend"): 70, ("knee_R", "bend"): 14,
         ("shoulder_L", "flex"): 128, ("shoulder_R", "flex"): 96, ("shoulder_L", "abduct"): 16, ("shoulder_R", "abduct"): 22, ("elbow_L", "bend"): 44, ("elbow_R", "bend"): 100, ("neck", "pitch"): -34}

def death_back(u): return seq(u, (0.16, JOLT_BACK), (0.50, FALL_MID), (0.82, LIE_OPEN), (1.0, LIE_OPEN))
def death_front(u):
    buckle = {("knee_L", "bend"): 64, ("knee_R", "bend"): 72, ("root", "z"): -0.20, ("root", "y"): -0.10, ("waist", "pitch"): 34, ("neck", "pitch"): 26, ("hip_L", "flex"): 30, ("hip_R", "flex"): 38,
              ("shoulder_L", "flex"): 30, ("shoulder_R", "flex"): 20, ("elbow_L", "bend"): 40, ("elbow_R", "bend"): 30}
    return seq(u, (0.12, {("waist", "pitch"): 16, ("neck", "pitch"): -10, ("root", "y"): -0.05}), (0.46, buckle), (0.82, PRONE), (1.0, PRONE))
def death_side(s):
    def f(u):
        spin = {("root", "yaw"): 48 * s, ("waist", "yaw"): 30 * s, ("waist", "roll"): -14 * s, ("root", "x"): -0.10 * s, ("root", "z"): -0.10, ("knee_L", "bend"): 30, ("knee_R", "bend"): 36,
                ("shoulder_L", "abduct"): 40, ("shoulder_R", "abduct"): 40, ("elbow_L", "bend"): 40, ("elbow_R", "bend"): 40, ("neck", "yaw"): 20 * s, ("hip_L", "flex"): 20, ("hip_R", "flex"): 14}
        return seq(u, (0.40, spin), (0.82, side(s)), (1.0, side(s)))
    return f
def death_headshot(u):
    snap = {("neck", "pitch"): -34, ("waist", "pitch"): -10, ("knee_L", "bend"): 40, ("knee_R", "bend"): 46, ("root", "z"): -0.14, ("root", "y"): 0.06, ("elbow_L", "bend"): 8, ("elbow_R", "bend"): 8}
    return seq(u, (0.14, snap), (0.52, plus(FALL_MID, {("shoulder_L", "abduct"): -44, ("shoulder_R", "abduct"): -40, ("shoulder_L", "flex"): -30, ("shoulder_R", "flex"): -40})), (0.86, LIE_TIGHT), (1.0, LIE_TIGHT))
def death_knees(u):
    sway = plus(KNEEL, {("waist", "pitch"): 14, ("waist", "roll"): 6, ("neck", "pitch"): 18})
    return seq(u, (0.24, KNEEL), (0.58, sway), (0.86, PRONE), (1.0, PRONE))
def death_blast(u):
    air = {("root", "y"): 1.00, ("root", "z"): 0.26, ("root", "pitch"): -62, ("hip_L", "flex"): 50, ("hip_R", "flex"): 30, ("knee_L", "bend"): 50, ("knee_R", "bend"): 70,
           ("shoulder_L", "abduct"): 84, ("shoulder_R", "abduct"): 76, ("shoulder_L", "flex"): 30, ("shoulder_R", "flex"): 50, ("elbow_L", "bend"): 30, ("elbow_R", "bend"): 50, ("waist", "pitch"): -16, ("neck", "pitch"): -20}
    land = plus(LIE_OPEN, {("root", "y"): 1.75, ("shoulder_R", "abduct"): 40, ("knee_L", "bend"): 30})
    slide = plus(LIE_OPEN, {("root", "y"): 2.05, ("shoulder_R", "abduct"): 40, ("knee_L", "bend"): 30})
    return seq(u, (0.34, air), (0.62, land), (0.90, slide), (1.0, slide))
def death_burn(u):
    """레이저·화염: 몸이 굳고 팔이 가슴으로 말리며 떨다가 뻣뻣하게 쓰러진다."""
    stiff = {("shoulder_L", "flex"): 42, ("shoulder_R", "flex"): 46, ("elbow_L", "bend"): 128, ("elbow_R", "bend"): 132, ("shoulder_L", "abduct"): 10, ("shoulder_R", "abduct"): 10,
             ("waist", "pitch"): -8, ("neck", "pitch"): -22, ("knee_L", "bend"): 14, ("knee_R", "bend"): 18, ("root", "z"): -0.02}
    down = plus(LIE_TIGHT, {("elbow_L", "bend"): 90, ("elbow_R", "bend"): 104, ("shoulder_L", "flex"): 40, ("shoulder_R", "flex"): 44, ("knee_L", "bend"): 20, ("neck", "yaw"): 20})
    base = seq(u, (0.14, stiff), (0.50, stiff), (0.84, down), (1.0, down)); k = (1 - smooth(0, 1, (u - 0.45) / 0.3)) * min(1.0, u / 0.1)
    return plus(base, {("waist", "roll"): 4.0 * k * sin(2 * pi * u * 26), ("neck", "yaw"): 7.0 * k * sin(2 * pi * u * 22 + 1.0), ("elbow_R", "bend"): 6.0 * k * sin(2 * pi * u * 30), ("waist", "pitch"): 3.0 * k * sin(2 * pi * u * 19)})
def death_shock(u):
    rigid = {("shoulder_L", "abduct"): 34, ("shoulder_R", "abduct"): 34, ("elbow_L", "bend"): 70, ("elbow_R", "bend"): 70, ("waist", "pitch"): -14, ("neck", "pitch"): -26, ("knee_L", "bend"): 8, ("knee_R", "bend"): 8, ("root", "z"): 0.01,
             ("hip_L", "flex"): -4, ("hip_R", "flex"): -4}
    base = seq(u, (0.10, rigid), (0.52, rigid), (0.70, plus(COLLAPSE, {("root", "pitch"): -20})), (0.90, PRONE), (1.0, PRONE)); k = (1 - smooth(0, 1, (u - 0.48) / 0.12)) * min(1.0, u / 0.08)
    return plus(base, {("waist", "roll"): 5.0 * k * sin(2 * pi * u * 34), ("neck", "yaw"): 8.0 * k * sin(2 * pi * u * 31), ("elbow_L", "bend"): 9.0 * k * sin(2 * pi * u * 37), ("elbow_R", "bend"): 9.0 * k * sin(2 * pi * u * 29 + 2), ("root", "x"): 0.01 * k * sin(2 * pi * u * 33)})
def death_slash(u):
    clutch = {("shoulder_R", "flex"): 38, ("elbow_R", "bend"): 118, ("shoulder_R", "abduct"): -14, ("shoulder_L", "flex"): 30, ("elbow_L", "bend"): 110, ("shoulder_L", "abduct"): -10, ("waist", "pitch"): 24, ("neck", "pitch"): 18,
              ("root", "y"): 0.14, ("knee_L", "bend"): 22, ("knee_R", "bend"): 30, ("hip_L", "flex"): 14, ("hip_R", "flex"): 20, ("root", "z"): -0.04}
    reel = plus(clutch, {("root", "y"): 0.26, ("root", "yaw"): -36, ("waist", "roll"): 12, ("root", "z"): -0.10, ("knee_R", "bend"): 30})
    return seq(u, (0.20, clutch), (0.52, reel), (0.86, plus(side(-1), {("root", "y"): 0.44})), (1.0, plus(side(-1), {("root", "y"): 0.44})))
def death_sit(u):
    slump = plus(SIT, {("waist", "pitch"): 46, ("neck", "pitch"): 40, ("waist", "roll"): 14, ("shoulder_L", "flex"): -22, ("shoulder_R", "flex"): -20, ("elbow_L", "bend"): -46, ("elbow_R", "bend"): -44, ("neck", "yaw"): 16})
    return seq(u, (0.0, SIT), (0.20, plus(SIT, {("waist", "pitch"): -12, ("neck", "pitch"): -16})), (0.80, slump), (1.0, slump))
def fall_wounded(u): return seq(u, (0.30, plus(KNEEL, {("waist", "pitch"): 30, ("shoulder_L", "flex"): 50, ("shoulder_R", "flex"): 50})), (0.85, CRAWL), (1.0, CRAWL))
def wounded_crawl(u):
    a = sin(2 * pi * u); b = cos(2 * pi * u)
    return plus(CRAWL, {("shoulder_L", "flex"): 18 * a, ("shoulder_R", "flex"): -22 * a, ("elbow_L", "bend"): -20 * a, ("elbow_R", "bend"): 26 * a, ("hip_L", "flex"): -16 * a, ("hip_R", "flex"): 18 * a,
                        ("knee_L", "bend"): -30 * a, ("knee_R", "bend"): 34 * a, ("root", "roll"): 7 * a, ("waist", "yaw"): 8 * a, ("neck", "pitch"): 6 * b, ("root", "z"): 0.012 * b})
def death_crawl(u): return seq(u, (0.0, CRAWL), (0.40, plus(CRAWL, {("neck", "pitch"): 26, ("shoulder_L", "flex"): 14, ("root", "z"): 0.03})), (0.85, PRONE), (1.0, PRONE))

def hit_dir(kind):
    """방향별 피격. front = 앞에서 맞아 뒤로 젖혀짐, back = 뒤에서 맞아 앞으로 꺾임."""
    P = {"front": {("waist", "pitch"): -16, ("root", "y"): 0.07, ("neck", "pitch"): -12, ("shoulder_L", "abduct"): 26, ("shoulder_R", "abduct"): 24, ("elbow_L", "bend"): 30, ("elbow_R", "bend"): 34, ("knee_L", "bend"): 14, ("knee_R", "bend"): 10},
         "back": {("waist", "pitch"): 22, ("root", "y"): -0.09, ("neck", "pitch"): -16, ("shoulder_L", "flex"): -24, ("shoulder_R", "flex"): -28, ("elbow_L", "bend"): 26, ("elbow_R", "bend"): 22, ("knee_L", "bend"): 20, ("knee_R", "bend"): 12, ("hip_L", "flex"): 14},
         "left": {("waist", "roll"): -16, ("waist", "yaw"): -18, ("root", "x"): -0.07, ("neck", "yaw"): 20, ("shoulder_L", "abduct"): -6, ("shoulder_R", "abduct"): 34, ("elbow_R", "bend"): 36, ("elbow_L", "bend"): 30, ("knee_R", "bend"): 16},
         "right": {("waist", "roll"): 16, ("waist", "yaw"): 18, ("root", "x"): 0.07, ("neck", "yaw"): -20, ("shoulder_R", "abduct"): -6, ("shoulder_L", "abduct"): 34, ("elbow_L", "bend"): 36, ("elbow_R", "bend"): 30, ("knee_L", "bend"): 16},
         "head": {("neck", "pitch"): -30, ("neck", "yaw"): 18, ("waist", "pitch"): -8, ("root", "y"): 0.04, ("shoulder_R", "flex"): 60, ("elbow_R", "bend"): 120, ("knee_L", "bend"): 10, ("knee_R", "bend"): 10},
         "leg": {("knee_R", "bend"): 52, ("hip_R", "flex"): 30, ("root", "z"): -0.10, ("waist", "pitch"): 26, ("waist", "roll"): -10, ("shoulder_L", "abduct"): 40, ("shoulder_R", "flex"): 30, ("elbow_R", "bend"): 60, ("neck", "pitch"): 10}}[kind]
    return lambda u: {k: v * sin(pi * min(1.0, u * 1.7)) * (1 - u) * 1.5 for k, v in P.items()}
def stagger(u):
    a = sin(2 * pi * u * 1.5); k = sin(pi * u)
    return {("root", "y"): 0.50 * smooth(0, 1, u / 0.8), ("root", "x"): 0.06 * a * k, ("root", "roll"): 7 * a * k, ("waist", "pitch"): (-14 + 10 * a) * k, ("waist", "roll"): -8 * a * k, ("neck", "pitch"): -8 * k,
            ("hip_L", "flex"): (-16 * a + 4) * k, ("hip_R", "flex"): (16 * a + 4) * k, ("knee_L", "bend"): (20 + 14 * a) * k, ("knee_R", "bend"): (20 - 14 * a) * k,
            ("shoulder_L", "abduct"): 34 * k, ("shoulder_R", "abduct"): 30 * k, ("elbow_L", "bend"): 40 * k, ("elbow_R", "bend"): 46 * k}

# 손 레이저 3인칭 자세
AIM_PALM = {("shoulder_R", "flex"): 84, ("shoulder_R", "abduct"): -6, ("elbow_R", "bend"): 8, ("elbow_R", "yaw"): 90, ("wrist_R", "abduct"): 70, ("shoulder_L", "flex"): 8, ("elbow_L", "bend"): 30, ("waist", "yaw"): 14, ("neck", "yaw"): -10,
            ("knee_L", "bend"): 12, ("knee_R", "bend"): 8, ("hip_L", "flex"): 10, ("root", "z"): -0.012}
def fire_palm(u):
    out = dict(AIM_PALM); out[("shoulder_R", "flex")] += 0.8 * sin(2 * pi * u * 9); out[("root", "y")] = 0.004 * sin(2 * pi * u * 9); out[("waist", "pitch")] = -1.5; return out

def fp_laser_raise(u):
    k = smooth(0, 1, u); o = sin(pi * u)
    return {("view", "y"): -0.10 * k, ("view", "z"): 0.05 * k - 0.03 * o, ("view", "x"): -0.03 * k, ("view", "pitch"): 6 * k, ("view", "roll"): -8 * k, ("hand", "pitch"): -78 * k, ("finger", "curl"): 8 - 4 * k, ("view", "value"): k}
def fp_laser_fire(u):
    a = sin(2 * pi * u * 7); b = sin(2 * pi * u * 11 + 1.3)
    return {("view", "y"): -0.10 + 0.006 + 0.0025 * a, ("view", "z"): 0.05 + 0.0018 * b, ("view", "x"): -0.03 + 0.0016 * a, ("view", "pitch"): 6 + 0.5 * b, ("view", "roll"): -8 + 0.5 * a, ("hand", "pitch"): -78, ("finger", "curl"): 4, ("view", "value"): 1.0}
def fp_laser_overheat(u):
    k = sin(pi * min(1.0, u * 1.4)); w = sin(2 * pi * u * 5) * (1 - u)
    return {("view", "y"): -0.10 + 0.14 * k, ("view", "z"): 0.05 - 0.12 * k, ("view", "x"): -0.03 + 0.03 * w, ("view", "pitch"): 6 - 26 * k, ("view", "roll"): -8 + 22 * w, ("hand", "pitch"): -78 + 60 * k, ("finger", "curl"): 4 + 30 * k, ("view", "value"): 1.0}
def fp_laser_lower(u):
    k = 1 - smooth(0, 1, u); return {("view", "y"): -0.10 * k, ("view", "z"): 0.05 * k, ("view", "x"): -0.03 * k, ("view", "pitch"): 6 * k, ("view", "roll"): -8 * k, ("hand", "pitch"): -78 * k, ("finger", "curl"): 8 - 4 * k, ("view", "value"): k}

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
    w("lmg_fire", 0.075, lambda u: {("bolt", "move_y"): kick(u, 0.05, 0.3), ("trigger", "pitch"): -10}, [(0.0, "muzzle"), (0.02, "eject")], True)
    w("lmg_reload", 3.4, lambda u: {("cover", "pitch"): 70 * (smooth(0, 1, u / 0.12) if u < 0.70 else 1 - smooth(0, 1, (u - 0.78) / 0.10)),
                                     ("mag", "move_z"): -0.22 * (smooth(0, 1, (u - 0.16) / 0.10) if u < 0.45 else 1 - smooth(0, 1, (u - 0.52) / 0.12)), ("mag", "value"): 0.0 if 0.27 < u < 0.52 else 1.0,
                                     ("bolt", "move_y"): kick(max(0.0, (u - 0.90) / 0.10), 0.05, 0.5)}, [(0.25, "cover_open"), (0.75, "mag_out"), (2.1, "mag_in"), (2.75, "cover_close"), (3.15, "chamber")])
    w("break_reload", 2.0, lambda u: {("barrels", "pitch"): -38 * (smooth(0, 1, u / 0.16) if u < 0.72 else 1 - smooth(0, 1, (u - 0.78) / 0.14)), ("hammer", "pitch"): -30 * smooth(0, 1, (u - 0.90) / 0.08)},
      [(0.2, "open"), (0.45, "eject"), (1.0, "shell_in"), (1.25, "shell_in"), (1.7, "close")])
    w("double_fire", 0.14, lambda u: {("hammer", "pitch"): 30 * (1 - smooth(0, 1, u * 4)), ("trigger", "pitch"): -kick(u, 14, 0.2)}, [(0.0, "muzzle")])
    w("grenade_prime", 0.5, lambda u: {("pin", "move_x"): 0.06 * smooth(0, 1, u / 0.4), ("pin", "value"): 0.0 if u > 0.4 else 1.0, ("lever", "pitch"): 80 * smooth(0, 1, (u - 0.7) / 0.3), ("glow_band", "value"): smooth(0.2, 1, u)}, [(0.2, "pin"), (0.4, "lever")])
    w("baton_arc", 0.6, lambda u: {("arc_glow", "value"): 0.55 + 0.45 * sin(2 * pi * u * 5) * sin(2 * pi * u * 1.5)}, [], True)
    w("hammer_thrust", 0.35, lambda u: {("thruster_glow", "value"): kick(u, 1.0, 0.2)}, [(0.0, "thrust")])
    w("knuckle_impact", 0.3, lambda u: {("impact_glow", "value"): kick(u, 1.0, 0.1)}, [(0.0, "impact")])
    # 사람 추가분
    h = lambda n, d, f, ev=(), loop=False, speed=0.0: c.append(clip(n, d, loop, f, speed, ev))
    h("sit_down", 1.1, sit_down, [(0.9, "seat")]); h("sit_loop", 5.0, sit_loop, loop=True); h("stand_up", 1.0, stand_up)
    h("knockdown", 0.9, knockdown, [(0.62, "body_fall")]); h("lie_loop", 3.0, lie_loop, loop=True); h("get_up", 1.6, get_up); h("collapse", 0.8, collapse, [(0.6, "body_fall")])
    h("aim_pistol", 2.4, hold(AIM_PISTOL), loop=True); h("aim_rifle", 2.4, hold(AIM_RIFLE), loop=True); h("low_ready", 3.0, hold(LOW_READY, 1.2), loop=True)
    h("fire_pistol_3p", 0.18, fire_3p(AIM_PISTOL, 9), [(0.0, "shot")]); h("fire_rifle_3p", 0.11, fire_3p(AIM_RIFLE, 3), [(0.0, "shot")], True)
    h("melee_slash", 0.62, melee_slash, [(0.14, "swing"), (0.27, "hit")]); h("melee_stab", 0.52, melee_stab, [(0.12, "swing"), (0.24, "hit")])
    h("melee_heavy", 1.05, melee_heavy, [(0.40, "swing"), (0.60, "hit")]); h("punch", 0.42, punch, [(0.10, "swing"), (0.20, "hit")]); h("throw", 0.9, throw, [(0.50, "release")])
    # 죽는 동작과 맞는 동작
    h("death_back", 1.1, death_back, [(0.0, "hit"), (0.70, "body_fall")]); h("death_front", 1.2, death_front, [(0.0, "hit"), (0.80, "body_fall")])
    h("death_left", 1.2, death_side(1), [(0.0, "hit"), (0.80, "body_fall")]); h("death_right", 1.2, death_side(-1), [(0.0, "hit"), (0.80, "body_fall")])
    h("death_headshot", 0.8, death_headshot, [(0.0, "hit"), (0.55, "body_fall")]); h("death_knees", 2.2, death_knees, [(0.0, "hit"), (0.45, "knees"), (1.75, "body_fall")])
    h("death_blast", 1.0, death_blast, [(0.0, "blast"), (0.55, "body_fall"), (0.80, "slide")]); h("death_burn", 1.7, death_burn, [(0.0, "burn"), (1.25, "body_fall")])
    h("death_shock", 1.6, death_shock, [(0.0, "shock"), (1.25, "body_fall")]); h("death_slash", 1.4, death_slash, [(0.0, "hit"), (1.05, "body_fall")])
    h("death_sit", 1.3, death_sit, [(0.0, "hit")]); h("fall_wounded", 1.0, fall_wounded, [(0.30, "knees"), (0.75, "body_fall")])
    h("wounded_crawl", 1.8, wounded_crawl, [(0.0, "drag"), (0.9, "drag")], loop=True, speed=0.35); h("death_crawl", 1.1, death_crawl, [(0.9, "body_fall")])
    for kind in ("front", "back", "left", "right", "head", "leg"): h("hit_" + kind, 0.5, hit_dir(kind), [(0.0, "hit")])
    h("stagger", 0.9, stagger, [(0.0, "hit"), (0.3, "foot_R"), (0.6, "foot_L")])
    h("aim_palm", 2.4, hold(AIM_PALM, 0.6), loop=True); h("fire_palm", 0.4, fire_palm, [(0.0, "beam")], True)
    # 1인칭
    f = lambda n, d, fn, ev=(), loop=False: c.append(clip(n, d, loop, fn, events=ev, rig="fp"))
    f("fp_idle", 4.0, fp_idle, loop=True); f("fp_raise_light", 0.30, fp_raise, [(0.0, "draw")]); f("fp_raise_heavy", 0.60, fp_raise, [(0.0, "draw")]); f("fp_lower", 0.25, fp_lower)
    f("fp_recoil_pistol", 0.22, fp_recoil(0.030, 4.2, 0.6), [(0.0, "shot")]); f("fp_recoil_revolver", 0.34, fp_recoil(0.050, 9.0, 1.0), [(0.0, "shot")])
    f("fp_recoil_auto", 0.12, fp_recoil(0.014, 1.3, 0.5), [(0.0, "shot")]); f("fp_recoil_lmg", 0.11, fp_recoil(0.018, 1.0, 0.9), [(0.0, "shot")])
    f("fp_recoil_shotgun", 0.42, fp_recoil(0.075, 11.0, 1.4), [(0.0, "shot")]); f("fp_recoil_sniper", 0.60, fp_recoil(0.095, 13.0, 0.8), [(0.0, "shot")])
    f("fp_reload", 1.6, fp_reload, [(0.05, "mag_out"), (1.0, "mag_in"), (1.35, "chamber")]); f("fp_ads_in", 0.18, fp_ads); f("fp_ads_out", 0.16, lambda u: fp_ads(1 - u))
    f("fp_slash", 0.62, fp_slash, [(0.14, "swing"), (0.27, "hit")]); f("fp_stab", 0.52, fp_stab, [(0.12, "swing"), (0.22, "hit")]); f("fp_punch", 0.42, fp_punch, [(0.08, "swing"), (0.17, "hit")])
    f("fp_laser_raise", 0.35, fp_laser_raise, [(0.0, "charge")]); f("fp_laser_fire", 0.5, fp_laser_fire, [(0.0, "beam")], True); f("fp_laser_overheat", 1.2, fp_laser_overheat, [(0.0, "overheat")]); f("fp_laser_lower", 0.25, fp_laser_lower)
    f("fp_heavy", 1.05, fp_heavy, [(0.40, "swing"), (0.60, "hit")]); f("fp_throw", 0.9, fp_throw, [(0.48, "release")]); f("fp_inspect", 3.0, fp_inspect); f("fp_sprint", 1.0, fp_sprint, loop=True); f("fp_land", 0.35, fp_land)
    # 사이버웨어 팔 (rig = cyberarm): joint = 부품 이름. open = 문 여는 각(도), move_x = 앞으로 미는 거리(m), move_z = 올리는 거리(m), value = 발광 0~1
    a = lambda n, d, fn, ev=(): c.append(clip(n, d, False, fn, events=ev, rig="cyberarm"))
    a("blade_deploy", 0.38, lambda u: {("door", "open"): 56 * smooth(0, 1, u / 0.40), ("blade", "move_x"): 0.23 * smooth(0, 1, (u - 0.36) / 0.52), ("edge_glow", "value"): smooth(0, 1, (u - 0.7) / 0.3)}, [(0.0, "open"), (0.14, "blade_out"), (0.34, "lock")])
    a("blade_retract", 0.32, lambda u: {("door", "open"): 56 * (1 - smooth(0, 1, (u - 0.5) / 0.5)), ("blade", "move_x"): 0.23 * (1 - smooth(0, 1, u / 0.55)), ("edge_glow", "value"): 1 - smooth(0, 1, u / 0.3)}, [(0.0, "blade_in"), (0.2, "close")])
    a("power_charge", 0.45, lambda u: {("knuckle_plate", "move_x"): 0.020 * smooth(0, 1, u / 0.3), ("piston", "move_x"): 0.018 * smooth(0, 1, u / 0.35), ("charge_glow", "value"): smooth(0, 1, u), ("finger", "curl"): 80 * smooth(0, 1, u / 0.3)}, [(0.0, "charge"), (0.45, "ready")])
    a("power_release", 0.30, lambda u: {("knuckle_plate", "move_x"): 0.020 * (1 - smooth(0, 1, u)), ("piston", "move_x"): 0.018 * (1 - kick(u, 1.0, 0.15)), ("charge_glow", "value"): 1 - smooth(0, 1, u / 0.5), ("finger", "curl"): 80}, [(0.0, "impact")])
    a("wire_deploy", 0.35, lambda u: {("spool_cover", "move_x"): -0.034 * smooth(0, 1, u / 0.3), ("spool", "spin"): 720 * smooth(0, 1, u), ("glow", "value"): 0.4 + 0.6 * smooth(0, 1, u), ("wire", "value"): smooth(0, 1, (u - 0.25) / 0.75)}, [(0.0, "open"), (0.1, "wire_out")])
    a("wire_retract", 0.30, lambda u: {("spool_cover", "move_x"): -0.034 * (1 - smooth(0, 1, (u - 0.6) / 0.4)), ("spool", "spin"): -720 * smooth(0, 1, u), ("glow", "value"): 1 - 0.6 * smooth(0, 1, u), ("wire", "value"): 1 - smooth(0, 1, u / 0.7)}, [(0.0, "wire_in"), (0.2, "close")])
    a("launcher_deploy", 0.40, lambda u: {("hatch", "open"): 72 * smooth(0, 1, u / 0.45), ("tube", "move_z"): 0.030 * smooth(0, 1, (u - 0.35) / 0.5), ("tube", "pitch"): -6 * smooth(0, 1, (u - 0.5) / 0.5), ("glow", "value"): 0.3 + 0.7 * smooth(0, 1, u)}, [(0.0, "open"), (0.16, "tube_up"), (0.38, "lock")])
    a("launcher_fire", 0.50, lambda u: {("hatch", "open"): 72, ("tube", "move_z"): 0.030, ("tube", "pitch"): -6, ("tube", "move_x"): -0.022 * kick(u, 1.0, 0.08), ("rocket", "value"): 0.0}, [(0.0, "muzzle"), (0.0, "backblast")])
    a("launcher_retract", 0.36, lambda u: {("hatch", "open"): 72 * (1 - smooth(0, 1, (u - 0.45) / 0.55)), ("tube", "move_z"): 0.030 * (1 - smooth(0, 1, u / 0.5)), ("tube", "pitch"): -6 * (1 - smooth(0, 1, u / 0.4)), ("glow", "value"): 1 - 0.7 * smooth(0, 1, u)}, [(0.0, "tube_down"), (0.18, "close")])
    a("laser_deploy", 0.40, lambda u: {("hand", "pitch"): -78 * smooth(0, 1, u / 0.35), ("finger", "curl"): 8 - 4 * smooth(0, 1, u / 0.35), ("iris", "value"): smooth(0, 1, (u - 0.2) / 0.3), ("cell_glow", "value"): 0.3 + 0.7 * smooth(0, 1, u)}, [(0.0, "charge"), (0.22, "iris_open"), (0.38, "ready")])
    c.append(clip("laser_fire", 0.5, True, lambda u: {("hand", "pitch"): -78, ("finger", "curl"): 4, ("iris", "value"): 1.0, ("cell_glow", "value"): 0.8 + 0.2 * sin(2 * pi * u * 6), ("emitter", "value"): 1.0, ("beam", "value"): 1.0}, events=[(0.0, "beam")], rig="cyberarm"))
    a("laser_overheat", 2.0, lambda u: {("hand", "pitch"): -78 * (1 - smooth(0, 1, u / 0.25)), ("finger", "curl"): 4 + 14 * smooth(0, 1, u / 0.25), ("iris", "value"): 1 - smooth(0, 1, u / 0.15), ("vent", "open"): 55 * (smooth(0, 1, u / 0.12) if u < 0.8 else 1 - smooth(0, 1, (u - 0.8) / 0.2)),
                                        ("heat_glow", "value"): (smooth(0, 1, u / 0.1) if u < 0.2 else 1 - smooth(0, 1, (u - 0.2) / 0.7)), ("cell_glow", "value"): 0.1 + 0.2 * smooth(0, 1, (u - 0.7) / 0.3), ("beam", "value"): 0.0, ("emitter", "value"): 0.0},
      [(0.0, "overheat"), (0.05, "vent_open"), (0.1, "steam"), (1.7, "vent_close"), (2.0, "ready")])
    a("laser_retract", 0.30, lambda u: {("hand", "pitch"): -78 * (1 - smooth(0, 1, u)), ("finger", "curl"): 4 + 4 * smooth(0, 1, u), ("iris", "value"): 1 - smooth(0, 1, u / 0.5), ("cell_glow", "value"): 1 - 0.7 * smooth(0, 1, u), ("beam", "value"): 0.0, ("emitter", "value"): 0.0}, [(0.0, "iris_close")])
    # 보안 기계 (rig = machine): joint = manifest의 관절 이름. yaw·pitch는 도, spin은 초당 회전수, value는 발광 0~1
    m = lambda n, d, fn, ev=(), loop=False: c.append(clip(n, d, loop, fn, events=ev, rig="machine"))
    m("drone_hover", 3.0, lambda u: {("root", "z"): 0.05 * sin(2 * pi * u), ("root", "roll"): 2.0 * sin(2 * pi * u + 1.0), ("root", "pitch"): 1.5 * sin(4 * pi * u), ("fan", "spin"): 40, ("gimbal_yaw", "yaw"): 50 * sin(2 * pi * u), ("gun_pitch", "pitch"): -12}, loop=True)
    m("drone_alert", 0.4, lambda u: {("root", "z"): 0.10 * sin(pi * u), ("root", "pitch"): 8 * smooth(0, 1, u), ("fan", "spin"): 40 + 25 * smooth(0, 1, u), ("gun_pitch", "pitch"): -12 + 12 * smooth(0, 1, u), ("eye", "value"): 0.4 + 0.6 * smooth(0, 1, u)}, [(0.0, "alert")])
    m("drone_fire", 0.10, lambda u: {("root", "pitch"): 8 - 1.5 * kick(u, 1.0), ("root", "y"): 0.010 * kick(u, 1.0), ("fan", "spin"): 65, ("eye", "value"): 1.0}, [(0.0, "muzzle")], True)
    m("drone_crash", 1.2, lambda u: {("root", "z"): -1.6 * u * u, ("root", "roll"): 200 * u * u, ("root", "pitch"): 40 * u, ("fan", "spin"): 40 * (1 - u), ("eye", "value"): 1 - smooth(0, 1, u * 2)}, [(0.0, "disabled"), (1.2, "impact")])
    m("turret_scan", 6.0, lambda u: {("yaw", "yaw"): 70 * sin(2 * pi * u), ("pitch", "pitch"): -4 + 3 * sin(4 * pi * u), ("status_glow", "value"): 0.5}, loop=True)
    m("turret_alert", 0.35, lambda u: {("pitch", "pitch"): -4 + 4 * smooth(0, 1, u), ("status_glow", "value"): 0.5 + 0.5 * smooth(0, 1, u), ("eye", "value"): 0.5 + 0.5 * smooth(0, 1, u)}, [(0.0, "alert")])
    m("turret_fire", 0.09, lambda u: {("recoil", "move_y"): kick(u, 0.035, 0.25), ("status_glow", "value"): 1.0, ("eye", "value"): 1.0}, [(0.0, "muzzle"), (0.02, "eject")], True)
    m("turret_shutdown", 1.0, lambda u: {("pitch", "pitch"): 30 * smooth(0, 1, u), ("status_glow", "value"): 1 - smooth(0, 1, u), ("eye", "value"): (1 - u) * (0.5 + 0.5 * sin(40 * u))}, [(0.0, "disabled")])
    m("camera_sweep", 8.0, lambda u: {("pan", "yaw"): 60 * sin(2 * pi * u), ("tilt", "pitch"): -18, ("eye", "value"): 0.6}, loop=True)
    m("camera_alert", 0.3, lambda u: {("tilt", "pitch"): -18, ("eye", "value"): 0.6 + 0.4 * sin(2 * pi * u * 3) ** 2}, [(0.0, "alert")])
    m("camera_disabled", 0.8, lambda u: {("tilt", "pitch"): -18 - 30 * smooth(0, 1, u), ("eye", "value"): 0.6 * (1 - smooth(0, 1, u * 1.5))}, [(0.0, "disabled")])
    # 시술소 (rig = clinic)
    k = lambda n, d, fn, ev=(), loop=False: c.append(clip(n, d, loop, fn, events=ev, rig="clinic"))
    k("chair_recline", 1.6, lambda u: {("recline", "pitch"): -22 * smooth(0, 1, u), ("legrest", "pitch"): -18 * smooth(0, 1, u), ("lift", "move_z"): 0.06 * smooth(0, 1, u / 0.6), ("status_glow", "value"): 0.4 + 0.6 * smooth(0, 1, u)}, [(0.0, "motor"), (1.5, "lock")])
    k("chair_release", 1.4, lambda u: {("recline", "pitch"): -22 * (1 - smooth(0, 1, u)), ("legrest", "pitch"): -18 * (1 - smooth(0, 1, u)), ("lift", "move_z"): 0.06 * (1 - smooth(0, 1, u)), ("status_glow", "value"): 1 - 0.6 * smooth(0, 1, u)}, [(0.0, "motor")])
    k("surgery_loop", 6.0, lambda u: {("arm_A_shoulder", "yaw"): 10 * sin(2 * pi * u), ("arm_A_elbow", "pitch"): 8 * sin(4 * pi * u + 0.4), ("arm_A_wrist", "pitch"): 14 * sin(6 * pi * u),
                                      ("arm_B_shoulder", "yaw"): -8 * sin(2 * pi * u + 1.2), ("arm_B_elbow", "pitch"): 10 * sin(4 * pi * u + 2.0), ("arm_B_wrist", "pitch"): 18 * sin(8 * pi * u),
                                      ("arm_C_shoulder", "yaw"): 22 * sin(2 * pi * u), ("arm_C_elbow", "pitch"): 4 * sin(2 * pi * u), ("lamp", "yaw"): 4 * sin(2 * pi * u), ("tool_glow", "value"): 0.6 + 0.4 * sin(2 * pi * u * 9) ** 2},
      [(0.5, "laser"), (1.6, "servo"), (2.9, "laser"), (4.2, "servo")], True)
    k("surgery_start", 1.2, lambda u: {("arm_A_elbow", "pitch"): -30 * (1 - smooth(0, 1, u)), ("arm_B_elbow", "pitch"): -30 * (1 - smooth(0, 1, u)), ("arm_C_elbow", "pitch"): -24 * (1 - smooth(0, 1, u)), ("tool_glow", "value"): smooth(0, 1, u), ("work_light", "value"): smooth(0.2, 1, u * 2)}, [(0.0, "servo"), (0.3, "light_on")])
    return c

def golden(clips):
    """Luau 포팅 검증용: 클립과 시각 -> 기대 값."""
    out = []
    for cl in clips:
        if cl["name"] not in ("walk", "run", "cower_enter", "robot_fire", "mag_reload", "knockdown", "fp_reload", "launcher_deploy", "turret_scan", "death_back", "death_burn", "laser_overheat"): continue
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
