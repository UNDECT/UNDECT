--!nonstrict
-- 지상 교통과 하늘 교통. 차선(꺾은선)을 따라 달리고, 앞차와 간격을 지키고, 빨간 신호 앞에 선다. 순수 모듈.
-- lane = {points = {{x=, z=, y=?}, ...}, loop = true, speed = 11, stops = {{s = 42.0, signal = "s1"}, ...}}
local Traffic = {}
Traffic.__index = Traffic

function Traffic.new(lanes, opts)
	opts = opts or {}
	local self = setmetatable({}, Traffic)
	self.lanes = lanes; self.vehicles = {}
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
		byLane[v.lane] = byLane[v.lane] or {}
		table.insert(byLane[v.lane], v)
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
			local a = self.accel * (1 - (v.v / v0) ^ 4)
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

return Traffic
