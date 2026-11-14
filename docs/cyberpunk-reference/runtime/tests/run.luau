-- 실행: (runtime 폴더에서) lune run tests/run.luau
local fs = require("@lune/fs")
local serde = require("@lune/serde")
local process = require("@lune/process")
local AnimSampler = require("../AnimSampler")
local RigSolver = require("../RigSolver")
local Crowd = require("../Crowd")
local Patrol = require("../Patrol")
local Traffic = require("../Traffic")
local Vitals = require("../Vitals")
local Laser = require("../Laser")
local Driving = require("../Driving")
local Carjack = require("../Carjack")
local Wanted = require("../Wanted")
local Security = require("../Security")
local CrowdNet = require("../CrowdNet")

local CLIPS = "../blender/out/anim/"
local passed, failed = 0, 0
local function check(name, cond, detail)
	if cond then passed += 1 else failed += 1; print("FAIL " .. name .. (if detail then "  " .. tostring(detail) else "")) end
end
local function load(name) return serde.decode("json", fs.readFile(CLIPS .. name .. ".json")) end

-- 1. 표본 추출이 기준값과 같은가
local clips = {}
local worst = 0
for _, g in load("_golden_samples") do
	clips[g.clip] = clips[g.clip] or load(g.clip)
	local pose = AnimSampler.sample(clips[g.clip], g.t)
	for key, want in g.pose do
		local joint, dof = string.match(key, "^(.-)%.(.+)$")
		worst = math.max(worst, math.abs(((pose[joint] or {})[dof] or 1e9) - want))
	end
end
check("sampler matches golden values", worst < 1e-4, worst)
for _, n in {"get_up", "melee_slash", "fp_recoil_shotgun", "knockdown", "death_front", "death_headshot", "death_blast", "wounded_crawl", "aim_palm"} do clips[n] = clips[n] or load(n) end

-- 2. 이벤트: 걷기 2.2초 동안 발 디딤 4번, 순서는 R L R L
local ev = AnimSampler.events(clips.walk, 0, 2.2)
check("walk footstep events", #ev == 4 and ev[1] == "foot_R" and ev[2] == "foot_L", table.concat(ev, ","))
local n = 0
for i = 1, 220 do n += #AnimSampler.events(clips.walk, (i - 1) * 0.01, i * 0.01) end
check("events are not lost or doubled across small steps", n == 4, n)
check("non-looping clip clamps at the end", AnimSampler.sample(clips.cower_enter, 99).root.z == AnimSampler.sample(clips.cower_enter, 0.45).root.z)
local mix = AnimSampler.blend({a = {x = 10}}, {a = {x = 20}, b = {y = 8}}, 0.25)
check("blend", math.abs(mix.a.x - 12.5) < 1e-9 and math.abs(mix.b.y - 2) < 1e-9)
check("walk cycle follows move speed", math.abs(AnimSampler.advanceBySpeed(clips.walk, 0, 1, 2.7) - 2.0) < 1e-9)

-- 3. 부품 행렬이 Blender에서 계산한 값과 같은가
local gr = load("_golden_rig")
local rig = RigSolver.fromManifest(gr.manifest)
check("rig has every joint", #rig.joints == 14, #rig.joints)
worst = 0
for _, c in gr.cases do
	local D = RigSolver.solve(rig, AnimSampler.sample(clips[c.clip], c.t))
	for part, want in c.parts do
		for i = 1, 12 do worst = math.max(worst, math.abs((D[part] or {})[i] - want[i])) end
	end
end
check("rig solver matches Blender matrices", worst < 1e-4, worst)

-- 3-1. 사람 뼈대(기본 자세가 팔을 벌린 자세)에서도 Blender 값과 같은가
local gh = load("_golden_human")
local hrig = RigSolver.fromManifest(gh.manifest)
check("human rig maps every joint", #hrig.joints == 44 and hrig.root == "pelvis", #hrig.joints)
worst = 0
local n = 0
for _, c in gh.cases do
	local D = RigSolver.solve(hrig, AnimSampler.sample(clips[c.clip], c.t))
	for part, want in c.parts do
		n += 1
		for i = 1, 12 do worst = math.max(worst, math.abs((D[part] or {})[i] - want[i])) end
	end
end
check("human rig solver matches Blender matrices", n > 100 and worst < 1e-4, worst)
do  -- 손 모양(손가락 굽힘)과 손목까지 Blender 값과 같은가
	local pose = {}
	for k, v in gh.hand_case.pose do
		local j, d = string.match(k, "^(.-)%.(.+)$")
		if not pose[j] then pose[j] = {} end
		pose[j][d] = v
	end
	local D = RigSolver.solve(hrig, pose)
	local w, cnt = 0, 0
	for part, want in gh.hand_case.parts do
		cnt += 1
		for i = 1, 12 do w = math.max(w, math.abs((D[part] or {})[i] - want[i])) end
	end
	check("human fingers and wrist match Blender matrices", cnt > 40 and w < 1e-4, w)
	local hp = serde.decode("json", fs.readFile(CLIPS .. "hand_poses.json"))
	local p2 = AnimSampler.hand({}, "R", hp.grip_pistol, 0.5)
	check("hand pose fills finger joints", p2.index_R_1.curl == hp.grip_pistol.index[1] * 0.5 and p2.pinky_R_3.curl == hp.grip_pistol.pinky[3] * 0.5 and p2.index_L_1 == nil)
end
do  -- 새 클립: 넘어지면 골반이 바닥 가까이 내려가고, 일어나면 처음 자세로 돌아온다
	local kd = AnimSampler.sample(clips.knockdown, clips.knockdown.duration)
	check("knockdown ends lying on the ground", kd.root.z < -0.7 and kd.root.pitch < -80, kd.root.z)
	local gu0, gu1 = AnimSampler.sample(clips.get_up, 0), AnimSampler.sample(clips.get_up, clips.get_up.duration)
	check("get_up starts lying and ends standing", gu0.root.z < -0.7 and math.abs(gu1.root.z) < 1e-6 and math.abs(gu1.hip_L.flex) < 1e-6)
	local ev = AnimSampler.events(clips.melee_slash, 0.2, 0.3)
	check("melee slash emits hit event", #ev == 1 and ev[1] == "hit", #ev)
	local n = 0
	for _, c in load("_index").clips do n += 1 end
	check("clip index lists every clip", n == 157, n)
	local r = AnimSampler.sample(clips.fp_recoil_shotgun, 1 / 30)
	check("first-person recoil kicks back and up", r.view.y > 0.03 and r.view.pitch > 4, r.view.y)
end
do  -- 중립 자세에서는 팔이 아래를 향해야 한다(어깨 -> 팔꿈치가 거의 수직)
	local D = RigSolver.solve(hrig, {})
	local J = gh.manifest.joints
	local function at(m, p) return {m[1]*p[1]+m[2]*p[2]+m[3]*p[3]+m[10], m[4]*p[1]+m[5]*p[2]+m[6]*p[3]+m[11], m[7]*p[1]+m[8]*p[2]+m[9]*p[3]+m[12]} end
	local sh, el = at(D[J.shoulder_L.parent], J.shoulder_L.pos), at(D[J.shoulder_L.bone], J.elbow_L.pos)
	local dx, dy, dz = el[1] - sh[1], el[2] - sh[2], el[3] - sh[3]
	local len = math.sqrt(dx*dx + dy*dy + dz*dz)
	check("human neutral pose hangs the arms down", -dz / len > 0.98, -dz / len)
end

-- 4. 군중
local function world()
	return {
		nodes = {{x = 0, z = 0}, {x = 40, z = 0}, {x = 40, z = 30}, {x = 0, z = 30}, {x = 40, z = -14}, {x = 0, z = -14}},
		edges = {{a = 1, b = 2, width = 4}, {a = 2, b = 3, width = 4}, {a = 3, b = 4, width = 4}, {a = 4, b = 1, width = 4},
			{a = 2, b = 5, width = 4, signal = "s1"}, {a = 5, b = 6, width = 4}, {a = 6, b = 1, width = 4, signal = "s1"}},
		obstacles = {{x = 20, z = 0.4, r = 0.6}, {x = 40.3, z = 15, r = 0.5}},
		activities = {{node = 3, kind = "talk", duration = {3, 6}, chance = 0.5}, {node = 4, kind = "phone", duration = {3, 6}, chance = 0.5}},
	}
end
local function segDist(px, pz, a, b)
	local dx, dz = b.x - a.x, b.z - a.z
	local u = math.clamp(((px - a.x) * dx + (pz - a.z) * dz) / (dx * dx + dz * dz), 0, 1)
	return math.sqrt((px - a.x - dx * u) ^ 2 + (pz - a.z - dz * u) ^ 2)
end
local function run(seed, steps, hook)
	local w = world()
	local c = Crowd.new(w, {seed = seed}); c:spawn(40)
	local off, close, minD, inObstacle = 0, 0, math.huge, 0
	for s = 1, steps do
		if hook then hook(c, s) end
		c:step(1 / 30, {s1 = true})
		if s > 150 then
			for i, a in c.agents do
				local d = math.huge
				for _, e in w.edges do d = math.min(d, segDist(a.x, a.z, w.nodes[e.a], w.nodes[e.b])) end
				if d > 2.0 + 0.9 then off += 1 end
				for _, ob in w.obstacles do
					if math.sqrt((a.x - ob.x) ^ 2 + (a.z - ob.z) ^ 2) < ob.r then inObstacle += 1 end
				end
				for j = i + 1, #c.agents do
					local b = c.agents[j]
					local dd = math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2)
					minD = math.min(minD, dd)
					if dd < 0.3 then close += 1 end
				end
			end
		end
	end
	return c, off, close, minD, inObstacle
end
local c1, off, close, minD, inOb = run(7, 1500)
local c2 = run(7, 1500)
local same = true
for i, a in c1.agents do
	if a.x ~= c2.agents[i].x or a.z ~= c2.agents[i].z then same = false end
end
check("crowd is deterministic for a seed", same)
local samples = (1500 - 150) * 40
check("agents stay on the sidewalk", off / samples < 0.005, off .. "/" .. samples)
check("agents rarely overlap", close / (samples * 39 / 2) < 0.0005, close .. " minD=" .. minD)
check("agents do not walk through props", inOb / samples < 0.002, inOb)
local moved, acts = 0, 0
for _, a in c1.agents do
	if a.state == "walk" and a.speed > 0.5 then moved += 1 end
	if a.state == "idle" then acts += 1 end
end
check("most agents are walking", moved >= 20, moved)
local sawActivity = false
run(3, 1500, function(c)
	for _, a in c.agents do
		if a.state == "idle" and (a.anim == "talk" or a.anim == "phone") then sawActivity = true end
	end
end)
check("activity points get used", sawActivity)
-- 빨간 신호: 횡단보도 위로 새로 들어가지 않는다
do
	local w = world()
	local c = Crowd.new(w, {seed = 11}); c:spawn(40)
	for _ = 1, 300 do c:step(1 / 30, {s1 = true}) end
	local onCross = {}
	for _, a in c.agents do onCross[a.id] = w.edges[a.edge].signal ~= nil end
	local entered, waiting = 0, 0
	for _ = 1, 900 do
		c:step(1 / 30, {s1 = false})
		for _, a in c.agents do
			local on = w.edges[a.edge].signal ~= nil
			if on and not onCross[a.id] then entered += 1 end
			onCross[a.id] = on
		end
	end
	for _, a in c.agents do if a.state == "wait" then waiting += 1 end end
	check("nobody starts crossing on red", entered == 0, entered)
	check("people wait at the red light", waiting > 0, waiting)
	for _ = 1, 60 do c:step(1 / 30, {s1 = true}) end
	local still = 0
	for _, a in c.agents do if a.state == "wait" then still += 1 end end
	check("waiting people go on green", still == 0, still)
end
-- 총성: 근처는 도망치거나 웅크리고, 도망친 사람은 멀어진다
do
	local w = world()
	local c = Crowd.new(w, {seed = 5}); c:spawn(40)
	for _ = 1, 200 do c:step(1 / 30, {s1 = true}) end
	local before = {}
	for _, a in c.agents do before[a.id] = math.sqrt((a.x - 20) ^ 2 + a.z ^ 2) end
	local hit = c:panic(20, 0, 18)
	local flee, cower = 0, 0
	for _, a in c.agents do
		if a.state == "flee" then flee += 1 elseif a.state == "cower" then cower += 1 end
	end
	check("panic affects nearby agents only", hit > 0 and hit < 40 and flee + cower == hit, hit)
	check("some flee and some cower", flee > 0 and cower > 0, flee .. "/" .. cower)
	for _ = 1, 90 do c:step(1 / 30, {s1 = true}) end
	local farther, fled = 0, 0
	for _, a in c.agents do
		if a.state == "flee" then
			fled += 1
			if math.sqrt((a.x - 20) ^ 2 + a.z ^ 2) > before[a.id] + 3 then farther += 1 end
		end
	end
	check("fleeing agents get away from the threat", fled > 0 and farther / fled > 0.8, farther .. "/" .. fled)
	for _ = 1, 400 do c:step(1 / 30, {s1 = true}) end
	local calm = 0
	for _, a in c.agents do if a.state ~= "flee" and a.state ~= "cower" then calm += 1 end end
	check("crowd calms down afterwards", calm == 40, calm)
end
-- LOD: 먼 사람은 덜 자주 갱신되지만 평균 속도는 비슷하다
do
	local w = world()
	local a = Crowd.new(w, {seed = 9}); a:spawn(1)
	local b = Crowd.new(w, {seed = 9}); b:spawn(1)
	for _ = 1, 600 do a:step(1 / 30, {s1 = true}); b:step(1 / 30, {s1 = true}, {x = 5000, z = 5000}) end
	local d = math.sqrt((a.agents[1].x - b.agents[1].x) ^ 2 + (a.agents[1].z - b.agents[1].z) ^ 2)
	check("far agents keep roughly the same pace", b.agents[1].lod == 2 and d < 6, d)
end

-- 5. 순찰
do
	local p = Patrol.new({{x = 0, z = 0, pause = 1.5}, {x = 12, z = 0}, {x = 12, z = 9, pause = 1.5}, {x = 0, z = 9}})
	local visited, movedWhileTurning, sawScan, sawTurn, maxStep = {}, 0, false, false, 0
	for _ = 1, 30 * 80 do
		local x0, z0 = p.x, p.z
		p:step(1 / 30)
		local st = math.sqrt((p.x - x0) ^ 2 + (p.z - z0) ^ 2)
		maxStep = math.max(maxStep, st)
		if p.state == "turn" then sawTurn = true; if st > 1e-9 then movedWhileTurning += 1 end end
		if p.anim == "robot_scan" then sawScan = true end
		for i, w in p.points do
			if math.sqrt((p.x - w.x) ^ 2 + (p.z - w.z) ^ 2) < 0.4 then visited[i] = true end
		end
	end
	check("patrol visits every waypoint", visited[1] and visited[2] and visited[3] and visited[4])
	check("robot turns in place before walking", sawTurn and movedWhileTurning == 0, movedWhileTurning)
	check("robot pauses to scan", sawScan)
	check("robot never exceeds its speed", maxStep <= 1.0 / 30 + 1e-9, maxStep)
	p:alert(p.x + 5, p.z + 5)
	for _ = 1, 90 do p:step(1 / 30) end
	local want = math.atan2(5, 5)
	check("alert turns to face the target and aims", p.aimed and math.abs((p.heading - want + math.pi) % (2 * math.pi) - math.pi) < 0.12 and p.anim == "robot_aim")
	p:clear(); p:step(1 / 30)
	check("patrol resumes after alert", p.state ~= "alert")
end

-- 6. 교통
do
	local lane = {points = {{x = 0, z = 0}, {x = 120, z = 0}, {x = 120, z = 60}, {x = 0, z = 60}}, loop = true, speed = 11, stops = {{s = 100, signal = "s1"}}}
	local t = Traffic.new({lane})
	check("lane length", math.abs(lane.length - 360) < 1e-9, lane.length)
	local cars = {}
	for i = 0, 7 do table.insert(cars, t:add(1, i * 14)) end
	local minGap, maxV, crossedOnRed = math.huge, 0, 0
	local function gaps()
		for i, a in cars do
			for j, b in cars do
				if i ~= j then
					local d = (b.s - a.s) % lane.length
					minGap = math.min(minGap, d - 4.7)
				end
			end
		end
	end
	for _ = 1, 30 * 40 do t:step(1 / 30, {s1 = true}); gaps(); for _, c in cars do maxV = math.max(maxV, c.v) end end
	check("cars never overlap", minGap > 0, minGap)
	check("cars keep to the lane speed", maxV <= 11.05 and maxV > 8, maxV)
	check("wheels spin with distance", cars[1].wheel > 100, cars[1].wheel)
	local before = {}
	for i, c in cars do before[i] = (c.s - 100) % lane.length end
	for _ = 1, 30 * 40 do
		t:step(1 / 30, {s1 = false}); gaps()
		for i, c in cars do
			local rel = (c.s - 100) % lane.length
			-- 정지선 뒤(큰 값)에서 정지선 앞(작은 값)으로 넘어가면 통과
			if before[i] > 300 and rel < 60 and (c.s + c.length / 2 - 100) % lane.length < 60 and before[i] - rel > 200 then crossedOnRed += 1 end
			before[i] = rel
		end
	end
	local stopped = 0
	for _, c in cars do if c.v < 0.05 then stopped += 1 end end
	check("cars stop at the red light", stopped >= 3 and minGap > 0, stopped .. " gap=" .. minGap)
	check("at most the cars already at the line run the red", crossedOnRed <= 1, crossedOnRed)
	for _ = 1, 30 * 10 do t:step(1 / 30, {s1 = true}) end
	local moving = 0
	for _, c in cars do if c.v > 1 then moving += 1 end end
	check("cars move again on green", moving >= 6, moving)
	-- 하늘 차선: 높이를 따라가고, 돌 때 기울고, 빠르면 추진기를 눕힌다
	local sky = {points = {{x = 0, z = 0, y = 60}, {x = 200, z = 0, y = 80}, {x = 200, z = 200, y = 80}, {x = 0, z = 200, y = 60}}, loop = true, speed = 25}
	local ts = Traffic.new({sky}); local av = ts:add(1, 0, 6.4)
	local maxBank, maxY, minY = 0, -math.huge, math.huge
	for _ = 1, 30 * 60 do ts:step(1 / 30); maxBank = math.max(maxBank, math.abs(av.bank)); maxY = math.max(maxY, av.y); minY = math.min(minY, av.y) end
	check("flying car follows altitude", minY >= 59.9 and maxY <= 80.1 and maxY - minY > 15, minY .. ".." .. maxY)
	check("flying car banks in turns and tilts pods at speed", maxBank > 0.1 and av.tilt > math.rad(60), maxBank .. " tilt=" .. av.tilt)
end

-- 7. 피해와 사망
do
	check("zones from bone names", Vitals.zoneOf("head") == "head" and Vitals.zoneOf("neck_01") == "neck" and Vitals.zoneOf("lowerarm_r") == "arm" and Vitals.zoneOf("calf_l") == "leg"
		and Vitals.zoneOf("spine_02") == "torso" and Vitals.zoneOf("index_02_l") == "arm" and Vitals.zoneOf("shin_R") == "leg")
	-- 맞은 방향: 사람이 +Z를 보고(facing 0) 총알이 -Z로 날아오면 앞에서 맞은 것이다.
	-- Roblox에서 +Z를 보는 사람의 오른쪽은 -X다. 그래서 +X로 날아가는 총알은 오른쪽에서 온 것이다
	check("hit side", Vitals.side(0, -1, 0) == "front" and Vitals.side(0, 1, 0) == "back" and Vitals.side(1, 0, 0) == "right" and Vitals.side(-1, 0, 0) == "left")
	for _, f in {0, 1.1, -2.3, 3.0} do   -- 어느 쪽을 보든: 자기 오른쪽 벡터 (-fz, fx) 방향으로 날아가는 것은 왼쪽에서 온 것
		local fx, fz = math.sin(f), math.cos(f)
		check("hit side holds for any facing", Vitals.side(-fz, fx, f) == "left" and Vitals.side(fz, -fx, f) == "right" and Vitals.side(-fx, -fz, f) == "front" and Vitals.side(fx, fz, f) == "back", f)
	end
	check("side decides which way the body falls", ({Vitals.hit(Vitals.new({health = 1}), {damage = 99, kind = "bullet", zone = "torso", dirX = -1, dirZ = 0, facing = 0, roll = 0.9})})[1].anim == "death_right")
	check("props and cloth do not take damage", Vitals.zoneOf("prop") == "none" and Vitals.hit(Vitals.new(), {damage = 999, kind = "bullet", part = "umbrella_prop"}).dealt == 0)
	check("vehicle hit throws the body", ({Vitals.hit(Vitals.new({health = 1}), {damage = 99, kind = "vehicle", zone = "torso"})})[1].anim == "death_blast")
	local saved = Vitals.GORE
	Vitals.GORE = 3
	local v = Vitals.new({health = 100})
	local r = Vitals.hit(v, {damage = 30, kind = "bullet", zone = "torso", dirX = 0, dirZ = -1, facing = 0})
	check("body shot hurts but does not kill", r.dealt == 30 and not r.killed and v.health == 70 and r.anim == "hit_front", r.anim)
	r = Vitals.hit(v, {damage = 30, kind = "bullet", zone = "head", dirX = 0, dirZ = -1, facing = 0})
	check("headshot multiplies and kills", r.dealt == 90 and r.killed and v.state == "dead" and r.anim == "death_headshot", r.anim)
	r = Vitals.hit(v, {damage = 30, kind = "bullet", zone = "torso"})
	check("dead stays dead", not r.killed and r.dealt == 0 and v.state == "dead")
	local function kill(kind, zone, dz, roll, opts)
		local vv = Vitals.new(opts or {health = 10})
		return Vitals.hit(vv, {damage = 500, kind = kind, zone = zone, dirX = 0, dirZ = dz, facing = 0, roll = roll or 0.9, roll2 = 0.9}), vv
	end
	check("death clip follows cause and direction", kill("bullet", "torso", -1).anim == "death_back" and kill("bullet", "torso", 1).anim == "death_front"
		and kill("laser", "torso", -1).anim == "death_burn" and kill("explosive", "torso", -1).anim == "death_blast" and kill("electric", "torso", -1).anim == "death_shock"
		and kill("blade", "torso", -1, 0.1).anim == "death_slash" and kill("bullet", "torso", -1, 0.05).anim == "death_knees" and kill("bullet", "torso", -1, 0.9, {health = 10, seated = true}).anim == "death_sit")
	local has = function(list, name) for _, e in list do if e == name then return true end end return false end
	local fx = kill("bullet", "head", -1).effects
	check("max gore gives blood, wounds and a lasting corpse", has(fx, "blood_spray") and has(fx, "blood_pool_grow") and has(fx, "wound_mark_body") and has(fx, "blood_wall_behind") and has(fx, "corpse_stay") and has(fx, "blood_mist"))
	fx = kill("laser", "torso", -1).effects
	check("laser burns instead of bleeding", has(fx, "burn_glow") and has(fx, "char_body") and not has(fx, "blood_spray") and not has(fx, "blood_pool"))
	local lr, lv = Vitals.hit(Vitals.new({health = 10}), {damage = 50, kind = "bullet", zone = "leg", dirX = 0, dirZ = -1, facing = 0, roll = 0.5, roll2 = 0.1}), nil
	check("lethal limb hit can leave the victim crawling", lr.downed and not lr.killed and lr.anim == "fall_wounded")
	lv = Vitals.new({health = 10}); Vitals.hit(lv, {damage = 50, kind = "bullet", zone = "leg", roll2 = 0.1})
	local died
	for _ = 1, 400 do died = died or Vitals.update(lv, 0.1) end
	check("crawling victim bleeds out", lv.state == "dead" and died and died.anim == "death_crawl")
	Vitals.GORE = 0
	fx = kill("bullet", "head", -1).effects
	check("gore 0 has no blood and dissolves", has(fx, "dissolve") and not has(fx, "blood_spray") and not has(fx, "corpse_stay") and #fx == 2, #fx)
	check("gore 0 uses the gentle collapse clip", kill("bullet", "head", -1).anim == "collapse" and kill("explosive", "torso", -1).anim == "collapse")
	lr = Vitals.hit(Vitals.new({health = 10}), {damage = 50, kind = "bullet", zone = "leg", roll2 = 0.1})
	check("gore 0 never leaves a crawling victim", lr.killed and not lr.downed)
	Vitals.GORE = saved
	do  -- 기계(보안 로봇·드론·포탑): 피가 아니라 불꽃과 기름, 기어가지 않고, 고장 동작으로 끝난다
		local m = Vitals.new({health = 10, machine = true})
		local mr = Vitals.hit(m, {damage = 500, kind = "bullet", zone = "leg", roll2 = 0.0})
		check("machines spark instead of bleeding", mr.killed and not mr.downed and mr.anim == "robot_shutdown" and has(mr.effects, "spark_burst") and has(mr.effects, "oil_leak")
			and not has(mr.effects, "blood_spray") and not has(mr.effects, "blood_pool") and m.bleed == 0)
		check("machine death clip can be set", ({Vitals.hit(Vitals.new({health = 1, machine = true, deathAnim = "drone_crash"}), {damage = 9, kind = "laser"})})[1].anim == "drone_crash")
	end
	local av = Vitals.new({health = 100, armor = 0.5})
	check("armor halves bullets but lasers cut through more", Vitals.hit(av, {damage = 20, kind = "bullet", zone = "torso"}).dealt == 10 and Vitals.hit(av, {damage = 20, kind = "laser", zone = "torso"}).dealt == 15)
end

-- 8. 군중 속 사망
do
	Vitals.GORE = 3
	local cr = Crowd.new(world(), {seed = 5}); cr:spawn(40)
	for _ = 1, 60 do cr:step(1 / 30, nil, nil) end
	local victim = cr.agents[1]
	local res = cr:damage(victim, {damage = 500, kind = "bullet", zone = "torso", dirX = 1, dirZ = 0, attacker = "player"})
	check("crowd agent dies", res.killed and victim.state == "dead" and victim.speed == 0 and string.sub(victim.anim, 1, 6) == "death_", victim.anim)
	local fled = 0
	for _, ag in cr.agents do if ag.state == "flee" or ag.state == "cower" then fled += 1 end end
	local ev = cr:drain()
	local gotDeath, gotWitness = false, false
	for _, e in ev do gotDeath = gotDeath or (e.type == "death" and e.id == 1 and e.attacker == "player"); gotWitness = gotWitness or e.type == "witnessed" end
	check("death is recorded and bystanders react", gotDeath and gotWitness and fled > 0 and #cr:drain() == 0, fled)
	local bx, bz, maxStep = victim.x, victim.z, 0
	for _ = 1, 30 do
		cr:step(1 / 30, nil, nil)
		maxStep = math.max(maxStep, math.sqrt((victim.x - bx) ^ 2 + (victim.z - bz) ^ 2)); bx, bz = victim.x, victim.z
	end
	check("knockback is spread over frames, never a jump", maxStep < 0.08, maxStep)
	local px, pz = victim.x, victim.z
	for _ = 1, 300 do cr:step(1 / 30, nil, nil) end
	check("corpse stays where it fell", math.abs(victim.x - px) < 0.01 and math.abs(victim.z - pz) < 0.01 and victim.state == "dead" and not victim.gone and cr:countAlive() == 39)
	local hurt = cr.agents[2]
	local hp = hurt.vitals.health
	res = cr:damage(hurt, {damage = 5, kind = "bullet", zone = "arm", dirX = 0, dirZ = 1})
	check("wounded agent staggers then flees", not res.killed and hurt.state == "stagger" and hurt.vitals.health < hp)
	for _ = 1, 40 do cr:step(1 / 30, nil, nil) end
	check("staggered agent runs away", hurt.state == "flee" and hurt.anim == "run", hurt.state)
	local blast = cr:explode(cr.agents[3].x, cr.agents[3].z, 6, 400, "player")
	check("explosion kills at the center", #blast >= 1 and cr.agents[3].state == "dead" and cr.agents[3].anim == "death_blast")
	do  -- 폭발이 등 뒤에서 터져도 터진 반대쪽으로 날아간다: 죽은 사람이 터진 곳을 보게 돌려 놓는다(클립은 보는 방향의 뒤로 날아간다)
		local cb = Crowd.new(world(), {seed = 4}); cb:spawn(1)
		local b = cb.agents[1]; b.heading = 0
		local sx, sz = b.x, b.z
		cb:explode(b.x, b.z - 2, 6, 900, "player")
		local faceX, faceZ = math.sin(b.heading), math.cos(b.heading)
		check("blast victim is thrown away from the blast", b.anim == "death_blast" and faceZ < -0.99 and math.abs(faceX) < 0.01 and b.x == sx and b.z == sz, b.heading)
	end
	do  -- 빔을 2초 동안 한 사람에게 쏜다: 사건이 쏟아지지 않고, 동작이 멈추지 않고, 주변이 전부 웅크리지 않는다
		local cl = Crowd.new(world(), {seed = 2}); cl:spawn(60)
		for _ = 1, 30 do cl:step(1 / 30) end
		local t = cl.agents[1]; t.vitals.health = 1e6; t.vitals.maxHealth = 1e6
		local hurtEvents, maxAnim = 0, 0
		for _ = 1, 120 do
			cl:damage(t, {damage = 4, kind = "laser", zone = "arm", dirX = 1, dirZ = 0})
			cl:step(1 / 60)
			maxAnim = math.max(maxAnim, if t.state == "stagger" then t.animTime else 0)
			for _, e in cl:drain() do if e.type == "hurt" then hurtEvents += 1 end end
		end
		local flee, cower = 0, 0
		for _, a in cl.agents do if a.state == "flee" then flee += 1 elseif a.state == "cower" then cower += 1 end end
		check("continuous beam does not flood hurt events", hurtEvents <= 6, hurtEvents)
		check("stagger animation keeps playing under the beam", maxAnim > 0.3, maxAnim)
		check("bystanders keep fleeing instead of all cowering", flee > cower, flee .. " flee / " .. cower .. " cower")
	end
	do  -- 걷는 사람은 시체를 밟지 않고 돌아간다
		local wk = Crowd.new({nodes = {{x = 0, z = 0}, {x = 60, z = 0}}, edges = {{a = 1, b = 2, width = 4}}}, {seed = 3}); wk:spawn(25)
		for _ = 1, 60 do wk:step(1 / 30) end
		local dead = wk.agents[1]
		wk:damage(dead, {damage = 9999, kind = "electric", zone = "torso"})      -- 주변이 도망치지 않게 겁 반경이 작은 종류
		for _, a in wk.agents do if a ~= dead and a.state ~= "dead" then a.state = "walk"; a.anim = "walk" end end
		for _ = 1, 30 do wk:step(1 / 30) end
		local closest = math.huge
		for _ = 1, 1500 do
			wk:step(1 / 30)
			for _, a in wk.agents do
				if a ~= dead and a.state == "walk" then closest = math.min(closest, math.sqrt((a.x - dead.x) ^ 2 + (a.z - dead.z) ^ 2)) end
			end
		end
		check("walkers step around a corpse", closest > 0.45, closest)
	end
	do  -- 다시 채울 자리가 없으면 치워진 상태 그대로 둔다
		local c3 = Crowd.new(world(), {seed = 6}); c3:spawn(3)
		c3:damage(c3.agents[1], {damage = 999, kind = "bullet", zone = "torso"}); c3.agents[1].gone = true
		check("failed refill leaves the agent removed", c3:refill({x = 20, z = 15}, 1000) == 0 and c3.agents[1].gone and c3.agents[1].state == "dead" and c3:countAlive() == 2)
		check("refill works once there is room", c3:refill({x = 20, z = 15}, 5) == 1 and c3:countAlive() == 3)
	end
	do  -- 사람은 Roblox 기준 오른쪽으로 비켜 걷는다: +X로 걸으면 오른쪽은 +Z다
		local wk = Crowd.new({nodes = {{x = 0, z = 0}, {x = 200, z = 0}}, edges = {{a = 1, b = 2, width = 4}}}, {seed = 1}); wk:spawn(30)
		for _ = 1, 600 do wk:step(1 / 30) end
		local okSide, n = 0, 0
		for _, a in wk.agents do
			local goingPlusX = wk.world.nodes[a.to].x > wk.world.nodes[a.from].x
			if a.x > 20 and a.x < 180 then n += 1; if (goingPlusX and a.z > 0) or (not goingPlusX and a.z < 0) then okSide += 1 end end
		end
		check("pedestrians keep to their right", n > 5 and okSide >= n * 0.8, okSide .. "/" .. n)
	end
	-- 수위 0: 시체가 곧 치워지고 먼 곳에 다시 채워진다
	Vitals.GORE = 0
	local c0 = Crowd.new(world(), {seed = 9}); c0:spawn(10)
	c0:damage(c0.agents[1], {damage = 500, kind = "bullet", zone = "torso", dirX = 1, dirZ = 0})
	for _ = 1, 90 do c0:step(1 / 30, nil, nil) end
	check("gore 0 removes the body", c0.agents[1].gone == true)
	local filled = c0:refill({x = c0.agents[1].x, z = c0.agents[1].z}, 5)
	check("refill brings the population back", filled == 1 and c0:countAlive() == 10 and c0.agents[1].state == "walk" and c0.agents[1].vitals.state == "alive")
	Vitals.GORE = 3
end

-- 9. 손 레이저
do
	local lz = Laser.new()
	local names = {}
	local function run(sec, held, hits)
		local total, last = 0, nil
		for _ = 1, math.floor(sec * 60 + 0.5) do
			last = lz:update(1 / 60, held, hits)
			for _, e in last.events do table.insert(names, e) end
			for _, d in last.damage do total += d.amount end
		end
		return total, last
	end
	local hits = {{target = "a", distance = 10, zone = "torso"}, {target = "b", distance = 12, zone = "torso"}, {target = "c", distance = 14, zone = "torso"}, {target = "wall", distance = 20, solid = true}}
	local dmg, last = run(0.3, true, hits)
	check("laser charges before the beam", dmg == 0 and last.state == "charging" and not last.beam)
	dmg, last = run(1.0, true, hits)
	check("laser beam damages and pierces one target", last.beam and dmg > 150 and #last.damage == 2 and last.damage[2].amount == last.damage[1].amount * 0.5 and last.length == 12, dmg)
	check("beam ramps to full power", last.power == 1)
	local _, l2 = run(0.05, true, {{target = "wall", distance = 7, solid = true}, {target = "a", distance = 10}})
	check("walls stop the beam", #l2.damage == 0 and l2.length == 7 and l2.endSolid)
	run(2.5, true, hits)
	check("laser overheats after sustained fire", lz.state == "overheated")
	dmg = run(1.0, true, hits)
	check("overheated laser cannot fire", dmg == 0 and lz.state == "overheated")
	run(1.5, false, hits)
	check("laser recovers after the lock", lz.state == "idle" and lz.heat == 0)
	local seen = table.concat(names, ",")
	check("laser events in order", string.find(seen, "charge,beam_on", 1, true) ~= nil and string.find(seen, "beam_off,overheat", 1, true) ~= nil and string.find(seen, "ready", 1, true) ~= nil, seen)
	local far = Laser.new()
	for _ = 1, 60 do far:update(1 / 60, true, {}) end
	local near = far:update(1 / 60, true, {{target = "n", distance = 5}}).damage[1].amount
	local distant = far:update(1 / 60, true, {{target = "f", distance = 59}}).damage[1].amount
	check("damage falls off with distance", distant < near * 0.6 and #far:update(1 / 60, true, {{target = "x", distance = 80}}).damage == 0)
	local a, b = Laser.clips("firing")
	check("laser clip names exist", a == "laser_fire" and b == "fp_laser_fire" and load(a).loop and load(b).rig == "fp")
	-- 레이저로 군중을 쏘면 타 죽는다
	local cr = Crowd.new(world(), {seed = 3}); cr:spawn(5)
	local gun = Laser.new()
	local ag = cr.agents[1]
	local t = 0
	while ag.state ~= "dead" and t < 600 do
		local o = gun:update(1 / 60, true, {{target = ag, distance = 8, zone = "torso"}})
		for _, d in o.damage do cr:damage(d.target, {damage = d.amount, kind = d.kind, zone = d.zone, dirX = 0, dirZ = 1}) end
		cr:step(1 / 60, nil, nil); t += 1
	end
	check("laser kills a bystander with the burn death", ag.state == "dead" and ag.anim == "death_burn" and t < 120, t)
end

-- 10. 운전
do
	local function drive(car, sec, input) local evs = {}; for _ = 1, math.floor(sec * 60 + 0.5) do for _, e in car:update(1 / 60, input) do table.insert(evs, e) end end; return evs end
	local car = Driving.new()
	drive(car, 4, {throttle = 1})
	check("car accelerates forward along its heading", car.speed > 18 and car.z > 30 and math.abs(car.x) < 1e-6, car.speed)
	local top = Driving.new(); drive(top, 40, {throttle = 1})
	check("car tops out at max speed", top.speed > 36 and top.speed <= 38.0001, top.speed)
	local h0 = car.heading
	drive(car, 1, {throttle = 0.3, steer = 1})
	check("steering right turns right (heading decreases, moves toward -X)", car.heading < h0 - 0.2 and car.vx < 0, car.heading)
	local slow, fast = Driving.new(), Driving.new()
	drive(slow, 1.0, {throttle = 1}); drive(fast, 12, {throttle = 1})
	local hs, hf = slow.heading, fast.heading
	drive(slow, 0.5, {throttle = 0, steer = -1}); drive(fast, 0.5, {throttle = 1, steer = -1})
	check("steering angle is limited at speed", math.abs(fast.steer) < math.abs(slow.steer) * 0.6, fast.steer)
	local b = Driving.new(); drive(b, 5, {throttle = 1}); local v0 = b.speed
	drive(b, 1, {throttle = -1})
	check("brakes slow the car and set the brake flag", b.speed < v0 - 12 and b.braking)
	drive(b, 6, {throttle = -1})
	check("holding reverse backs up to the reverse limit", b.speed < -5 and b.speed >= -9.0001, b.speed)
	local d = Driving.new(); drive(d, 5, {throttle = 1})
	local ev = drive(d, 0.8, {throttle = 0.5, steer = 1, handbrake = true})
	local slid = false
	for _, e in ev do slid = slid or e == "skid_start" end
	local g = Driving.new(); drive(g, 5, {throttle = 1}); drive(g, 0.8, {throttle = 0.5, steer = 1})
	check("handbrake makes the car slide; normal cornering does not", slid and d.skid > 0.35 and g.skid < 0.3, d.skid .. " / " .. g.skid)
	local w = Driving.new(); drive(w, 4, {throttle = 1}); local hit = w:impact(0, -1)
	check("hitting a wall kills the speed into it", hit > 18 and w.vz < 0.3 * 0 + 6 and w.speed < 8, w.speed)
	local carDmg, riderDmg = Driving.crashDamage(hit)
	check("crash damage scales with impact speed", carDmg > 25 and riderDmg > 5 and Driving.crashDamage(3) == 0)
	check("damage: smoking then burning then wrecked", w:damage(70) == "smoking" and w.state == "smoking" and w:damage(40) == "on_fire" and w.state == "burning")
	local evs = drive(w, 4.2, {throttle = 1})
	local boom = false
	for _, e in evs do boom = boom or e == "explode" end
	check("a burning car explodes after four seconds", boom and w.state == "wrecked" and w.engine == false)
	local r = Driving.new(); drive(r, 5, {throttle = 1}); drive(r, 0.6, {throttle = 1, steer = 1})
	check("body rolls away from the turn", r.roll < -0.02, r.roll)
end

-- 11. 차 훔치기
do
	local function run(att, sec, roll)
		local names = {}
		for _ = 1, math.floor(sec * 60 + 0.5) do for _, e in att:update(1 / 60, false, roll) do table.insert(names, e.type); names[e.type] = e end end
		return names
	end
	local has = function(list, name) for _, e in list do if e == name then return true end end return false end
	local parked = Carjack.vehicle({kind = "parked"})
	check("a locked parked car can be smashed, or hacked with a deck", table.concat(Carjack.options(parked, {}), ",") == "smash" and table.concat(Carjack.options(parked, {hasDeck = true}), ",") == "hack,smash")
	check("cannot simply open a locked car", Carjack.begin(parked, "enter", {}) == nil)
	local att = Carjack.begin(parked, "smash", {})
	local a1 = att:current()
	local ev = run(att, 6)
	check("smash: glass, alarm, crime, door, seat, hotwire, done", a1 == "car_smash_window" and has(ev, "glass_break") and has(ev, "alarm_on") and has(ev, "door_open") and has(ev, "seated") and has(ev, "engine_on") and has(ev, "done")
		and ev.crime.crime == "vehicle_theft" and ev.crime.noise == 16 and parked.stolen and parked.engine and parked.windowBroken, table.concat(ev, ","))
	check("alarm keeps ringing then stops", Carjack.alarm(parked, 1) == true and Carjack.alarm(parked, 60) == false)
	local quiet = Carjack.vehicle({kind = "parked"})
	ev = run(Carjack.begin(quiet, "hack", {hasDeck = true}), 4)
	check("hack is silent: no alarm, no hotwire", has(ev, "unlocked") and has(ev, "done") and not has(ev, "alarm_on") and not has(ev, "glass_break") and not has(ev, "engine_on") and ev.crime.noise == 0 and quiet.engine)
	local moving = Carjack.vehicle({kind = "traffic", speed = 11})
	check("cannot pull a driver out of a fast car", #Carjack.options(moving, {armed = true}) == 0)
	moving.speed = 1
	check("a slow occupied car can be jacked; a gun adds the threat option", table.concat(Carjack.options(moving, {}), ",") == "pull_driver" and table.concat(Carjack.options(moving, {armed = true}), ",") == "pull_driver,threaten")
	att = Carjack.begin(moving, "pull_driver", {})
	ev = run(att, 3, 0.1)
	check("carjacking throws the driver out and is a heavier crime", has(ev, "driver_out") and ev.driver_out.reaction == "flee" and ev.crime.crime == "carjacking" and moving.occupied == false and moving.stolen and has(ev, "done"))
	check("driver reactions cover flee, freeze and fight", Carjack.driverReaction(moving, "pull_driver", 0.7) == "freeze" and Carjack.driverReaction(moving, "pull_driver", 0.95) == "fight"
		and Carjack.driverReaction(Carjack.vehicle({kind = "security"}), "pull_driver", 0.1) == "hostile")
	local c2 = Carjack.begin(Carjack.vehicle({kind = "parked"}), "smash", {})
	c2:update(0.3); local cev = c2:update(0.1, true)
	check("an interrupted attempt is canceled before the glass breaks", cev[1].type == "canceled" and c2.canceled and #c2:update(1) == 0)
	check("a stolen empty car can simply be entered again", table.concat(Carjack.options(parked, {}), ",") == "enter")
	local open1 = Carjack.vehicle({kind = "parked", locked = false})
	local oe = run(Carjack.begin(open1, "enter", {}), 2)
	check("taking an unlocked car is still theft, but silent and with no hotwire", oe.crime ~= nil and oe.crime.crime == "vehicle_theft" and oe.crime.noise == 0 and not has(oe, "engine_on") and not has(oe, "alarm_on") and open1.engine)
	local again = run(Carjack.begin(open1, "enter", {}), 2)
	check("getting back into a car you already stole is not a new crime", again.crime == nil and has(again, "done"))
	for _, m in Carjack.METHODS do for _, st in m.steps do clips[st[3]] = clips[st[3]] or load(st[3]) end end
	check("every theft step has its clip", clips.car_smash_window.rig == "humanoid" and load("car_hotwire").duration >= Carjack.HOTWIRE[2] and load("car_door").rig == "vehicle")
	check("traffic drivers react to threats", Carjack.trafficReaction("aimed", 0.1) == "stop" and Carjack.trafficReaction("shot", 0.9) == "bail" and Carjack.trafficReaction("blocked", 0.1) == "honk")
end

-- 12. 수배와 보안 대응
do
	local w = Wanted.new()
	check("an unseen crime does not raise the wanted level", #w:report("vehicle_theft", {x = 0, z = 0}) == 0 and w.level == 0 and w.points == 0)
	local ev = w:report("vehicle_theft", {x = 5, z = 5, reported = true})
	check("a citizen report raises it to level 1 and starts a search", w.level == 1 and w.state == "search" and ev[1].type == "level_up")
	w:report("carjacking", {x = 5, z = 5, seenBySecurity = true})
	check("a carjacking seen by security is level 2 and tracked", w.level == 2 and w.state == "wanted")
	local spawned = {}
	local function tick(sec, ctx)
		local all = {}
		for _ = 1, math.floor(sec * 10 + 0.5) do
			for _, e in w:update(0.1, ctx) do table.insert(all, e); all[e.type] = e; if e.type == "spawn" then spawned[e.unit] = (spawned[e.unit] or 0) + 1 end end
		end
		return all
	end
	tick(10, {x = 0, z = 0, heading = 0, speed = 15, inVehicle = true, seen = true})
	check("level 2 sends two robots, one patrol car and one drone, no roadblock", spawned.robot == 2 and spawned.car == 1 and spawned.drone == 1 and spawned.flyer == nil and Wanted.RESPONSE[2].lethal == false, (spawned.robot or 0) .. "/" .. (spawned.car or 0))
	w:report("kill", {x = 0, z = 0, seenBySecurity = true})
	local e3 = tick(10, {x = 0, z = 0, heading = 0, speed = 20, inVehicle = true, seen = true})
	check("level 3 allows lethal force and sets a roadblock ahead on the route", w.level == 3 and Wanted.RESPONSE[3].lethal and e3.roadblock ~= nil and e3.roadblock.z > 59 and math.abs(e3.roadblock.x) < 1e-6, e3.roadblock and e3.roadblock.z)
	local lost = tick(1, {x = 300, z = 0, heading = 0, speed = 20, inVehicle = true, seen = false})
	check("breaking line of sight starts a search around the last seen spot", w.state == "search" and lost.lost ~= nil and lost.search.x == 0 and lost.search.z == 0)
	local t0 = w.searchTimer; w:swappedVehicle(false)
	check("swapping cars unseen halves the search", math.abs(w.searchTimer - t0 / 2) < 1e-9)
	local cleared = tick(40, {x = 300, z = 0, heading = 0, speed = 0, inVehicle = false, seen = false})
	check("staying hidden clears the wanted level", w.level == 0 and w.state == "clear" and cleared.clear ~= nil)
	local s = Wanted.new(); s:report("vehicle_theft", {x = 0, z = 0, seenBySecurity = true})
	local got = nil
	for _ = 1, 40 do for _, e in s:update(0.1, {x = 0, z = 0, seen = true, stopped = true, unarmed = true}) do if e.type == "busted" then got = e end end end
	check("stopping unarmed at low level ends in arrest", got ~= nil and s.level == 0)
	local k = Wanted.new(); k:report("kill_security", {x = 0, z = 0, seenBySecurity = true}); local busted = false
	for _ = 1, 60 do for _, e in k:update(0.1, {x = 0, z = 0, seen = true, stopped = true, unarmed = true}) do busted = busted or e.type == "busted" end end
	check("no arrest once lethal force is authorised", k.level == 4 and not busted)
	local five = Wanted.new()
	for _ = 1, 4 do five:report("kill_security", {seenBySecurity = true, x = 0, z = 0}) end
	local lock = false
	for _, e in five:update(0.1, {x = 0, z = 0, heading = 0, speed = 0, seen = true}) do lock = lock or (e.type == "lockdown" and e.on) end
	check("level 5 locks the district down", five.level == 5 and lock)
	-- 보안 로봇의 판단
	local o = Wanted.robotOrder({x = 0, z = 10}, {x = 0, z = 0, vx = 0, vz = 0, inVehicle = false}, 1, true)
	check("level 1 robot orders a halt", o.action == "halt" and o.anim == "robot_halt")
	o = Wanted.robotOrder({x = 0.4, z = 12}, {x = 0, z = 0, vx = 0, vz = 14, inVehicle = true}, 2, true)
	check("robot dodges a car driven at it", o.action == "dodge" and (o.side == "left" or o.side == "right"))
	o = Wanted.robotOrder({x = 9, z = 12}, {x = 0, z = 0, vx = 0, vz = 14, inVehicle = true}, 3, true)
	check("level 3 robot shoots the tires of a passing car", o.action == "fire" and o.at == "tires")
	check("robot reports when it loses sight", Wanted.robotOrder({x = 0, z = 0}, {x = 50, z = 0}, 3, false).action == "report")
	-- 순찰차가 달아나는 차를 따라잡는다
	local function chase(steerAt)
		local thief, cop = Driving.new({x = 0, z = 0}), Driving.new(Wanted.PATROL_CAR); cop.x, cop.z = 6, -40
		local minD, maxD = math.huge, 0
		for i = 1, 60 * 40 do
			thief:update(1 / 60, {throttle = 0.7, steer = steerAt(i)})
			cop:update(1 / 60, Wanted.pursuitInput(cop, thief, "follow"))
			local d = math.sqrt((cop.x - thief.x) ^ 2 + (cop.z - thief.z) ^ 2)
			if i > 900 then minD = math.min(minD, d); maxD = math.max(maxD, d) end
		end
		return minD, maxD, math.sqrt((cop.x - thief.x) ^ 2 + (cop.z - thief.z) ^ 2)
	end
	local mn, mx, fin = chase(function(i) return 0.06 * math.sin(i / 120) end)
	check("patrol car closes 40 m and holds station behind a fleeing car", mn > 5 and mx < 16 and fin < 14, mn .. ".." .. mx)
	mn, mx, fin = chase(function(i) return if i > 900 and i < 1080 then 1 else 0 end)
	check("patrol car recovers after the thief makes a hard turn", fin < 14 and mn > 4, fin)
	mn, mx, fin = chase(function(i) return if i % 600 < 200 then 0.25 else -0.1 end)
	check("patrol car is never shaken off by constant weaving", mx < 60, mx)
	check("pursuit asks for a catch-up boost only when far", Wanted.pursuitInput(Driving.new(), {x = 0, z = 100, vx = 0, vz = 20, heading = 0}).boost > 1.5 and Wanted.pursuitInput(Driving.new(), {x = 0, z = 10, vx = 0, vz = 20, heading = 0}).boost == 1)
end

-- 13. 차와 범죄에 대한 시민 반응
do
	Vitals.GORE = 3
	local street = {nodes = {{x = 0, z = 0}, {x = 0, z = 120}}, edges = {{a = 1, b = 2, width = 4}}}
	local cr = Crowd.new(street, {seed = 8}); cr:spawn(40)
	for _ = 1, 60 do cr:step(1 / 30) end
	-- 인도를 따라 시속 약 50 km로 달린다
	local carZ, dodged, hit, near = -10, 0, 0, 0
	for _ = 1, 600 do
		carZ += 14 / 60
		local hits = cr:vehicle({x = 0.6, z = carZ, vx = 0, vz = 14, attacker = "player"})
		hit += #hits
		cr:step(1 / 60)
		for _, e in cr:drain() do if e.type == "near_miss" then near += 1 end end
	end
	for _, a in cr.agents do if a.state == "flee" or a.state == "dodge" then dodged += 1 end end
	check("people dive out of the way of a car on the sidewalk", near >= 5, near)
	check("most of them make it", near > hit, near .. " dodged / " .. hit .. " hit")
	local slowHit = Crowd.new(street, {seed = 2}); slowHit:spawn(1)
	local p = slowHit.agents[1]; p.vitals.health = 100
	local res = slowHit:vehicle({x = p.x, z = p.z - 0.5, vx = 0, vz = 4, attacker = "player"})
	check("a slow bump hurts but does not kill", #res == 1 and not res[1].result.killed and p.vitals.health < 100 and p.vitals.health > 80, p.vitals.health)
	local fastHit = Crowd.new(street, {seed = 2}); fastHit:spawn(1)
	local q = fastHit.agents[1]
	res = fastHit:vehicle({x = q.x, z = q.z - 0.5, vx = 0, vz = 20, attacker = "player"})
	check("a fast hit kills and throws the body", #res == 1 and res[1].result.killed and q.anim == "death_blast")
	-- 차 도둑을 본 시민: 구경, 촬영, 신고
	local w1 = Crowd.new(street, {seed = 12}); w1:spawn(60)
	for _ = 1, 30 do w1:step(1 / 30) end
	local n = w1:witness("vehicle_theft", 0, 60, 30, 1)
	check("petty theft: people watch, film or call it in, nobody flees", n.watch > 0 and n.report > 0 and n.flee == 0 and n.cower == 0, n.watch .. "/" .. n.report)
	local reports = 0
	for _ = 1, 150 do w1:step(1 / 30); for _, e in w1:drain() do if e.type == "report" and e.crime == "vehicle_theft" then reports += 1 end end end
	check("a finished call becomes a report", reports == n.report, reports .. " of " .. n.report)
	local w2 = Crowd.new(street, {seed = 12}); w2:spawn(60)
	for _ = 1, 30 do w2:step(1 / 30) end
	local n2 = w2:witness("vehicle_theft", 0, 60, 30, 1)
	w2:panic(0, 60, 40)                                              -- 총을 쏴서 겁을 주면 신고가 끊긴다
	local r2 = 0
	for _ = 1, 150 do w2:step(1 / 30); for _, e in w2:drain() do if e.type == "report" then r2 += 1 end end end
	check("scaring callers off stops their reports", n2.report > 0 and r2 < n2.report, r2 .. " of " .. n2.report)
	local n3 = Crowd.new(street, {seed = 12}); n3:spawn(60)
	for _ = 1, 30 do n3:step(1 / 30) end
	local v = n3:witness("carjacking", 0, 60, 30, 2)
	check("a violent carjacking makes people flee, cower, film or call", v.flee > 0 and v.report + v.record + v.cower > 0, v.flee)
	do  -- 차 주인이 보고 있었다
		local oc = Crowd.new(street, {seed = 5}); oc:spawn(3)
		for _ = 1, 30 do oc:step(1 / 30) end
		local owner = oc.agents[1]
		check("owner shouts at the thief", oc:ownerReact(owner, "vehicle_theft", owner.x + 6, owner.z) and owner.anim == "shake_fist")
		local rep = false
		for _ = 1, 240 do oc:step(1 / 30); for _, e in oc:drain() do rep = rep or (e.type == "report" and e.id == owner.id) end end
		check("then calls it in", rep)
	end
	-- 끌려 나온 운전자
	local d1 = Crowd.new(street, {seed = 3}); d1:spawn(2)
	local drv = d1:eject(1.5, 40, 0, "flee", "carjacking")
	check("ejected driver tumbles out first", drv.state == "thrown" and drv.anim == "carjack_victim" and drv.x == 1.5 and drv.z == 40)
	local sawFlee, reported = false, false
	for _ = 1, 600 do
		d1:step(1 / 30); sawFlee = sawFlee or drv.state == "flee"
		for _, e in d1:drain() do reported = reported or (e.type == "report" and e.id == drv.id and e.crime == "carjacking") end
	end
	local far = math.sqrt((drv.x - 1.5) ^ 2 + (drv.z - 40) ^ 2)
	check("the driver runs off", sawFlee and far > 8, far)
	local reps = 0
	for seed = 1, 20 do
		local dc = Crowd.new(street, {seed = seed}); dc:spawn(1)
		local dd = dc:eject(1.5, 40, 0, "flee", "carjacking")
		for _ = 1, 600 do dc:step(1 / 30); for _, e in dc:drain() do if e.type == "report" and e.id == dd.id then reps += 1 end end end
	end
	check("most ejected drivers call it in once they are clear", reps >= 12 and reps <= 20, reps)
	local d2 = Crowd.new(street, {seed = 3}); d2:spawn(1)
	local f = d2:eject(1.5, 40, 0, "fight")
	local attacks = false
	for _ = 1, 90 do d2:step(1 / 30); for _, e in d2:drain() do attacks = attacks or e.type == "driver_attacks" end end
	check("a driver who fights back is handed to combat AI", attacks and f.state == "handoff")
	-- NPC 운전자
	local tr = Traffic.new({{points = {{x = 0, z = 0}, {x = 0, z = 400}}, loop = false, speed = 11}})
	local npc = tr:add(1, 10)
	for _ = 1, 300 do tr:step(1 / 30) end
	tr.obstacles = {{x = 0, z = npc.z + 25, r = 2.4, v = 0}}
	for _ = 1, 300 do tr:step(1 / 30) end
	check("traffic stops behind a car blocking its lane", npc.v < 0.3 and npc.z < tr.obstacles[1].z - 2.4 - npc.length / 2 + 0.2, npc.v)
	tr.obstacles = {}
	tr:react(npc, "speed_off")
	for _ = 1, 150 do tr:step(1 / 30) end
	check("a scared driver speeds off above the lane speed", npc.v > 13, npc.v)
	tr:react(npc, "bail")
	for _ = 1, 300 do tr:step(1 / 30) end
	check("a driver who bails leaves the car stopped", npc.v < 0.2 and npc.abandoned)
	local z0 = npc.z
	local st = tr:takeOver(npc)
	for _ = 1, 60 do tr:step(1 / 30) end
	check("a taken-over car leaves the lane simulation", npc.external and npc.z == z0 and st.z == z0 and st.heading == npc.heading)
end

-- 14. 보안 로봇 두뇌
do
	local seq = 0
	local function rnd() seq = (seq * 16807 + 11) % 2147483647; return seq / 2147483647 end
	local function run(bot, sec, target, level)
		local all = {}
		for _ = 1, math.floor(sec * 30 + 0.5) do for _, e in bot:update(1 / 30, target, level) do table.insert(all, e); all[e.type] = (all[e.type] or 0) + 1 end end
		return all
	end
	local route = {{x = 0, z = 0}, {x = 0, z = 20}, {x = 10, z = 20}, {x = 10, z = 0}}
	local bot = Security.new(route, {rand = rnd})
	run(bot, 6, nil, 0)
	check("security robot patrols its route", bot.state == "patrol" and bot.z > 3 and bot.anim == "walk_heavy", bot.z)
	local guard = Security.new(nil, {x = 0, z = 0, heading = 0, rand = rnd})
	check("vision: in front yes, behind no, behind a wall no, very close always", guard:sees({x = 0, z = 20, visible = true}) and not guard:sees({x = 0, z = -20, visible = true})
		and not guard:sees({x = 0, z = 20, visible = false}) and guard:sees({x = 0, z = -3, visible = true}) and not guard:sees({x = 0, z = 60, visible = true}) and guard:sees({x = 0, z = 50, visible = true, inVehicle = true}))
	local e = run(guard, 0.4, {x = 0, z = 30, visible = true}, 0)
	local farAware = guard.awareness
	check("awareness builds up instead of snapping", farAware > 0.05 and farAware < 1 and e.noticed == nil, farAware)
	local sneaky, loud = Security.new(nil, {x = 0, z = 0, rand = rnd}), Security.new(nil, {x = 0, z = 0, rand = rnd})
	run(sneaky, 0.25, {x = 0, z = 15, visible = true, crouched = true}, 0); run(loud, 0.25, {x = 0, z = 15, visible = true, armed = true}, 0)
	check("crouching is noticed slower than waving a gun", sneaky.awareness < loud.awareness * 0.4, sneaky.awareness .. " / " .. loud.awareness)
	e = run(guard, 4, {x = 0, z = 30, visible = true}, 0)
	check("an innocent bystander is noticed but left alone", guard.awareness == 1 and e.noticed == 1 and e.warn == nil and e.fire == nil and guard.state == "patrol")
	run(guard, 5, nil, 0)
	check("awareness fades when the target is gone", guard.awareness < 0.01)
	-- 수배 1: 정지 명령, 쏘지 않는다
	local b1 = Security.new(nil, {x = 0, z = 0, rand = rnd})
	e = run(b1, 8, {x = 0, z = 25, vx = 0, vz = 0, visible = true}, 1)
	check("wanted level 1: closes in and orders a halt, never fires", b1.state == "halt" and (e.warn or 0) >= 2 and e.fire == nil and (e.seen or 0) >= 5 and b1.z > 10 and b1.anim == "robot_halt", b1.z)
	-- 수배 3: 사격
	local b3 = Security.new(nil, {x = 0, z = 0, rand = rnd})
	local ev3 = run(b3, 10, {x = 0, z = 20, vx = 0, vz = 0, visible = true}, 3)
	local hits = 0
	for i = 1, #ev3 do local x = ev3[i]; if x.type == "fire" and x.hit then hits += 1 end end
	check("wanted level 3: aims, then fires bursts and lands some", b3.state == "engage" and (ev3.fire or 0) >= 12 and hits >= 4 and hits < ev3.fire, (ev3.fire or 0) .. " shots " .. hits .. " hits")
	local first = nil
	local bq = Security.new(nil, {x = 0, z = 0, rand = rnd})
	for i = 1, 60 do for _, x in bq:update(1 / 30, {x = 0, z = 20, visible = true}, 3) do if x.type == "fire" and not first then first = i / 30 end end end
	check("there is a beat to react before the first shot", first ~= nil and first > 0.5, first)
	local farShots, nearShots = 0, 0
	local carEv = run(Security.new(nil, {x = 0, z = 0, rand = rnd}), 20, {x = 0, z = 24, vx = 14, vz = 0, visible = true, inVehicle = true}, 3)
	local tires = 0
	for i = 1, #carEv do local x = carEv[i]; if x.type == "fire" then farShots += 1; if x.accuracy < 0.4 then nearShots += 1 end; if x.at == "tires" then tires += 1 end end end
	check("a fast car is hard to hit and the robot goes for the tires", farShots > 0 and nearShots == farShots and tires == farShots, farShots)
	-- 놓치면 수색, 그다음 순찰 복귀
	local bs = Security.new(route, {rand = rnd})
	run(bs, 3, {x = 5, z = 12, visible = true}, 3)
	local lostEv = run(bs, 1, {x = 5, z = 12, visible = false}, 3)
	check("losing sight starts a search at the last seen spot", bs.state == "search" and lostEv.lost == 1)
	local back = run(bs, 40, {x = 200, z = 200, visible = false}, 3)
	check("after searching it returns to its patrol", bs.state == "patrol" and back.resume == 1)
	-- 차가 덮쳐 오면 피한다
	local bd = Security.new(nil, {x = 0.3, z = 12, heading = math.pi, rand = rnd})
	local x0 = bd.x
	local dv = run(bd, 0.4, {x = 0, z = 0, vx = 0, vz = 14, visible = true, inVehicle = true}, 2)
	check("robot sidesteps a car driven at it", dv.dodge == 1 and math.abs(bd.x - x0) > 0.8, bd.x - x0)
	-- 맞으면 바로 알아채고, 부서지면 꺼진다
	local bh = Security.new(nil, {x = 0, z = 0, heading = 0, rand = rnd})
	local r = bh:damageBy({damage = 40, kind = "bullet", zone = "torso", dirX = 0, dirZ = 1})
	check("a shot in the back alerts it and turns it around", r.crime == "assault_security" and bh.awareness == 1 and math.abs(math.cos(bh.heading) + 1) < 1e-6 and not r.killed)
	local shotsToKill = 1
	while not r.killed and shotsToKill < 100 do r = bh:damageBy({damage = 40, kind = "bullet", zone = "torso", dirX = 0, dirZ = 1}); shotsToKill += 1 end
	check("it takes sustained fire to destroy and then it shuts down", r.killed and r.crime == "kill_security" and shotsToKill >= 8 and bh.state == "down" and bh.anim == "robot_shutdown" and r.anim == "robot_shutdown", shotsToKill)
	check("a destroyed robot does nothing", #bh:update(1, {x = 0, z = 5, visible = true}, 5) == 0)
end

-- 15. 서버 -> 클라이언트 전송
do
	local names = {}
	for _, c in load("_index").clips do table.insert(names, c.name) end
	table.sort(names)
	local anims = CrowdNet.animTable(names)
	check("anim table fits in one byte", #names <= 255 and anims.ids.walk ~= nil and anims.names[anims.ids.death_back] == "death_back", #names)
	local cr = Crowd.new(world(), {seed = 21}); cr:spawn(80)
	for _ = 1, 90 do cr:step(1 / 30) end
	cr:damage(cr.agents[1], {damage = 999, kind = "bullet", zone = "torso", dirX = 1, dirZ = 0})
	local focus = {x = cr.agents[1].x, z = cr.agents[1].z}
	local buf = CrowdNet.pack(cr.agents, focus, 30, anims)
	local list = CrowdNet.unpack(buf, anims)
	local inRange = 0
	for _, a in cr.agents do if (a.x - focus.x) ^ 2 + (a.z - focus.z) ^ 2 <= 900 then inRange += 1 end end
	check("only nearby agents are sent, ten bytes each", #list == inRange and #list < 80 and buffer.len(buf) == 10 + 10 * #list, #list .. " of 80")
	local worst, deadOk = 0, false
	for _, it in list do
		local a = cr.agents[it.id]
		worst = math.max(worst, math.abs(a.x - it.x), math.abs(a.z - it.z), math.abs(((a.heading - it.heading + math.pi) % (2 * math.pi)) - math.pi) / 4)
		if it.anim ~= a.anim then worst = 99 end
		if it.id == 1 then deadOk = it.dead and string.sub(it.anim, 1, 6) == "death_" end
	end
	check("positions survive the round trip within 2 cm and 2 degrees", worst < 0.011, worst)
	check("death state and clip survive the round trip", deadOk)
	check("the cap keeps the nearest", #CrowdNet.unpack(CrowdNet.pack(cr.agents, focus, 500, anims, 12), anims) == 12)
	-- 클라이언트 보간: 10 Hz로 받은 것을 60 Hz로 그려도 튀지 않는다
	local sv = Crowd.new(world(), {seed = 22}); sv:spawn(30)
	for _ = 1, 60 do sv:step(1 / 30) end
	local ip = CrowdNet.Interp.new(0.15)
	local t, lastPos, maxJump, shown = 0, {}, 0, 0
	for frame = 1, 600 do
		t += 1 / 60
		if frame % 2 == 0 then sv:step(1 / 30) end
		if frame % 6 == 0 then ip:push(CrowdNet.unpack(CrowdNet.pack(sv.agents, {x = 20, z = 10}, 200, anims), anims), t) end
		if frame > 60 then
			local view = ip:sample(t)
			shown = 0
			for id, v in view do
				shown += 1
				local p = lastPos[id]
				if p then maxJump = math.max(maxJump, math.sqrt((v.x - p.x) ^ 2 + (v.z - p.z) ^ 2)) end
				lastPos[id] = {x = v.x, z = v.z}
			end
		end
	end
	check("interpolated motion is smooth at 60 fps from 10 Hz snapshots", shown == 30 and maxJump < 0.12, maxJump)
	local gone = CrowdNet.Interp.new(0.15)
	gone:push({{id = 7, x = 0, z = 0, heading = 0, anim = "walk", animTime = 0}}, 0); gone:push({}, 1.0)
	local n = 0
	for _ in gone:sample(1.0) do n += 1 end
	check("agents that stop arriving are dropped", n == 0)
	-- 서버는 플레이어 여러 명을 기준으로 갱신 빈도를 정한다
	local multi = Crowd.new(world(), {seed = 5}); multi:spawn(20)
	multi:step(1 / 30, nil, {{x = 0, z = 0}, {x = 40, z = 30}})
	local near = 0
	for _, a in multi.agents do if a.lod == 0 then near += 1 end end
	check("crowd level of detail follows the nearest of several players", near == 20, near)
end

print(string.format("%d passed, %d failed", passed, failed))
if failed > 0 then process.exit(1) end
