--!nonstrict
-- 지상 교통과 하늘 교통. 차선(꺾은선)을 따라 달리고, 앞차와 간격을 지키고, 빨간 신호 앞에 선다. 순수 모듈.
-- lane = {points = {{x=, z=, y=?}, ...}, loop = true, speed = 11, stops = {{s = 42.0, signal = "s1"}, ...}}
local Traffic = {}
Traffic.__index = Traffic

function Traffic.new(lanes, opts)
	opts = opts or {}
	local self = setmetatable({}, Traffic)
	self.lanes = lanes; self.vehicles = {}
	self.obstacles = {}       -- 차선 밖에서 온 장애물: 플레이어 차, 차단선, 길에 쓰러진 사람. 게임이 매 프레임 {x, z, r, v}로 채운다
	self.accel = opts.accel or 2.2; self.brake = opts.brake or 3.5; self.gap = opts.gap or 2.5; self.headway = opts.headway or 1.2
	for _, ln in lanes do
		local n = #ln.points; ln.cum = {0}
		local last = if ln.loop then n else n - 1
		for i = 1, last do
			local a, b = ln.points[i], ln.points[i % n + 1]
			ln.cum[i + 1] = ln.cum[i] + math.sqrt((b.x - a.x) ^ 2 + (b.z - a.z) ^ 2)
		end
		ln.length = ln.cum[#ln.cum]
	end
	return self
end

function Traffic:add(laneIndex: number, s: number, length: number?, wheelRadius: number?)
	local v = {lane = laneIndex, s = s, v = 0, length = length or 4.7, wheelRadius = wheelRadius or 0.345, wheel = 0,
		x = 0, y = 0, z = 0, heading = 0, bank = 0, tilt = 0, braking = false}
	table.insert(self.vehicles, v)
	self:place(v)
	return v
end

local function at(ln, s: number)
	if ln.loop then s = s % ln.length else s = math.clamp(s, 0, ln.length) end
	local n = #ln.points
	local i = 1
	while i < #ln.cum - 1 and ln.cum[i + 1] <= s do i += 1 end
	local a, b = ln.points[i], ln.points[i % n + 1]
	local seg = ln.cum[i + 1] - ln.cum[i]
	local u = if seg > 1e-9 then (s - ln.cum[i]) / seg else 0
	return a.x + (b.x - a.x) * u, (a.y or 0) + ((b.y or 0) - (a.y or 0)) * u, a.z + (b.z - a.z) * u
end

function Traffic:place(v)
	local ln = self.lanes[v.lane]
	local x, y, z = at(ln, v.s)
	local fx, _, fz = at(ln, v.s + 2.0)
	local bx, _, bz = at(ln, v.s - 2.0)
	v.x, v.y, v.z = x, y, z
	if (fx - bx) ^ 2 + (fz - bz) ^ 2 > 1e-9 then v.heading = math.atan2(fx - bx, fz - bz) end
end

-- signals = {s1 = true(초록) | false(빨강)}
function Traffic:step(dt: number, signals)
	local byLane = {}
	for _, v in self.vehicles do
		if not v.external then                    -- 플레이어가 가져간 차는 차선에서 빠진다
			byLane[v.lane] = byLane[v.lane] or {}
			table.insert(byLane[v.lane], v)
		end
	end
	for li, list in byLane do
		local ln = self.lanes[li]
		table.sort(list, function(a, b) return a.s < b.s end)
		for i, v in list do
			local v0 = ln.speed or 11
			-- 앞에 있는 것까지의 여유 거리: 앞차 또는 빨간 정지선
			local free = math.huge
			local dv = 0
			local lead = list[i + 1]
			if not lead and ln.loop and #list > 1 then lead = list[1] end
			if lead and lead ~= v then
				local d = lead.s - v.s
				if d <= 0 then d += ln.length end
				free = d - (lead.length + v.length) / 2
				dv = v.v - lead.v
			end
			for _, st in (ln.stops or {}) do
				if signals and signals[st.signal] == false then
					local d = st.s - v.s
					if d < 0 and ln.loop then d += ln.length end
					local toLine = d - v.length / 2
					if toLine >= -0.5 and toLine < free then free = math.max(0, toLine); dv = v.v end
				end
			end
			-- 차선 밖 장애물(플레이어 차 등)이 앞길에 있으면 그 앞에서 선다
			local hx, hz = math.sin(v.heading), math.cos(v.heading)
			for _, ob in self.obstacles do
				local ox, oz = ob.x - v.x, ob.z - v.z
				local ahead = ox * hx + oz * hz
				if ahead > 0 and ahead < 45 and math.abs(ox * hz - oz * hx) < 1.7 + (ob.r or 1.2) * 0.4 then
					local d = ahead - (ob.r or 1.2) - v.length / 2
					if d < free then free = math.max(0, d); dv = v.v - (ob.v or 0) end
				end
			end
			-- 운전자 반응: 멈춤(손 들기), 버리고 도망, 급히 달아남
			if v.hold and v.hold > 0 then v.hold -= dt; free = 0; dv = v.v end
			if v.abandoned then free = 0; dv = v.v end
			local boost = 1
			if v.boost and v.boost > 0 then v.boost -= dt; boost = 1.8; v0 *= 1.7 end
			local a = self.accel * boost * (1 - (v.v / v0) ^ 4)
			if free < math.huge then
				local want = self.gap + v.v * self.headway + v.v * dv / (2 * math.sqrt(self.accel * self.brake))
				a -= self.accel * (math.max(0, want) / math.max(free, 0.05)) ^ 2
			end
			a = math.max(a, -self.brake * 2.5)
			local prevHeading = v.heading
			v.braking = a < -0.4
			v.v = math.max(0, v.v + a * dt)
			local move = v.v * dt
			if free < math.huge then move = math.min(move, math.max(0, free - 0.05)) end   -- 절대 겹치지 않는다
			v.s += move
			if ln.loop then v.s = v.s % ln.length else v.s = math.min(v.s, ln.length) end
			v.wheel += move / v.wheelRadius
			self:place(v)
			-- 비행 차량용: 방향을 틀 때 기울고, 빠를수록 추진기를 앞으로 눕힌다
			local rate = ((v.heading - prevHeading + math.pi) % (2 * math.pi) - math.pi) / math.max(dt, 1e-6)
			local bank = math.clamp(-rate * 0.45, -0.45, 0.45)
			v.bank += (bank - v.bank) * math.min(1, dt * 3)
			v.tilt += (math.rad(75) * math.min(1, v.v / v0) - v.tilt) * math.min(1, dt * 2)
		end
	end
end

-- 플레이어가 이 차를 빼앗았다. 차선에서 빼고, 지금 위치와 속도를 돌려준다(Driving.new에 넘긴다).
function Traffic:takeOver(v)
	v.external = true; v.abandoned = false
	return {x = v.x, z = v.z, heading = v.heading, speed = v.v}
end

-- NPC 운전자의 반응을 적용한다. reaction = Carjack.trafficReaction의 값.
--   stop: 6초 동안 선다 / speed_off: 8초 동안 급가속해 달아난다 / bail: 차를 세우고 버린다(운전자는 Crowd:eject로 내보낸다) / honk, reverse: 선다
function Traffic:react(v, reaction: string)
	if reaction == "speed_off" then v.boost = 8; v.hold = 0
	elseif reaction == "bail" then v.abandoned = true
	elseif reaction == "stop" then v.hold = 6
	else v.hold = 2 end
	v.reaction = reaction
end

return Traffic
