# Blender 에셋 (자체 디자인, 코드로 생성)

모든 모델은 스크립트가 만든다. 손으로 모델링한 파일은 없다. 같은 스크립트를 돌리면 같은 결과가 나온다.

## 실행
```
pip install bpy            # Blender 5.x 파이썬 모듈 (Python 3.13)
python security_robot.py out/security_robot all
python car.py out/car all            # 변형: python car.py out/car render cab
python street.py out/street scene    # 밤거리 장면
python street.py out/street modules  # 거리 소품 10종 내보내기
```
- 품질: 환경 변수 `KIT_SAMPLES`(기본 80).
- 결과: 폴더마다 `.glb`, `.blend`, `.manifest.json`, 렌더 사진.

## 파일
| 파일 | 내용 |
|---|---|
| `kit.py` | 공용 도구: 재질(금속, 도장, 콘크리트, 젖은 아스팔트, 창 불빛), 기본 형상, 부품·관절 기록, 스튜디오 조명, 렌더, 내보내기 |
| `security_robot.py` | 보안 로봇. 키 약 1.95 m, 부품 15개, 관절 14개 |
| `car.py` | 각진 쐐기형 세단. 색 변형 4종(택시 포함), 바퀴 4개가 따로 돈다 |
| `street.py` | 거리 소품 10종, 건물 생성기, 초대형 건물, 고가 선로, 밤거리 장면 |
| `out/` | 만들어진 결과물 |

## 규칙
- 단위 m, 앞 = -Y, 위 = +Z.
- `finish(..., part="이름")`으로 만든 오브젝트는 그 부품에 속한다. 게임에서 부품 단위로 합친다.
- `pivot(...)`으로 관절 위치와 축을 기록한다. `manifest.json`에 들어간다.
- 재질은 절차 재질이다. 게임에 넣으려면 텍스처로 구워야 한다(`send-to-claude-code-blender-assets.md` 3번).
- 이름, 로고, 표기는 전부 자체 제작이거나 자리 표시다.
