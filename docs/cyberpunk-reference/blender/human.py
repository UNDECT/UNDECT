"""맨얼굴 사람 (MPFB + MakeHuman CC0 에셋) + 자체 사이버웨어 장식.
실행: python human.py <출력폴더> [render] [이름...]
필요: Blender 확장 MPFB 2.0.x, MakeHuman 에셋 묶음(CC0만 사용)을 MPFB 사용자 데이터 폴더에 풀어 둘 것. README 참고.
MPFB는 GPL이라 저장소에 넣지 않는다. 만들어진 사람은 CC0 에셋 + 이 스크립트가 만든 장식으로만 이뤄진다.
-Y를 바라본다. 뼈대는 MPFB의 game_engine 리그(뼈 53개)다.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from math import radians
from mathutils import Vector, Matrix
import kit
from kit import finish, box, cyl, torus, T, RX, RY, RZ, S

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = ARGS[0] if ARGS else "out/human"
RENDER = len(ARGS) > 1 and ARGS[1] == "render"
ONLY = ARGS[2:] if len(ARGS) > 2 else []
DATA = os.path.expanduser(os.environ.get("MPFB_DATA", "~/.config/blender/5.3/extensions/.user/user_default/mpfb/data"))
TEX = 1024
NOT_CC0_PACKS = ("hair03", "masks02")   # CC-BY 묶음은 쓰지 않는다

def cc0_assets():
    ok = set()
    for f in os.listdir(os.path.join(DATA, "packs")):
        if f.endswith(".json") and f[:-5] not in NOT_CC0_PACKS: ok |= set(json.load(open(os.path.join(DATA, "packs", f))).keys())
    return ok

def asset(kind, name, ext="mhclo"):
    p = os.path.join(DATA, kind, name, name + "." + ext)
    if not os.path.exists(p):
        c = [f for f in os.listdir(os.path.join(DATA, kind, name)) if f.endswith("." + ext)]
        p = os.path.join(DATA, kind, name, c[0])
    return p

# 색: 옷을 흑백으로 만든 뒤 이 색(선형 값, 옷의 평균색)을 입힌다. 어둡고 채도 낮게, 포인트만 진하게
INK, CHAR, OLIVE, NAVY, RUST, BONE, TEAL, WINE = (0.012, 0.012, 0.015), (0.045, 0.045, 0.052), (0.075, 0.085, 0.04), (0.02, 0.035, 0.095), (0.28, 0.085, 0.03), (0.45, 0.42, 0.36), (0.018, 0.085, 0.095), (0.17, 0.02, 0.035)
# 쓰지 않는 에셋: 다른 프로젝트 로고가 찍힌 옷(casualsuit02·04, female_casualsuit01·02), 정치 문구 모자, 다른 작품 캐릭터를 닮은 소품
PEOPLE = {
    # 전원 성인이다(age 0.5 = 25세쯤, 1.0 = 노인. 0.5 아래는 쓰지 않는다). gender 0 여 ~ 1 남, race = (아시아, 백인, 아프리카). tint = 옷 이름 -> 입힐 색. cyber = 붙일 장식. hair_tint = 머리 염색
    "man_a": dict(role="거리 사람", gender=1.0, age=0.52, weight=0.50, muscle=0.55, height=0.6, race=(0.8, 0.2, 0.0), skin="young_asian_male", hair="short01", brow="eyebrow003",
                  clothes=["male_casualsuit05"], shoes="shoes04", tint={"male_casualsuit05": CHAR}, cyber=["visor", "ear"], glow="glow_cyan"),
    "woman_a": dict(role="거리 사람", gender=0.0, age=0.5, weight=0.42, muscle=0.40, height=0.55, race=(0.75, 0.25, 0.0), skin="young_asian_female", hair="bob02", brow="eyebrow006",
                    clothes=["joepal_crude_t-shirt_female", "cortu_cargo_pants", "toigo_gloves_short"], shoes="toigo_ankle_boots_female",
                    tint={"joepal_crude_t-shirt_female": INK, "cortu_cargo_pants": NAVY}, hair_tint=(0.10, 0.75, 0.80), cyber=["cheek", "neck"], glow="glow_magenta"),
    "man_b": dict(role="노동자", gender=1.0, age=0.62, weight=0.62, muscle=0.50, height=0.55, race=(0.05, 0.15, 0.8), skin="middleage_african_male", hair="short04", brow="eyebrow009",
                  clothes=["male_worksuit01"], shoes="shoes05", tint={"male_worksuit01": RUST}, cyber=["ear", "neck"], glow="glow_amber"),
    "woman_b": dict(role="회사원", gender=0.0, age=0.56, weight=0.45, muscle=0.38, height=0.62, race=(0.1, 0.85, 0.05), skin="young_caucasian_female", hair="braid01", brow="eyebrow001",
                    clothes=["toigo_female_double-breasted_suit"], shoes="toigo_ankle_boots_female", tint={"toigo_female_double-breasted_suit": INK}, cyber=["visor_thin", "ear"], glow="glow_cyan"),
    "man_c": dict(role="임원", gender=1.0, age=0.85, weight=0.55, muscle=0.35, height=0.5, race=(0.1, 0.85, 0.05), skin="old_caucasian_male", hair="short04", brow="eyebrow010",
                  clothes=["toigo_male_double-breasted_suit"], shoes="shoes01", tint={"toigo_male_double-breasted_suit": INK}, hair_tint=(0.7, 0.7, 0.72), cyber=["eyes", "neck"], glow="glow_red"),
    "woman_c": dict(role="거리 사람", gender=0.0, age=0.5, weight=0.48, muscle=0.55, height=0.6, race=(0.05, 0.1, 0.85), skin="young_african_female", hair="afro01", brow="eyebrow005",
                    clothes=["toigo_basic_tucked_t-shirt", "cortu_cargo_pants", "toigo_gloves_short"], shoes="toigo_ankle_boots_female",
                    tint={"toigo_basic_tucked_t-shirt": WINE, "cortu_cargo_pants": INK}, hair_tint=(0.9, 0.15, 0.55), cyber=["visor", "cheek"], glow="glow_magenta"),
    "man_d": dict(role="거리 사람", gender=1.0, age=0.5, weight=0.44, muscle=0.50, height=0.5, race=(0.9, 0.1, 0.0), skin="young_asian_male", hair="short02", brow="eyebrow004",
                  clothes=["elvs_crude_t-shirt_male", "cortu_cargo_pants", "toigo_gloves_short"], shoes="toigo_ankle_boots_male",
                  tint={"elvs_crude_t-shirt_male": INK, "cortu_cargo_pants": OLIVE}, hair_tint=(0.85, 0.75, 0.15), cyber=["cheek", "ear", "neck"], glow="glow_amber"),
    "woman_d": dict(role="거리 사람", gender=0.0, age=0.58, weight=0.50, muscle=0.40, height=0.58, race=(0.3, 0.6, 0.1), skin="middleage_caucasian_female", hair="long01", brow="eyebrow002",
                    clothes=["toigo_female_suit_2"], shoes="toigo_ankle_boots_female", tint={"toigo_female_suit_2": WINE}, hair_tint=(0.75, 0.78, 0.85), cyber=["cheek", "ear"], glow="glow_cyan"),
    "merchant": dict(role="상인", gender=1.0, age=0.74, weight=0.72, muscle=0.40, height=0.42, race=(0.6, 0.3, 0.1), skin="old_asian_male", hair="short04", brow="eyebrow007",
                     clothes=["namuhekam_male_polo_shirt", "toigo_wool_pants", "jujube_newsboy_cap"], shoes="shoes05", tint={"namuhekam_male_polo_shirt": OLIVE, "toigo_wool_pants": INK, "jujube_newsboy_cap": CHAR},
                     hair_tint=(0.6, 0.6, 0.62), cyber=["ear", "neck", "badge"], glow="glow_amber"),
    # 시술소 의사: 수술복 느낌의 청록 작업복 + 장갑 + 확대경 + 귀 장치 + 가슴 표지
    "doctor": dict(role="시술의", gender=1.0, age=0.7, weight=0.58, muscle=0.45, height=0.5, race=(0.7, 0.3, 0.0), skin="middleage_asian_male", hair="short04", brow="eyebrow008",
                   clothes=["male_casualsuit01", "toigo_gloves_short"], shoes="toigo_ankle_boots_male",
                   tint={"male_casualsuit01": TEAL}, cyber=["monocle", "ear", "neck", "badge"], glow="glow_cyan"),
}

# 1인칭 팔: 사람을 만든 뒤 팔만 남긴다. 소매+장갑, 맨팔 두 가지
PEOPLE["fp_sleeve"] = dict(role="1인칭 팔(재킷 소매 + 장갑)", fp=True, gender=1.0, age=0.52, weight=0.50, muscle=0.60, height=0.60, race=(0.5, 0.4, 0.1), skin="young_caucasian_male", hair="short01", brow="eyebrow003",
                           clothes=["male_casualsuit05", "toigo_gloves_short"], shoes="shoes04", tint={"male_casualsuit05": CHAR}, cyber=[], glow="glow_cyan")
PEOPLE["fp_bare"] = dict(role="1인칭 팔(맨팔)", fp=True, gender=1.0, age=0.52, weight=0.50, muscle=0.65, height=0.60, race=(0.5, 0.4, 0.1), skin="young_caucasian_male", hair="short01", brow="eyebrow003",
                         clothes=["elvs_crude_t-shirt_male", "cortu_cargo_pants"], shoes="shoes04", tint={"elvs_crude_t-shirt_male": INK}, cyber=[], glow="glow_cyan")
ARM_BONES = ("upperarm_", "lowerarm_", "hand_", "index_", "middle_", "ring_", "pinky_", "thumb_")

def keep_arms(rig):
    """팔 뼈에 붙은 부분만 남기고 나머지 형상을 지운다. 눈 위치(카메라 자리)를 돌려준다."""
    import bmesh
    eyes = find(".high-poly"); bb = [eyes.matrix_world @ Vector(c) for c in eyes.bound_box]; eye = [round(sum(v[i] for v in bb) / 8, 4) for i in range(3)]
    for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        arm = {g.index for g in ob.vertex_groups if g.name.startswith(ARM_BONES)}; bone = {g.index for g in ob.vertex_groups if g.name in rig.data.bones}
        keep = set()
        for v in ob.data.vertices:
            wa = sum(g.weight for g in v.groups if g.group in arm); wt = sum(g.weight for g in v.groups if g.group in bone)
            if wt > 0 and wa / wt > 0.5: keep.add(v.index)
        if not keep: bpy.data.objects.remove(ob); continue
        for m in [m for m in ob.modifiers if m.type == "MASK"]:   # 가림 마스크를 먼저 굳힌다
            vg = ob.vertex_groups.get(m.vertex_group)
            if vg: keep -= {v.index for v in ob.data.vertices if any(g.group == vg.index and g.weight > 0.5 for g in v.groups)} if m.invert_vertex_group else {v.index for v in ob.data.vertices if not any(g.group == vg.index and g.weight > 0.5 for g in v.groups)}
            ob.modifiers.remove(m)
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS"); bm.to_mesh(ob.data); bm.free()
        if not ob.data.vertices: bpy.data.objects.remove(ob)
    return eye

def tint(ob, color, strength=1.0, lift=1.0):
    """바탕색 텍스처를 흑백으로 만든 뒤, 평균 밝기가 color가 되도록 색을 입혀 새 그림으로 바꾼다(옷·머리 염색).
    원본이 밝든 어둡든 결과 색이 같다. lift < 1이면 어두운 부분을 끌어올린다(검은 머리 염색용). 내보낸 파일에도 그대로 남는다."""
    import numpy as np
    for sl in ob.material_slots:
        m = sl.material
        for n in ([n for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.name == "diffuseTexture" and n.image] if m and m.node_tree else []):
            im = n.image
            if max(im.size) > TEX: im.scale(min(TEX, im.size[0]), min(TEX, im.size[1]))
            w, h = im.size; a = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
            lin = np.where(a[:, :3] <= 0.04045, a[:, :3] / 12.92, ((a[:, :3] + 0.055) / 1.055) ** 2.4)
            lum = (lin @ np.array([0.2126, 0.7152, 0.0722], np.float32))[:, None] ** lift
            used = (a[:, 3:4] > 0.5) & (lum > 0.004); mean = float(lum[used].mean()) if used.any() else 0.2
            out = np.clip(lin * (1 - strength) + strength * (lum / mean) * np.array(color, np.float32), 0, 1)
            a[:, :3] = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
            im2 = bpy.data.images.new(im.name.rsplit(".", 1)[0] + "_" + ob.name.split(".")[-1] + "_tint", w, h, alpha=True)
            im2.pixels = a.ravel(); im2.pack(); n.image = im2

def band(r, thick, h, half_deg, n=28):
    """머리를 감싸는 휜 띠. 앞(-Y)을 중심으로 좌우 half_deg도."""
    import bmesh
    from math import sin, cos
    bm = bmesh.new(); ring = []
    for i in range(n + 1):
        a = radians(-half_deg + 2 * half_deg * i / n); sx, cy = sin(a), -cos(a)
        ring.append([bm.verts.new((rr * sx, rr * cy, z)) for rr in (r, r + thick) for z in (-h / 2, h / 2)])
    for i in range(n):
        a, b = ring[i], ring[i + 1]
        for q in ((0, 1), (1, 3), (3, 2), (2, 0)): bm.faces.new((a[q[0]], a[q[1]], b[q[1]], b[q[0]]))
    bm.faces.new(ring[0]); bm.faces.new(ring[-1][::-1]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def find(suffix):
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o.name.endswith(suffix): return o

def attach(ob, rig, bone):
    mw = ob.matrix_world.copy(); ob.parent = rig; ob.parent_type = "BONE"; ob.parent_bone = bone
    bpy.context.view_layer.update(); ob.matrix_world = mw

def cyberware(sp, base, rig):
    """눈·귀·목 위치를 실제 얼굴에서 찾아 자체 장식을 붙인다."""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); ev = base.evaluated_get(dg)
    eyes = find(".high-poly"); bb = [eyes.matrix_world @ Vector(c) for c in eyes.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb); yf = min(v.y for v in bb); ez = sum(v.z for v in bb) / 8
    def hit(origin, direction):
        ok, loc, nor, _ = ev.ray_cast(Vector(origin), Vector(direction))
        return loc if ok else None
    g = sp["glow"]; made = []; n0 = set(kit.COL.objects)
    for c in sp["cyber"]:
        if c in ("visor", "visor_thin"):
            h = 0.030 if c == "visor" else 0.015; t = hit((0.3, yf + 0.045, ez), (-1, 0, 0)); r = (t.x if t else 0.072) + 0.006; yc = yf - 0.016 + r
            kit.mat_simple("visor_lens", (0.012, 0.03, 0.04) if g == "glow_cyan" else (0.04, 0.012, 0.03), 0.9, 0.06)
            finish("visor_lens", band(r, 0.0025, h, 74), "visor_lens", 0, 1, T(0, yc, ez + 0.002), "cyber_head", smooth=True)
            finish("visor_frame", band(r + 0.0008, 0.004, 0.004, 76), "gunmetal", 0, 1, T(0, yc, ez + 0.002 + h / 2), "cyber_head", smooth=True)
            finish("visor_line", band(r + 0.0030, 0.0012, 0.0022, 60), g, 0, 1, T(0, yc, ez + 0.002 - h / 2 + 0.004), "cyber_head", smooth=True)
            from math import sin, cos
            for s in (-1, 1):
                ax, ay = s * r * sin(radians(74)), yc - r * cos(radians(74))
                finish("visor_arm", box(0.004, 0.060, 0.010), "gunmetal", 0.001, 1, T(ax, ay + 0.030, ez + 0.004), "cyber_head")
                finish("visor_hinge", cyl(0.005, 0.005, 0.012, 10, "z"), "chrome", 0, 1, T(ax, ay, ez + 0.004), "cyber_head")
        elif c == "monocle":
            cx = x1 - (x1 - x0) * 0.2
            finish("monocle_ring", torus(0.021, 0.004, 20, 8, "y"), "gunmetal", 0, 1, T(cx, yf - 0.014, ez), "cyber_head")
            finish("monocle_lens", cyl(0.019, 0.019, 0.003, 20, "y"), g, 0, 1, T(cx, yf - 0.014, ez), "cyber_head")
            finish("monocle_barrel", cyl(0.012, 0.016, 0.030, 16, "y"), "gunmetal", 0.001, 1, T(cx, yf - 0.030, ez), "cyber_head")
            finish("monocle_arm", box(0.050, 0.006, 0.006), "gunmetal", 0.001, 1, T(cx + 0.030, yf - 0.004, ez + 0.012) @ RZ(-25), "cyber_head")
        elif c == "eyes":
            for sl in eyes.material_slots:
                b = next((n for n in sl.material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if b:
                    b.inputs["Emission Color"].default_value = (1.0, 0.15, 0.1, 1); b.inputs["Emission Strength"].default_value = 0.9
        elif c == "ear":
            p = hit((-0.3, yf + 0.098, ez - 0.012), (1, 0, 0))
            if p:
                finish("ear_disc", cyl(0.017, 0.014, 0.008, 18, "x"), "gunmetal", 0.001, 1, T(p.x - 0.003, p.y, p.z) @ RZ(180), "cyber_head")
                finish("ear_led", cyl(0.006, 0.006, 0.002, 12, "x"), g, 0, 1, T(p.x - 0.0075, p.y, p.z), "cyber_head")
                finish("ear_bar", box(0.004, 0.044, 0.005), "gunmetal", 0.001, 1, T(p.x - 0.004, p.y - 0.026, p.z + 0.010) @ RX(-14), "cyber_head")
                finish("ear_tip", box(0.005, 0.006, 0.007), g, 0, 1, T(p.x - 0.004, p.y - 0.050, p.z + 0.016), "cyber_head")
        elif c == "cheek":
            for s in (-1, 1):
                for k in range(2):
                    p = hit((s * (0.030 + 0.012 * k), yf - 0.3, ez - 0.036 - 0.012 * k), (0, 1, 0))
                    if p: finish("cheek_line", box(0.020, 0.0016, 0.0022), g, 0, 1, T(p.x, p.y - 0.0008, p.z) @ RZ(-s * 28) @ RY(s * 12), "cyber_head")
        elif c == "neck":
            p = hit((0.0, 0.4, ez - 0.118), (0, -1, 0))
            if p:
                finish("neck_port", cyl(0.014, 0.012, 0.006, 16, "y"), "gunmetal", 0.001, 1, T(p.x, p.y + 0.002, p.z), "cyber_neck")
                finish("neck_led", cyl(0.005, 0.005, 0.002, 10, "y"), g, 0, 1, T(p.x, p.y + 0.0056, p.z), "cyber_neck")
                for s in (-1, 1): finish("neck_pin", cyl(0.003, 0.003, 0.004, 8, "y"), "chrome", 0, 1, T(p.x + s * 0.020, p.y + 0.001, p.z + 0.004), "cyber_neck")
        elif c == "badge":
            cl = find("." + sp["clothes"][0]); ec = cl.evaluated_get(dg); ok, p, _, _ = ec.ray_cast(Vector((0.085, yf - 0.4, ez - 0.30)), Vector((0, 1, 0)))
            if ok:
                finish("badge", box(0.050, 0.004, 0.030), "gunmetal", 0.002, 1, T(p.x, p.y - 0.003, p.z), "cyber_chest")
                finish("badge_glow", box(0.040, 0.002, 0.008), g, 0, 1, T(p.x, p.y - 0.006, p.z + 0.006), "cyber_chest")
    for o in set(kit.COL.objects) - n0:
        attach(o, rig, {"cyber_head": "head", "cyber_neck": "neck_01", "cyber_chest": "spine_03"}[o["part"]]); made.append(o.name)
    return made

def aim(rig, bone, d):
    """뼈가 d 방향(세계 좌표)을 가리키게 돌린다."""
    bpy.context.view_layer.update(); pb = rig.pose.bones[bone]; h = pb.head.copy()
    q = (pb.tail - pb.head).normalized().rotation_difference(Vector(d).normalized())
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix

# 의미 관절(anim.py) -> 이 뼈대의 뼈
SEM = [("waist", "spine_01"), ("neck", "neck_01")] + [(f"{j}_{S}", f"{b}_{c}") for S, c in (("L", "l"), ("R", "r"))
       for j, b in (("hip", "thigh"), ("knee", "calf"), ("ankle", "foot"), ("shoulder", "upperarm"), ("elbow", "lowerarm"), ("wrist", "hand"))]
FINGERS = ("thumb", "index", "middle", "ring", "pinky")

def rig_joints(rig):
    """의미 관절 대응표. 이 뼈대의 기본 자세는 팔을 벌린 자세라서, 팔을 내린 '중립 자세'까지의 회전(neutral)도 같이 적는다.
    손가락 관절(index_L_1 ...)은 curl 한 가지로만 움직인다. axis = 중립 자세에서 그 마디가 손바닥 쪽으로 굽는 축."""
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update(); rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    for side, sg in (("l", 1), ("r", -1)):
        aim(rig, "upperarm_" + side, (sg * 0.10, 0.0, -1)); aim(rig, "lowerarm_" + side, (sg * 0.07, -0.03, -1))
    bpy.context.view_layer.update(); driven = {b for _, b in SEM} | {f"{f}_0{k}_{c}" for f in FINGERS for k in (1, 2, 3) for c in "lr"}
    def anc(bone):
        p = rig.data.bones[bone].parent
        while p and p.name not in driven and p.name != "pelvis": p = p.parent
        return p.name if p else "pelvis"
    joints = {"root": {"bone": "pelvis", "pos": [round(v, 5) for v in rest["pelvis"].translation]}}
    def add(j, b, axis=None):
        N = (rig.pose.bones[b].matrix @ rest[b].inverted()).to_3x3()
        joints[j] = {"bone": b, "parent": anc(b), "pos": [round(v, 5) for v in rest[b].translation], "neutral": [round(N[r][c], 6) for r in range(3) for c in range(3)]}
        if axis is not None: joints[j]["axis"] = [round(v, 5) for v in (N @ axis).normalized()]
    for j, b in SEM: add(j, b)
    H = lambda n: rig.data.bones[n].head_local.copy(); D = lambda n: (rig.data.bones[n].tail_local - rig.data.bones[n].head_local).normalized()
    for S, c in (("L", "l"), ("R", "r")):
        n = (H("index_01_" + c) - H("hand_" + c)).cross(H("pinky_01_" + c) - H("hand_" + c)).normalized()
        if n.dot(H("thumb_02_" + c) - H("hand_" + c)) < 0: n = -n          # n = 손바닥이 보는 쪽
        for f in FINGERS:
            for k in (1, 2, 3):
                b = f"{f}_0{k}_{c}"; d = D(b)
                v = (H("index_01_" + c) - H("thumb_01_" + c)).normalized() + n * 0.6 if f == "thumb" else n   # 엄지는 검지 뿌리 쪽으로 굽는다
                add(f"{f}_{S}_{k}", b, d.cross(v).normalized())
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return joints, rest

def jrot(joint, d, axis=None):
    side = 1 if "_L" in joint else -1
    rz = d.get("yaw", 0.0); rx = d.get("pitch", 0.0) - d.get("flex", 0.0) - d.get("dorsi", 0.0) + d.get("bend", 0.0) * (1 if joint.startswith("knee") else -1)
    ry = d.get("roll", 0.0) - d.get("abduct", 0.0) * side
    R = Matrix.Rotation(radians(rz), 4, "Z") @ Matrix.Rotation(radians(rx), 4, "X") @ Matrix.Rotation(radians(ry), 4, "Y")
    return Matrix.Rotation(radians(d.get("curl", 0.0)), 4, Vector(axis)) @ R if axis else R

def solve(joints, pose):
    """자세 {"hip_L.flex": 20, ...} -> 뼈 이름별 변환(기본 자세 기준, 세계 좌표). runtime/RigSolver.luau와 같은 계산."""
    by = {}
    for k, v in pose.items():
        j, d = k.split("."); by.setdefault(j, {})[d] = v
    r = by.get("root", {}); p = Vector(joints["root"]["pos"]); TR = Matrix.Translation
    D = {"pelvis": TR((r.get("x", 0), r.get("y", 0), r.get("z", 0))) @ TR(p) @ jrot("root", r) @ TR(-p)}; N = {"pelvis": Matrix.Identity(4)}
    pend = [j for j in joints if j != "root"]
    while pend:
        for j in [j for j in pend if joints[j]["parent"] in D]:
            J = joints[j]; n = J["neutral"]; Nj = Matrix((n[0:3], n[3:6], n[6:9])).to_4x4(); q = Vector(J["pos"])
            D[J["bone"]] = D[J["parent"]] @ TR(q) @ N[J["parent"]].inverted() @ jrot(j, by.get(j, {}), J.get("axis")) @ Nj @ TR(-q); N[J["bone"]] = Nj; pend.remove(j)
    return D

def hand_pose(name, sides="LR"):
    """out/anim/hand_poses.json의 손 모양을 자세 표로 바꾼다."""
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

def build(name):
    kit.reset(); bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
    from bl_ext.user_default.mpfb.services.humanservice import HumanService as HS
    sp = PEOPLE[name]; ok = cc0_assets()
    for a in [sp["hair"], sp["brow"], sp["shoes"], sp["skin"]] + sp["clothes"]:
        if a not in ok: raise RuntimeError("CC0 목록에 없는 에셋: " + a)
    if sp["age"] < 0.5: raise RuntimeError("성인만 만든다: " + name)
    macro = {"gender": sp["gender"], "age": sp["age"], "muscle": sp["muscle"], "weight": sp["weight"], "proportions": 0.6, "height": sp["height"],
             "cupsize": 0.45, "firmness": 0.5, "race": {"asian": sp["race"][0], "caucasian": sp["race"][1], "african": sp["race"][2]}}
    base = HS.create_human(scale=0.1, macro_detail_dict=macro)
    HS.add_builtin_rig(base, "game_engine")
    HS.set_character_skin(asset("skins", sp["skin"], "mhmat"), base, skin_type="MAKESKIN")
    for kind, nm, typ in (("eyes", "high-poly", "Eyes"), ("eyebrows", sp["brow"], "Eyebrows"), ("eyelashes", "eyelashes01", "Eyelashes"),
                          ("teeth", "teeth_base", "Teeth"), ("hair", sp["hair"], "Hair")):
        HS.add_mhclo_asset(asset(kind, nm), base, asset_type=typ, material_type="MAKESKIN")
    for c in sp["clothes"] + [sp["shoes"]]:
        HS.add_mhclo_asset(asset("clothes", c), base, asset_type="Clothes", material_type="MAKESKIN")
    for cname, col in sp.get("tint", {}).items():
        ob = find("." + cname)
        if ob: tint(ob, col)
    if sp["shoes"].startswith("toigo_"): tint(find("." + sp["shoes"]), INK)
    if sp.get("hair_tint"): tint(find("." + sp["hair"]), [c * 0.30 for c in sp["hair_tint"]], 0.95, lift=0.7)
    skin = base.material_slots[0].material; skin.name = "skin"   # 몸은 재질 하나로 합친다(전부 같은 텍스처)
    for sl in base.material_slots: sl.material = skin
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    kit.M.clear(); kit.base_materials()   # MPFB가 안 쓰는 재질을 지우므로 다시 만든다
    made = cyberware(sp, base, rig)
    return base, rig, made

def export(name, base, rig, made, sp, joints, extra=None):
    for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for im in bpy.data.images:   # 게임용: 텍스처는 1024까지
        if im.size[0] > TEX or im.size[1] > TEX: im.scale(min(TEX, im.size[0]), min(TEX, im.size[1]))
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True); dg = bpy.context.evaluated_depsgraph_get(); tris = {}
    objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "ARMATURE") and not o.name.startswith("stage_")]
    for o in objs:
        if o.type == "MESH":
            me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); tris[o.name] = len(me.loop_triangles); o.evaluated_get(dg).to_mesh_clear()
    for o in bpy.context.scene.objects: o.select_set(o in objs)
    try: bpy.ops.export_scene.gltf(filepath=os.path.join(d, f"human_{name}.glb"), export_apply=True, use_selection=True, export_extras=True, export_image_format="WEBP", export_image_quality=85)
    except Exception as e: print("gltf:", repr(e)[:200])
    man = {"name": "human_" + name, "role": sp.get("role"), "units": "m", "forward": "-Y", "up": "+Z", "rig": "mpfb game_engine", "height": round(max(v.co.z for v in base.evaluated_get(dg).data.vertices), 3),
           "bones": [b.name for b in rig.data.bones], "joints": joints, "triangles": sum(tris.values()), "triangles_by_mesh": tris, "cyberware": made, "glow": sp["glow"],
           "attach": {"cyber_head": "head", "cyber_neck": "neck_01", "cyber_chest": "spine_03", "hand_R": "hand_r", "hand_L": "hand_l"},
           "assets_cc0": [sp["skin"], sp["hair"], sp["brow"], sp["shoes"]] + sp["clothes"] + ["high-poly", "eyelashes01", "teeth_base"],
           "tint": {k: list(v) for k, v in sp.get("tint", {}).items()}, "hair_tint": list(sp["hair_tint"]) if sp.get("hair_tint") else None}
    man.update(extra or {})
    json.dump(man, open(os.path.join(d, f"human_{name}.manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(f"EXPORT human_{name} tris={man['triangles']} meshes={len(tris)} cyber={len(made)} h={man['height']}", flush=True)

def golden(joints, clips_dir):
    """Luau 쪽 RigSolver 검증용: 사람 뼈대에 클립을 적용했을 때 뼈별 행렬."""
    cases = []
    for cn in ("walk", "run", "cower_enter"):
        cl = json.load(open(os.path.join(clips_dir, cn + ".json")))
        for t in (0.0, 0.21, cl["duration"] * 0.6):
            D = solve(joints, sample(cl, t))
            cases.append({"clip": cn, "t": round(t, 5), "parts": {b: [round(m[r][c], 6) for r in range(3) for c in range(3)] + [round(m[r][3], 6) for r in range(3)] for b, m in D.items()}})
    hp = dict(sample(json.load(open(os.path.join(clips_dir, "walk.json"))), 0.3)); hp.update(hand_pose("grip_pistol", "R")); hp.update(hand_pose("fist", "L")); hp["wrist_R.flex"] = 20
    D = solve(joints, hp); hand_case = {"pose": hp, "parts": {b: [round(m[r][c], 6) for r in range(3) for c in range(3)] + [round(m[r][3], 6) for r in range(3)] for b, m in D.items()}}
    json.dump({"manifest": {"joints": joints}, "cases": cases, "hand_case": hand_case}, open(os.path.join(clips_dir, "_golden_human.json"), "w"), separators=(",", ":"))
    print("GOLDEN human", len(cases))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); clips = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "anim")
    for name in PEOPLE:
        if (ONLY and name not in ONLY) or (not ONLY and PEOPLE[name].get("fp") and os.environ.get("HUMAN_SKIP_FP")): continue
        base, rig, made = build(name); joints, rest = rig_joints(rig); sp = PEOPLE[name]; extra = {}
        res = tuple(int(c) for c in os.environ.get("HUMAN_RES", "800,1200").split(","))
        if sp.get("fp"):
            extra["eye"] = keep_arms(rig); base = next(o for o in bpy.context.scene.objects if o.type == "MESH")
            if RENDER:
                pose = {"shoulder_L.flex": 62, "shoulder_R.flex": 62, "shoulder_L.abduct": -4, "shoulder_R.abduct": -4, "elbow_L.bend": 46, "elbow_R.bend": 46}
                pose.update(hand_pose("grip_pistol", "R")); pose.update(hand_pose("relaxed", "L")); apply_pose(rig, joints, rest, pose)
                e = extra["eye"]; kit.studio((0, -0.35, 1.25), 0.7, floor_z=0.6)
                kit.shot(os.path.join(OUT, f"{name}_view.png"), (e[0], e[1] + 0.06, e[2] + 0.02), (0, -0.60, 1.20), 20, res=(res[1], res[0]))
                kit.shot(os.path.join(OUT, f"{name}.png"), (-1.55, -1.95, 1.95), (0, -0.32, 1.22), 60, res=(res[1], res[0]))
        elif RENDER:
            apply_pose(rig, joints, rest, STAND); kit.studio((0, 0, 0.9), 1.0)
            kit.shot(os.path.join(OUT, f"human_{name}.png"), (-1.5, -4.3, 1.45), (0, 0, 0.90), 70, res=res)
            hz = (rig.matrix_world @ rig.pose.bones["head"].head).z + 0.09
            fill = kit.area("face_fill", (-0.5, -1.6, hz + 0.25), (0, 0, hz), 0.8, 26, (1.0, 0.95, 0.9))
            kit.shot(os.path.join(OUT, f"human_{name}_face.png"), (-0.42, -1.05, hz + 0.03), (0, -0.02, hz), 85, res=(res[0], res[0]))
            strips = os.environ.get("HUMAN_STRIPS", "walk" if os.environ.get("HUMAN_WALK") else "")   # 클립이 이 뼈대에서 제대로 도는지 확인하는 연속 사진
            if strips:
                bpy.data.objects.remove(fill)
                for cn in strips.split(","):
                    cl = json.load(open(os.path.join(clips, cn + ".json")))
                    for i in range(6):
                        apply_pose(rig, joints, rest, sample(cl, cl["duration"] * i / (6 if cl["loop"] else 5)))
                        kit.shot(os.path.join(OUT, f"_{cn}_{name}_{i}.png"), (-2.9, -4.4, 1.3), (0, 0.1, 0.80), 60, res=(330, 560))
        for o in [o for o in kit.COL.objects if o.type == "LIGHT" or o.name == "stage_floor"]: bpy.data.objects.remove(o)
        export(name, base, rig, made, sp, joints, extra)
        if name == "man_a": golden(joints, clips)
