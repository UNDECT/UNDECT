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
| `Driving.luau` | 모는 차의 움직임: 가속·제동, 속도에 따라 줄어드는 조향, 접지 한계, 핸드브레이크 미끄러짐, 충돌, 차 체력(연기 → 불 → 폭발) | ✅ |
| `Carjack.luau` | 차 훔쳐 타기: 그냥 타기, 잠금 해킹, 창 깨기, 운전자 끌어내기, 총으로 위협, 시동 따기, 경보기, 운전자 반응 | ✅ |
| `Wanted.luau` | 수배 0~5단계와 보안 대응: 알려진 범죄만 반영, 단계별 부대, 수색·해제·체포, 차단선, 순찰차 운전 입력, 보안 로봇 판단 | ✅ |
| `Security.luau` | 보안 로봇 한 대의 두뇌: 순찰, 시야와 인지도, 정지 명령, 조준·점사, 차 피하기, 수색, 복귀, 피격·파괴 | ✅ |
| `CrowdNet.luau` | 서버 → 클라이언트 전송: 주변 것만 10바이트씩 묶기, 풀기, 클라이언트 보간 | ✅ |
| `RigAnimator.luau` | Roblox 연결: 자세를 Bone/Motor6D의 `Transform`에 적용, 동작 전환 섞기. 사람은 `RigAnimator.new(model, manifest.joints)` | ⚠️ Studio에서 확인 필요 |
| `tests/run.luau` | 테스트 189개 | `lune run tests/run.luau` (이 폴더에서 실행) |

## 클립
위치는 `../blender/out/anim/*.json`(158개)이고 목록은 `_index.json`에 있다. `rig` 값으로 어디에 쓰는 클립인지 구분한다.

| rig | 개수 | 클립 | 적용 대상 |
|---|---|---|---|
| `humanoid` | 77 | **차**: `car_door_open`, `car_enter`, `car_exit`, `drive_idle`, `drive_steer_L/R`, `car_smash_window`, `car_hack`, `car_hotwire`, `carjack_pull`, `carjack_victim` / **반응**: `hands_up`, `point`, `record_phone`, `phone_report`, `startle`, `dodge_left/right`, `shake_fist`, `robot_halt` / **죽음**: `death_back`, `death_front`, `death_left`, `death_right`, `death_headshot`, `death_knees`, `death_blast`, `death_burn`, `death_shock`, `death_slash`, `death_sit`, `death_crawl` / **부상**: `fall_wounded`, `wounded_crawl` / **피격**: `hit_front`, `hit_back`, `hit_left`, `hit_right`, `hit_head`, `hit_leg`, `stagger` / 손 레이저: `aim_palm`, `fire_palm` / 이동: `walk`, `walk_slow`, `run`, `walk_heavy` / 대기: `idle`, `look_around`, `talk`, `phone` / 반응: `cower_enter`, `cower_loop`, `hit_react`, `knockdown`, `lie_loop`, `get_up`, `collapse` / 앉기: `sit_down`, `sit_loop`, `stand_up` / 무기 자세: `aim_pistol`, `aim_rifle`, `low_ready`, `fire_pistol_3p`, `fire_rifle_3p` / 근접: `melee_slash`, `melee_stab`, `melee_heavy`, `punch`, `throw` / 로봇: `robot_scan`, `robot_alert`, `robot_aim`, `robot_fire`, `robot_shutdown`, `robot_boot` | 사람, 가면 NPC, 보안 로봇 |
| `fp` | 30 | `fp_car_enter`, `fp_car_exit`, `fp_drive`, `fp_smash`, `fp_pull`, `fp_laser_raise`, `fp_laser_fire`, `fp_laser_overheat`, `fp_laser_lower`, `fp_idle`, `fp_raise_light`, `fp_raise_heavy`, `fp_lower`, `fp_recoil_pistol/revolver/auto/lmg/shotgun/sniper`, `fp_reload`, `fp_ads_in`, `fp_ads_out`, `fp_slash`, `fp_stab`, `fp_punch`, `fp_heavy`, `fp_throw`, `fp_inspect`, `fp_sprint`, `fp_land` | 1인칭 팔과 무기 뭉치 |
| `weapon` | 15 | `pistol_fire`, `revolver_fire`, `auto_fire`, `lmg_fire`, `double_fire`, `shotgun_pump`, `bolt_cycle`, `mag_reload`, `lmg_reload`, `break_reload`, `charge`, `grenade_prime`, `baton_arc`, `hammer_thrust`, `knuckle_impact` | 무기의 움직이는 부품 |
| `cyberarm` | 13 | `laser_deploy/fire/overheat/retract`, `blade_deploy/retract`, `power_charge/release`, `wire_deploy/retract`, `launcher_deploy/fire/retract` | 사이버웨어 팔 부품 |
| `machine` | 11 | `drone_hover/alert/fire/crash`, `turret_scan/alert/fire/shutdown`, `camera_sweep/alert/disabled` | 드론, 포탑, 감시 카메라 |
| `vehicle` | 7 | `car_door`, `car_door_close`, `car_window_break`, `car_alarm`, `car_engine_start`, `patrol_lightbar`, `car_brake` | 차의 문, 창, 발광 |
| `clinic` | 4 | `chair_recline`, `chair_release`, `surgery_start`, `surgery_loop` | 시술 의자, 천장 로봇 팔 |

- `humanoid` 클립은 뼈대와 무관한 "의미 관절"로 적혀 있다(`hip_L.flex`, `knee_L.bend`, `waist.yaw` …). 규칙은 `../blender/anim.py` 맨 위 주석을 본다. 관절 이름이 같으면 어떤 모델에도 쓸 수 있다.
- `fp` 클립의 `view` 관절은 팔과 무기 뭉치 전체를 카메라 기준으로 옮기는 값이다: `x` 오른쪽, `y` 뒤(+)·앞(−), `z` 위(m), `pitch` 총구 위(+), `yaw` 왼쪽(+), `roll`(도). `value`는 0~1 진행률이다(조준 정도, 손에서 떠남 등). **걷기 흔들림은 없다.** 멈춰 있을 때의 숨쉬기 흔들림(`fp_idle`)만 있다.
- 타고 내리는 클립(`car_enter`, `car_exit`, `car_door_open`, `carjack_*`, `car_smash_window`, `car_hack`)의 뿌리는 **앉은 자리가 원점**이고 운전석(왼쪽 문) 기준이다. 문밖은 +X로 0.95 m다. 오른쪽 문은 좌우를 뒤집어 쓴다(`_L`·`_R`을 바꾸고 `x`, `yaw`, `roll` 부호를 뒤집는다).
- `weapon`, `cyberarm`, `machine`, `vehicle`, `clinic` 클립은 관절 이름이 부품(또는 manifest의 관절) 이름이다. `move_x/y/z`는 이동(m), `pitch/yaw/roll/open`은 회전(도), `spin`은 회전수, `value`는 발광 세기나 보임 여부(0~1)다. 이 클립들은 `AnimSampler.sample`로 값을 뽑아 게임 코드가 부품에 직접 적용한다(`RigAnimator`를 쓰지 않는다).
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
- 축과 배율은 스스로 알아낸다: 만들 때 뼈 위치를 manifest와 견주어 가져오기 축((-x, z, y) 또는 (x, z, -y))과 스터드/m 배율을 고른다. `anim.axisError`가 0.15를 넘으면 모델이 기본 자세가 아니거나 `frame`이 틀린 것이다. 부품 모델은 `RigAnimator.new(model, nil, nil, manifest.pivots)`처럼 pivots를 넘긴다.
- 모델을 세울 때는 `anim:placement(위치, heading)`을 쓴다(앞이 -Z인지 +Z인지 맞춰 준다). 자세 하나를 바로 넣어 볼 때는 `anim:applyPose({shoulder_R = {flex = 90}})`.
- 축 확인: `calibrate` 클립(6초)의 0, 1.2, 2.4, 3.6, 4.8, 6.0초 자세가 `../blender/out/anim/calibration_human.png`의 6칸과 같아야 한다.
- 사람(`human_*`)은 뼈 이름을 바꾸지 않는다. `joints` 표가 `hip_L → thigh_L`, `waist → spine`처럼 이어 준다. 기본 자세가 중립 자세라서 `neutral`은 전부 단위 행렬이다.
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
- 피해 종류(`kind`): `bullet`, `shotgun`, `blade`, `blunt`, `laser`, `fire`, `electric`, `explosive`, `vehicle`(차에 치임), `fall`. 부위는 `zone`을 주거나 맞은 뼈 이름을 `part`로 준다(`Vitals.zoneOf`가 머리·목·몸통·팔·다리로 바꾼다). 배수는 머리 3.0, 목 2.2, 몸통 1.0, 팔 0.6, 다리 0.7.
- 사망 클립은 원인과 방향으로 고른다: 폭발 `death_blast`, 레이저·불 `death_burn`, 감전 `death_shock`, 칼 `death_slash`, 머리·목 `death_headshot`, 앉아 있으면 `death_sit`, 그 밖에는 앞에서 맞으면 `death_back`, 뒤에서 맞으면 `death_front`, 옆에서 맞으면 반대쪽으로 `death_left/right`, 가끔 `death_knees`.
- **수위는 `Vitals.GORE` 한 곳에서 바꾼다.** 지금은 3이다.

| 값 | 맞았을 때 | 죽었을 때 | 시체 |
|---|---|---|---|
| 0 | `hit_flash` | `dissolve` | 1.5초 뒤 사라짐 (Kids 설정용) |
| 1 | `hit_flash`, `hit_dust` | `corpse_fade` | 12초 뒤 사라짐 |
| 2 | 위 + `blood_spray`, `blood_drops_ground` (레이저는 `burn_glow`, `smoke_wisp`) | `blood_pool`, `corpse_stay` | 남음 |
| 3 | 위 + `wound_mark_body`, `blood_wall_behind`, 칼은 `slash_mark_body`·`blood_arc`, 레이저는 `burn_mark_body` | `blood_pool_grow`, 머리는 `blood_mist`, 레이저는 `char_body`·`smoke_corpse` | 남음. 팔다리에 치명상을 입으면 40%는 바로 죽지 않고 기어가다 죽는다 |

- 빔처럼 매 프레임 `crowd:damage`를 불러도 된다. 비틀거림은 한 번만 시작하고 `hurt` 사건도 그때 한 번만 남는다. 이미 도망치는 사람은 다시 놀라게 해도 웅크림으로 바뀌지 않는다.
- 밀려나는 거리는 0.3초쯤에 걸쳐 나눠 옮긴다(순간 이동 없음). 폭발로 죽으면 터진 곳을 보게 돌려 놓아서 `death_blast`가 터진 반대쪽으로 날아간다. 죽는 클립에 든 뿌리 이동은 그대로 두고 에이전트 위치는 옮기지 않는다.
- 걷는 사람은 시체를 돌아서 간다. 손에 든 물건·옷자락(`prop`, `umbrella`, `skirt`)에 맞은 것은 피해가 없다.
- 기계(보안 로봇, 드론, 포탑)는 `Vitals.new({machine = true, deathAnim = "drone_crash"})`로 만든다. 피 대신 `spark_burst`, `dent_mark_body`, `oil_leak`, `machine_down`이 나오고, 기어가지 않으며, 죽으면 고장 동작(기본 `robot_shutdown`)을 튼다.
- 이 모듈은 이펙트의 **이름**만 돌려준다. 파티클·데칼·소리는 게임 쪽에서 이름마다 붙인다. 신체 절단은 넣지 않았다.

## 차 훔쳐 타기, 운전, 수배
```lua
-- 타기
local v = Carjack.vehicle({kind = "parked"})                       -- 또는 "traffic"(NPC가 모는 차), "security"(순찰차)
local options = Carjack.options(v, {hasDeck = true, armed = false}) -- {"hack", "smash"} 같은 목록
local attempt = Carjack.begin(v, "smash", player)
-- 매 프레임
for _, e in attempt:update(dt, interrupted, math.random()) do
	if e.type == "crime" then crowd:witness(e.crime, x, z, e.noise + 6, if e.crime == "carjacking" then 2 else 1) end
	if e.type == "driver_out" then crowd:eject(x, z, heading, e.reaction, "carjacking") end
	if e.type == "alarm_on" then ... end                             -- 보안이 60 m 안이면 wanted:report(crime, {alarm = true})
end
local clipName, progress = attempt:current()

-- 몰기
local car = Driving.new({x = x, z = z, heading = heading})
for _, e in car:update(dt, {throttle = t, steer = s, handbrake = hb}) do ... end   -- skid_start, skid_stop, explode
crowd:vehicle({x = car.x, z = car.z, vx = car.vx, vz = car.vz, attacker = player}) -- 시민이 피하거나 치인다
traffic.obstacles = {{x = car.x, z = car.z, r = 2.4, v = car.speed}}              -- 뒤차가 선다
local hitSpeed = car:impact(nx, nz)                                                -- 벽·차에 부딪혔을 때

-- 수배
for _, e in crowd:drain() do
	if e.type == "report" then wanted:report(e.crime, {reported = true, x = e.x, z = e.z}) end
	if e.type == "hit_by_vehicle" then wanted:report("hit_pedestrian", {seenBySecurity = securitySees, x = e.x, z = e.z}) end
end
for _, order in wanted:update(dt, {x = car.x, z = car.z, heading = car.heading, speed = car.speed, inVehicle = true, seen = securitySees}) do
	-- spawn(unit, x, z) / roadblock(x, z, heading, spikes) / lost / search / found / clear / busted / lockdown
end
patrol:update(dt, Wanted.pursuitInput(patrol, car, "follow"))                      -- patrol = Driving.new(Wanted.PATROL_CAR)
local order = Wanted.robotOrder(robot, {x = car.x, z = car.z, vx = car.vx, vz = car.vz, inVehicle = true}, wanted.level, seen)
```
- 수배는 범죄가 보안에 **알려졌을 때만** 오른다: 보안이 직접 봤거나(`seenBySecurity`), 시민이 4초짜리 신고 전화를 끝냈거나(`reported`), 경보기가 보안 근처에서 울렸을 때(`alarm`). 신고하는 사람을 놀라게 해 쫓으면 신고가 끊긴다.
- 단계별 부대와 허용 대응은 `Wanted.RESPONSE`, 범죄별 점수는 `Wanted.CRIMES`, 타는 방법별 시간은 `Carjack.METHODS`, 차의 성질은 `Driving.DEFAULTS`에 있다. 수치는 거기서만 고친다.
- 순찰차는 멀어지면 빨라지는 보정(`boost`, 최대 1.6배)을 쓴다. 이것이 없으면 급하게 꺾는 차를 다시 따라잡지 못한다(테스트로 확인).

## 보안 로봇과 서버 구조
```lua
-- 서버
local bot = Security.new(waypoints, {rand = math.random})          -- waypoints가 없으면 제자리 경비
for _, e in bot:update(dt, {x = px, z = pz, vx = vx, vz = vz, inVehicle = inCar, visible = lineOfSight, crouched = c, armed = a}, wanted.level) do
	-- noticed / seen(1초마다) / warn / fire{at, hit, damage} / dodge / lost{x, z} / resume
end
local res = bot:damageBy({damage = 34, kind = "bullet", part = "torso", dirX = dx, dirZ = dz})   -- res.crime = assault_security | kill_security
-- bot.x, bot.z, bot.heading, bot.anim, bot.awareness(0~1, 잠입 표시용)

local anims = CrowdNet.animTable(sortedClipNames)                   -- 서버와 클라이언트가 같은 목록
remote:FireClient(player, CrowdNet.pack(crowd.agents, {x = px, z = pz}, 120, anims))   -- 초당 10번, UnreliableRemoteEvent
-- 클라이언트
interp:push(CrowdNet.unpack(buf, anims), os.clock())                -- interp = CrowdNet.Interp.new(0.15)
for id, a in interp:sample(os.clock()) do ... end                   -- a.x, a.z, a.heading, a.anim, a.animTime, a.dead
```
- 군중, 교통, 보안, 수배는 **서버에서** 돌린다. `crowd:step(dt, signals, {플레이어 위치들})`처럼 위치 목록을 넘기면 가장 가까운 플레이어 기준으로 갱신 빈도를 줄인다.
- 클라이언트는 받은 위치를 0.15초 늦게 보간해서 놓고, 뼈 동작은 `anim`과 `animTime`으로 직접 튼다. 한 개에 10바이트, 위치 오차 2 cm, 방향 오차 1.4°다.
- 단위는 전부 m다. 화면에 놓는 마지막 한 곳에서만 `RigAnimator.STUDS_PER_METER`(3.143)를 곱한다.
- `Security`의 수치(시야 38 m·110°, 체력 260, 점사 3발, 한 발 피해 9)는 `Security.DEFAULTS`에 있다. 1~2단계는 쏘지 않고, 3단계부터 0.6초 조준한 뒤 쏜다. 명중률은 거리와 대상 속도에 따라 8~90%다.

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
- `Crowd`, `Patrol`, `Traffic`, `Vitals`는 평면 좌표 `x, z`와 `heading`(라디안, `atan2(dx, dz)`)을 쓴다. 단위는 m 기준이다. 스터드로 쓰려면 위치·속도·반경에 같은 배율을 곱한다.
- **`x, z`는 Roblox의 `X, Z`에 그대로 대응시킨다(뒤집지 않는다).** `heading` 0은 +Z를 본다. 모델은 `CFrame.new(pos) * CFrame.Angles(0, heading + math.pi, 0)`로 세운다(모델의 앞이 -Z이기 때문이다). 이 대응에서 사람의 오른쪽은 `(-fz, fx)`이고, 좌우 판정·우측 보행·쓰러지는 방향이 전부 이 약속을 따른다. 축을 뒤집어 넘기면 좌우가 전부 반대로 나온다.
- `heading`이 커지는 쪽이 왼쪽으로 도는 것이다. `Traffic`의 `bank`는 +가 오른쪽으로 기우는 것이다.
- 클립의 뿌리 이동(주저앉기, 눕기, 날아가기)은 골반 높이 0.95 m 기준이다. `RigAnimator`가 모델의 골반 높이 비율로 맞춘다(`rootScale`).
- Roblox 축으로 바꾸는 표는 `RigAnimator.AXIS` 한 곳에만 있다. 가져온 모델의 축이 다르면 이 표만 고친다.
