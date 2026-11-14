--!nonstrict
-- 수배와 보안 대응. Roblox API를 쓰지 않는 순수 모듈.
-- 범죄가 "보안에 알려졌을 때만" 수배가 오른다: 보안 로봇·드론·카메라가 직접 봤거나, 시민이 신고를 끝냈거나, 경보기가 보안 근처에서 울렸을 때.
-- 수배 단계(0~5)마다 보내는 부대와 허용되는 대응이 정해져 있고, 시야에서 벗어나면 수색으로 바뀌었다가 풀린다.
local Wanted = {}
Wanted.__index = Wanted

-- 범죄별 점수. level = 이 범죄 하나로 곧바로 오르는 최소 단계
Wanted.CRIMES = {
	reckless = {points = 4, level = 0},            -- 난폭 운전(인도 주행, 신호 위반, 아슬아슬하게 스침)
	vehicle_damage = {points = 6, level = 0},
	vehicle_theft = {points = 22, level = 1},      -- 세워 둔 차 훔치기
	carjacking = {points = 34, level = 2},         -- 사람이 탄 차 빼앗기
	hit_pedestrian = {points = 30, level = 2},
	assault = {points = 26, level = 1},
	weapon_fire = {points = 20, level = 1},
	kill = {points = 55, level = 3},
	assault_security = {points = 60, level = 3},
	kill_security = {points = 90, level = 4},
	destroy_patrol = {points = 90, level = 4},
	evade_roadblock = {points = 18, level = 0},
}
Wanted.THRESHOLD = {20, 55, 110, 190, 300}          -- 단계 1~5가 되는 점수

-- 단계별 대응. robots = 걸어서 오는 보안 로봇, cars = 순찰차, drones = 드론, flyers = 순찰 비행 차량
-- lethal = 사격 허용, tires = 바퀴 사격, roadblock = 차단선 간격(초), spikes = 못판, pit = 옆구리 들이받기, lockdown = 구역 봉쇄(볼라드·포탑)
Wanted.RESPONSE = {
	[0] = {robots = 0, cars = 0, drones = 0, flyers = 0, lethal = false, tires = false, roadblock = nil, spikes = false, pit = false, lockdown = false, evade = 0},
	[1] = {robots = 2, cars = 0, drones = 0, flyers = 0, lethal = false, tires = false, roadblock = nil, spikes = false, pit = false, lockdown = false, evade = 18},
	[2] = {robots = 2, cars = 1, drones = 1, flyers = 0, lethal = false, tires = false, roadblock = nil, spikes = false, pit = false, lockdown = false, evade = 26},
	[3] = {robots = 3, cars = 2, drones = 2, flyers = 0, lethal = true, tires = true, roadblock = 45, spikes = false, pit = true, lockdown = false, evade = 36},
	[4] = {robots = 4, cars = 3, drones = 2, flyers = 1, lethal = true, tires = true, roadblock = 32, spikes = true, pit = true, lockdown = false, evade = 48},
	[5] = {robots = 6, cars = 4, drones = 3, flyers = 2, lethal = true, tires = true, roadblock = 24, spikes = true, pit = true, lockdown = true, evade = 60},
}

function Wanted.new(opts)
	opts = opts or {}
	local self = setmetatable({}, Wanted)
	self.points = 0; self.level = 0
	self.state = "clear"                     -- clear | wanted(위치를 안다) | search(놓쳐서 찾는 중)
	self.lastX, self.lastZ = 0, 0            -- 마지막으로 본 곳
	self.searchTimer = 0; self.searchRadius = 0; self.roadblockTimer = 0
	self.units = {robots = 0, cars = 0, drones = 0, flyers = 0}
	self.spawnCooldown = 0; self.haltTimer = 0
	self.decay = opts.decay or 1.5           -- 수배가 풀린 뒤 초당 줄어드는 점수
	return self
end

local function levelFor(points: number): number
	local lv = 0
	for i, t in Wanted.THRESHOLD do if points >= t then lv = i end end
	return lv
end

-- 범죄가 보안에 알려졌다. info = {x, z, seenBySecurity = bool, reported = bool(시민 신고), alarm = bool}
-- 셋 중 하나도 아니면 아무도 모르는 범죄다: 수배가 오르지 않는다.
function Wanted:report(crime: string, info)
	info = info or {}
	local c = Wanted.CRIMES[crime]
	local ev = {}
	if not c or not (info.seenBySecurity or info.reported or info.alarm) then return ev end
	local before = self.level
	self.points += c.points
	self.level = math.max(levelFor(self.points), c.level, self.level)
	if self.level > 0 and self.points < Wanted.THRESHOLD[self.level] then self.points = Wanted.THRESHOLD[self.level] end
	if info.x then self.lastX, self.lastZ = info.x, info.z end
	if self.level > 0 then
		-- 직접 본 것이 아니면(신고·경보) 위치만 알고 출동한다: 수색 상태에서 시작한다
		if info.seenBySecurity then self.state = "wanted" elseif self.state == "clear" then
			self.state = "search"; self.searchTimer = Wanted.RESPONSE[self.level].evade; self.searchRadius = 25
		end
		if self.state == "search" then self.searchTimer = math.max(self.searchTimer, Wanted.RESPONSE[self.level].evade) end
	end
	if self.level > before then table.insert(ev, {type = "level_up", level = self.level, crime = crime}) end
	return ev
end

-- 플레이어가 차를 바꿨다(보안이 보지 못한 곳에서). 수색 시간이 절반으로 준다.
function Wanted:swappedVehicle(seen: boolean)
	if self.state == "search" and not seen then self.searchTimer *= 0.5 end
end

-- 매 프레임. ctx = {x, z, heading, speed, inVehicle, seen = 보안이 지금 보고 있다, stopped = 멈춰 있다, unarmed = 무기를 내렸다}
-- 돌려주는 값: 명령·사건 목록.
--   {type = "spawn", unit = "robot"|"car"|"drone"|"flyer", x, z}   부대를 보내라(플레이어 앞뒤 60~120 m, 화면 밖)
--   {type = "roadblock", x, z, heading, spikes}                    차단선을 쳐라
--   {type = "lost"} / {type = "search", x, z, radius} / {type = "clear"} / {type = "busted"}(체포) / {type = "lockdown", on}
function Wanted:update(dt: number, ctx)
	local ev = {}
	local plan = Wanted.RESPONSE[self.level]
	if self.state == "clear" then
		if self.points > 0 then self.points = math.max(0, self.points - self.decay * dt) end
		return ev
	end
	if ctx.seen then
		if self.state == "search" then table.insert(ev, {type = "found"}) end
		self.state = "wanted"; self.lastX, self.lastZ = ctx.x, ctx.z
	elseif self.state == "wanted" then
		self.state = "search"; self.searchTimer = plan.evade; self.searchRadius = 20
		table.insert(ev, {type = "lost"}); table.insert(ev, {type = "search", x = self.lastX, z = self.lastZ, radius = self.searchRadius})
	end
	if self.state == "search" then
		self.searchTimer -= dt
		self.searchRadius = math.min(140, self.searchRadius + 6 * dt)       -- 수색 범위가 점점 넓어진다
		if self.searchTimer <= 0 then
			self.state = "clear"; self.level = 0; self.points = math.min(self.points, Wanted.THRESHOLD[1] - 1)
			self.units = {robots = 0, cars = 0, drones = 0, flyers = 0}; self.haltTimer = 0
			table.insert(ev, {type = "clear"}); if plan.lockdown then table.insert(ev, {type = "lockdown", on = false}) end
			return ev
		end
	end
	-- 단계 1~2: 멈추고 무기를 내린 채 3초 있으면 체포로 끝난다(사격 허용 단계에서는 안 된다)
	if not plan.lethal and ctx.seen and ctx.stopped and ctx.unarmed then
		self.haltTimer += dt
		if self.haltTimer >= 3 then
			self.state = "clear"; self.level = 0; self.points = 0; self.haltTimer = 0
			self.units = {robots = 0, cars = 0, drones = 0, flyers = 0}
			table.insert(ev, {type = "busted"}); return ev
		end
	else
		self.haltTimer = 0
	end
	-- 부대 보충: 한 번에 하나씩, 1.5초 간격
	self.spawnCooldown -= dt
	if self.spawnCooldown <= 0 then
		for _, kind in {"robots", "cars", "drones", "flyers"} do
			if self.units[kind] < plan[kind] then
				local ahead = if kind == "robots" then 45 else 90
				local side = if (self.units[kind] % 2) == 0 then 1 else -1
				local hx, hz = math.sin(ctx.heading or 0), math.cos(ctx.heading or 0)
				local bx, bz = if self.state == "wanted" then ctx.x else self.lastX, if self.state == "wanted" then ctx.z else self.lastZ
				-- 차와 로봇은 번갈아 앞뒤에서, 드론과 비행 차량은 뒤 위에서 온다
				local dir = if kind == "cars" or kind == "robots" then side else -1
				table.insert(ev, {type = "spawn", unit = string.sub(kind, 1, -2), x = bx + hx * ahead * dir - hz * 12 * side, z = bz + hz * ahead * dir + hx * 12 * side})
				self.units[kind] += 1; self.spawnCooldown = 1.5
				break
			end
		end
	end
	-- 차단선: 차로 달아날 때만, 가는 길 앞쪽에
	if plan.roadblock and ctx.inVehicle and self.state == "wanted" then
		self.roadblockTimer -= dt
		if self.roadblockTimer <= 0 and (ctx.speed or 0) > 6 then
			self.roadblockTimer = plan.roadblock
			local rb = Wanted.roadblock(ctx.x, ctx.z, ctx.heading or 0, ctx.speed or 0)
			table.insert(ev, {type = "roadblock", x = rb.x, z = rb.z, heading = rb.heading, spikes = plan.spikes})
		end
	end
	if plan.lockdown and not self.locked then self.locked = true; table.insert(ev, {type = "lockdown", on = true}) end
	if not plan.lockdown then self.locked = false end
	return ev
end

-- 부대 하나가 파괴되거나 떨어져 나갔다(다시 보충된다).
function Wanted:unitLost(kind: string)
	local k = kind .. "s"
	if self.units[k] and self.units[k] > 0 then self.units[k] -= 1 end
end

-- 차단선 자리: 달리는 방향 앞쪽, 속도에 따라 60~160 m. 차단선은 길을 가로질러 선다.
-- 실제 게임에서는 이 점에서 가장 가까운 도로 구간으로 옮긴다.
function Wanted.roadblock(x: number, z: number, heading: number, speed: number)
	local d = math.clamp(speed * 6, 60, 160)
	return {x = x + math.sin(heading) * d, z = z + math.cos(heading) * d, heading = heading + math.pi / 2, distance = d,
		parts = {"barrier", "barrier", "barrier", "patrol_car", "robot", "robot"}}
end

-- 순찰차는 일반 차보다 빠르고 가속이 좋아야 따라잡는다. Driving.new(Wanted.PATROL_CAR)로 만든다.
Wanted.PATROL_CAR = {maxSpeed = 46, accel = 9.5, grip = 13}

-- 순찰차의 운전 입력(Driving:update에 그대로 넣는다). 목표의 조금 앞을 노리고, 급하게 꺾을 때는 속도를 줄인다.
-- mode: "follow"(뒤에서 따라가며 경고) | "pit"(옆에 붙어 뒤 옆구리를 민다) | "block"(앞질러 막는다)
function Wanted.pursuitInput(car, target, mode: string?)
	mode = mode or "follow"
	local lead = if mode == "block" then 1.6 elseif mode == "pit" then 0.5 else 0.3
	local tx, tz = target.x + (target.vx or 0) * lead, target.z + (target.vz or 0) * lead
	local gap = math.sqrt((target.x - car.x) ^ 2 + (target.z - car.z) ^ 2)
	if mode == "follow" then                                    -- 뒤 8 m 지점을 따라간다. 가까워지면 그 점이 내 뒤로 가지 않게 당긴다
		local back = math.min(8, gap * 0.5)
		tx -= math.sin(target.heading or 0) * back; tz -= math.cos(target.heading or 0) * back
	elseif mode == "pit" then                                   -- 뒤 옆구리(오른쪽 뒤)
		local h = target.heading or 0
		tx += -math.cos(h) * 1.6 - math.sin(h) * 1.4; tz += math.sin(h) * 1.6 - math.cos(h) * 1.4
	end
	local dx, dz = tx - car.x, tz - car.z
	local dist = math.sqrt(dx * dx + dz * dz)
	local want = math.atan2(dx, dz)
	local diff = (want - car.heading + math.pi) % (2 * math.pi) - math.pi     -- + = 왼쪽으로 돌아야 한다
	-- 0.5초 안에 그 방향을 보도록 도는 빠르기를 정하고, 그 빠르기를 내는 조향 각을 거꾸로 구한다(좌우로 흔들리지 않는다)
	local v = math.max(math.abs(car.speed), 3)
	local yawMax = (car.maxLatAccel or 11) * (1 + math.clamp((gap - 25) / 60, 0, 0.6)) / v
	local yawWant = math.clamp(diff / 0.5, -yawMax, yawMax)
	local angle = math.atan(yawWant * (car.wheelbase or 2.87) / v)               -- + = 왼쪽으로 꺾는 각
	local limit = (car.maxSteer or math.rad(34)) * (1 + ((car.steerAtSpeed or 0.26) - 1) * math.clamp(v / (car.maxSpeed or 38), 0, 1))
	local steer = math.clamp(-angle / limit, -1, 1)                              -- 조향 +는 오른쪽
	local targetSpeed = math.sqrt((target.vx or 0) ^ 2 + (target.vz or 0) ^ 2)
	local wantSpeed = if mode == "follow" then targetSpeed + math.clamp((gap - 9) * 0.9, -6, 22) else targetSpeed + 8
	-- 그 점까지 가면서 diff만큼 꺾으려면 필요한 회전 반지름이 있고, 타이어가 버티는 속도는 sqrt(옆 가속 한계 × 반지름)이다
	local radius = math.max(dist, 4) / (2 * math.sin(math.clamp(math.abs(diff), 0.02, math.pi / 2)))
	wantSpeed = math.min(wantSpeed, car.maxSpeed * (1 + math.clamp((gap - 25) / 60, 0, 0.6)), math.sqrt((car.maxLatAccel or 11) * radius) * 0.95)
	local throttle = math.clamp((wantSpeed - car.speed) * 0.6, -1, 1)
	-- 멀어질수록 더 빨라진다(25 m부터, 최대 1.6배). 게임의 추격 차가 흔히 쓰는 방법이고, 이것이 없으면 급하게 꺾는 차를 다시 못 따라잡는다
	local boost = 1 + math.clamp((gap - 25) / 60, 0, 0.6)
	return {throttle = throttle, steer = steer, handbrake = math.abs(diff) > 1.4 and car.speed > 12, boost = boost}
end

-- 걸어 다니는 보안 로봇이 할 일. robot = {x, z}, target = {x, z, vx, vz, inVehicle}, level = 수배 단계
--   {action = "halt"}     길로 나와 손을 들어 정지 명령(robot_halt). 3초 경고
--   {action = "dodge", side} 차가 덮쳐 오면 옆으로 피한다(dodge_left / dodge_right)
--   {action = "aim"} / {action = "fire", at = "tires"|"driver"}   조준 / 사격
--   {action = "chase"}    걸어서 쫓는다(차는 못 따라잡는다 -> 무전으로 넘긴다)
--   {action = "report"}   시야에서 놓쳤다. 마지막 위치를 알린다
function Wanted.robotOrder(robot, target, level: number, seen: boolean)
	if not seen then return {action = "report", anim = "robot_scan"} end
	local dx, dz = robot.x - target.x, robot.z - target.z
	local dist = math.sqrt(dx * dx + dz * dz)
	local vx, vz = target.vx or 0, target.vz or 0
	local speed = math.sqrt(vx * vx + vz * vz)
	if target.inVehicle and speed > 5 and dist < 22 then
		-- 차가 이쪽으로 오고 있고 1.3초 안에 닿으면 피한다
		local closing = (vx * dx + vz * dz) / math.max(dist, 1e-6)          -- 로봇 쪽으로 다가오는 속도
		local lateral = math.abs(vx * dz - vz * dx) / math.max(speed, 1e-6)  -- 차가 지나갈 선에서 떨어진 거리
		if closing > 0 and lateral < 1.6 and dist / closing < 1.3 then
			local cross = vx * dz - vz * dx
			return {action = "dodge", side = if cross > 0 then "left" else "right", anim = if cross > 0 then "dodge_left" else "dodge_right"}
		end
	end
	local plan = Wanted.RESPONSE[level] or Wanted.RESPONSE[0]
	if level <= 0 then return {action = "watch", anim = "robot_scan"} end
	if not plan.lethal then
		if dist < 14 then return {action = "halt", anim = "robot_halt"} end
		return {action = "chase", anim = "walk_heavy"}
	end
	if dist < 45 then
		return {action = "fire", at = if target.inVehicle and plan.tires then "tires" else "driver", anim = "robot_fire"}
	end
	return {action = "chase", anim = "walk_heavy"}
end

return Wanted
