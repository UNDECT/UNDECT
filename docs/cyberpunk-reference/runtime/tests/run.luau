-- 실행: (runtime 폴더에서) lune run tests/run.luau
local fs = require("@lune/fs")
local serde = require("@lune/serde")
local process = require("@lune/process")
local AnimSampler = require("../AnimSampler")
local RigSolver = require("../RigSolver")
local Crowd = require("../Crowd")
local Patrol = require("../Patrol")
local Traffic = require("../Traffic")

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
for _, n in {"get_up", "melee_slash", "fp_recoil_shotgun", "knockdown"} do clips[n] = clips[n] or load(n) end

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
	check("clip index lists every clip", n == 94, n)
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

print(string.format("%d passed, %d failed", passed, failed))
if failed > 0 then process.exit(1) end
