--!nonstrict
-- Roblox 쪽 연결 모듈. AnimSampler로 뽑은 자세를 모델의 뼈(Bone)나 Motor6D에 적용한다.
-- 주의: 이 파일만 Roblox API를 쓴다. Lune에서 테스트하지 못했으니 Studio에서 반드시 확인한다.
--
-- 전제 (에셋을 변환할 때 맞출 것)
--   1. 뼈는 manifest.json의 pivots 위치에 둔다. 뼈의 기준 방향은 회전 없이 월드 축과 나란히 둔다.
--   2. 뼈 이름은 관절 이름과 같다(hip_L, knee_L, waist, neck ...). 뿌리 뼈 이름은 "root".
--   3. 에셋 좌표(Blender: 앞 -Y, 위 +Z)를 Roblox(앞 -Z, 위 +Y)로 가져올 때 축이 어떻게 바뀌었는지 AXIS로 알려 준다.
--      기본값은 rbx = (-bx, bz, by). 가져온 결과가 다르면 이 표만 바꾼다.
local AnimSampler = require("./AnimSampler")
local RigSolver = require("./RigSolver")

local RigAnimator = {}
RigAnimator.__index = RigAnimator

-- P: Blender 축 -> Roblox 축. 행 = Roblox x, y, z.
RigAnimator.AXIS = {{-1, 0, 0}, {0, 0, 1}, {0, 1, 0}}
RigAnimator.STUDS_PER_METER = 1 / 0.28

local function convert(m, scale: number)
	-- R_rbx = P · R_b · Pᵀ, t_rbx = P · t_b · scale
	local P = RigAnimator.AXIS
	local Rb = {{m[1], m[2], m[3]}, {m[4], m[5], m[6]}, {m[7], m[8], m[9]}}
	local R = {}
	for i = 1, 3 do
		R[i] = {}
		for j = 1, 3 do
			local s = 0
			for a = 1, 3 do for b = 1, 3 do s += P[i][a] * Rb[a][b] * P[j][b] end end
			R[i][j] = s
		end
	end
	local t = {}
	for i = 1, 3 do t[i] = (P[i][1] * m[10] + P[i][2] * m[11] + P[i][3] * m[12]) * scale end
	return CFrame.new(t[1], t[2], t[3], R[1][1], R[1][2], R[1][3], R[2][1], R[2][2], R[2][3], R[3][1], R[3][2], R[3][3])
end

-- model 안에서 이름이 관절 이름과 같은 Bone 또는 Motor6D를 찾는다.
function RigAnimator.new(model: Instance)
	local self = setmetatable({}, RigAnimator)
	self.joints = {}
	for _, d in model:GetDescendants() do
		if d:IsA("Bone") or d:IsA("Motor6D") then self.joints[d.Name] = d end
	end
	self.pose = {}; self.poseB = {}; self.mixed = {}
	self.time = 0; self.clip = nil; self.prev = nil; self.prevTime = 0; self.fade = 0; self.fadeLen = 0.2
	return self
end

-- 클립을 바꾼다. fade초 동안 이전 동작과 섞는다.
function RigAnimator:play(clip, fade: number?)
	if self.clip == clip then return end
	self.prev, self.prevTime = self.clip, self.time
	self.clip, self.time = clip, 0
	self.fadeLen = fade or 0.2; self.fade = if self.prev then self.fadeLen else 0
end

-- 매 프레임 호출. moveSpeed를 주면 걷기 주기를 실제 이동 속도에 맞춘다. 지나간 이벤트 이름을 돌려준다.
function RigAnimator:update(dt: number, moveSpeed: number?)
	local clip = self.clip
	if not clip then return {} end
	local t0 = self.time
	self.time = if moveSpeed then AnimSampler.advanceBySpeed(clip, t0, dt, moveSpeed) else t0 + dt
	local pose = AnimSampler.sample(clip, self.time, self.pose)
	if self.fade > 0 and self.prev then
		self.prevTime += dt; self.fade = math.max(0, self.fade - dt)
		local old = AnimSampler.sample(self.prev, self.prevTime, self.poseB)
		table.clear(self.mixed)
		pose = AnimSampler.blend(old, pose, 1 - self.fade / self.fadeLen, self.mixed)
	end
	for name, joint in self.joints do
		local dofs = pose[name]
		local m = RigSolver.jointRotation(name, dofs)
		if name == "root" and dofs then m[10], m[11], m[12] = dofs.x or 0, dofs.y or 0, dofs.z or 0 end
		joint.Transform = convert(m, RigAnimator.STUDS_PER_METER)
	end
	return AnimSampler.events(clip, t0, self.time)
end

return RigAnimator
