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
python human.py out/human render       # 맨얼굴 사람 10명 + 1인칭 팔 2종 (아래 '사람' 준비가 필요)
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
| `human.py` | 맨얼굴 사람 10명(거리 사람 5, 노동자, 상인, 회사원, 임원, 시술의)과 1인칭 팔 2종. 뼈대 53개, 사이버웨어 장식, 애니메이션 관절 대응표(손가락 포함) |
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

## 사람 (`human.py`) 준비
사람 몸·얼굴·옷은 외부 도구로 만든다. 저장소에는 넣지 않았으니 한 번만 준비한다.
1. Blender 확장 **MPFB 2.0.x**(GPL)를 설치한다. `pip install bpy` 환경이면 `~/.config/blender/5.3/extensions/user_default/mpfb`에 풀고 `bl_ext.user_default.mpfb`를 켠다.
2. MakeHuman 에셋 묶음을 MPFB 사용자 데이터 폴더(`~/.config/blender/5.3/extensions/.user/user_default/mpfb/data`, 다른 위치면 환경 변수 `MPFB_DATA`)에 푼다: 시스템 에셋, shirts01, pants01, shoes01, suits01, gloves01, eyebrows01, eyelashes01, skins02.
3. **CC0 묶음만 쓴다.** `human.py`가 `data/packs/*.json`으로 목록을 만들고, CC0가 아닌 묶음(`hair03`, `masks02`)의 에셋을 쓰면 멈춘다. 로고가 찍힌 옷, 정치 문구 소품, 다른 작품 캐릭터를 닮은 소품도 쓰지 않는다.
- 결과물(`out/human/<이름>/human_<이름>.glb`)은 CC0 에셋과 이 스크립트가 만든 장식으로만 이뤄진다. 쓴 에셋 이름은 `manifest.json`의 `assets_cc0`에 있다.
- 옷과 머리 색은 텍스처를 흑백으로 만든 뒤 다시 칠한다(`tint`). 사람을 늘리려면 `PEOPLE` 표에 한 줄을 더한다.
- `manifest.json`의 `joints`는 애니메이션 클립의 관절 이름 → 이 뼈대의 뼈 이름 대응표다. 기본 자세가 팔을 벌린 자세라서 팔을 내린 자세까지의 회전(`neutral`)이 같이 들어 있다.
- 환경 변수: `HUMAN_RES`(사진 크기), `HUMAN_STRIPS=walk,knockdown,...`(클립을 뼈대에 적용한 연속 사진), `HUMAN_SKIP_FP=1`(1인칭 팔 건너뛰기).
- 1인칭 팔(`fp_sleeve`, `fp_bare`)은 사람을 만든 뒤 팔 뼈에 붙은 부분만 남긴 것이다. `manifest.json`의 `eye`가 카메라 자리다.
- 손 모양은 `out/anim/hand_poses.json`에 있다(편 손, 주먹, 권총 쥐기, 소총 쥐기, 받치는 손, 근접 무기 쥐기, 가리키기).
