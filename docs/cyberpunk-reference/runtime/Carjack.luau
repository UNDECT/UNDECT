--!nonstrict
-- 차를 훔쳐 타기. Roblox API를 쓰지 않는 순수 모듈.
-- 차의 상태(세워 둔 차, 달리는 차, 잠김, 경보기)에 따라 쓸 수 있는 방법을 알려 주고,
-- 고른 방법을 단계별로 진행시키며 그때그때 틀 동작과 일어난 일(문 열림, 유리 깨짐, 경보, 운전자 끌려 나옴)을 돌려준다.
local Carjack = {}
Carjack.__index = Carjack

-- 방법별 단계. 단계 = {이름, 걸리는 시간, 사람 동작, 사건}. noise = 소리가 퍼지는 반경(m), crime = 수배에 넘길 범죄 이름
Carjack.METHODS = {
	enter = {noise = 0, crime = nil, steps = {
		{"open", 0.45, "car_door_open", "door_open"}, {"sit", 0.9, "car_enter", "seated"}}},
	hack = {noise = 0, crime = "vehicle_theft", steps = {      -- 사이버덱으로 잠금을 푼다: 조용하고 경보가 울리지 않는다
		{"hack", 2.2, "car_hack", "unlocked"}, {"open", 0.45, "car_door_open", "door_open"}, {"sit", 0.9, "car_enter", "seated"}}},
	smash = {noise = 16, crime = "vehicle_theft", steps = {     -- 창을 깨고 문을 연다
		{"smash", 0.7, "car_smash_window", "glass_break"}, {"open", 0.6, "car_door_open", "door_open"}, {"sit", 0.9, "car_enter", "seated"}}},
	pull_driver = {noise = 14, crime = "carjacking", steps = {  -- 운전자를 끌어낸다
		{"open", 0.4, "car_door_open", "door_open"}, {"pull", 1.1, "carjack_pull", "driver_out"}, {"sit", 0.9, "car_enter", "seated"}}},
	threaten = {noise = 8, crime = "carjacking", steps = {      -- 총을 겨눠 내리게 한다
		{"threaten", 1.3, "aim_pistol", "driver_out"}, {"open", 0.3, "car_door_open", "door_open"}, {"sit", 0.9, "car_enter", "seated"}}},
}
Carjack.HOTWIRE = {"hotwire", 3.2, "car_hotwire", "engine_on"}   -- 열쇠 없이 시동 걸기. 해킹으로 열었거나 운전자를 끌어냈으면 건너뛴다
Carjack.ALARM_TIME = 25
Carjack.ALARM_RADIUS = 32

-- 차 한 대의 도난 관련 상태. kind: "parked"(세워 둔 차) | "traffic"(NPC가 모는 차) | "security"(순찰차)
function Carjack.vehicle(opts)
	opts = opts or {}
	local kind = opts.kind or "parked"
	return {kind = kind, locked = if opts.locked ~= nil then opts.locked else kind == "parked", alarm = if opts.alarm ~= nil then opts.alarm else kind ~= "traffic",
		occupied = kind ~= "parked", engine = kind ~= "parked", windowBroken = false, alarmTimer = 0, stolen = false, owner = opts.owner, speed = opts.speed or 0}
end

-- 지금 쓸 수 있는 방법들. player = {hasDeck = 사이버덱 있음, armed = 총을 들고 있음}. 달리는 차는 느릴 때(3 m/s 이하)만 된다.
function Carjack.options(v, player)
	player = player or {}
	local out = {}
	if v.stolen and not v.occupied then return {"enter"} end
	if v.occupied then
		if math.abs(v.speed or 0) <= 3 then
			table.insert(out, "pull_driver")
			if player.armed then table.insert(out, "threaten") end
		end
		return out
	end
	if not v.locked or v.windowBroken then table.insert(out, "enter"); return out end
	if player.hasDeck then table.insert(out, "hack") end
	table.insert(out, "smash")
	return out
end

-- 시도를 시작한다. 쓸 수 없는 방법이면 nil.
function Carjack.begin(v, method: string, player)
	local ok = false
	for _, m in Carjack.options(v, player) do ok = ok or m == method end
	if not ok then return nil end
	local def = Carjack.METHODS[method]
	local steps = table.clone(def.steps)
	-- 세워 둔 차를 창을 깨고 탔으면 시동을 따야 한다
	if method == "smash" or (method == "enter" and v.windowBroken and not v.stolen) then table.insert(steps, Carjack.HOTWIRE) end
	-- 잠기지 않은 남의 차를 그냥 타고 가는 것도 절도다(조용하니 본 사람이 있을 때만 문제가 된다)
	local crime = def.crime
	if method == "enter" and not v.stolen and v.kind ~= "player" then crime = "vehicle_theft" end
	return setmetatable({vehicle = v, method = method, steps = steps, index = 1, time = 0, done = false, canceled = false, noise = def.noise, crime = crime, reported = false}, Carjack)
end

-- 지금 틀 동작 이름과 그 단계의 진행률(0~1).
function Carjack:current()
	local st = self.steps[self.index]
	if not st then return nil, 1 end
	return st[3], math.clamp(self.time / st[2], 0, 1)
end

-- 매 프레임. interrupted = 맞았거나, 차가 떠났거나, 플레이어가 취소했다.
-- 돌려주는 값: 사건 목록. 각 사건은 {type = 이름, ...}
--   door_open, unlocked, glass_break, alarm_on, driver_out(reaction = 운전자 반응), seated, engine_on, done, canceled, crime(crime = 이름, noise = 반경)
function Carjack:update(dt: number, interrupted: boolean?, roll: number?)
	local ev = {}
	if self.done or self.canceled then return ev end
	local v = self.vehicle
	if interrupted then
		self.canceled = true; table.insert(ev, {type = "canceled", step = self.steps[self.index][1]})
		return ev
	end
	self.time += dt
	while not self.done do
		local st = self.steps[self.index]
		if self.time < st[2] then break end
		self.time -= st[2]; self.index += 1
		local name = st[4]
		if name == "glass_break" then
			v.windowBroken = true; v.locked = false
			table.insert(ev, {type = "glass_break"})
			if v.alarm then v.alarmTimer = Carjack.ALARM_TIME; table.insert(ev, {type = "alarm_on", radius = Carjack.ALARM_RADIUS, time = Carjack.ALARM_TIME}) end
		elseif name == "unlocked" then
			v.locked = false; table.insert(ev, {type = "unlocked"})
		elseif name == "driver_out" then
			v.occupied = false
			table.insert(ev, {type = "driver_out", reaction = Carjack.driverReaction(v, self.method, roll or 0.5), owner = v.owner})
		elseif name == "seated" then
			v.stolen = true; v.kind = "player"
			table.insert(ev, {type = "seated"})
		elseif name == "engine_on" then
			v.engine = true; table.insert(ev, {type = "engine_on"})
		else
			table.insert(ev, {type = name})
		end
		-- 범죄는 남이 볼 수 있게 된 순간(유리가 깨지거나 운전자가 끌려 나오거나, 조용한 방법은 자리에 앉는 순간) 한 번만 알린다
		if self.crime and not self.reported and (name == "glass_break" or name == "driver_out" or name == "seated") then
			self.reported = true; table.insert(ev, {type = "crime", crime = self.crime, noise = self.noise})
		end
		if self.index > #self.steps then
			self.done = true
			if not v.engine then v.engine = true end          -- 해킹·끌어내기·열쇠가 있던 차는 바로 시동이 걸린다
			table.insert(ev, {type = "done"})
		end
	end
	return ev
end

-- 끌려 나오거나 위협받은 운전자의 반응. roll = 0~1 난수.
--   flee(도망치고 나중에 신고) / freeze(손 들고 얼어붙음) / fight(덤빈다) / hostile(순찰차: 바로 적대)
function Carjack.driverReaction(v, method: string, roll: number): string
	if v.kind == "security" then return "hostile" end
	if method == "threaten" then return if roll < 0.75 then "flee" elseif roll < 0.97 then "freeze" else "fight" end
	return if roll < 0.62 then "flee" elseif roll < 0.82 then "freeze" else "fight"
end

-- 경보기: 매 프레임 줄어든다. 울리는 동안 true.
function Carjack.alarm(v, dt: number): boolean
	if v.alarmTimer > 0 then v.alarmTimer = math.max(0, v.alarmTimer - dt); return v.alarmTimer > 0 end
	return false
end

-- 달리는 NPC 차가 플레이어를 보고 하는 일. threat = "aimed"(총을 겨눔) | "shot"(총에 맞음) | "rammed"(들이받힘) | "blocked"(길을 막음)
--   stop(멈추고 손 든다) / speed_off(급히 달아난다) / bail(차를 버리고 도망) / honk(경적) / reverse(뒤로 뺀다)
function Carjack.trafficReaction(threat: string, roll: number): string
	if threat == "aimed" then return if roll < 0.55 then "stop" elseif roll < 0.9 then "speed_off" else "bail" end
	if threat == "shot" then return if roll < 0.7 then "speed_off" else "bail" end
	if threat == "rammed" then return if roll < 0.5 then "speed_off" elseif roll < 0.8 then "bail" else "honk" end
	return if roll < 0.7 then "honk" else "reverse"
end

return Carjack
