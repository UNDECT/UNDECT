--!nonstrict
-- Roblox 쪽 연결 모듈. AnimSampler로 뽑은 자세를 모델의 뼈(Bone)나 Motor6D에 적용한다.
-- 주의: 이 파일만 Roblox API를 쓴다. Lune에서 테스트하지 못했으니 Studio에서 반드시 확인한다.
--
-- 전제 (에셋을 변환할 때 맞출 것)
--   부품 모델(로봇, 가면 NPC): 뼈를 manifest.json의 pivots 위치에 두고, 뼈 이름을 관절 이름과 같게 한다(hip_L, knee_L, waist ...). 뿌리 뼈는 "root".
--   뼈대 모델(사람, human_*):   뼈대를 그대로 가져오고 RigAnimator.new(model, manifest.joints)로 대응표를 넘긴다. 뼈 이름은 바꾸지 않는다.
--   뼈의 기준 방향은 아무래도 된다. 만들 때(=기본 자세일 때) 뼈가 모델 기준으로 어느 쪽을 보는지 읽어 두고 그만큼 보정한다.
--   에셋 좌표(Blender: 앞 -Y, 위 +Z)를 Roblox(앞 -Z, 위 +Y)로 가져올 때 축이 어떻게 바뀌었는지는 AXIS로 알려 준다.
--   기본값은 rbx = (-bx, bz, by). 가져온 결과가 다르면 이 표만 바꾼다.
local AnimSampler = require("./AnimSampler")
local RigSolver = require("./RigSolver")

local RigAnimator = {}
RigAnimator.__index = RigAnimator

-- P: Blender 축 -> Roblox 축. 행 = Roblox x, y, z.
RigAnimator.AXIS = {{-1, 0, 0}, {0, 0, 1}, {0, 1, 0}}
RigAnimator.STUDS_PER_METER = 3.143   -- 프로젝트의 사람 파이프라인과 같은 배율(키 1.75 m = 5.5스터드). 한 곳에서만 정한다

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

-- 기본 자세에서 관절이 모델 기준으로 보는 방향(회전만).
local function restRotation(joint: Instance, frame: CFrame): CFrame
	local world = if joint:IsA("Bone") then (joint :: Bone).WorldCFrame else (joint :: Motor6D).Part0.CFrame * (joint :: Motor6D).C0
	return frame:ToObjectSpace(world).Rotation
end

-- joints를 생략하면 이름이 관절 이름과 같은 Bone/Motor6D를 찾는다(부품 모델).
-- joints = manifest.json의 joints(사람)면 그 표에 적힌 뼈를 찾고 중립 자세 보정까지 한다.
-- 반드시 모델이 기본 자세일 때(애니메이션을 틀기 전에) 만든다. frame = 모델의 기준 좌표(기본값: 모델 피벗).
function RigAnimator.new(model: Instance, joints: any?, frame: CFrame?)
	local self = setmetatable({}, RigAnimator)
	local found = {}
	for _, d in model:GetDescendants() do
		if d:IsA("Bone") or d:IsA("Motor6D") then found[d.Name] = d end
	end
	local base = frame or (if model:IsA("Model") then (model :: Model):GetPivot() else CFrame.identity)
	self.joints = {}; self.rest = {}; self.neutral = {}; self.parentNeutral = {}; self.axis = {}; self.hands = {}
	if joints then
		local byBone = {}
		for name, j in joints do byBone[j.bone] = j end
		for name, j in joints do
			local inst = found[j.bone]
			if inst then
				self.joints[name] = inst; self.neutral[name] = j.neutral; self.axis[name] = j.axis
				self.parentNeutral[name] = if j.parent and byBone[j.parent] then byBone[j.parent].neutral else nil
			else
				warn("RigAnimator: 뼈를 찾지 못했다 " .. j.bone)
			end
		end
	else
		self.joints = found
	end
	for name, inst in self.joints do self.rest[name] = restRotation(inst, base) end
	-- 클립의 뿌리 이동(주저앉기, 눕기)은 골반 높이 0.95 m 기준이다. 키가 다른 모델은 골반 높이 비율만큼 줄이거나 늘린다
	self.rootScale = if joints and joints.root and joints.root.pos then joints.root.pos[3] / 0.95 else 1
	self.pose = {}; self.poseB = {}; self.mixed = {}
	self.time = 0; self.clip = nil; self.prev = nil; self.prevTime = 0; self.fade = 0; self.fadeLen = 0.2
	return self
end

-- 손 모양을 정한다(사람 뼈대만). side = "L" | "R", handPose = hand_poses.json의 한 항목(예: grip_pistol). nil이면 푼다.
function RigAnimator:setHand(side: string, handPose, weight: number?)
	self.hands[side] = if handPose then {pose = handPose, weight = weight or 1} else nil
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
	for side, h in self.hands do AnimSampler.hand(pose, side, h.pose, h.weight) end
	for name, joint in self.joints do
		local dofs = pose[name]
		local m = RigSolver.localRotation(name, dofs, self.parentNeutral[name], self.neutral[name], self.axis[name])
		if name == "root" and dofs then
			local k = self.rootScale
			m[10], m[11], m[12] = (dofs.x or 0) * k, (dofs.y or 0) * k, (dofs.z or 0) * k
		end
		-- 모델 기준 회전을 뼈 자신의 축으로 옮긴다: restᵀ · M · rest
		local rest = self.rest[name]
		joint.Transform = rest:Inverse() * convert(m, RigAnimator.STUDS_PER_METER) * rest
	end
	return AnimSampler.events(clip, t0, self.time)
end

return RigAnimator
