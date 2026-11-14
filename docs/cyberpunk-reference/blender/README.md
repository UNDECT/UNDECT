# Blender 에셋 (자체 디자인, 코드로 생성)

모든 모델은 스크립트가 만든다. 손으로 모델링한 파일은 없다. 같은 스크립트를 돌리면 같은 결과가 나온다.

## 실행
```
pip install bpy            # Blender 5.x 파이썬 모듈 (Python 3.13)
python security_robot.py out/security_robot all
python car.py out/car all            # 변형: python car.py out/car render cab  (cab, corp, teal, patrol). 문 4개와 실내가 있다
python street.py out/street scene    # 밤거리 장면
python street.py out/street modules  # 거리 소품 10종 내보내기
python weapons.py out/weapons render  # 무기 17종
python flying_car.py out/flying_car all   # 변형: ... render patrol
python npc.py out/npc render           # 거리 NPC 5종
python person.py out/human render     # 맨얼굴 사람 10명 + 1인칭 팔 2종 (전부 자체 제작, 준비물 없음)
python machines.py out/machines render # 드론, 포탑, 감시 카메라
python clinic.py out/clinic modules    # 시술 의자, 천장 로봇 팔, 도구 수레
python clinic.py out/clinic scene      # 시술소 장면 (시술의 포함)
python cyber_arms.py out/cyber_arms render   # 사이버웨어 팔 4종 (접힌 상태 + 펼친 상태)
python street.py out/street scene_day  # 낮 거리
python districts.py out/street all     # 구역 3종: slum, corp, rich
python anim.py out/anim clips          # 애니메이션 클립 157개
```
- 품질: 환경 변수 `KIT_SAMPLES`(기본 80).
- 결과: 폴더마다 `.glb`, `.blend`, `.manifest.json`, 렌더 사진.

## 파일
| 파일 | 내용 |
|---|---|
| `kit.py` | 공용 도구: 재질(금속, 도장, 콘크리트, 젖은 아스팔트, 창 불빛), 기본 형상, 부품·관절 기록, 스튜디오 조명, 렌더, 내보내기 |
| `security_robot.py` | 보안 로봇. 키 약 1.95 m, 부품 15개, 관절 14개 |
| `car.py` | 각진 쐐기형 세단. 변형 5종(택시, 보안 순찰차 포함). 바퀴 4개, 문 4개, 운전대가 따로 움직이고 실내(좌석, 계기판)가 있다 |
| `street.py` | 거리 소품 10종, 건물 생성기, 초대형 건물, 고가 선로, 밤거리·낮거리 장면 |
| `weapons.py` | 총 10종(권총, 리볼버, 기관단총, 돌격소총, 경기관총, 정밀 소총, 저격총, 산탄총 3종), 근접 5종(장검, 단검, 곤봉, 망치, 주먹 무기), 수류탄 2종 |
| `flying_car.py` | 추진기 4개짜리 비행 차량. 변형 3종 |
| `npc.py` | 얼굴을 가린 거리 NPC 5종 |
| `person.py` | 맨얼굴 사람 10명(거리 사람 5, 노동자, 상인, 회사원, 임원, 시술의)과 1인칭 팔 2종. 머리·얼굴·손·옷·머리카락·신발·뼈대를 전부 코드로 만든다. 외부 에셋과 그림 파일이 없다 |
| `machines.py` | 드론, 포탑, 감시 카메라 |
| `clinic.py` | 시술 의자, 천장 로봇 팔 3개와 수술등, 도구 수레, 시술소 장면 |
| `cyber_arms.py` | 사이버웨어 팔 4종: 파워암, 나노와이어, 런처, 손 레이저 (블레이드 팔은 `../samples/cyber-arm`) |
| `districts.py` | 구역별 건물 양식 3종과 구역 그림: 빈민, 기업, 부유층 |
| `anim.py` | 애니메이션 클립 생성과 미리보기 |
| `out/` | 만들어진 결과물 |

## 규칙
- 단위 m, 앞 = -Y, 위 = +Z.
- `finish(..., part="이름")`으로 만든 오브젝트는 그 부품에 속한다. 게임에서 부품 단위로 합친다.
- `pivot(...)`으로 관절 위치와 축을 기록한다. `manifest.json`에 들어간다.
- 재질은 절차 재질이다. 게임에 넣으려면 텍스처로 구워야 한다(`send-to-claude-code-blender-assets.md` 3번).
- 이름, 로고, 표기는 전부 자체 제작이거나 자리 표시다.

## 사람 (`person.py`)
외부 에셋이나 사람 생성 도구를 쓰지 않는다. `pip install bpy`만 있으면 돈다.
- **얼굴**: 높이마다 앞·뒤·옆 윤곽을 정해 가로 단면을 쌓고(`head_mesh`), 그 위에 눈구멍·코·입·턱을 수식으로 빚는다. 생김새는 `FACE` 표의 수치이고 사람마다 일부를 바꾼다(`PEOPLE`의 `face`).
- **몸과 옷**: 옷 아래에 몸을 만들지 않는다. 윗옷 몸통·소매·바지·신발을 단면 고리로 만들고, 드러나는 곳(머리, 목, 손, 반소매면 팔)만 피부로 만든다.
- **머리카락**: 머리 격자를 바깥으로 밀어 만든다(`hair`). 모양: `buzz, short, slick, bob, long, afro, bun, bald`.
- **뼈대와 가중치**: 뼈 47개를 직접 만들고(`skeleton`, `make_rig`), 정점마다 가까운 뼈 선분까지의 거리로 가중치를 준다(`skin_to`). 기본 자세가 팔을 내린 중립 자세라서 `manifest.joints`의 `neutral`은 전부 단위 행렬이다.
- **그림 파일 없음**: 재질은 색과 수치뿐이다. 내보낼 때 그림이 하나라도 있으면 멈춘다. `manifest.json`에 `"images": 0`, `"made_by": "person.py ..."`가 들어간다.
- **성인만**: `PEOPLE`의 `age`가 20 미만이면 멈춘다.
- **올리기 전 검사**: `python upload_check.py <꺼낼 폴더> out` → 그림이 든 사람 파일(예전 파일)을 `BLOCK`으로 표시한다.
- 환경 변수: `HUMAN_RES`(사진 크기), `HUMAN_STRIPS=walk,knockdown,...`(클립을 뼈대에 적용한 연속 사진), `HUMAN_GOLDEN=1`(Luau 검증값 `_golden_human.json` 다시 만들기).
- 사람을 늘리려면 `PEOPLE` 표에 한 줄을 더한다. 얼굴만 빨리 보려면 `python person.py <폴더> heads`.
