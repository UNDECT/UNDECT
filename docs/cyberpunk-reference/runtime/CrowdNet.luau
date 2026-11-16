--!nonstrict
-- 서버의 군중·차 상태를 클라이언트에 보내는 꾸러미. Roblox API를 쓰지 않는 순수 모듈(Luau의 buffer만 쓴다).
-- 서버: 플레이어마다 pack(주변 것들만)해서 초당 10번쯤 UnreliableRemoteEvent로 보낸다. 한 개에 10바이트다.
-- 클라이언트: unpack한 것을 Interp에 넣고, 조금 늦은 시각(0.15초 전)을 뽑아 부드럽게 보인다. 뼈 동작은 클라이언트가 anim과 animTime으로 직접 튼다.
local CrowdNet = {}

local POS = 0.02            -- 위치 단위(m). 꾸러미 중심에서 ±655 m까지
local TIME = 0.05           -- animTime 단위(초). 12.75초까지
local HEADER = 10           -- f32 중심 x, f32 중심 z, u16 개수
local EACH = 10             -- u16 id, i16 x, i16 z, u8 방향, u8 동작 번호, u8 animTime, u8 표시

-- 동작 이름 <-> 번호. 서버와 클라이언트가 같은 목록(예: 클립 목록의 이름을 정렬한 것)을 쓴다.
function CrowdNet.animTable(names)
	local ids = {}
	for i, n in names do ids[n] = i end
	return {ids = ids, names = names}
end

-- items = {{id, x, z, heading, anim, animTime, state, gone}, ...} (Crowd.agents나 Traffic.vehicles를 그대로 넣어도 된다)
-- focus에서 radius 안의 것만 담는다. 최대 limit개(가까운 것부터). buffer를 돌려준다.
function CrowdNet.pack(items, focus, radius: number, anims, limit: number?)
	local near = {}
	for _, it in items do
		if not it.gone then
			local d = (it.x - focus.x) ^ 2 + (it.z - focus.z) ^ 2
			if d <= radius * radius then table.insert(near, {it, d}) end
		end
	end
	table.sort(near, function(a, b) return a[2] < b[2] end)
	local n = math.min(#near, limit or 200)
	local buf = buffer.create(HEADER + n * EACH)
	buffer.writef32(buf, 0, focus.x); buffer.writef32(buf, 4, focus.z); buffer.writeu16(buf, 8, n)
	for i = 1, n do
		local it = near[i][1]
		local o = HEADER + (i - 1) * EACH
		buffer.writeu16(buf, o, it.id % 65536)
		buffer.writei16(buf, o + 2, math.clamp(math.round((it.x - focus.x) / POS), -32768, 32767))
		buffer.writei16(buf, o + 4, math.clamp(math.round((it.z - focus.z) / POS), -32768, 32767))
		buffer.writeu8(buf, o + 6, math.round(((it.heading or 0) % (2 * math.pi)) / (2 * math.pi) * 256) % 256)
		buffer.writeu8(buf, o + 7, anims.ids[it.anim] or 0)
		buffer.writeu8(buf, o + 8, math.clamp(math.round((it.animTime or 0) / TIME), 0, 255))
		buffer.writeu8(buf, o + 9, if it.state == "dead" then 1 else 0)
	end
	return buf
end

function CrowdNet.unpack(buf, anims)
	local cx, cz, n = buffer.readf32(buf, 0), buffer.readf32(buf, 4), buffer.readu16(buf, 8)
	local out = {}
	for i = 1, n do
		local o = HEADER + (i - 1) * EACH
		table.insert(out, {
			id = buffer.readu16(buf, o), x = cx + buffer.readi16(buf, o + 2) * POS, z = cz + buffer.readi16(buf, o + 4) * POS,
			heading = buffer.readu8(buf, o + 6) / 256 * 2 * math.pi, anim = anims.names[buffer.readu8(buf, o + 7)],
			animTime = buffer.readu8(buf, o + 8) * TIME, dead = buffer.readu8(buf, o + 9) == 1,
		})
	end
	return out
end

-- 클라이언트 쪽 보간. push(받은 목록, 받은 시각)로 넣고 sample(지금 시각 - delay)로 뽑는다.
local Interp = {}
Interp.__index = Interp
CrowdNet.Interp = Interp

function Interp.new(delay: number?)
	return setmetatable({delay = delay or 0.15, tracks = {}, last = 0}, Interp)
end

function Interp:push(list, time: number)
	self.last = time
	for _, it in list do
		local tr = self.tracks[it.id]
		if not tr then tr = {}; self.tracks[it.id] = tr end
		tr.a, tr.ta = tr.b, tr.tb
		tr.b, tr.tb = it, time
		tr.seen = time
	end
end

-- 돌려주는 값: id -> {x, z, heading, anim, animTime, dead}. 0.6초 넘게 소식이 없는 것은 뺀다(멀어졌거나 치워졌다).
function Interp:sample(now: number)
	local t = now - self.delay
	local out = {}
	for id, tr in self.tracks do
		if self.last - tr.seen > 0.6 then
			self.tracks[id] = nil
		elseif tr.a and tr.tb > tr.ta then
			local u = math.clamp((t - tr.ta) / (tr.tb - tr.ta), 0, 1.25)          -- 조금은 앞으로 내다본다
			local dh = (tr.b.heading - tr.a.heading + math.pi) % (2 * math.pi) - math.pi
			local same = tr.a.anim == tr.b.anim
			out[id] = {x = tr.a.x + (tr.b.x - tr.a.x) * u, z = tr.a.z + (tr.b.z - tr.a.z) * u, heading = tr.a.heading + dh * math.min(u, 1),
				anim = tr.b.anim, animTime = if same then tr.a.animTime + (tr.b.animTime - tr.a.animTime) * math.min(u, 1) + math.max(0, t - tr.tb) else math.max(0, tr.b.animTime + (t - tr.tb)), dead = tr.b.dead}
		else
			out[id] = {x = tr.b.x, z = tr.b.z, heading = tr.b.heading, anim = tr.b.anim, animTime = tr.b.animTime, dead = tr.b.dead}
		end
	end
	return out
end

return CrowdNet
