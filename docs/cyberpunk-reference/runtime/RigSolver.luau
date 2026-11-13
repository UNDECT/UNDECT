--!nonstrict
-- 자세(관절 각도) -> 부품별 변환 행렬. Roblox API를 쓰지 않는 순수 모듈.
-- 좌표는 에셋 원본 그대로다: 단위 m, 앞 = -Y, 위 = +Z (Blender). Roblox 좌표로 바꾸는 일은 RigAnimator가 한다.
-- 행렬은 {r11,r12,r13, r21,r22,r23, r31,r32,r33, tx,ty,tz} (회전 3x3은 행 우선).
local RigSolver = {}

local rad = math.rad

local function mul(a, b)
	return {
		a[1]*b[1] + a[2]*b[4] + a[3]*b[7], a[1]*b[2] + a[2]*b[5] + a[3]*b[8], a[1]*b[3] + a[2]*b[6] + a[3]*b[9],
		a[4]*b[1] + a[5]*b[4] + a[6]*b[7], a[4]*b[2] + a[5]*b[5] + a[6]*b[8], a[4]*b[3] + a[5]*b[6] + a[6]*b[9],
		a[7]*b[1] + a[8]*b[4] + a[9]*b[7], a[7]*b[2] + a[8]*b[5] + a[9]*b[8], a[7]*b[3] + a[8]*b[6] + a[9]*b[9],
		a[1]*b[10] + a[2]*b[11] + a[3]*b[12] + a[10],
		a[4]*b[10] + a[5]*b[11] + a[6]*b[12] + a[11],
		a[7]*b[10] + a[8]*b[11] + a[9]*b[12] + a[12],
	}
end
RigSolver.mul = mul

local function rotX(deg) local c, s = math.cos(rad(deg)), math.sin(rad(deg)); return {1,0,0, 0,c,-s, 0,s,c, 0,0,0} end
local function rotY(deg) local c, s = math.cos(rad(deg)), math.sin(rad(deg)); return {c,0,s, 0,1,0, -s,0,c, 0,0,0} end
local function rotZ(deg) local c, s = math.cos(rad(deg)), math.sin(rad(deg)); return {c,-s,0, s,c,0, 0,0,1, 0,0,0} end

-- 한 관절의 회전(이동 없음). 규칙은 anim.py와 같다: Rz(yaw) · Rx(pitch - flex - dorsi ± bend) · Ry(roll - abduct·side)
function RigSolver.jointRotation(joint: string, dofs)
	if not dofs then return {1,0,0, 0,1,0, 0,0,1, 0,0,0} end
	local side = if string.sub(joint, -2) == "_L" then 1 else -1
	local rz = dofs.yaw or 0
	local rx = (dofs.pitch or 0) - (dofs.flex or 0) - (dofs.dorsi or 0)
	rx += (dofs.bend or 0) * (if string.sub(joint, 1, 4) == "knee" then 1 else -1)
	local ry = (dofs.roll or 0) - (dofs.abduct or 0) * side
	return mul(mul(rotZ(rz), rotX(rx)), rotY(ry))
end

-- 관절 위치 p를 중심으로 회전: T(p) · R · T(-p)
local function about(R, p)
	local x, y, z = p[1], p[2], p[3]
	return {R[1],R[2],R[3], R[4],R[5],R[6], R[7],R[8],R[9],
		x - (R[1]*x + R[2]*y + R[3]*z), y - (R[4]*x + R[5]*y + R[6]*z), z - (R[7]*x + R[8]*y + R[9]*z)}
end

-- manifest.json의 pivots로 뼈대를 만든다. 부모가 먼저 오도록 정렬한다.
function RigSolver.fromManifest(manifest, rootPart: string?, rootHeight: number?)
	local rig = {root = rootPart or "pelvis", rootPivot = {0, 0, rootHeight or 0.95}, joints = {}}
	local pending = {}
	for name, pv in manifest.pivots do
		table.insert(pending, {name = name, parent = pv.parent, child = pv.child, pos = pv.pos})
	end
	table.sort(pending, function(a, b) return a.name < b.name end)
	local have = {[rig.root] = true}
	local progressed = true
	while #pending > 0 and progressed do
		progressed = false
		for i = #pending, 1, -1 do
			local j = pending[i]
			if have[j.parent] then
				table.insert(rig.joints, j); have[j.child] = true
				table.remove(pending, i); progressed = true
			end
		end
	end
	return rig
end

-- 부품 이름 -> 행렬. 관절에 속하지 않은 부품은 뿌리(root) 행렬을 쓴다.
function RigSolver.solve(rig, pose)
	local r = pose.root or {}
	local R = about(RigSolver.jointRotation("root", r), rig.rootPivot)
	R[10] += r.x or 0; R[11] += r.y or 0; R[12] += r.z or 0
	local D = {[rig.root] = R}
	for _, j in rig.joints do
		D[j.child] = mul(D[j.parent], about(RigSolver.jointRotation(j.name, pose[j.name]), j.pos))
	end
	return D
end

return RigSolver
