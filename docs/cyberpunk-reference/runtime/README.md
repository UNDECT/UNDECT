# 런타임: 애니메이션 재생과 NPC·차량 이동 (Luau)

게임에 그대로 넣어 쓰는 모듈이다. `RigAnimator`만 Roblox API를 쓰고, 나머지는 순수 로직이라 Lune으로 테스트한다.

| 파일 | 하는 일 | 테스트 |
|---|---|---|
| `AnimSampler.luau` | 클립 JSON에서 시각별 자세 뽑기, 두 자세 섞기, 이벤트(발 디딤·총구·탄피) 뽑기, 이동 속도에 걷기 주기 맞추기, 손 모양 더하기 | ✅ Blender 쪽 기준값과 비교 |
| `RigSolver.luau` | 자세(관절 각도) → 부품(뼈)별 변환 행렬. `manifest.json`의 `pivots`(부품 모델)나 `joints`(사람 뼈대)로 뼈대를 만든다 | ✅ Blender가 계산한 행렬과 비교(로봇, 사람) |
| `Crowd.luau` | 거리 군중: 인도 그래프 따라 걷기, 서로 비켜 가기, 소품 피하기, 신호 대기, 활동(대화·전화), 총성에 도망·웅크림, 거리별 갱신 줄이기, **맞기·죽기·시체·목격·다시 채우기** | ✅ |
| `Patrol.luau` | 보안 로봇 순찰: 점 돌기, 모퉁이에서 멈춰 훑기, 제자리 회전 후 출발, 경계 시 목표 조준 | ✅ |
| `Traffic.luau` | 지상·하늘 교통: 차선 따라 주행, 앞차 간격, 빨간 신호 정지, 바퀴 회전, 비행 차량 기울기와 추진기 각도 | ✅ |
| `Vitals.luau` | NPC 체력·피격·사망: 부위 배수, 피해 종류, 맞은 방향, 사망 클립 고르기, 부상당해 기어가기, 수위(`Vitals.GORE` 0~3)별 이펙트 목록 | ✅ |
| `Laser.luau` | 손 레이저 발사: 충전 → 빔(세기 상승, 관통, 거리 감쇠) → 과열 잠김 → 회복 | ✅ |
| `RigAnimator.luau` | Roblox 연결: 자세를 Bone/Motor6D의 `Transform`에 적용, 동작 전환 섞기. 사람은 `RigAnimator.new(model, manifest.joints)` | ⚠️ Studio에서 확인 필요 |
| `tests/run.luau` | 테스트 80개 | `lune run tests/run.luau` (이 폴더에서 실행) |

## 클립
위치는 `../blender/out/anim/*.json`(125개)이고 목록은 `_index.json`에 있다. `rig` 값으로 어디에 쓰는 클립인지 구분한다.

| rig | 개수 | 클립 | 적용 대상 |
|---|---|---|---|
| `humanoid` | 57 | **죽음**: `death_back`, `death_front`, `death_left`, `death_right`, `death_headshot`, `death_knees`, `death_blast`, `death_burn`, `death_shock`, `death_slash`, `death_sit`, `death_crawl` / **부상**: `fall_wounded`, `wounded_crawl` / **피격**: `hit_front`, `hit_back`, `hit_left`, `hit_right`, `hit_head`, `hit_leg`, `stagger` / 손 레이저: `aim_palm`, `fire_palm` / 이동: `walk`, `walk_slow`, `run`, `walk_heavy` / 대기: `idle`, `look_around`, `talk`, `phone` / 반응: `cower_enter`, `cower_loop`, `hit_react`, `knockdown`, `lie_loop`, `get_up`, `collapse` / 앉기: `sit_down`, `sit_loop`, `stand_up` / 무기 자세: `aim_pistol`, `aim_rifle`, `low_ready`, `fire_pistol_3p`, `fire_rifle_3p` / 근접: `melee_slash`, `melee_stab`, `melee_heavy`, `punch`, `throw` / 로봇: `robot_scan`, `robot_alert`, `robot_aim`, `robot_fire`, `robot_shutdown`, `robot_boot` | 사람, 가면 NPC, 보안 로봇 |
| `fp` | 25 | `fp_laser_raise`, `fp_laser_fire`, `fp_laser_overheat`, `fp_laser_lower`, `fp_idle`, `fp_raise_light`, `fp_raise_heavy`, `fp_lower`, `fp_recoil_pistol/revolver/auto/lmg/shotgun/sniper`, `fp_reload`, `fp_ads_in`, `fp_ads_out`, `fp_slash`, `fp_stab`, `fp_punch`, `fp_heavy`, `fp_throw`, `fp_inspect`, `fp_sprint`, `fp_land` | 1인칭 팔과 무기 뭉치 |
| `weapon` | 15 | `pistol_fire`, `revolver_fire`, `auto_fire`, `lmg_fire`, `double_fire`, `shotgun_pump`, `bolt_cycle`, `mag_reload`, `lmg_reload`, `break_reload`, `charge`, `grenade_prime`, `baton_arc`, `hammer_thrust`, `knuckle_impact` | 무기의 움직이는 부품 |
| `cyberarm` | 13 | `laser_deploy/fire/overheat/retract`, `blade_deploy/retract`, `power_charge/release`, `wire_deploy/retract`, `launcher_deploy/fire/retract` | 사이버웨어 팔 부품 |
| `machine` | 11 | `drone_hover/alert/fire/crash`, `turret_scan/alert/fire/shutdown`, `camera_sweep/alert/disabled` | 드론, 포탑, 감시 카메라 |
| `clinic` | 4 | `chair_recline`, `chair_release`, `surgery_start`, `surgery_loop` | 시술 의자, 천장 로봇 팔 |

- `humanoid` 클립은 뼈대와 무관한 "의미 관절"로 적혀 있다(`hip_L.flex`, `knee_L.bend`, `waist.yaw` …). 규칙은 `../blender/anim.py` 맨 위 주석을 본다. 관절 이름이 같으면 어떤 모델에도 쓸 수 있다.
- `fp` 클립의 `view` 관절은 팔과 무기 뭉치 전체를 카메라 기준으로 옮기는 값이다: `x` 오른쪽, `y` 뒤(+)·앞(−), `z` 위(m), `pitch` 총구 위(+), `yaw` 왼쪽(+), `roll`(도). `value`는 0~1 진행률이다(조준 정도, 손에서 떠남 등). **걷기 흔들림은 없다.** 멈춰 있을 때의 숨쉬기 흔들림(`fp_idle`)만 있다.
- `weapon`, `cyberarm`, `machine`, `clinic` 클립은 관절 이름이 부품(또는 manifest의 관절) 이름이다. `move_x/y/z`는 이동(m), `pitch/yaw/roll/open`은 회전(도), `spin`은 회전수, `value`는 발광 세기나 보임 여부(0~1)다. 이 클립들은 `AnimSampler.sample`로 값을 뽑아 게임 코드가 부품에 직접 적용한다(`RigAnimator`를 쓰지 않는다).
- 이벤트: `foot_L/R`, `shot`, `muzzle`, `eject`, `mag_out`, `mag_in`, `chamber`, `swing`, `hit`, `release`, `body_fall`, `seat`, `draw`, `alert`, `disabled`, `impact`, `open`, `lock` 등. 소리와 이펙트를 여기에 붙인다.
- 30fps 키라서 반동처럼 아주 빠른 움직임은 첫 프레임(1/30초)에 정점이 온다.
- 죽는 클립은 반복하지 않는다. 끝 자세가 시체 자세라서 마지막 프레임에서 멈춘 채로 둔다.
- 미리보기 사진: `../blender/out/anim/preview_*.png` (`preview_human_actions.png` = 사람 동작 12개, `preview_human_deaths.png` = 죽음·피격 20개)

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

## NPC를 맞히고 죽이기
```lua
-- 총알·칼·빔이 군중 한 사람에게 맞았을 때 (ag = crowd.agents의 한 항목)
local res = crowd:damage(ag, {damage = 34, kind = "bullet", part = hitBone.Name, dirX = dir.X, dirZ = dir.Z, attacker = player})
-- res.killed / res.downed / res.anim(틀 클립) / res.effects(낼 이펙트 이름들) / res.knock(밀려난 거리)
crowd:explode(x, z, 6, 400, player)            -- 폭발
for _, e in crowd:drain() do ... end           -- death, downed, hurt, witnessed, corpse_gone 사건
crowd:refill({x = px, z = pz}, 60)             -- 치워진 시체 수만큼 플레이어에게서 60 m 밖에 새로 채운다
```
- 에이전트 상태가 늘었다: `stagger`(맞고 비틀거림 → 곧 `flee`), `falling` → `downed`(기어감, `wounded_crawl`) → `dead`. `ag.anim`과 `ag.animTime`(그 클립을 튼 지 몇 초)을 그대로 `RigAnimator`에 넘긴다. `dead`면 클립을 반복하지 않고 끝 프레임에 멈춘다.
- 피해 종류(`kind`): `bullet`, `shotgun`, `blade`, `blunt`, `laser`, `fire`, `electric`, `explosive`, `fall`. 부위는 `zone`을 주거나 맞은 뼈 이름을 `part`로 준다(`Vitals.zoneOf`가 머리·목·몸통·팔·다리로 바꾼다). 배수는 머리 3.0, 목 2.2, 몸통 1.0, 팔 0.6, 다리 0.7.
- 사망 클립은 원인과 방향으로 고른다: 폭발 `death_blast`, 레이저·불 `death_burn`, 감전 `death_shock`, 칼 `death_slash`, 머리·목 `death_headshot`, 앉아 있으면 `death_sit`, 그 밖에는 앞에서 맞으면 `death_back`, 뒤에서 맞으면 `death_front`, 옆에서 맞으면 반대쪽으로 `death_left/right`, 가끔 `death_knees`.
- **수위는 `Vitals.GORE` 한 곳에서 바꾼다.** 지금은 3이다.

| 값 | 맞았을 때 | 죽었을 때 | 시체 |
|---|---|---|---|
| 0 | `hit_flash` | `dissolve` | 1.5초 뒤 사라짐 (Kids 설정용) |
| 1 | `hit_flash`, `hit_dust` | `corpse_fade` | 12초 뒤 사라짐 |
| 2 | 위 + `blood_spray`, `blood_drops_ground` (레이저는 `burn_glow`, `smoke_wisp`) | `blood_pool`, `corpse_stay` | 남음 |
| 3 | 위 + `wound_mark_body`, `blood_wall_behind`, 칼은 `slash_mark_body`·`blood_arc`, 레이저는 `burn_mark_body` | `blood_pool_grow`, 머리는 `blood_mist`, 레이저는 `char_body`·`smoke_corpse` | 남음. 팔다리에 치명상을 입으면 40%는 바로 죽지 않고 기어가다 죽는다 |

- 이 모듈은 이펙트의 **이름**만 돌려준다. 파티클·데칼·소리는 게임 쪽에서 이름마다 붙인다. 신체 절단은 넣지 않았다.

## 손 레이저
```lua
local laser = Laser.new()                                   -- 값은 Laser.DEFAULTS
local out = laser:update(dt, triggerHeld, hits)             -- hits = 빔 길 위에서 맞은 것들(가까운 순서), 벽은 solid = true
if out.beam then drawBeam(out.length, out.power) end       -- beam_out 붙임점에서 그린다
for _, d in out.damage do crowd:damage(d.target, {damage = d.amount, kind = "laser", part = d.part, dirX = dir.X, dirZ = dir.Z, attacker = player}) end
for _, e in out.events do ... end                           -- charge, beam_on, beam_off, overheat, ready, cancel
local armClip, viewClip = Laser.clips(out.state)            -- 상태가 바뀔 때 틀 클립
```
- 기본값: 충전 0.35초, 초당 피해 240(처음 50% → 0.6초에 100%), 사거리 60 m(30 m부터 줄어 끝에서 50%), 첫 대상을 뚫고 하나 더(50%), 약 3.3초 연속 발사하면 과열되어 2초 잠김, 쉬면 초당 25% 식음.
- 빔은 연속 피해라서 `update`가 프레임마다 `dps × dt`만큼 준다. 레이저에 죽으면 `death_burn`이 나온다.

## 좌표
- 클립과 `RigSolver`는 에셋 원본 좌표를 쓴다: 단위 m, 앞 = -Y, 위 = +Z.
- `Crowd`, `Patrol`, `Traffic`은 평면 좌표 `x, z`와 `heading`(라디안, `atan2(dx, dz)`)을 쓴다. 단위는 m 기준이다. 스터드로 쓰려면 위치·속도·반경에 같은 배율을 곱한다.
- Roblox 축으로 바꾸는 표는 `RigAnimator.AXIS` 한 곳에만 있다. 가져온 모델의 축이 다르면 이 표만 고친다.
