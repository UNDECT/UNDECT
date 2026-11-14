--!nonstrict
-- 보안 로봇 한 대의 두뇌. Roblox API를 쓰지 않는 순수 모듈.
-- 순찰(Patrol) -> 알아챔(인지도가 차오른다) -> 정지 명령 -> 교전 -> 놓치면 수색 -> 순찰로 복귀. 부서지면 꺼진다.
-- 무엇을 할지는 수배 단계(Wanted)가 정한다: 1~2단계는 쏘지 않고 정지 명령만, 3단계부터 사격한다.
local Patrol = require("./Patrol")
local Vitals = require("./Vitals")
local Wanted = require("./Wanted")

local Security = {}
Security.__index = Security

Security.DEFAULTS = {
	range = 38,            -- 보는 거리(m). 차는 1.5배 멀리서도 본다
	fov = math.rad(110),   -- 시야각. 4 m 안은 뒤에 있어도 알아챈다
	health = 260,
	armor = 0.35,
	walk = 1.4, run = 3.4, -- 걷는 속도, 쫓는 속도(m/s). 차는 못 따라잡는다
	keepNear = 12, keepFar = 26,   -- 교전 중 유지하는 거리
	aimTime = 0.6,         -- 조준하고 첫 발까지
	burst = 3, shotGap = 0.14, burstGap = 0.9,
	damage = 9,            -- 한 발 피해
	searchTime = 7,        -- 마지막으로 본 곳에서 훑어보는 시간
}

-- waypoints = Patrol에 넘길 순찰 점(없으면 제자리 경비). opts.rand = 0~1 난수 함수
function Security.new(waypoints, opts)
	opts = opts or {}
	local self = setmetatable({}, Security)
	for k, v in Security.DEFAULTS do self[k] = v end
	for k, v in opts do self[k] = v end
	self.rand = opts.rand or math.random
	self.patrol = if waypoints and #waypoints >= 2 then Patrol.new(waypoints, {speed = self.walk}) else nil
	self.x = if self.patrol then self.patrol.x else (opts.x or 0)
	self.z = if self.patrol then self.patrol.z else (opts.z or 0)
	self.heading = if self.patrol then self.patrol.heading else (opts.heading or 0)
	self.vitals = Vitals.new({health = self.health, armor = self.armor, machine = true, deathAnim = "robot_shutdown"})
	self.state = "patrol"; self.anim = if self.patrol then "walk_heavy" else "robot_scan"; self.moveSpeed = 0
	self.awareness = 0; self.timer = 0; self.shots = 0; self.warnTimer = 0; self.reportTimer = 0
	self.lastX, self.lastZ = self.x, self.z
	return self
end

-- 지금 대상이 보이는가. target.visible = 사이에 벽이 없다(게임이 레이캐스트로 알려 준다)
function Security:sees(target): boolean
	if not target or not target.visible or self.state == "down" then return false end
	local dx, dz = target.x - self.x, target.z - self.z
	local dist = math.sqrt(dx * dx + dz * dz)
	if dist < 4 then return true end
	if dist > self.range * (if target.inVehicle then 1.5 else 1) then return false end
	local diff = (math.atan2(dx, dz) - self.heading + math.pi) % (2 * math.pi) - math.pi
	return math.abs(diff) <= self.fov / 2
end

local function turn(self, tx: number, tz: number, dt: number, rate: number)
	local diff = (math.atan2(tx - self.x, tz - self.z) - self.heading + math.pi) % (2 * math.pi) - math.pi
	self.heading += math.clamp(diff, -rate * dt, rate * dt)
	return math.abs(diff)
end

local function moveToward(self, tx: number, tz: number, speed: number, dt: number)
	local dx, dz = tx - self.x, tz - self.z
	local d = math.sqrt(dx * dx + dz * dz)
	if d < 0.3 then self.moveSpeed = 0; return d end
	if turn(self, tx, tz, dt, 2.4) < 0.6 then
		local step = math.min(d, speed * dt)
		self.x += dx / d * step; self.z += dz / d * step; self.moveSpeed = speed
	else
		self.moveSpeed = 0
	end
	return d
end

-- 매 프레임. target = {x, z, vx, vz, inVehicle, visible, crouched, armed(무기를 꺼내 듦), hostile(방금 눈앞에서 범죄)}, level = 수배 단계.
-- 돌려주는 값: 사건 목록
--   {type = "noticed"}                       알아챘다(인지도 1)
--   {type = "seen"}                          보고 있다. 1초마다 나온다 -> Wanted의 seen과 범죄 신고(seenBySecurity)에 쓴다
--   {type = "warn"}                          정지 명령을 외친다
--   {type = "fire", at, hit, damage}         한 발 쐈다. at = "player" | "driver" | "tires"
--   {type = "dodge", side}                   달려오는 차를 피한다
--   {type = "lost", x, z} / {type = "resume"}  놓쳤다(마지막 위치) / 순찰로 돌아간다
function Security:update(dt: number, target, level: number)
	local ev = {}
	if self.state == "down" then self.moveSpeed = 0; return ev end
	local seen = self:sees(target)
	-- 인지도: 가까울수록, 무기를 들었을수록 빨리 차고, 웅크리면 천천히 찬다. 안 보이면 줄어든다
	if seen then
		local dist = math.sqrt((target.x - self.x) ^ 2 + (target.z - self.z) ^ 2)
		local rate = 0.5 + 2.2 * (1 - math.clamp(dist / self.range, 0, 1))
		if target.crouched then rate *= 0.45 end
		if target.armed or target.hostile then rate *= 2 end
		if level > 0 then rate *= 3 end                                   -- 수배 중이면 거의 바로 알아본다
		local was = self.awareness
		self.awareness = math.min(1, self.awareness + rate * dt)
		if was < 1 and self.awareness >= 1 then table.insert(ev, {type = "noticed"}) end
		self.lastX, self.lastZ = target.x, target.z
	else
		self.awareness = math.max(0, self.awareness - 0.35 * dt)
	end
	local detected = seen and self.awareness >= 1
	if detected then
		self.reportTimer -= dt
		if self.reportTimer <= 0 then self.reportTimer = 1; table.insert(ev, {type = "seen"}) end
	end
	local wantsAction = detected and (level > 0 or target.hostile)
	if wantsAction then
		local order = Wanted.robotOrder(self, target, math.max(level, 1), true)
		if order.action == "dodge" then
			-- 차가 지나갈 선에서 옆으로 1.8 m 비킨다
			local vx, vz = target.vx or 0, target.vz or 0
			local sp = math.max(math.sqrt(vx * vx + vz * vz), 1e-6)
			local side = if (vx * (self.z - target.z) - vz * (self.x - target.x)) > 0 then 1 else -1
			self.x += -vz / sp * side * 1.8 * math.min(1, dt * 6); self.z += vx / sp * side * 1.8 * math.min(1, dt * 6)
			if self.state ~= "dodge" then table.insert(ev, {type = "dodge", side = order.side}) end
			self.state = "dodge"; self.anim = order.anim; self.moveSpeed = 0
		elseif order.action == "fire" then
			if self.state ~= "engage" then self.state = "engage"; self.timer = self.aimTime; self.shots = 0 end
			local dist = math.sqrt((target.x - self.x) ^ 2 + (target.z - self.z) ^ 2)
			if dist > self.keepFar then moveToward(self, target.x, target.z, self.run, dt); self.anim = "walk_heavy"
			else turn(self, target.x, target.z, dt, 3.0); self.moveSpeed = 0; self.anim = "robot_aim" end
			self.timer -= dt
			if self.timer <= 0 and dist <= 45 then
				local speed = math.sqrt((target.vx or 0) ^ 2 + (target.vz or 0) ^ 2)
				local acc = math.clamp(0.78 - dist / 120 - speed * 0.018, 0.08, 0.9)
				table.insert(ev, {type = "fire", at = if target.inVehicle then order.at else "player", hit = self.rand() < acc, damage = self.damage, accuracy = acc})
				self.anim = "robot_fire"; self.shots += 1
				if self.shots >= self.burst then self.shots = 0; self.timer = self.burstGap else self.timer = self.shotGap end
			end
		else   -- halt, chase: 다가가며 정지 명령
			self.state = "halt"
			local dist = math.sqrt((target.x - self.x) ^ 2 + (target.z - self.z) ^ 2)
			if dist > self.keepNear then moveToward(self, target.x, target.z, self.run, dt); self.anim = "walk_heavy"
			else turn(self, target.x, target.z, dt, 3.0); self.moveSpeed = 0; self.anim = "robot_halt" end
			self.warnTimer -= dt
			if self.warnTimer <= 0 and dist < 30 then self.warnTimer = 3; table.insert(ev, {type = "warn"}) end
		end
	elseif self.state == "engage" or self.state == "halt" or self.state == "dodge" then
		if seen then                                                       -- 수배가 풀렸다
			self.state = "patrol"; table.insert(ev, {type = "resume"})
		else
			self.state = "search"; self.timer = self.searchTime
			table.insert(ev, {type = "lost", x = self.lastX, z = self.lastZ})
		end
	elseif self.state == "search" then
		local d = moveToward(self, self.lastX, self.lastZ, self.run, dt)
		self.anim = if d < 0.5 then "robot_scan" else "walk_heavy"
		if d < 0.5 then
			self.timer -= dt
			if self.timer <= 0 then self.state = "patrol"; table.insert(ev, {type = "resume"}) end
		end
	else   -- patrol: 순찰하거나 제자리 경비. 수상하면(인지도가 차는 중) 그쪽을 본다
		if seen and self.awareness > 0.3 and self.awareness < 1 then
			turn(self, target.x, target.z, dt, 2.0); self.moveSpeed = 0; self.anim = "robot_scan"
		elseif self.patrol then
			-- 순찰 경로에서 벗어나 있으면 걸어서 돌아간 뒤 이어서 돈다
			local dx, dz = self.patrol.x - self.x, self.patrol.z - self.z
			if dx * dx + dz * dz > 0.25 then
				moveToward(self, self.patrol.x, self.patrol.z, self.walk, dt); self.anim = "walk_heavy"
			else
				self.patrol:step(dt)
				self.x, self.z, self.heading = self.patrol.x, self.patrol.z, self.patrol.heading
				self.anim = self.patrol.anim; self.moveSpeed = self.patrol.moveSpeed
			end
		else
			self.moveSpeed = 0; self.anim = "robot_scan"
		end
	end
	return ev
end

-- 로봇이 맞았다. hit = Vitals.hit에 넘기는 값(dirX, dirZ = 공격이 날아가는 방향). 맞으면 그 자리에서 알아채고 쏜 쪽을 본다.
-- 돌려주는 값: Vitals.hit의 결과에 crime("assault_security" 또는 "kill_security")을 더한 것
function Security:damageBy(hit)
	hit.facing = self.heading; hit.roll = self.rand(); hit.roll2 = self.rand()
	local res = Vitals.hit(self.vitals, hit)
	if res.killed then
		self.state = "down"; self.anim = "robot_shutdown"; self.moveSpeed = 0; res.crime = "kill_security"
	elseif self.state ~= "down" then
		self.awareness = 1; res.crime = "assault_security"
		local dx, dz = hit.dirX or 0, hit.dirZ or 0
		if dx ~= 0 or dz ~= 0 then self.heading = math.atan2(-dx, -dz) end
	end
	return res
end

return Security
