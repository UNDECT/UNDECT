--!nonstrict
-- 보안 로봇 순찰. 정해진 점을 돌고, 모퉁이에서 멈춰 훑고, 방향을 바꿀 때는 제자리에서 먼저 돈다. 순수 모듈.
-- waypoints = {{x=, z=, pause=2.0?}, ...}  (닫힌 고리)
local Patrol = {}
Patrol.__index = Patrol

function Patrol.new(waypoints, opts)
	opts = opts or {}
	local self = setmetatable({}, Patrol)
	self.points = waypoints
	self.i = 2
	self.x, self.z = waypoints[1].x, waypoints[1].z
	self.speed = opts.speed or 1.0
	self.turnRate = opts.turnRate or 1.6       -- 초당 라디안. 사람보다 느리고 무겁게
	self.turnFirst = math.rad(opts.turnFirstDeg or 25)
	self.heading = math.atan2(waypoints[2].x - self.x, waypoints[2].z - self.z)
	self.state = "walk"; self.anim = "walk_heavy"; self.timer = 0; self.phase = 0; self.moveSpeed = 0
	return self
end

local function turnToward(self, want: number, dt: number): number
	local diff = (want - self.heading + math.pi) % (2 * math.pi) - math.pi
	local lim = self.turnRate * dt
	self.heading += math.clamp(diff, -lim, lim)
	return math.abs(diff)
end

function Patrol:step(dt: number)
	if self.state == "alert" then
		local err = turnToward(self, math.atan2(self.tx - self.x, self.tz - self.z), dt * 2.2)
		self.timer += dt; self.moveSpeed = 0
		self.anim = if self.timer < 0.35 then "robot_alert" else "robot_aim"
		self.aimed = self.timer >= 0.35 and err < math.rad(6)
		return
	end
	if self.state == "pause" then
		self.timer -= dt; self.moveSpeed = 0
		if self.timer <= 0 then self.state = "walk"; self.anim = "walk_heavy" end
		return
	end
	local p = self.points[self.i]
	local dx, dz = p.x - self.x, p.z - self.z
	local dist = math.sqrt(dx * dx + dz * dz)
	if dist < 0.25 then
		self.i = self.i % #self.points + 1
		if p.pause and p.pause > 0 then self.state = "pause"; self.anim = "robot_scan"; self.timer = p.pause end
		self.moveSpeed = 0
		return
	end
	local err = turnToward(self, math.atan2(dx, dz), dt)
	if err > self.turnFirst then
		self.state = "turn"; self.anim = "idle"; self.moveSpeed = 0     -- 제자리 회전
	else
		self.state = "walk"; self.anim = "walk_heavy"
		self.moveSpeed = math.min(self.speed, dist / math.max(dt, 1e-6))
		local step = self.moveSpeed * dt
		self.x += math.sin(self.heading) * step; self.z += math.cos(self.heading) * step
		self.phase = (self.phase + step / 1.34) % 1
	end
end

function Patrol:alert(tx: number, tz: number)
	if self.state ~= "alert" then self.timer = 0 end
	self.state = "alert"; self.tx, self.tz = tx, tz; self.aimed = false
end

function Patrol:clear()
	if self.state == "alert" then self.state = "walk"; self.anim = "walk_heavy"; self.aimed = false end
end

return Patrol
