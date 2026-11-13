--!nonstrict
-- 애니메이션 클립(JSON을 표로 읽은 것)에서 자세를 뽑는다. Roblox API를 쓰지 않는 순수 모듈.
-- 클립 형식과 관절·자유도 규칙은 blender/anim.py 맨 위 주석을 본다.
local AnimSampler = {}

-- pose[joint][dof] = 값. out을 주면 그 표를 다시 쓴다(가비지 줄이기).
function AnimSampler.sample(clip, t: number, out)
	local pose = out or {}
	local d = clip.duration
	if clip.loop then t = t % d else t = math.clamp(t, 0, d) end
	for _, tr in clip.tracks do
		local ks = tr.keys
		local n = #ks
		local step = d / (n - 1)
		local i = math.min(n - 2, math.floor(t / step))
		local a, b = ks[i + 1], ks[i + 2]
		local u = (t - a[1]) / (b[1] - a[1])
		local j = pose[tr.joint]
		if not j then j = {}; pose[tr.joint] = j end
		j[tr.dof] = a[2] + (b[2] - a[2]) * u
	end
	return pose
end

-- 두 자세를 섞는다. w = 0이면 a, 1이면 b. 한쪽에만 있는 값은 0에서 섞는다.
function AnimSampler.blend(a, b, w: number, out)
	local pose = out or {}
	for joint, dofs in a do
		local o = pose[joint]; if not o then o = {}; pose[joint] = o end
		local bj = b[joint]
		for dof, v in dofs do o[dof] = v + (((bj and bj[dof]) or 0) - v) * w end
	end
	for joint, dofs in b do
		local o = pose[joint]; if not o then o = {}; pose[joint] = o end
		local aj = a[joint]
		for dof, v in dofs do
			if not (aj and aj[dof] ~= nil) then o[dof] = v * w end
		end
	end
	return pose
end

-- (t0, t1] 구간에 지나간 이벤트 이름을 돌려준다. 반복 클립은 끝을 넘어가는 경우도 처리한다.
function AnimSampler.events(clip, t0: number, t1: number)
	local hits = {}
	if #clip.events == 0 or t1 <= t0 then return hits end
	local d = clip.duration
	if not clip.loop then
		for _, e in clip.events do
			if e[1] > t0 and e[1] <= t1 or (t0 <= 0 and e[1] == 0 and t1 > 0) then table.insert(hits, e[2]) end
		end
		return hits
	end
	local k0 = math.floor(t0 / d)
	local k1 = math.floor(t1 / d)
	for k = k0, k1 do
		for _, e in clip.events do
			local te = k * d + e[1]
			if te > t0 and te <= t1 then table.insert(hits, e[2]) end
		end
	end
	return hits
end

-- 이동 속도에 맞춰 걷기 주기를 진행시킨다(발 미끄러짐 방지). 돌려주는 값은 새 시각.
function AnimSampler.advanceBySpeed(clip, t: number, dt: number, moveSpeed: number)
	if clip.speed and clip.speed > 0 then return t + dt * (moveSpeed / clip.speed) end
	return t + dt
end

-- 손 모양(hand_poses.json의 한 항목)을 자세에 더한다. side = "L" 또는 "R". 손가락 관절 이름은 index_R_1 같은 꼴이다.
-- weight로 두 손 모양 사이를 섞을 수 있다(0 = 편 손, 1 = 그 모양).
function AnimSampler.hand(pose, side: string, handPose, weight: number?)
	local w = weight or 1
	for finger, curls in handPose do
		for k, deg in curls do
			local name = finger .. "_" .. side .. "_" .. k
			local d = pose[name]
			if not d then d = {}; pose[name] = d end
			d.curl = deg * w
		end
	end
	return pose
end

return AnimSampler
