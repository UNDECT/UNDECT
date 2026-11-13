# 런타임: 애니메이션 재생과 NPC·차량 이동 (Luau)

게임에 그대로 넣어 쓰는 모듈이다. `RigAnimator`만 Roblox API를 쓰고, 나머지는 순수 로직이라 Lune으로 테스트한다.

| 파일 | 하는 일 | 테스트 |
|---|---|---|
| `AnimSampler.luau` | 클립 JSON에서 시각별 자세 뽑기, 두 자세 섞기, 이벤트(발 디딤·총구·탄피) 뽑기, 이동 속도에 걷기 주기 맞추기 | ✅ Blender 쪽 기준값과 비교 |
| `RigSolver.luau` | 자세(관절 각도) → 부품별 변환 행렬. `manifest.json`의 관절로 뼈대를 만든다 | ✅ Blender가 계산한 행렬과 비교 |
| `Crowd.luau` | 거리 군중: 인도 그래프 따라 걷기, 서로 비켜 가기, 소품 피하기, 신호 대기, 활동(대화·전화), 총성에 도망·웅크림, 거리별 갱신 줄이기 | ✅ |
| `Patrol.luau` | 보안 로봇 순찰: 점 돌기, 모퉁이에서 멈춰 훑기, 제자리 회전 후 출발, 경계 시 목표 조준 | ✅ |
| `Traffic.luau` | 지상·하늘 교통: 차선 따라 주행, 앞차 간격, 빨간 신호 정지, 바퀴 회전, 비행 차량 기울기와 추진기 각도 | ✅ |
| `RigAnimator.luau` | Roblox 연결: 자세를 Bone/Motor6D의 `Transform`에 적용, 동작 전환 섞기 | ⚠️ Studio에서 확인 필요 |
| `tests/run.luau` | 테스트 37개 | `lune run tests/run.luau` (이 폴더에서 실행) |

## 클립
- 위치: `../blender/out/anim/*.json` (24개). 목록은 `_index.json`.
- 사람·로봇 공용: `walk`, `walk_slow`, `run`, `idle`, `look_around`, `talk`, `phone`, `cower_enter`, `cower_loop`, `hit_react`
- 로봇: `walk_heavy`, `robot_scan`, `robot_alert`, `robot_aim`, `robot_fire`, `robot_shutdown`, `robot_boot`
- 무기 부품: `pistol_fire`, `revolver_fire`, `auto_fire`, `shotgun_pump`, `bolt_cycle`, `mag_reload`, `charge`
- 클립은 뼈대와 무관한 "의미 관절"로 적혀 있다(`hip_L.flex`, `knee_L.bend`, `waist.yaw` …). 규칙은 `../blender/anim.py` 맨 위 주석을 본다. 관절 이름이 같으면 어떤 모델에도 쓸 수 있다.
- 미리보기 사진: `../blender/out/anim/preview_*.png`

## 쓰는 법 (요약)
```lua
local clip = HttpService:JSONDecode(walkJson)      -- 또는 ModuleScript로 변환해 둔 표
local anim = RigAnimator.new(npcModel)
anim:play(clip, 0.2)
-- 매 프레임
local events = anim:update(dt, agent.speed)        -- 걷기 주기를 이동 속도에 맞춘다
for _, e in events do if e == "foot_L" or e == "foot_R" then playFootstep() end end
```
```lua
local crowd = Crowd.new(world, {seed = 1}); crowd:spawn(40)
crowd:step(dt, signals, {x = camX, z = camZ})      -- agent.x, z, heading, anim, speed, state
crowd:panic(x, z, 25)                               -- 총성
```

## 좌표
- 클립과 `RigSolver`는 에셋 원본 좌표를 쓴다: 단위 m, 앞 = -Y, 위 = +Z.
- `Crowd`, `Patrol`, `Traffic`은 평면 좌표 `x, z`와 `heading`(라디안, `atan2(dx, dz)`)을 쓴다. 단위는 m 기준이다. 스터드로 쓰려면 위치·속도·반경에 같은 배율을 곱한다.
- Roblox 축으로 바꾸는 표는 `RigAnimator.AXIS` 한 곳에만 있다. 가져온 모델의 축이 다르면 이 표만 고친다.
