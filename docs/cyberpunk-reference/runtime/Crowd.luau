--!nonstrict
-- 거리 군중 이동. 인도 그래프를 따라 걷고, 서로 비켜 가고, 소품을 피하고, 신호를 기다리고, 총성에 도망치거나 웅크린다.
-- Roblox API를 쓰지 않는 순수 모듈(평면 x, z). 단위는 m 기준(스터드로 쓰려면 속도·반경을 같이 곱한다).
-- world = {
--   nodes = {{x=, z=}, ...},
--   edges = {{a=1, b=2, width=3.0, signal="s1"?}, ...},   -- signal이 있으면 횡단보도
--   obstacles = {{x=, z=, r=}, ...},                       -- 노점, 가로등, 자판기 등
--   activities = {{node=3, kind="talk"|"phone"|"look_around"|"idle", duration={4, 10}, chance=0.3}, ...},
-- }
local Vitals = require("./Vitals")

local Crowd = {}
Crowd.__index = Crowd

local CELL = 2.0
local STRIDE = {walk = 1.43, flee = 2.86}

local function rngNew(seed: number)
	local s = seed % 2147483647
	if s <= 0 then s += 2147483646 end
	return function(): number
		s = (s * 16807) % 2147483647
		return (s - 1) / 2147483646
	end
end

function Crowd.new(world, opts)
	opts = opts or {}
	local self = setmetatable({}, Crowd)
	self.world = world
	self.rand = rngNew(opts.seed or 1)
	self.agents = {}
	self.radius = opts.radius or 0.32
	self.personal = opts.personal or 1.1
	self.lodNear = opts.lodNear or 40
	self.lodFar = opts.lodFar or 110
	self.frame = 0
	self.events = {}                              -- 사망·목격 등. Crowd:drain()으로 꺼낸다
	self.corpseTime = opts.corpseTime             -- 시체가 남는 시간(초). nil이면 수위에 따라: 0 -> 1.5, 1 -> 12, 2 이상 -> 계속
	self.adj = {}
	for i = 1, #world.nodes do self.adj[i] = {} end
	for ei, e in world.edges do
		table.insert(self.adj[e.a], {edge = ei, to = e.b})
		table.insert(self.adj[e.b], {edge = ei, to = e.a})
	end
	self.actAt = {}
	for _, a in (world.activities or {}) do
		self.actAt[a.node] = self.actAt[a.node] or {}
		table.insert(self.actAt[a.node], a)
	end
	return self
end

local function target(self, ag)
	local w = self.world
	local a, b = w.nodes[ag.from], w.nodes[ag.to]
	local dx, dz = b.x - a.x, b.z - a.z
	local len = math.sqrt(dx * dx + dz * dz)
	if len < 1e-6 then return b.x, b.z end
	-- 진행 방향의 오른쪽으로 lane만큼 비켜서 걷는다(마주 오는 사람과 자연히 갈린다)
	return b.x + (dz / len) * ag.lane, b.z - (dx / len) * ag.lane
end

local function pickLane(self, edge)
	local half = math.max(0.2, edge.width / 2 - self.radius - 0.15)
	return (0.15 + 0.85 * self.rand()) * half
end

-- 에이전트를 무작위 인도 위에 새로 놓는다(처음 만들 때와 다시 채울 때 같이 쓴다).
local function place(self, ag)
	local w = self.world
	local ei = 1 + math.floor(self.rand() * #w.edges) % #w.edges
	local e = w.edges[ei]
	local from, to = e.a, e.b
	if self.rand() < 0.5 then from, to = to, from end
	ag.from, ag.to, ag.edge, ag.lane = from, to, ei, pickLane(self, e)
	ag.state, ag.anim, ag.phase, ag.timer = "walk", "walk", self.rand(), 0
	ag.pref, ag.speed = 1.05 + 0.5 * self.rand(), 0
	ag.pending, ag.tx, ag.tz, ag.gone, ag.animTime = nil, nil, nil, false, 0
	ag.vitals = Vitals.new({health = 60 + 40 * self.rand()})
	local u = self.rand()
	local a, b = w.nodes[from], w.nodes[to]
	local tx, tz = target(self, ag)
	local sx, sz = a.x + (tx - b.x), a.z + (tz - b.z)
	ag.x, ag.z = sx + (tx - sx) * u, sz + (tz - sz) * u
	ag.heading = math.atan2(tx - sx, tz - sz)
end

function Crowd:spawn(count: number)
	for _ = 1, count do
		local ag = {id = #self.agents + 1, x = 0, z = 0, heading = 0}
		place(self, ag)
		table.insert(self.agents, ag)
	end
	return self.agents
end

local function chooseNext(self, ag, signals)
	local w = self.world
	local opts = self.adj[ag.to]
	local cands = {}
	for _, o in opts do
		if o.to ~= ag.from then table.insert(cands, o) end
	end
	if #cands == 0 then cands = opts end
	local pick
	if ag.state == "flee" and ag.tx then
		-- 위협에서 가장 멀어지는 길
		local best = -math.huge
		for _, o in cands do
			local n = w.nodes[o.to]
			local d = (n.x - ag.tx) ^ 2 + (n.z - ag.tz) ^ 2
			if d > best then best = d; pick = o end
		end
	else
		pick = cands[1 + math.floor(self.rand() * #cands) % #cands]
	end
	local e = w.edges[pick.edge]
	if e.signal and ag.state ~= "flee" and signals and signals[e.signal] == false then
		ag.state = "wait"; ag.anim = "idle"; ag.pending = pick; ag.speed = 0
		return
	end
	ag.from, ag.to, ag.edge = ag.to, pick.to, pick.edge
	ag.lane = pickLane(self, e)
	ag.pending = nil
end

local function steer(self, ag, grid, dt: number, maxSpeed: number, turnRate: number)
	local tx, tz = target(self, ag)
	local dx, dz = tx - ag.x, tz - ag.z
	local dist = math.sqrt(dx * dx + dz * dz)
	local vx, vz = 0, 0
	if dist > 1e-6 then vx, vz = dx / dist * maxSpeed, dz / dist * maxSpeed end
	-- 서로 비켜 가기
	local cx, cz = math.floor(ag.x / CELL), math.floor(ag.z / CELL)
	local P = self.personal
	for ix = cx - 1, cx + 1 do
		for iz = cz - 1, cz + 1 do
			local cell = grid[ix * 73856093 + iz * 19349663]
			if cell then
				for _, o in cell do
					if o ~= ag then
						local ox, oz = ag.x - o.x, ag.z - o.z
						local d = math.sqrt(ox * ox + oz * oz)
						if d < P and d > 1e-6 then
							local k = (P - d) / P * 2.4
							vx += ox / d * k; vz += oz / d * k
						end
					end
				end
			end
		end
	end
	-- 소품 피하기
	for _, ob in (self.world.obstacles or {}) do
		local ox, oz = ag.x - ob.x, ag.z - ob.z
		local d = math.sqrt(ox * ox + oz * oz)
		local reach = ob.r + self.radius + 0.5
		if d < reach and d > 1e-6 then
			local k = (reach - d) / reach * 3.2
			vx += ox / d * k; vz += oz / d * k
		end
	end
	local sp = math.sqrt(vx * vx + vz * vz)
	if sp > maxSpeed then vx, vz = vx / sp * maxSpeed, vz / sp * maxSpeed; sp = maxSpeed end
	if sp > 1e-4 then
		local want = math.atan2(vx, vz)
		local diff = (want - ag.heading + math.pi) % (2 * math.pi) - math.pi
		local lim = turnRate * dt
		ag.heading += math.clamp(diff, -lim, lim)
	end
	-- 속도는 부드럽게 따라간다
	ag.speed += (sp - ag.speed) * math.min(1, dt * 6)
	local step = ag.speed * dt
	ag.x += math.sin(ag.heading) * step
	ag.z += math.cos(ag.heading) * step
	return dist, step
end

-- signals = {s1 = true(초록) | false(빨강)}, focus = {x=, z=} (카메라 위치: 멀리 있는 사람은 덜 자주 갱신)
function Crowd:step(dt: number, signals, focus)
	self.frame += 1
	local grid = {}
	for _, ag in self.agents do
		if ag.state ~= "dead" then                       -- 시체는 길을 막지 않는다
			local key = math.floor(ag.x / CELL) * 73856093 + math.floor(ag.z / CELL) * 19349663
			local cell = grid[key]
			if not cell then cell = {}; grid[key] = cell end
			table.insert(cell, ag)
		end
	end
	for _, ag in self.agents do
		local skip = 1
		if focus then
			local d = math.sqrt((ag.x - focus.x) ^ 2 + (ag.z - focus.z) ^ 2)
			ag.lod = if d < self.lodNear then 0 elseif d < self.lodFar then 1 else 2
			skip = if ag.lod == 0 then 1 elseif ag.lod == 1 then 2 else 4
		end
		if ag.state == "dead" or ag.state == "downed" or ag.state == "stagger" or ag.state == "falling" then skip = 1 end
		if (self.frame + ag.id) % skip == 0 then
			local h = dt * skip
			ag.animTime = (ag.animTime or 0) + h
			if ag.state ~= "dead" and ag.vitals then
				local r = Vitals.update(ag.vitals, h)
				if r and r.killed then
					ag.state = "dead"; ag.anim = r.anim; ag.animTime = 0; ag.speed = 0; ag.timer = self:corpseSeconds()
					table.insert(self.events, {type = "death", id = ag.id, x = ag.x, z = ag.z, cause = ag.vitals.cause, anim = r.anim, effects = r.effects})
				end
			end
			if ag.state == "dead" then
				ag.timer -= h
				if ag.timer <= 0 and not ag.gone then
					ag.gone = true; table.insert(self.events, {type = "corpse_gone", id = ag.id, x = ag.x, z = ag.z})
				end
			elseif ag.state == "stagger" then
				ag.timer -= h
				if ag.timer <= 0 then                         -- 맞고 나면 도망친다
					ag.state = "flee"; ag.anim = "run"; ag.timer = 8 + 4 * self.rand(); ag.fleeSpeed = 3.4 + 1.0 * self.rand()
				end
			elseif ag.state == "falling" then
				ag.timer -= h
				if ag.timer <= 0 then ag.state = "downed"; ag.anim = "wounded_crawl"; ag.animTime = 0 end
			elseif ag.state == "downed" then                  -- 위협 반대쪽으로 기어간다
				local sp = 0.35
				ag.x += math.sin(ag.heading) * sp * h; ag.z += math.cos(ag.heading) * sp * h; ag.speed = sp
			elseif ag.state == "walk" or ag.state == "flee" then
				local fleeing = ag.state == "flee"
				local dist, step = steer(self, ag, grid, h, if fleeing then ag.fleeSpeed else ag.pref, if fleeing then 8 else 4)
				ag.phase = (ag.phase + step / (if fleeing then STRIDE.flee else STRIDE.walk)) % 1
				if fleeing then
					ag.timer -= h
					if ag.timer <= 0 then ag.state = "walk"; ag.anim = "walk"; ag.tx = nil end
				end
				if dist < 0.7 then
					local acts = self.actAt[ag.to]
					if not fleeing and acts then
						local a = acts[1 + math.floor(self.rand() * #acts) % #acts]
						if self.rand() < (a.chance or 0.25) then
							ag.state = "idle"; ag.anim = a.kind; ag.speed = 0
							ag.timer = a.duration[1] + (a.duration[2] - a.duration[1]) * self.rand()
						end
					end
					if ag.state ~= "idle" then chooseNext(self, ag, signals) end
				end
			elseif ag.state == "idle" then
				ag.timer -= h
				if ag.timer <= 0 then ag.state = "walk"; ag.anim = "walk"; chooseNext(self, ag, signals) end
			elseif ag.state == "wait" then
				local e = self.world.edges[ag.pending.edge]
				if not signals or signals[e.signal] ~= false then
					ag.state = "walk"; ag.anim = "walk"
					ag.from, ag.to, ag.edge = ag.to, ag.pending.to, ag.pending.edge
					ag.lane = pickLane(self, e); ag.pending = nil
				end
			elseif ag.state == "cower" then
				ag.timer -= h
				if ag.timer <= 0 then ag.state = "walk"; ag.anim = "walk" end
			end
		end
	end
end

-- 총성·폭발: 반경 안의 사람은 웅크리거나(30%) 도망친다. 위협 쪽으로 가던 사람은 돌아선다.
function Crowd:panic(x: number, z: number, radius: number)
	local w = self.world
	local n = 0
	for _, ag in self.agents do
		local d = math.sqrt((ag.x - x) ^ 2 + (ag.z - z) ^ 2)
		if d <= radius and ag.state ~= "cower" and ag.state ~= "dead" and ag.state ~= "downed" and ag.state ~= "falling" and ag.state ~= "stagger" then
			n += 1
			if self.rand() < 0.3 then
				ag.state = "cower"; ag.anim = "cower_loop"; ag.speed = 0; ag.timer = 4 + 4 * self.rand()
			else
				ag.state = "flee"; ag.anim = "run"; ag.timer = 6 + 4 * self.rand()
				ag.fleeSpeed = 4.0 + 1.0 * self.rand(); ag.tx, ag.tz = x, z; ag.pending = nil
				-- 지금 가는 방향이 위협 쪽이면 돌아선다
				local b = w.nodes[ag.to]
				if (b.x - ag.x) * (ag.x - x) + (b.z - ag.z) * (ag.z - z) < 0 then ag.from, ag.to = ag.to, ag.from end
			end
		end
	end
	return n
end

function Crowd:corpseSeconds(): number
	if self.corpseTime then return self.corpseTime end
	return if Vitals.GORE <= 0 then 1.5 elseif Vitals.GORE == 1 then 12 else math.huge
end

-- 군중 한 사람이 맞았다. hit = {damage, kind, zone | part, dirX, dirZ(공격이 날아가는 방향), attacker}
-- 피해를 계산하고, 상태와 동작을 바꾸고, 주변 사람을 놀라게 하고, 사건을 기록한다. Vitals.hit의 결과를 돌려준다.
function Crowd:damage(ag, hit)
	if ag.state == "dead" and ag.gone then return nil end
	local wasAlive = ag.state ~= "dead"
	hit.facing = ag.heading; hit.roll = self.rand(); hit.roll2 = self.rand()
	local res = Vitals.hit(ag.vitals, hit)
	local dx, dz = hit.dirX or 0, hit.dirZ or 0
	local len = math.sqrt(dx * dx + dz * dz)
	if len > 1e-6 and res.knock > 0 then ag.x += dx / len * res.knock; ag.z += dz / len * res.knock end
	if res.killed then
		ag.state = "dead"; ag.anim = res.anim; ag.animTime = 0; ag.speed = 0; ag.timer = self:corpseSeconds(); ag.pending = nil
		table.insert(self.events, {type = "death", id = ag.id, x = ag.x, z = ag.z, cause = hit.kind or "bullet", anim = res.anim, attacker = hit.attacker, effects = res.effects})
	elseif res.downed then
		ag.state = "falling"; ag.anim = "fall_wounded"; ag.animTime = 0; ag.speed = 0; ag.timer = 1.0; ag.pending = nil
		if len > 1e-6 then ag.heading = math.atan2(dx, dz) end            -- 공격이 날아온 반대쪽으로 기어간다
		table.insert(self.events, {type = "downed", id = ag.id, x = ag.x, z = ag.z, attacker = hit.attacker, effects = res.effects})
	elseif wasAlive and res.anim and ag.state ~= "downed" and ag.state ~= "falling" then
		ag.state = "stagger"; ag.anim = res.anim; ag.animTime = 0; ag.speed = 0; ag.timer = if res.anim == "stagger" then 0.9 else 0.5; ag.pending = nil
		ag.tx, ag.tz = ag.x - dx, ag.z - dz
		table.insert(self.events, {type = "hurt", id = ag.id, x = ag.x, z = ag.z, attacker = hit.attacker, effects = res.effects})
	end
	if wasAlive and res.fear > 0 then
		local n = self:panic(ag.x, ag.z, res.fear)
		if res.killed and n > 0 then table.insert(self.events, {type = "witnessed", id = ag.id, x = ag.x, z = ag.z, witnesses = n, attacker = hit.attacker}) end
	end
	return res
end

-- 폭발: 반경 안의 모두에게 거리에 따라 줄어드는 피해를 준다.
function Crowd:explode(x: number, z: number, radius: number, damage: number, attacker)
	local out = {}
	for _, ag in self.agents do
		local dx, dz = ag.x - x, ag.z - z
		local d = math.sqrt(dx * dx + dz * dz)
		if d <= radius and not ag.gone then
			local res = self:damage(ag, {damage = damage * (1 - 0.7 * d / radius), kind = "explosive", zone = "torso", dirX = dx, dirZ = dz, attacker = attacker})
			if res then table.insert(out, {agent = ag, result = res}) end
		end
	end
	return out
end

-- 쌓인 사건을 꺼낸다(수배·경찰 출동, 소리, 이펙트에 쓴다).
function Crowd:drain()
	local ev = self.events
	self.events = {}
	return ev
end

-- 죽어서 치워진 사람 자리를 채운다. 플레이어(focus)에게서 minDist보다 먼 곳에만 새로 놓는다. 채운 수를 돌려준다.
function Crowd:refill(focus, minDist: number)
	local n = 0
	for _, ag in self.agents do
		if ag.gone then
			for _ = 1, 8 do
				place(self, ag)
				if not focus or math.sqrt((ag.x - focus.x) ^ 2 + (ag.z - focus.z) ^ 2) >= minDist then n += 1; break end
				ag.gone = true
			end
		end
	end
	return n
end

function Crowd:countAlive(): number
	local n = 0
	for _, ag in self.agents do if ag.state ~= "dead" then n += 1 end end
	return n
end

return Crowd
