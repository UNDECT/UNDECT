# Claude Code에 보낼 메시지 — Blender 에셋 반영 (역할 분담 변경)

> **보내는 법**: 개발 세션에 아래 `---` 아래 전체를 붙여 넣으세요. 이 메시지는 앞서 보낸 캐릭터·그래픽 프롬프트의 "모델을 직접 만든다"는 부분을 바꿉니다.

---

## 0. 무엇이 바뀌었나
- **모델 디자인과 제작은 다른 세션이 한다.** 보안 로봇·드론·포탑·감시 카메라, 차량, 비행 차량, 무기 17종, 맨얼굴 사람 10명과 가면 NPC 5종, 1인칭 팔, 사이버웨어 팔 4종, 시술소, 거리 소품, 구역 4종의 건물 규칙과 분위기 그림, 애니메이션 클립 94개를 Blender 스크립트로 만들어 저장소에 올려 두었다. 앞으로 모든 그래픽 요소는 이 방식으로 바꾼다.
- **너의 일은 그 에셋을 게임에 그대로 반영하는 것이다.** 모양, 비율, 색, 재질, 발광 위치를 바꾸지 않는다.
- 지금 하는 C2(행인)는 그대로 계속한다. 맨얼굴 사람은 아직 이쪽에서 만들지 못했다(뒤 6번). 얼굴을 가린 거리 NPC 5종은 군중에 섞어 쓴다.
- 기존 규칙은 그대로다: 한국어, `cyber-3v3.rbxl` 저장 금지, `rojo build -o cyber-rpg.rbxl` 금지, computer-use 금지, 기능 브랜치 커밋, Lune 테스트 전부 통과, Studio 확인은 직접.

## 1. 받아 오기
```
git clone --depth 1 -b ccr-9e6cc8c3-bftdlm https://github.com/UNDECT/UNDECT.git <임시폴더>
```
- `<임시폴더>/docs/cyberpunk-reference/blender/` → `cyber-rpg/tools/blender/fable/` 로 복사한다(스크립트와 `out/` 폴더 전부).
- `<임시폴더>/docs/cyberpunk-reference/samples/cyber-arm/` → `cyber-rpg/tools/blender/fable/cyber-arm/` 로 복사한다.
- 다시 만들려면: `pip install bpy` 한 파이썬으로 `python security_robot.py <출력폴더> all` 처럼 실행한다. 스크립트 맨 위 주석에 사용법이 있다. Blender 실행 파일로 돌릴 때는 `blender --background --python security_robot.py -- <출력폴더> all`.
- 이 스크립트들을 **고쳐서 디자인을 바꾸지 않는다.** 굽기·뼈·LOD·내보내기 단계는 네 파이프라인(`tools/blender/bake`, `validate.py`)에 추가한다.

## 2. 에셋 목록
| 에셋 | 스크립트 | 결과물 (`out/` 아래) | 삼각형 | 부품 / 관절 |
|---|---|---|---|---|
| 보안 로봇 | `security_robot.py` | `security_robot/security_robot.{glb,blend,manifest.json}`, 사진 3장 | 약 6만 2천 | 부품 15 / 관절 14 |
| 세단(기본) | `car.py` | `car/car.{glb,blend,manifest.json}`, 사진 3장 | 약 2만 6천 | 부품 5(차체+바퀴 4) / 관절 4 |
| 택시 변형 | `car.py ... cab` | `car/car_cab.*`, 사진 1장 | 비슷 | 같음 |
| 다른 색 변형 | `car.py ... corp`, `teal` | 필요할 때 생성 | 비슷 | 같음 |
| 거리 소품 10종 | `street.py ... modules` | `street/modules/<이름>.{glb,blend,manifest.json}`, 모음 사진 | 종류별 수백~수천 | 가로등, 자판기, 실외기, 바리케이드, 쓰레기 더미, 노점, 돌출 세로 간판, 광고판, 고가 선로 구간, 교각 |
| 밤거리 장면 | `street.py ... scene` | `street/street_night.png` | — | **분위기 목표 그림.** 건물 생성 규칙의 기준 |
| 비행 차량 | `flying_car.py` | `flying_car/flying_car.{glb,blend,manifest.json}`, 사진 3장. 변형 `patrol`(보안 순찰), `cargo` | 약 1만 8천 | 부품 10(동체, 착륙 다리, 추진기 4, 팬 4) / 관절 8 |
| 무기 17종 | `weapons.py` | `weapons/<이름>/<이름>.{glb,blend,manifest.json}`, 사진 각 1장, `weapons_sheet.png` | 1천~1만 2천 | 총 10: `pistol`, `revolver`, `smg`, `rifle`, `lmg`, `dmr`, `sniper`, `shotgun`(펌프), `shotgun_double`(2연발), `shotgun_auto`(자동). 근접 5: `katana`, `knife`, `baton`, `hammer`, `knuckles`. 투척 2: `grenade`, `grenade_emp`. 움직이는 부품과 붙임점 기록 |
| 거리 NPC 5종 | `npc.py` | `npc/<이름>/npc_<이름>.{glb,blend,manifest.json}`, 사진 각 1장 | 약 3만 5천 | 우비, 테크웨어, 작업자, 배달부, 회사원. 부품 11~13 / 관절 10~11 |
| 맨얼굴 사람 10명 | `human.py` | `human/<이름>/human_<이름>.{glb,manifest.json}`, 사진 각 2장, `human_sheet.png`, `human_faces.png`, `human_walk_check.png` | 약 3만 7천~4만 9천 | 거리 사람 5(`man_a`, `woman_a`, `woman_c`, `man_d`, `woman_d`), 노동자(`man_b`), 상인(`merchant`), 회사원(`woman_b`), 임원(`man_c`), 시술의(`doctor`). 뼈 53개(스킨 메시), 손가락 관절 포함 |
| 1인칭 팔 2종 | `human.py ... fp_sleeve fp_bare` | `human/fp_sleeve/`, `human/fp_bare/` (GLB, manifest), 사진 각 2장(`*_view.png`가 1인칭 시점) | 6천~9천 | 재킷 소매+장갑, 맨팔. 사람과 같은 뼈대. `manifest.eye`가 카메라 자리 |
| 드론, 포탑, 감시 카메라 | `machines.py` | `machines/<이름>/<이름>.{glb,blend,manifest.json}`, 사진 각 2장, `machines_sheet.png` | 드론 1만 4천, 포탑 8천, 카메라 3천 | 드론: 팬 4, 총좌(좌우·상하). 포탑: 받침→몸(좌우)→머리(상하)→총열(반동). 카메라: 좌우·상하 |
| 시술소 | `clinic.py` | `clinic/{chair,surgery_rig,cart}/…`, 사진 각 2장, **`clinic_scene.png`, `clinic_scene_close.png`(시술소 분위기 목표)** | 의자 1만 1천, 로봇 팔 1만 4천, 수레 4천 | 의자: 높이, 등받이, 다리 받침, 머리 받침, 팔걸이 2. 천장 로봇 팔 3개(어깨·팔꿈치·손목)와 수술등. 수레: 도구, 약병, 화면 |
| 사이버웨어 팔 3종 | `cyber_arms.py` | `cyber_arms/{power,nanowire,launcher}/arm_<이름>.{glb,blend,manifest.json}`, 사진 각 2장(접힘, 펼침), `cyber_arms_sheet.png` | 1만 4천~1만 8천 | 파워암, 나노와이어, 런처. 손가락 14마디가 따로 움직인다. 펼침 동작은 `manifest.deploy`와 클립 |
| 낮 거리, 구역 3종 | `street.py ... scene_day`, `districts.py` | `street/street_day.png`, `street/district_{slum,corp,rich}.png`, `street/districts_sheet.png`(4구역 비교) | — | **낮 분위기 목표**와 **구역별 분위기 목표**. 건물 생성 규칙의 기준 |
| 사이버웨어 팔 | `cyber-arm/make_arm.py` | 사진 4장, `cyber_arm_closed.glb` | 약 5만 4천 | 부품 약 180개(문 4장, 칼날, 손가락 마디) |
| 공용 도구 | `kit.py` | — | — | 재질, 형상, 관절 기록, 내보내기 |

`manifest.json` 읽는 법
- `parts`: 게임에서 따로 움직이는 단위. 이름이 같은 부품끼리 한 메시로 합친다.
- `pivots`: 관절. `pos`(m), `axis`, `parent`, `child`, `range`(도). 뼈를 여기에 단다.
- `triangles_by_part`: 부품별 삼각형 수.
- `joints`(사람만): 애니메이션 관절 이름 → 뼈 이름 대응표. `RigAnimator.new(model, manifest.joints)`에 그대로 넘긴다.
- 좌표: 단위 m, 앞 = -Y, 위 = +Z. 로블록스로 옮길 때 1 m ≈ 3스터드 기준으로 맞추고, 로봇 키가 약 6.2~6.6스터드가 되게 한다.

## 3. 에셋마다 할 일 (기계적인 변환만)
1. **재질 굽기**: Blender 절차 재질(도장 벗겨짐, 긁힘, 때, 결)을 텍스처로 굽는다. Color, Normal, Roughness, Metalness, 발광 마스크. 부품 묶음마다 아틀라스 하나. `.blend` 파일을 열어 그대로 구우면 된다.
   - 글자(FONT)와 케이블(CURVE) 오브젝트는 메시로 바꾼 뒤 굽는다.
   - 발광 재질(`glow_*`, `win_*`, `sodium`)은 발광 마스크로 옮기고, 색과 세기는 게임에서 바꿀 수 있게 `EmissiveTint`·`EmissiveStrength`로 둔다.
2. **합치기와 뼈**: `parts` 단위로 메시를 합치고 `pivots` 위치에 뼈를 단다. 정점당 뼈 영향은 1개면 된다(딱딱한 부품).
3. **삼각형 수**: 메시 하나에 2만 개 이하. 넘으면 부품 단위로 나눈다. LOD 3단은 Decimate로 만든다(LOD1 35%, LOD2 12%). 실루엣이 무너지면 비율을 올린다.
4. **검사와 업로드**: `validate.py` 통과 → 업로드 → `manifest`에 에셋 ID 기록.
5. **나란히 비교**: Studio에서 Blender 사진과 같은 각도로 찍어 나란히 놓는다. 다른 점 상위 5개를 적는다. 색, 실루엣, 발광 위치가 다르면 고치고, 고칠 수 없으면 이유와 함께 보고한다.

**하지 말 것**
- 모양·비율·색을 "더 낫게" 고치지 않는다. 이상해 보이면 스크린샷과 함께 사용자에게 알린다. 디자인 수정은 에셋을 만든 세션이 한다.
- 부품을 빼거나 단순화할 때는 LOD 단계에서만 한다. LOD0은 원본 그대로다.
- 새 주요 에셋(새 적, 새 차종, 새 건물 양식, 무기)을 직접 모델링하지 않는다. 필요하면 목록으로 요청한다(7번).

## 4. 에셋별 연결 방법

### 보안 로봇 → 스펙 `SEC` (C7b)
- 지금 있는 보안 로봇의 AI, 판정, 테스트는 유지하고 **겉모습만 교체**한다.
- 부품 이름과 판정 부위 대응: `head`, `torso`, `pelvis`, `upperarm_L/R`, `forearm_L/R`, `hand_L/R`, `thigh_L/R`, `shin_L/R`, `foot_L/R`.
- 상태등: `visor`, `status_lamp`, `core_glow`, `ear_lens`, `shin_glow`의 발광 색을 상태에 따라 바꾼다(평소, 의심, 전투, 해킹당함, 꺼짐). 색은 `UiTheme` 상태색을 쓴다.
- 약점: 등의 `weak_point`(주황 발광판). 스캔하면 표시되고 맞으면 큰 피해.
- 무장: 오른팔 `gun_*`(2연장 총)에서 총구 화염과 예광탄이 나온다. 왼팔 `lamp_lens`는 탐조등, `scanner_glow`는 신분 스캐너다.
- 분리 부위(크롬 부품 이탈): `head`, `upperarm`+`forearm`+`hand` 한 팔, `pauldron_*`, `gun_*`, `backpack`.
- 동작은 C2에서 만든 "코드가 뼈를 직접 움직이는 방식"으로 `SEC-30~40`을 만든다. 걸음은 사람보다 무겁게.
- 표기 "SEC 112"는 자리 표시다. 보안 회사 이름과 로고가 정해지면 바꾼다. 기체마다 번호를 다르게 한다.

### 차량 → 스펙 `VEH`, `WLD-64` (C7 교통, C13)
- 바퀴 4개는 `wheel_FL/FR/RL/RR` 관절(축 X)로 굴린다. 반지름은 `manifest`의 `wheel_radius`.
- 발광: `light_bar_f`, `headlamp`(흰색), `light_bar_r`(빨강), `side_line`, `hub_ring`, `underglow`. 밤에 켜고 낮에 끈다. 브레이크를 밟으면 뒤 발광이 세진다.
- 변형 4종(`crimson`, `cab`, `corp`, `teal`)을 색만 바꿔 쓴다. 택시는 지붕 표시등이 있다.
- 유리는 불투명한 짙은 색이다. 실내 모델은 없다(차에 타는 기능을 만들 때 요청한다).
- 클라이언트 전용 교통과 주차 차량에 먼저 쓴다.

### 거리 소품과 건물 → 스펙 `WLD`, 간판 규칙 (C3~C7)
- `street_night.png`가 **밤 분위기 목표**다. 고정 촬영 지점 사진을 이 그림과 나란히 놓고 비교한다.
- 소품 10종은 `BuildKit`의 해당 소품을 대체한다.
- 건물은 로블록스 쪽에서 코드로 만든다. `street.py`의 `building()`이 쓰는 규칙을 그대로 옮긴다.
  - 층 높이 3.6 m, 창 간격 3.2 m, 창 크기 1.7 × 1.55 m, 창마다 창틀(세로·가로 살, 창턱)
  - 층마다 가로 띠, 6.4 m마다 세로 기둥
  - 불 켜진 창 비율: 따뜻한 색 15%, 차가운 색 6%, 분홍 2.5%, 나머지는 어두운 유리
  - 실외기는 창의 16%에 붙는다
  - 1층 가게: 폭 6.2 m, 30%는 셔터가 내려가 있고 간판이 없다. 연 가게만 차양과 간판 **하나**
  - 옥상: 난간, 물탱크, 안테나와 빨간 경고등
- 간판 수(이 장면 기준): 영웅 광고 1, 옥상 광고판 1, 돌출 세로 간판 3, 가게 간판은 가게당 1. 이보다 늘리지 않는다.
- 도로 위를 가로지르는 고가 선로 1개와 공중 통로 1개가 화면에 들어온다.
- 먼 초대형 건물은 창 불빛 격자와 꼭대기 로고, 빨간 경고등만 있는 단순한 덩어리다.
- 조명 기준(Blender 값이라 그대로 옮기지 말고 인상만 맞춘다): 전체는 어둡고, 간판 근처에만 색 빛 웅덩이(마젠타, 시안, 주황)가 있다. 젖은 바닥에 간판이 비친다. 안개 때문에 먼 건물이 연해진다.

### 낮과 구역 양식 → 스펙 `WLD`, C3~C4
- `street_day.png`가 **낮 분위기 목표**다: 흐리고 뿌연 낮, 콘크리트 색이 드러나고 간판은 켜져 있지만 약하게 보인다. 맑은 파란 하늘이 아니다.
- 구역 4종의 목표 그림: 번화가 = `street_night.png`, 빈민 = `district_slum.png`, 기업 = `district_corp.png`, 부유층 = `district_rich.png`. 구역 경계에서 사진만 보고 구역을 맞힐 수 있어야 한다.
- 건물 규칙은 `districts.py`의 생성 함수에서 옮긴다. 거리 뼈대(도로 14 m, 인도 4 m)는 네 구역이 같다.

| 구역 | 건물 (`districts.py`) | 소품·조명 | 간판 |
|---|---|---|---|
| 빈민 `slum_block` | 6.1 m·12.2 m 컨테이너와 덧댄 방을 3~8층 쌓는다. 층마다 0.5~0.9 m씩 어긋난다. 색은 녹, 파랑, 초록, 노랑, 어두운 콘크리트. 골이 진 벽, 창 75%(그중 따뜻한 불 45%), 실외기 35%, 발코니와 빨래 30%, 옥상 물탱크 60% | 인도 위 비닐 천막(파랑·주황) 70%, 길을 가로지르는 전선 14줄, 노점 3, 쓰레기 더미 6, 드럼통 불, 나트륨등 2개만 켜짐. 주황빛, 갈색 안개 | 합판에 손으로 쓴 작은 간판(블록의 절반), 큰 광고 없음 |
| 기업 `corp_block` | 높이 14 m 브루탈 콘크리트 기단 + 뒤로 물러난 검은 유리 탑(90~230 m). 기단에 가로 창 띠 3줄과 흰 띠 조명, 양끝 버팀벽, 유리 정문과 노랑·검정 경고 띠. 탑은 3 m 간격 세로 살 | 인도 가장자리 볼라드(3 m 간격, 위에 흰 띠), 검문소 차단봉과 초소, 바리케이드, 보안 로봇 2, 포탑 1, 감시 카메라, 순찰 드론과 순찰 비행 차량. 차가운 흰빛·푸른빛 | 탑 꼭대기 로고 1개, 정문 위 표기 문자뿐 |
| 부유층 `rich_block` | 층고 4.2 m 흰 석재 테라스. 3층부터 층마다 0.9 m씩 뒤로 물러난다. 층마다 바닥판이 튀어나오고 유리 난간, 금빛 실내등, 화분. 1층은 금빛 로비와 금테 차양, 작은 금속 로고. 옥상 정원 | 인도 화단과 가로수(9 m 간격), 화단 간접등, 도로 중앙 수로, 유리 공중 통로. 따뜻한 금빛 | 큰 고급 홀로그램 1개(고리와 글자), 건물마다 작은 금속 로고 |

### 무기 → 스펙 `GUN`, `WPN`, `MELEE` (C10)
- 지금 `GunShapes.luau`가 코드로 조립하는 총 12종을 이 모델로 바꾼다. 무기군이 같은 것끼리 대응시키고, 대응표를 먼저 보여 준다. 모델이 없는 총은 `docs/asset-requests.md`에 적는다. `GunShapes`는 불러오기 실패 때 대체용과 원거리 LOD로 남긴다.
- 좌표: 총구가 -Y, 위가 +Z, 원점은 쥐는 손 위치다. 기존 뷰모델의 손 위치와 부착물 자리에 맞춘다.
- `manifest`의 `pivots`가 붙임점이다: `muzzle`(총구 화염, 예광탄 시작점), `eject`(탄피 배출), `grip`(오른손), `support`(왼손), `sight`(조준경 자리), `mag`(탄창).
- 따로 움직이는 부품: `slide`(권총), `bolt`(소총·기관단총·저격총), `mag`(재장전 때 빠짐), `trigger`, `cylinder`(리볼버, 회전), `hammer`, `pump`(산탄총, 앞뒤로), `coil_glow`(저격총, 충전량에 따라 밝기), `edge_glow`(장검 날 빛).
- 양식: 권총·돌격소총은 군용 각진 양식(도탄형에 배정), 기관단총은 흰색 기업 양식(유도형), 저격총은 코일이 달린 충전 관통형, 리볼버·산탄총은 거리 개조 양식.
- 발광(조준경 렌즈, 레이저, 탄창 창, 코일)은 발광 마스크로 옮기고 상태에 따라 켜고 끈다.
- 추가 9종
  - `lmg`(경기관총, 군용): 탄통(`mag`)이 아래에 달리고 급탄 덮개(`cover`)가 뒤 축으로 75° 열린다. 양각대. 클립 `lmg_fire`, `lmg_reload`
  - `dmr`(정밀 소총, 기업): 소음기 일체형, 조준경, 엄지 구멍 개머리판. 반자동이라 `auto_fire`를 한 발씩 쓴다
  - `shotgun_double`(2연발, 거리 개조): 총열 뭉치(`barrels`)가 앞 축으로 38° 꺾인다. 공이치기 2개. 클립 `double_fire`, `break_reload`
  - `shotgun_auto`(자동, 군용): 원통 탄창(`mag`). 클립 `auto_fire`, `mag_reload`
  - `baton`(전기 곤봉): `arc_glow`가 켜져 있는 동안 깜빡인다(`baton_arc`). 타격점 `tip`
  - `hammer`(충격 망치, 양손): 휘두를 때 `thruster_glow`가 번쩍인다(`hammer_thrust`). `grip`, `support`, `tip`
  - `knuckles`(주먹 무기): 맞는 순간 `impact_glow`(`knuckle_impact`)
  - `grenade`, `grenade_emp`: 핀(`pin`)을 뽑고 손잡이(`lever`)가 튄다(`grenade_prime`). `glow_band`가 터지기 전까지 밝아진다
- 스펙 `WPN-01`의 무기군이 전부 채워졌다. 게임의 총 12종과 근접·투척을 이 17종에 대응시킨 표를 먼저 보여 준다.

### 비행 차량 → 스펙 `WLD-65`, `VEH` (C7 하늘 교통)
- `SkyTraffic`의 비행 차량을 이 모델로 바꾼다. 변형 3종(`civil`, `patrol`, `cargo`)을 섞는다.
- 추진기 4개(`pod_FL/FR/RL/RR`)는 X축으로 기울인다(떠 있을 때 0°, 전진할 때 60~80°). 팬(`fan_*`)은 Z축으로 돈다.
- 발광: 추진기 아래 `thrust_glow`, 배 아래 `belly_glow`, 뒤 `nozzle_glow`, 앞 `nose_light`·`headlamp`, 옆 `nav_light`(왼쪽 빨강, 오른쪽 청록). 순찰 변형은 지붕 경광등이 번갈아 깜빡인다.
- 착륙 다리(`skid`)는 비행 중에 숨기거나 접는다.

### 거리 NPC → 스펙 `WLD-60~63` (C2 군중과 합침)
- 얼굴을 가린 5종(우비+발광 우산, 테크웨어+헬멧, 작업자+안전모, 배달부+배달 상자, 회사원+모자·목도리)을 군중에 섞는다. 맨얼굴 사람(`human` 10명)과 비율을 정해 같이 쓴다.
- 뼈 동작은 C2의 "코드가 뼈를 직접 움직이는 방식"을 그대로 쓴다. 부품과 관절 이름이 로봇과 같다(`thigh_L`, `shin_L`, `upperarm_L`, `forearm_L`, `head`, `torso`, `pelvis`).
- 긴 옷자락(`skirt`)은 걸을 때 앞뒤로 조금 흔든다. 소품(`prop`: 우산, 공구함, 서류 가방)은 손에 붙어 있다.
- 색과 발광색을 바꿔 변형을 늘린다(겉옷 색, 바지 색, 발광색은 `npc.py`의 `SPEC` 표를 본다).
- 가까이서 보면 인형 같은 단순한 형태다. 가까운 거리에는 맨얼굴 사람(`human`)을 우선 세우고, 이 5종은 중간·먼 거리 군중과 비 오는 밤 분위기용으로 쓴다.

### 맨얼굴 사람 → 스펙 `WLD-60~63`, `DOC`, `CLN` (C2 군중, C11 시술소)
사람은 다른 에셋과 다르다. **뼈대가 든 스킨 메시**이고 텍스처가 이미 그림 파일로 들어 있다(1024, GLB 안에 포함). 3번의 "재질 굽기"와 "합치기와 뼈"는 하지 않는다.
1. **가져오기**: GLB를 Blender에서 열어 FBX로 내보내거나 GLB를 바로 올린다. 뼈 53개와 뼈 이름은 그대로 둔다. 뼈 영향은 정점당 4개 이하로 줄인다(Limit Total).
2. **메시 합치기**: 몸·눈·눈썹·속눈썹·치아·머리·옷·신발·장식이 따로 들어 있다(21~24개). 재질 기준으로 합쳐 메시 수를 줄인다: 불투명(피부+옷+신발+장식 금속), 반투명(머리+눈썹+속눈썹), 발광(장식의 `glow_*`). 합치면서 아틀라스로 다시 굽는 것은 해도 된다(모양과 색은 바꾸지 않는다).
3. **재질**: 내보낸 파일은 전부 반투명(BLEND)으로 표시돼 있다. 피부·옷·신발은 불투명으로 바꾼다. 머리·눈썹·속눈썹만 알파를 쓴다.
4. **삼각형**: 한 사람이 3만 7천~4만 9천이다. 가까운 거리용 LOD0은 2만 이하 메시 2~3개로 나누고, LOD1 35%, LOD2 12%를 만든다. 옷 아래 몸은 이미 지워져 있다. **옷을 벗긴 몸을 내보내지 않는다.**
5. **애니메이션**: `RigAnimator.new(model, manifest.joints)`로 만들면 `humanoid` 클립 전부가 그대로 돈다. 확인 기준은 `human/human_walk_check.png`(걷기 6장)와 `anim/preview_human_actions.png`(새 동작 12개)다. 손가락은 `anim:setHand`로 움직인다.
6. **장식(사이버웨어)**: 바이저, 확대경, 귀 장치, 뺨 선, 목 단자, 가슴 표지는 `manifest.cyberware`에 이름이 있고 머리·목·가슴 뼈에 붙어 있다. 발광색은 `manifest.glow`다. 발광 세기는 밤에 얼굴이 묻히지 않을 만큼만 준다.
7. **쓰는 곳**: 진행 중인 C2 작업은 끊지 않는다. C2가 끝난 뒤 행인의 겉모습만 이 10명으로 바꾼다(가까운 거리). 가면 NPC 5종은 중간·먼 거리와 비 오는 밤 군중에 섞는다. `doctor`는 시술소 의사(`DOC`) 자리에, `merchant`는 가게와 노점에 세운다.
8. **사람 늘리기**: 옷 색·머리 색·발광색만 바꾼 변형은 게임에서 텍스처 색조로 만들지 말고 요청한다(`human.py`의 `PEOPLE` 표에 한 줄 더하면 된다). 얼굴·체형이 다른 사람도 같은 방식으로 요청한다.
9. **출처**: 몸·옷·머리는 MakeHuman CC0 에셋이고 장식은 자체 제작이다. `manifest.assets_cc0`에 쓴 에셋 이름이 있다. 프로젝트의 출처 목록에 옮겨 적는다.

### 드론, 포탑, 감시 카메라 → 스펙 `SEC`, `ENM`, `NET` (C7b, 전투·잠입)
- 색과 양식은 보안 로봇과 같다(남색 장갑, 밝은 회색, 주황 표시, 붉은 눈). 같은 보안 체계로 보여야 한다.
- **드론**(폭 약 1 m): 팬 4개(`fan_FL/FR/RL/RR`, Z축 회전), 배 아래 총좌 `gimbal`(`gimbal_yaw` 좌우 ±180°) → `gun`(`gun_pitch` 상하 −60~20°). 붙임점 `muzzle`, `eye`. 발광 `eye`(붉은 눈), `thrust_glow`. 클립 `drone_hover`, `drone_alert`, `drone_fire`, `drone_crash`. 이동은 `Traffic`의 하늘 경로나 `Patrol`을 높이만 더해 쓴다.
- **포탑**(높이 약 1.15 m, 뒤집으면 천장형): `base` → `yoke`(`yaw` ±170°) → `head`(`pitch` −35~45°) → `barrels`(`recoil`). 발광 `status_glow`(받침 고리, 옆 표시등), `eye`. 클립 `turret_scan`, `turret_alert`, `turret_fire`, `turret_shutdown`. 해킹·무력화하면 `turret_shutdown`을 틀고 발광을 끈다.
- **감시 카메라**(벽 설치): `base` → `arm`(`pan` ±90°) → `head`(`tilt` −50~20°). 발광 `eye`. 클립 `camera_sweep`, `camera_alert`, `camera_disabled`. 시야 원뿔은 `eye` 붙임점에서 낸다.
- 경계 단계 색: 평소 = 발광 50%, 의심 = 주황으로 바꿈, 경보 = 붉은색 100%와 깜빡임. 색은 `EmissiveTint`로 바꾼다.

### 시술소 → 스펙 `CLN`, `DOC`, `SURG` (C11)
- **`clinic_scene.png`가 시술소 분위기 목표**다: 어두운 방, 수술등 하나가 의자를 비추고, 벽에 자홍·청록 띠 조명, 선반과 수납장, 벽 화면. 시술의가 의자 왼팔 받침 옆에 선다.
- **의자**(`chair`): 부품 `base`, `seat`(`lift` 높이), `back`(`recline`), `headrest`, `legrest`, `armrest_L`, `armrest_R`. 왼쪽 팔걸이(+X)는 팔 시술용 받침이다(고정 고리 3개, 작업등, 받침 접시). 머리 받침 양옆에 접속 장치. 발광 `status_glow`(기둥 고리, 옆선, 고정 고리), `work_light`. 클립 `chair_recline`(플레이어가 앉으면), `chair_release`.
- **천장 로봇 팔**(`surgery_rig`): 고리형 받침, 수술등(`lamp`), 팔 3개: `arm_A`(레이저), `arm_B`(집게), `arm_C`(스캐너). 팔마다 `_shoulder`(좌우), `_elbow`, `_wrist`, 끝점 `_tip`. 발광 `tool_glow`, `work_light`, `status_glow`. 클립 `surgery_start`, `surgery_loop`. 레이저 불꽃과 소리는 `surgery_loop`의 `laser`·`servo` 이벤트에 붙인다.
- **도구 수레**(`cart`): 도구, 약병 3개(`vial_glow`), 칩 상자, 화면(`monitor`, 회전). 화면의 심박선과 막대(`screen_glow`)는 시술 중에 움직이게 한다(UV 스크롤이나 SurfaceGui).
- 시술 연출 순서(스펙 `SURG`): 플레이어가 의자에 앉는다(`sit_down` → 1인칭 시점 고정) → `chair_recline` → `surgery_start` → `surgery_loop`(화면 어두워짐, 부위 강조) → `chair_release` → `stand_up`. 시술의는 `talk`와 `idle`을 쓰고, 시술 중에는 화면 쪽을 본다.

### 사이버웨어 팔 3종과 1인칭 팔 → 스펙 `CW`, `BODY` (C10, C11)
- 좌표는 블레이드 팔과 같다: X = 팔꿈치 → 손끝, Y = 엄지 쪽, Z = 손등 쪽. 팔꿈치가 원점, 손목이 x = 0.27 m. 게임의 오른팔 아래팔 뼈에 맞춰 붙인다.
- 공통 부품: `forearm`, `hand`, 손가락 `finger1_a` ~ `finger4_c`(검지~새끼, 마디 3개씩), `thumb_a`, `thumb_b`, 발광 `glow`. 관절은 `manifest.pivots`에 있다.
- **파워암**(`power`, 노랑·검정): 옆 유압 피스톤(`piston`), 손목 코일(`charge_glow`), 너클 판(`knuckle_plate`). 클립 `power_charge`(주먹을 쥐고 판이 2 cm 나오며 코일이 밝아진다) → 타격 → `power_release`.
- **나노와이어**(`nanowire`, 흰색·검정, 자홍 발광): 손목 안쪽 감개(`spool`)와 덮개(`spool_cover`). **실은 모델에 없다.** 붙임점 `wire_out`부터 Beam이나 Trail로 그린다(굵기 약 2 mm, 자홍 발광, 길이 2.5~3 m, 채찍처럼 휘는 곡선). 클립 `wire_deploy`, `wire_retract`.
- **런처**(`launcher`, 올리브·검정, 붉은 발광): 손등 문 2장(`hatch_L`, `hatch_R`)이 72° 열리고 발사관(`tube`)이 3 cm 올라온다. 탄두(`rocket`)는 쏘면 숨긴다. 붙임점 `muzzle`, `backblast`(뒤로 나가는 연기). 옆의 탄약 표시등 3개. 클립 `launcher_deploy`, `launcher_fire`, `launcher_retract`.
- **블레이드 팔**: 클립 `blade_deploy`, `blade_retract`가 생겼다(문 56° → 칼날 23 cm 전진 → 날 발광).
- **1인칭 팔**(`fp_sleeve`, `fp_bare`): 진짜 사람 팔이다. 스킨 메시이고 사람과 같은 뼈대·관절표를 쓴다. `manifest.eye`가 카메라 자리다. 사이버웨어를 달면 오른쪽 아래팔과 손을 숨기고 그 자리에 사이버웨어 팔을 붙인다(팔꿈치를 `lowerarm_r` 머리에, X축을 뼈 방향에 맞춘다).
- 1인칭 동작은 `fp_*` 클립을 쓴다. `view` 값을 팔·무기 뭉치 전체의 카메라 기준 이동·회전으로 적용한다. 무기군별 대응: 권총 `fp_recoil_pistol` + `fp_raise_light`, 리볼버 `fp_recoil_revolver`, 기관단총·소총 `fp_recoil_auto`, 경기관총 `fp_recoil_lmg`, 산탄총 `fp_recoil_shotgun`, 저격총·정밀 소총 `fp_recoil_sniper`, 큰 총 꺼내기 `fp_raise_heavy`. 기존 반동·조준 값이 이미 승인된 것이면 그 값을 유지하고 이 클립은 빈 곳에만 쓴다.
- 손 모양은 `anim:setHand("R", handPoses.grip_pistol)`처럼 준다(`blender/out/anim/hand_poses.json`). 총을 쥔 손가락이 손잡이를 뚫으면 굽힘 값을 무기별로 조금 줄인다.
- **걷기 흔들림은 넣지 않는다.** `fp_idle`은 멈춰 있을 때의 숨쉬기 흔들림뿐이다.

### 블레이드 팔 → 스펙 `CW-14` (C11)
- 등쪽 장갑 문이 바깥 모서리를 축으로 56° 열리고, 칼집에서 칼날이 앞으로 나온다. 꺼내기 애니메이션은 이 순서로 만든다: 문 열림(0.15초) → 칼날 전진(0.2초) → 잠금.
- 1인칭에서 보이는 각도(팔 안쪽, 손바닥) 보강이 필요하면 요청한다.

## 4-1. 애니메이션과 이동도 받아서 쓴다 (새로 만들지 않는다)
`docs/cyberpunk-reference/runtime/`에 Luau 모듈과 테스트가, `blender/out/anim/`에 클립 94개와 손 모양 8개가 있다. `runtime/README.md`를 먼저 읽는다.

1. **넣기**: `runtime/*.luau`를 `src/shared/Fable/`(이름은 프로젝트 규칙에 맞게)로 복사한다. 클립 JSON은 ModuleScript 표로 변환하는 빌드 단계를 만든다. `tests/run.luau`의 검사 47개를 프로젝트의 Lune 테스트에 편입한다(경로만 고친다).
2. **고치지 않는다**: 걸음 곡선, 군중 규칙, 순찰·교통 로직을 다시 짜지 않는다. 버그를 찾으면 재현 테스트와 함께 사용자에게 알린다. Roblox 연결부(`RigAnimator`)만 Studio에서 확인하며 고친다.
3. **`RigAnimator` 확인 (가장 먼저)**: 이 파일만 여기서 테스트하지 못했다. 보안 로봇에 `walk_heavy`를 틀고 Blender 미리보기(`preview_robot_walk_heavy.png`)와 같은 자세가 나오는지 본다. 팔다리가 엉뚱한 축으로 돌면 `RigAnimator.AXIS` 표를 고친다. 뼈는 관절 위치에 만든다. 뼈의 기준 방향은 `RigAnimator`가 모델에서 읽어 보정하므로 맞추지 않아도 된다. 그다음 사람(`human_man_a`)에 `walk`를 틀어 `human_walk_check.png`와 비교한다.
4. **군중**: C2에서 만든 군중 이동을 `Crowd`로 바꾼다. 허브의 인도 그래프(`nodes`, `edges`), 소품 위치(`obstacles`), 활동 지점(`activities`)은 맵 정보(`WLD-150~153`)에서 만든다. 횡단보도는 `signal`로 신호등과 묶는다. 총성 이벤트는 `crowd:panic(x, z, 반경)`으로 넘긴다. 에이전트의 `anim`, `speed`, `heading`을 그대로 `RigAnimator`에 넘긴다.
5. **보안 로봇**: 이동은 `Patrol`, 동작은 `walk_heavy` / `robot_scan` / `robot_alert` → `robot_aim` / `robot_fire` / `robot_shutdown` / `robot_boot`. 기존 AI의 판단(발각, 경고 단계)은 유지하고 **몸을 움직이는 부분만** 이걸로 바꾼다.
6. **차량**: 지상 교통과 `SkyTraffic`의 이동을 `Traffic`으로 바꾼다. `wheel`(라디안)을 바퀴 4개에, `bank`와 `tilt`를 비행 차량 몸체와 추진기에 적용한다. `braking`이면 뒤 발광을 세게 한다.
7. **무기**: 발사·재장전 때 부품 클립(`pistol_fire`, `auto_fire`, `shotgun_pump`, `mag_reload` 등)을 틀고, 클립의 이벤트(`muzzle`, `eject`, `mag_out`, `mag_in`, `chamber`)에 총구 화염·탄피·소리를 붙인다.
8. **발소리**: 걷기·달리기 클립의 `foot_L` / `foot_R` 이벤트에 바닥 재질별 발소리를 붙인다.
9. **새 사람 동작**: 앉기(`sit_down`, `sit_loop`, `stand_up`), 넘어짐(`knockdown`, `lie_loop`, `get_up`), 쓰러짐(`collapse`: 무릎을 꿇고 주저앉는다. Kids 설정에서는 이 뒤에 소멸 연출을 붙인다), 3인칭 무기 자세(`aim_pistol`, `aim_rifle`, `low_ready`, `fire_pistol_3p`, `fire_rifle_3p`), 근접(`melee_slash`, `melee_stab`, `melee_heavy`, `punch`), 던지기(`throw`). 근접은 `hit` 이벤트에서 판정하고 `swing`에서 휘두르는 소리를 낸다. 미리보기는 `preview_human_actions.png`다.
10. **부품 클립**(`weapon`, `cyberarm`, `machine`, `clinic`)은 `AnimSampler.sample`로 값을 뽑아 부품에 직접 적용한다. 값의 뜻은 `runtime/README.md`의 클립 표 아래에 있다.
11. **아직 없는 동작**: 사다리, 수영, 차 타고 내리기, 문 여는 손, 얼굴 표정(눈 깜빡임, 입 모양). 필요하면 `docs/asset-requests.md`에 적는다.
12. 웅크릴 때 손에 든 소품(공구함, 서류 가방, 우산)은 손에서 떼어 바닥에 떨어뜨린다.

## 5. 단계 순서에 미치는 영향
| 단계 | 바뀐 점 |
|---|---|
| C3~C7 허브 | 소품과 건물 규칙은 위 에셋을 쓴다. 분위기 비교 기준은 `street_night.png`(밤)와 `street_day.png`(낮)이다. C4의 구역 양식은 `district_*.png`와 `districts.py` 규칙을 쓴다 |
| C7b 보안 NPC | 외형 시안 단계를 건너뛴다. `security_robot`, `machines`(드론, 포탑, 감시 카메라)를 쓴다 |
| C10 팔·총 | `weapons` 17종, 1인칭 팔 `fp_sleeve`·`fp_bare`, `fp_*` 클립, 손 모양을 쓴다. `GunShapes`는 불러오기 실패 대체용과 원거리 LOD로만 남긴다 |
| C2 군중 | 진행 중인 작업을 먼저 끝낸다. 그 뒤 맨얼굴 행인의 겉모습을 `human` 10명으로 바꾸고, 이동은 `Crowd`, 동작은 `RigAnimator`로 옮긴다 |
| C11 사이버웨어 | 팔 4종(`cyber-arm` 블레이드, `cyber_arms`의 파워암·나노와이어·런처), 시술소 `clinic`, 시술의 `human/doctor`를 쓴다. 에셋을 기다릴 것이 없다 |
| C13 차량 | `car`를 쓴다 |

## 6. 아직 없는 에셋 (만들지 말고 기다릴 것)
이전 목록(나머지 무기, 사이버웨어 팔 3종, 1인칭 팔, 시술소, 드론, 포탑, 낮 그림, 구역 양식)은 전부 만들었다. 남은 것은 아래뿐이다.
- 적 차림(갱, 기업 경비)과 보스: 적·보스 디자인이 아직 승인되지 않았다. 승인 전에는 만들지 않는다.
- 사람 추가분: 아이·노인 여성 변형, 구역별 차림(부유층 옷, 빈민 옷).
- 탈것 추가분: 오토바이, 화물차, 버스.
- 실내 소품: 가게 내부, 술집, 집 가구. 모험 맵 전용 소품(맵 기획 승인 뒤).
- 동작: 4-1의 11번.

## 7. 에셋을 요청하는 방법
필요한 에셋이 생기면 `docs/asset-requests.md`에 적고 사용자에게 알린다.
- 무엇인지, 어디에 쓰는지, 크기, 따로 움직여야 하는 부분, 붙여야 하는 이펙트 위치, 삼각형 예산, 급한 정도.

## 8. 시작
1. 저장소에서 받아 `tools/blender/fable/`에 넣는다.
2. **보안 로봇 하나를 끝까지** 반영한다(굽기, 뼈, LOD, 업로드, 허브에 세우기). Blender 사진과 Studio 사진을 나란히 놓아 보여 주고 멈춘다.
3. 승인되면 같은 방식으로 차량, 거리 소품 순서로 진행한다.
