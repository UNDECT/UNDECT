# 런타임: 애니메이션 재생과 NPC·차량 이동 (Luau)

게임에 그대로 넣어 쓰는 모듈이다. `RigAnimator`만 Roblox API를 쓰고, 나머지는 순수 로직이라 Lune으로 테스트한다.

| 파일 | 하는 일 | 테스트 |
|---|---|---|
| `AnimSampler.luau` | 클립 JSON에서 시각별 자세 뽑기, 두 자세 섞기, 이벤트(발 디딤·총구·탄피) 뽑기, 이동 속도에 걷기 주기 맞추기, 손 모양 더하기 | ✅ Blender 쪽 기준값과 비교 |
| `RigSolver.luau` | 자세(관절 각도) → 부품(뼈)별 변환 행렬. `manifest.json`의 `pivots`(부품 모델)나 `joints`(사람 뼈대)로 뼈대를 만든다 | ✅ Blender가 계산한 행렬과 비교(로봇, 사람) |
| `Crowd.luau` | 거리 군중: 인도 그래프 따라 걷기, 서로 비켜 가기, 소품 피하기, 신호 대기, 활동(대화·전화), 총성에 도망·웅크림, 거리별 갱신 줄이기 | ✅ |
| `Patrol.luau` | 보안 로봇 순찰: 점 돌기, 모퉁이에서 멈춰 훑기, 제자리 회전 후 출발, 경계 시 목표 조준 | ✅ |
| `Traffic.luau` | 지상·하늘 교통: 차선 따라 주행, 앞차 간격, 빨간 신호 정지, 바퀴 회전, 비행 차량 기울기와 추진기 각도 | ✅ |
| `RigAnimator.luau` | Roblox 연결: 자세를 Bone/Motor6D의 `Transform`에 적용, 동작 전환 섞기. 사람은 `RigAnimator.new(model, manifest.joints)` | ⚠️ Studio에서 확인 필요 |
| `tests/run.luau` | 테스트 47개 | `lune run tests/run.luau` (이 폴더에서 실행) |

## 클립
위치는 `../blender/out/anim/*.json`(94개)이고 목록은 `_index.json`에 있다. `rig` 값으로 어디에 쓰는 클립인지 구분한다.

| rig | 개수 | 클립 | 적용 대상 |
|---|---|---|---|
| `humanoid` | 34 | 이동: `walk`, `walk_slow`, `run`, `walk_heavy` / 대기: `idle`, `look_around`, `talk`, `phone` / 반응: `cower_enter`, `cower_loop`, `hit_react`, `knockdown`, `lie_loop`, `get_up`, `collapse` / 앉기: `sit_down`, `sit_loop`, `stand_up` / 무기 자세: `aim_pistol`, `aim_rifle`, `low_ready`, `fire_pistol_3p`, `fire_rifle_3p` / 근접: `melee_slash`, `melee_stab`, `melee_heavy`, `punch`, `throw` / 로봇: `robot_scan`, `robot_alert`, `robot_aim`, `robot_fire`, `robot_shutdown`, `robot_boot` | 사람, 가면 NPC, 보안 로봇 |
| `fp` | 21 | `fp_idle`, `fp_raise_light`, `fp_raise_heavy`, `fp_lower`, `fp_recoil_pistol/revolver/auto/lmg/shotgun/sniper`, `fp_reload`, `fp_ads_in`, `fp_ads_out`, `fp_slash`, `fp_stab`, `fp_punch`, `fp_heavy`, `fp_throw`, `fp_inspect`, `fp_sprint`, `fp_land` | 1인칭 팔과 무기 뭉치 |
| `weapon` | 15 | `pistol_fire`, `revolver_fire`, `auto_fire`, `lmg_fire`, `double_fire`, `shotgun_pump`, `bolt_cycle`, `mag_reload`, `lmg_reload`, `break_reload`, `charge`, `grenade_prime`, `baton_arc`, `hammer_thrust`, `knuckle_impact` | 무기의 움직이는 부품 |
| `cyberarm` | 9 | `blade_deploy/retract`, `power_charge/release`, `wire_deploy/retract`, `launcher_deploy/fire/retract` | 사이버웨어 팔 부품 |
| `machine` | 11 | `drone_hover/alert/fire/crash`, `turret_scan/alert/fire/shutdown`, `camera_sweep/alert/disabled` | 드론, 포탑, 감시 카메라 |
| `clinic` | 4 | `chair_recline`, `chair_release`, `surgery_start`, `surgery_loop` | 시술 의자, 천장 로봇 팔 |

- `humanoid` 클립은 뼈대와 무관한 "의미 관절"로 적혀 있다(`hip_L.flex`, `knee_L.bend`, `waist.yaw` …). 규칙은 `../blender/anim.py` 맨 위 주석을 본다. 관절 이름이 같으면 어떤 모델에도 쓸 수 있다.
- `fp` 클립의 `view` 관절은 팔과 무기 뭉치 전체를 카메라 기준으로 옮기는 값이다: `x` 오른쪽, `y` 뒤(+)·앞(−), `z` 위(m), `pitch` 총구 위(+), `yaw` 왼쪽(+), `roll`(도). `value`는 0~1 진행률이다(조준 정도, 손에서 떠남 등). **걷기 흔들림은 없다.** 멈춰 있을 때의 숨쉬기 흔들림(`fp_idle`)만 있다.
- `weapon`, `cyberarm`, `machine`, `clinic` 클립은 관절 이름이 부품(또는 manifest의 관절) 이름이다. `move_x/y/z`는 이동(m), `pitch/yaw/roll/open`은 회전(도), `spin`은 회전수, `value`는 발광 세기나 보임 여부(0~1)다. 이 클립들은 `AnimSampler.sample`로 값을 뽑아 게임 코드가 부품에 직접 적용한다(`RigAnimator`를 쓰지 않는다).
- 이벤트: `foot_L/R`, `shot`, `muzzle`, `eject`, `mag_out`, `mag_in`, `chamber`, `swing`, `hit`, `release`, `body_fall`, `seat`, `draw`, `alert`, `disabled`, `impact`, `open`, `lock` 등. 소리와 이펙트를 여기에 붙인다.
- 30fps 키라서 반동처럼 아주 빠른 움직임은 첫 프레임(1/30초)에 정점이 온다.
- 미리보기 사진: `../blender/out/anim/preview_*.png` (`preview_human_actions.png`가 새 사람 동작 12개다)

## 손 모양
`../blender/out/anim/hand_poses.json`: `open`, `relaxed`, `fist`, `grip_pistol`, `grip_rifle`, `support`, `grip_melee`, `point`. 손가락마다 마디 3개의 굽힘 각(도)이다.
```lua
anim:setHand("R", handPoses.grip_pistol)      -- 오른손으로 권총을 쥔다. nil을 주면 푼다
anim:setHand("L", handPoses.support, 0.8)     -- 세 번째 값으로 세기를 조절한다
```
사람 뼈대(`human_*`, `fp_*`)에서만 된다. 손가락 관절은 `manifest.joints`의 `index_R_1` 같은 항목이고 `curl` 한 가지로 움직인다.

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

## 사람 뼈대에 쓰기
```lua
local man = HttpService:JSONDecode(manifestJson)         -- human_<이름>.manifest.json
local anim = RigAnimator.new(humanModel, man.joints)     -- 모델이 기본 자세일 때 만든다
anim:play(walkClip, 0.2)
```
- 사람(`human_*`)은 뼈 이름을 바꾸지 않는다. `joints` 표가 `hip_L → thigh_l`처럼 이어 준다.
- 사람 뼈대의 기본 자세는 팔을 벌린 자세다. `joints`의 `neutral`이 팔을 내린 자세로 돌려 준다. 클립이 없는 상태로 `update`만 돌려도 팔이 내려와야 한다.
- 뼈의 기준 방향은 모델에서 직접 읽어 보정한다. 그래서 가져오기 도구가 뼈 축을 바꿔도 된다.

## 좌표
- 클립과 `RigSolver`는 에셋 원본 좌표를 쓴다: 단위 m, 앞 = -Y, 위 = +Z.
- `Crowd`, `Patrol`, `Traffic`은 평면 좌표 `x, z`와 `heading`(라디안, `atan2(dx, dz)`)을 쓴다. 단위는 m 기준이다. 스터드로 쓰려면 위치·속도·반경에 같은 배율을 곱한다.
- Roblox 축으로 바꾸는 표는 `RigAnimator.AXIS` 한 곳에만 있다. 가져온 모델의 축이 다르면 이 표만 고친다.
