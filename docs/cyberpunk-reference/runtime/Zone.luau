--!nonstrict
-- 배틀로얄의 줄어드는 구역. Roblox API를 쓰지 않는 순수 모듈.
-- 인원에 맞춰 첫 전장의 크기를 정하고, 큰 맵 안에서 매 판 다른 자리를 고른 뒤, 단계마다 다음 원을 지금 원 안에 잡고 줄여 간다.
-- 좌표는 Crowd와 같다: x, z, 단위 m, 초.
local Zone = {}
Zone.__index = Zone

Zone.DENSITY = 10          -- 첫 전장의 밀도(명/km²). 40명이면 약 4 km², 반지름 약 1,130 m
Zone.MIN_RADIUS = 350      -- 인원이 아주 적어도 이보다 작게 시작하지 않는다
-- 단계: wait = 원이 멈춰 있는 시간, shrink = 줄어드는 시간, scale = 다음 원의 반지름 비율, dps = 원 밖에서 받는 초당 피해
Zone.PHASES = {
	{wait = 100, shrink = 120, scale = 0.62, dps = 1},
	{wait = 70, shrink = 90, scale = 0.58, dps = 2},
	{wait = 55, shrink = 70, scale = 0.55, dps = 4},
	{wait = 45, shrink = 55, scale = 0.50, dps = 7},
	{wait = 35, shrink = 45, scale = 0.45, dps = 11},
	{wait = 25, shrink = 35, scale = 0.0, dps = 16},     -- 마지막: 한 점으로 닫힌다
}

-- 인원 -> 첫 원의 반지름(m)
function Zone.radiusFor(players: number): number
	local area = math.max(1, players) / Zone.DENSITY * 1e6
	return math.max(Zone.MIN_RADIUS, math.sqrt(area / math.pi))
end

-- 한 판의 길이(초): 낙하가 끝난 뒤부터 마지막 원이 닫힐 때까지
function Zone.duration(phases): number
	local t = 0
	for _, p in (phases or Zone.PHASES) do t += p.wait + p.shrink end
	return t
end

-- 첫 원의 중심을 고른다. 원이 맵 밖으로 나가지 않게 한다. bounds = {minX, maxX, minZ, maxZ}, rand = 0~1 난수 함수.
-- blocked(x, z) -> true면 그 자리는 쓰지 않는다(예: 맵 가장자리 바다, 지하 전용 구역). 못 찾으면 맵 가운데.
function Zone.pickStart(bounds, radius: number, rand, blocked)
	local x0, x1 = bounds.minX + radius, bounds.maxX - radius
	local z0, z1 = bounds.minZ + radius, bounds.maxZ - radius
	if x0 > x1 then x0, x1 = (bounds.minX + bounds.maxX) / 2, (bounds.minX + bounds.maxX) / 2 end
	if z0 > z1 then z0, z1 = (bounds.minZ + bounds.maxZ) / 2, (bounds.minZ + bounds.maxZ) / 2 end
	for _ = 1, 30 do
		local x, z = x0 + (x1 - x0) * rand(), z0 + (z1 - z0) * rand()
		if not blocked or not blocked(x, z) then return x, z end
	end
	return (bounds.minX + bounds.maxX) / 2, (bounds.minZ + bounds.maxZ) / 2
end

-- opts: {x, z, radius, phases, rand}
function Zone.new(opts)
	local self = setmetatable({}, Zone)
	self.rand = opts.rand or math.random
	self.phases = opts.phases or Zone.PHASES
	self.x, self.z, self.r = opts.x or 0, opts.z or 0, opts.radius or 1000     -- 지금 원
	self.fx, self.fz, self.fr = self.x, self.z, self.r                         -- 줄어들기 시작한 때의 원
	self.phase = 0; self.state = "idle"; self.timer = 0; self.finished = false
	self.nx, self.nz, self.nr = self.x, self.z, self.r                         -- 다음 원(지도에 흰 원으로 미리 보여 준다)
	return self
end

local function nextCircle(self, p)
	local nr = self.r * p.scale
	local a, d = self.rand() * math.pi * 2, math.sqrt(self.rand()) * (self.r - nr)   -- 다음 원은 지금 원 안에 완전히 들어간다
	return self.x + math.sin(a) * d, self.z + math.cos(a) * d, nr
end

-- 낙하가 끝났을 때 한 번 부른다.
function Zone:start()
	self.phase = 1; self.state = "wait"; self.timer = self.phases[1].wait
	self.nx, self.nz, self.nr = nextCircle(self, self.phases[1])
	return {{type = "phase", phase = 1, wait = self.timer, nextX = self.nx, nextZ = self.nz, nextR = self.nr}}
end

-- 매 프레임(서버). 사건 목록을 돌려준다: phase(다음 원이 정해짐), shrink_start, shrink_end, closed
function Zone:update(dt: number)
	local ev = {}
	if self.finished or self.phase == 0 then return ev end
	self.timer -= dt
	local p = self.phases[self.phase]
	if self.state == "wait" then
		if self.timer <= 0 then
			self.state = "shrink"; self.timer += p.shrink
			self.fx, self.fz, self.fr = self.x, self.z, self.r
			table.insert(ev, {type = "shrink_start", phase = self.phase, time = p.shrink})
		end
	end
	if self.state == "shrink" then
		local u = math.clamp(1 - self.timer / p.shrink, 0, 1)
		self.x = self.fx + (self.nx - self.fx) * u; self.z = self.fz + (self.nz - self.fz) * u; self.r = self.fr + (self.nr - self.fr) * u
		if self.timer <= 0 then
			self.x, self.z, self.r = self.nx, self.nz, self.nr
			table.insert(ev, {type = "shrink_end", phase = self.phase})
			if self.phase >= #self.phases then
				self.finished = true; self.state = "closed"; table.insert(ev, {type = "closed"})
			else
				local carry = self.timer
				self.phase += 1; self.state = "wait"; self.timer = self.phases[self.phase].wait + carry
				self.nx, self.nz, self.nr = nextCircle(self, self.phases[self.phase])
				table.insert(ev, {type = "phase", phase = self.phase, wait = self.timer, nextX = self.nx, nextZ = self.nz, nextR = self.nr})
			end
		end
	end
	return ev
end

function Zone:inside(x: number, z: number): boolean
	return (x - self.x) ^ 2 + (z - self.z) ^ 2 <= self.r * self.r
end

-- 원 밖에 있는 동안 받는 피해(이 프레임 몫). 안에 있으면 0. 멀리 벗어날수록 조금 더 아프다(원 반지름의 절반만큼 벗어나면 2배).
function Zone:damage(x: number, z: number, dt: number): number
	if self.phase == 0 then return 0 end
	local d = math.sqrt((x - self.x) ^ 2 + (z - self.z) ^ 2) - self.r
	if d <= 0 then return 0 end
	local p = self.phases[math.min(self.phase, #self.phases)]
	return p.dps * (1 + math.min(1, d / math.max(50, self.r * 0.5))) * dt
end

-- 화면 표시용: 지금 원, 다음 원, 남은 시간, 상태
function Zone:info()
	return {x = self.x, z = self.z, r = self.r, nextX = self.nx, nextZ = self.nz, nextR = self.nr, phase = self.phase, state = self.state, timeLeft = math.max(0, self.timer)}
end

return Zone
