"""Roblox에 올리기 전에 GLB 안의 그림을 꺼내 확인한다. bpy 없이 파이썬만으로 돈다.

  python upload_check.py <꺼낼 폴더> <glb 또는 폴더> [...]

하는 일
  1. GLB마다 안에 든 그림(텍스처)을 <꺼낼 폴더>/<파일 이름>/ 에 꺼낸다. 올리기 전에 이 그림을 전부 눈으로 본다.
  2. 사람 파일(human_*.glb)은 그림이 한 장도 없어야 하고, 옆의 manifest.json의 made_by가 person.py여야 한다(자체 제작본).
     아니면 BLOCK으로 표시하고 종료 코드 1로 끝난다. BLOCK이 하나라도 있으면 아무것도 올리지 않는다.

이 검사는 예전 파일을 걸러 낼 뿐이다. 글자·주소·알몸처럼 보이는 것이 없는지는 꺼낸 그림을 직접 보고 판단한다.
"""
import glob
import json
import os
import struct
import sys

EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def read_glb(path):
    with open(path, "rb") as fh:
        magic, _, _ = struct.unpack("<4sII", fh.read(12))
        if magic != b"glTF":
            raise ValueError("GLB가 아니다: " + path)
        ln, _ = struct.unpack("<II", fh.read(8))
        doc = json.loads(fh.read(ln))
        head = fh.read(8)
        blob = b""
        if len(head) == 8:
            ln, _ = struct.unpack("<II", head)
            blob = fh.read(ln)
    return doc, blob


def check(path, out):
    doc, blob = read_glb(path)
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    images = doc.get("images", [])
    problems = []
    dest = os.path.join(out, stem)
    for i, im in enumerate(images):
        name = im.get("name") or "image%d" % i
        if "bufferView" not in im:
            problems.append("바깥 파일을 가리키는 그림: " + str(im.get("uri")))
            continue
        bv = doc["bufferViews"][im["bufferView"]]
        data = blob[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, name.replace("/", "_") + EXT.get(im.get("mimeType"), ".bin")), "wb") as fh:
            fh.write(data)
    if stem.startswith("human_"):
        man = os.path.join(os.path.dirname(path), stem + ".manifest.json")
        info = json.load(open(man, encoding="utf-8")) if os.path.exists(man) else {}
        if images: problems.append("사람 파일에 그림이 %d장 들어 있다. 예전 파일이다" % len(images))
        if not str(info.get("made_by", "")).startswith("person.py"): problems.append("manifest의 made_by가 person.py가 아니다. 예전 파일이다")
    print("%-5s %s  그림 %d장%s" % ("BLOCK" if problems else "OK", base, len(images), "" if not images else "  -> " + dest))
    for p in problems:
        print("      " + p)
    return not problems


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    out = sys.argv[1]
    files = []
    for a in sys.argv[2:]:
        files += sorted(glob.glob(os.path.join(a, "**", "*.glb"), recursive=True)) if os.path.isdir(a) else [a]
    ok = [check(f, out) for f in files]
    print("\n%d개 중 %d개 통과. 꺼낸 그림: %s" % (len(ok), sum(ok), out))
    print("통과한 파일도 꺼낸 그림을 전부 열어 보고 올린다." if all(ok) else "BLOCK이 있다. 아무것도 올리지 않는다.")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
