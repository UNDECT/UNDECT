--!nonstrict
-- 플레이어(와 추격 차량)가 모는 차의 움직임. Roblox API를 쓰지 않는 순수 모듈.
-- 입력(가속·제동·조향·핸드브레이크)을 받아 위치, 방향, 속도, 미끄러짐, 차체 기울기, 바퀴 회전을 낸다.
-- 좌표는 Crowd와 같다: x, z = Roblox의 X, Z. heading = atan2(dx, dz)이고 커지는 쪽이 왼쪽 회전이다. 단위 m, 초.
local Driving = {}
Driving.__index = Driving

Driving.DEFAULTS = {
	maxSpeed = 38,        -- 앞으로 최고 속도(m/s, 약 137 km/h)
	reverseMax = 9,
	accel = 7.5,          -- 가속(m/s²). 속도가 오를수록 줄어든다
	brake = 17,
	drag = 0.9,           -- 발을 뗐을 때 줄어드는 정도(m/s²)
	wheelbase = 2.87,
	maxSteer = math.rad(34),
	steerRate = 3.2,      -- 운전대가 목표 각을 따라가는 빠르기(1/s)
	steerAtSpeed = 0.26,  -- 최고 속도에서 쓸 수 있는 조향 각의 비율(빠를수록 덜 꺾인다)
	grip = 12,            -- 옆으로 미끄러지는 속도가 줄어드는 빠르기(1/s). 클수록 레일 위를 달리는 느낌
	handbrakeGrip = 1.6,  -- 핸드브레이크를 당긴 동안의 값. 작을수록 잘 미끄러진다
	handbrakeTurn = 1.7,  -- 핸드브레이크 중 회전 배율
	maxLatAccel = 11,     -- 타이어가 버티는 옆 가속(m/s², 약 1.1 g). 이보다 급하게는 돌지 못한다(언더스티어)
	wheelRadius = 0.345,
	health = 100,
}

function Driving.new(opts)
	local self = setmetatable({}, Driving)
	for k, v in Driving.DEFAULTS do self[k] = v end
	for k, v in (opts or {}) do self[k] = v end
	self.x = self.x or 0; self.z = self.z or 0; self.heading = self.heading or 0
	self.vx = 0; self.vz = 0                 -- 속도 벡터(차가 보는 방향과 다를 수 있다 = 미끄러짐)
	self.speed = 0                           -- 앞뒤 방향 속도(+ 앞, - 뒤)
	self.steer = 0                           -- 지금 조향 각(라디안, + 오른쪽)
	self.wheel = 0; self.roll = 0; self.pitch = 0; self.skid = 0
	self.braking = false; self.engine = true; self.state = "ok"; self.burnTimer = 0
	return self
end

-- input = {throttle = -1~1(앞·뒤), steer = -1~1(+ 오른쪽), handbrake = bool, boost = 1~1.6(추격 차량용: 멀어지면 더 빨라진다)}.
-- 돌려주는 값은 그 프레임의 사건 목록.
function Driving:update(dt: number, input)
	input = input or {}
	local ev = {}
	local thr = math.clamp(input.throttle or 0, -1, 1)
	local boost = math.clamp(input.boost or 1, 1, 1.6)
	local vmax = self.maxSpeed * boost
	if not self.engine or self.state == "wrecked" then thr = 0 end
	local fx, fz = math.sin(self.heading), math.cos(self.heading)
	local fwd = self.vx * fx + self.vz * fz
	local rx, rz = -fz, fx                                   -- 오른쪽
	local lat = self.vx * rx + self.vz * rz
	-- 조향: 빠를수록 덜 꺾인다
	local limit = self.maxSteer * (1 + (self.steerAtSpeed - 1) * math.clamp(math.abs(fwd) / self.maxSpeed, 0, 1))
	local want = math.clamp(input.steer or 0, -1, 1) * limit
	self.steer += (want - self.steer) * math.min(1, self.steerRate * dt)
	-- 앞뒤 힘
	local a = 0
	local before = fwd
	if thr > 0 then
		a = if fwd < -0.5 then self.brake * thr else self.accel * boost * thr * (1 - math.clamp(fwd / vmax, 0, 1) ^ 2)
	elseif thr < 0 then
		a = if fwd > 0.5 then self.brake * thr else self.accel * 0.7 * thr * (1 - math.clamp(-fwd / self.reverseMax, 0, 1) ^ 2)
	end
	if input.handbrake then a -= math.clamp(fwd, -1, 1) * self.brake * 0.6 end
	if thr == 0 or self.state == "smoking" then a -= math.clamp(fwd * 4, -1, 1) * self.drag * (if self.state == "smoking" then 3 else 1) end
	fwd = math.clamp(fwd + a * dt, -self.reverseMax, vmax * (if self.state == "smoking" then 0.6 else 1))
	if thr == 0 and math.abs(fwd) < 0.15 then fwd = 0 end
	self.braking = (thr < 0 and before > 0.5) or (thr > 0 and before < -0.5) or (input.handbrake == true and math.abs(before) > 0.5)
	-- 옆 미끄러짐: 접지가 좋으면 금방 사라지고, 핸드브레이크 중에는 남는다
	local grip = if input.handbrake then self.handbrakeGrip else self.grip
	lat *= math.exp(-grip * dt)
	-- 회전(자전거 모형). heading이 커지는 쪽이 왼쪽이라 오른쪽 조향은 heading을 줄인다
	local yaw = -fwd / self.wheelbase * math.tan(self.steer)
	local yawMax = self.maxLatAccel * boost / math.max(math.abs(fwd), 1)
	yaw = math.clamp(yaw, -yawMax, yawMax) * (if input.handbrake then self.handbrakeTurn else 1)
	local newHeading = self.heading + yaw * dt
	-- 방향이 바뀌어도 속도 벡터는 관성으로 남는다 -> 옆 속도가 생긴다
	local wx, wz = fx * fwd + rx * lat, fz * fwd + rz * lat
	self.heading = newHeading
	fx, fz = math.sin(self.heading), math.cos(self.heading); rx, rz = -fz, fx
	fwd = wx * fx + wz * fz; lat = wx * rx + wz * rz
	self.vx, self.vz = fx * fwd + rx * lat, fz * fwd + rz * lat
	self.x += self.vx * dt; self.z += self.vz * dt
	self.speed = fwd
	local wasSkid = self.skid > 0.35
	self.skid = math.clamp(math.abs(lat) / 5, 0, 1)
	if self.skid > 0.35 and not wasSkid then table.insert(ev, "skid_start") elseif self.skid <= 0.35 and wasSkid then table.insert(ev, "skid_stop") end
	-- 보이는 것: 바퀴 회전, 차체 기울기
	self.wheel += fwd * dt / self.wheelRadius
	local latAcc = fwd * yaw                                 -- 원심력
	self.roll += (math.clamp(latAcc * 0.009, -0.10, 0.10) - self.roll) * math.min(1, dt * 6)    -- + = 오른쪽으로 기움. 오른쪽으로 돌면 왼쪽(-)으로 기운다
	self.pitch += (math.clamp(-a * 0.006, -0.06, 0.06) - self.pitch) * math.min(1, dt * 6)      -- + = 앞이 들림
	if self.state == "burning" then
		self.burnTimer -= dt
		if self.burnTimer <= 0 then self.state = "wrecked"; self.engine = false; table.insert(ev, "explode") end
	end
	return ev
end

-- 무언가에 부딪혔다. (nx, nz) = 부딪힌 면의 바깥 방향(단위 벡터). 면으로 파고드는 속도를 없애고 조금 튕긴다.
-- 돌려주는 값: 부딪힌 속도(m/s). 이 값으로 소리 크기와 피해를 정한다.
function Driving:impact(nx: number, nz: number, bounce: number?)
	local into = -(self.vx * nx + self.vz * nz)
	if into <= 0 then return 0 end
	local k = 1 + (bounce or 0.25)
	self.vx += nx * into * k; self.vz += nz * into * k
	self.speed = self.vx * math.sin(self.heading) + self.vz * math.cos(self.heading)
	return into
end

-- 차가 받는 피해(충돌, 총격). 돌려주는 값: 상태가 바뀌었으면 그 사건 이름.
function Driving:damage(amount: number)
	if self.state == "wrecked" then return nil end
	self.health -= amount
	if self.health <= 0 and self.state ~= "burning" then
		self.state = "burning"; self.burnTimer = 4; self.engine = false       -- 불이 붙고 4초 뒤 터진다. 그 전에 내려야 한다
		return "on_fire"
	elseif self.health <= 35 and self.state == "ok" then
		self.state = "smoking"                                                 -- 연기가 나고 최고 속도가 60%로 줄어든다
		return "smoking"
	end
	return nil
end

-- 충돌 속도 -> 차 피해량, 탄 사람 피해량
function Driving.crashDamage(impactSpeed: number)
	if impactSpeed < 4 then return 0, 0 end
	return (impactSpeed - 4) * 2.2, math.max(0, impactSpeed - 14) * 2.5
end

return Driving
