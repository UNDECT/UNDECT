--!nonstrict
-- 손 레이저(연속 빔 무기) 발사 로직. Roblox API를 쓰지 않는 순수 모듈.
-- 게임 쪽이 매 프레임 "방아쇠를 누르고 있는가"와 "빔이 지나는 길에 맞은 것들"을 넘기면,
-- 상태(충전·발사·과열), 빔의 세기와 길이, 누구에게 얼마의 피해를 줄지, 지금 일어난 이벤트를 돌려준다.
--   idle -> charging(충전) -> firing(발사, 열이 오른다) -> overheated(과열, 잠김) -> idle
local Laser = {}
Laser.__index = Laser

Laser.DEFAULTS = {
	dps = 240,           -- 초당 피해(최대 세기일 때)
	range = 60,          -- 사거리(m)
	chargeTime = 0.35,   -- 누르고 빔이 나오기까지
	rampTime = 0.6,      -- 빔이 최대 세기에 이르는 시간. 처음에는 startPower에서 시작한다
	startPower = 0.5,
	heatPerSec = 0.30,   -- 쏘는 동안 초당 오르는 열(1이면 과열). 기본값이면 약 3.3초 연속 발사
	coolPerSec = 0.25,   -- 쏘지 않을 때 초당 식는 열
	overheatLock = 2.0,  -- 과열되면 이 시간 동안 못 쏜다(방열판이 열린다)
	pierce = 1,          -- 첫 대상을 뚫고 더 맞히는 수
	pierceFalloff = 0.5, -- 뚫을 때마다 피해가 이만큼 곱해진다
	falloffStart = 30,   -- 이 거리부터 피해가 줄어 range에서 falloffEnd배가 된다
	falloffEnd = 0.5,
}

function Laser.new(opts)
	local self = setmetatable({}, Laser)
	for k, v in Laser.DEFAULTS do self[k] = v end
	for k, v in (opts or {}) do self[k] = v end
	self.state = "idle"; self.timer = 0; self.heat = 0; self.power = 0; self.beamTime = 0
	return self
end

local function falloff(self, d: number): number
	if d <= self.falloffStart then return 1 end
	local u = math.clamp((d - self.falloffStart) / math.max(1e-6, self.range - self.falloffStart), 0, 1)
	return 1 + (self.falloffEnd - 1) * u
end

-- hits = 빔 길 위에서 맞은 것들, 가까운 순서: {{target = 아무 값, distance = m, solid = true면 벽(빔이 멈춘다), zone | part = 부위}, ...}
-- 돌려주는 값: {state, beam, power(0~1), heat(0~1), length, damage = {{target, amount, zone, part, kind = "laser"}}, events = {...}, endSolid}
function Laser:update(dt: number, held: boolean, hits)
	local out = {state = self.state, beam = false, power = 0, heat = self.heat, length = 0, damage = {}, events = {}, endSolid = false}
	local ev = out.events
	if self.state == "overheated" then
		self.timer -= dt
		self.heat = math.max(0, self.heat - dt / self.overheatLock)
		if self.timer <= 0 then self.state = "idle"; self.heat = 0; table.insert(ev, "ready") end
	elseif self.state == "idle" then
		self.heat = math.max(0, self.heat - self.coolPerSec * dt)
		if held then self.state = "charging"; self.timer = self.chargeTime; table.insert(ev, "charge") end
	elseif self.state == "charging" then
		self.heat = math.max(0, self.heat - self.coolPerSec * dt * 0.5)
		if not held then
			self.state = "idle"; table.insert(ev, "cancel")
		else
			self.timer -= dt
			if self.timer <= 0 then self.state = "firing"; self.beamTime = 0; table.insert(ev, "beam_on") end
		end
	elseif self.state == "firing" then
		if not held then
			self.state = "idle"; table.insert(ev, "beam_off")
		else
			self.beamTime += dt
			self.heat += self.heatPerSec * dt
			self.power = self.startPower + (1 - self.startPower) * math.clamp(self.beamTime / self.rampTime, 0, 1)
			out.beam = true; out.power = self.power
			local length, left, mult = self.range, self.pierce + 1, 1
			for _, h in (hits or {}) do
				if h.distance > self.range then break end
				if h.solid then length = h.distance; out.endSolid = true; break end
				table.insert(out.damage, {target = h.target, amount = self.dps * self.power * mult * falloff(self, h.distance) * dt, zone = h.zone, part = h.part, kind = "laser", distance = h.distance})
				left -= 1; mult *= self.pierceFalloff
				if left <= 0 then length = h.distance; break end
			end
			out.length = length
			if self.heat >= 1 then
				self.heat = 1; self.state = "overheated"; self.timer = self.overheatLock
				table.insert(ev, "beam_off"); table.insert(ev, "overheat")
			end
		end
	end
	out.state = self.state; out.heat = self.heat
	return out
end

-- 지금 틀어야 할 클립 이름(사이버웨어 팔, 1인칭). 상태가 바뀐 프레임에만 쓰면 된다.
function Laser.clips(state: string)
	if state == "charging" then return "laser_deploy", "fp_laser_raise" end
	if state == "firing" then return "laser_fire", "fp_laser_fire" end
	if state == "overheated" then return "laser_overheat", "fp_laser_overheat" end
	return "laser_retract", "fp_laser_lower"
end

return Laser
