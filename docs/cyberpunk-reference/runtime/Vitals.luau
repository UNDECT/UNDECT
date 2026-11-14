--!nonstrict
-- NPC의 체력, 피격, 사망. Roblox API를 쓰지 않는 순수 모듈.
-- 무엇에 어디를 어느 방향에서 맞았는지 받아서: 피해량, 반응 동작(피격·비틀거림·쓰러짐·사망 클립), 내야 할 이펙트 목록을 돌려준다.
-- 수위(Vitals.GORE)는 한 곳에서 조절한다. 지금은 가장 높게(3) 두고 나중에 낮춘다.
--   0 = 피 없음. 죽으면 주저앉은 뒤 사라진다(Kids 설정)
--   1 = 맞은 곳 번쩍임과 먼지. 시체는 잠깐 남았다가 사라진다
--   2 = 피 튐, 바닥 핏자국. 시체가 남는다
--   3 = 2에 더해 상처 자국, 뒤쪽 벽 핏자국, 커지는 피 웅덩이, 화상·그을음, 부상당해 기어가는 상태
local Vitals = {}

Vitals.GORE = 3

-- 부위별 피해 배수
Vitals.ZONE = {head = 3.0, neck = 2.2, torso = 1.0, arm = 0.6, leg = 0.7}

-- 피해 종류. stagger = 비틀거리게 하는 힘(0~1), knock = 밀려나는 거리(m), fear = 주변 사람이 놀라는 반경(m)
Vitals.TYPE = {
	bullet = {stagger = 0.35, knock = 0.15, fear = 25},
	shotgun = {stagger = 0.9, knock = 0.8, fear = 30},
	blade = {stagger = 0.45, knock = 0.1, fear = 10},
	blunt = {stagger = 0.8, knock = 0.5, fear = 10},
	laser = {stagger = 0.15, knock = 0.0, fear = 18, burn = true},
	fire = {stagger = 0.2, knock = 0.0, fear = 15, burn = true},
	electric = {stagger = 1.0, knock = 0.0, fear = 12},
	explosive = {stagger = 1.0, knock = 2.0, fear = 45},
	fall = {stagger = 1.0, knock = 0.0, fear = 0},
}

-- 뼈·부품 이름 -> 부위. 사람(human_*), 가면 NPC, 로봇의 이름을 다 받는다.
function Vitals.zoneOf(name: string): string
	local n = string.lower(name)
	if string.find(n, "head", 1, true) or string.find(n, "eye", 1, true) or string.find(n, "visor", 1, true) then return "head" end
	if string.find(n, "neck", 1, true) then return "neck" end
	if string.find(n, "arm", 1, true) or string.find(n, "hand", 1, true) or string.find(n, "clavicle", 1, true) or string.find(n, "finger", 1, true)
		or string.find(n, "index", 1, true) or string.find(n, "middle", 1, true) or string.find(n, "ring", 1, true) or string.find(n, "pinky", 1, true) or string.find(n, "thumb", 1, true) then return "arm" end
	if string.find(n, "thigh", 1, true) or string.find(n, "calf", 1, true) or string.find(n, "shin", 1, true) or string.find(n, "foot", 1, true) or string.find(n, "ball", 1, true) or string.find(n, "leg", 1, true) then return "leg" end
	return "torso"
end

-- opts: health(기본 100), armor(0~1, 피해를 줄이는 비율), seated(앉아 있음)
function Vitals.new(opts)
	opts = opts or {}
	local h = opts.health or 100
	return {health = h, maxHealth = h, armor = opts.armor or 0, state = "alive", seated = opts.seated or false,
		bleed = 0, burn = 0, downTimer = 0, wounds = {}, cause = nil, killer = nil}
end

-- 맞은 방향: 공격이 날아온 진행 방향(dirX, dirZ)과 맞는 사람이 보는 방향(facing, 라디안, atan2(dx, dz))으로
-- "앞에서 맞음"(front) / "뒤에서"(back) / "왼쪽에서"(left) / "오른쪽에서"(right)를 가린다.
function Vitals.side(dirX: number, dirZ: number, facing: number): string
	local fx, fz = math.sin(facing), math.cos(facing)
	local len = math.sqrt(dirX * dirX + dirZ * dirZ)
	if len < 1e-6 then return "front" end
	local dx, dz = dirX / len, dirZ / len
	local along = dx * fx + dz * fz           -- +1이면 등 뒤에서 앞으로 날아옴
	local across = dx * fz - dz * fx          -- +면 맞는 사람의 왼쪽에서 오른쪽으로
	if math.abs(along) >= math.abs(across) then return if along < 0 then "front" else "back" end
	return if across > 0 then "left" else "right"
end

local DEATH_BY_SIDE = {front = "death_back", back = "death_front", left = "death_right", right = "death_left"}

-- 사망 클립 고르기. 원인과 부위가 먼저고, 그다음이 맞은 방향이다.
function Vitals.deathClip(kind: string, zone: string, side: string, v, roll: number): string
	if v and v.state == "downed" then return "death_crawl" end
	if v and v.seated then return "death_sit" end
	if kind == "explosive" then return "death_blast" end
	if kind == "laser" or kind == "fire" then return "death_burn" end
	if kind == "electric" then return "death_shock" end
	if kind == "blade" then return if roll < 0.6 then "death_slash" else DEATH_BY_SIDE[side] end
	if zone == "head" or zone == "neck" then return "death_headshot" end
	if kind == "fall" then return "death_front" end
	if roll < 0.18 then return "death_knees" end
	return DEATH_BY_SIDE[side] or "death_back"
end

local function hitClip(zone: string, side: string, kind: string, strong: boolean): string
	if strong then return "stagger" end
	if zone == "head" or zone == "neck" then return "hit_head" end
	if zone == "leg" then return "hit_leg" end
	return "hit_" .. side
end

-- 수위에 따라 내야 할 이펙트 이름. 게임 쪽에서 이름마다 파티클·데칼·소리를 붙인다.
function Vitals.effects(kind: string, zone: string, killed: boolean, gore: number?)
	local g = gore or Vitals.GORE
	local out = {}
	local t = Vitals.TYPE[kind] or Vitals.TYPE.bullet
	if g <= 0 then
		table.insert(out, "hit_flash")
		if killed then table.insert(out, "dissolve") end
		return out
	end
	table.insert(out, "hit_flash"); table.insert(out, "hit_dust")
	if kind == "electric" then table.insert(out, "arc_sparks") end
	if kind == "explosive" then table.insert(out, "scorch_ground") end
	if t.burn then table.insert(out, "smoke_wisp") end
	if g >= 2 then
		if t.burn then
			table.insert(out, "burn_glow")              -- 맞은 곳이 잠깐 달아오른다
		elseif kind ~= "electric" and kind ~= "fall" then
			table.insert(out, "blood_spray"); table.insert(out, "blood_drops_ground")
		end
		if killed then table.insert(out, "corpse_stay") end
		if killed and not t.burn and kind ~= "electric" then table.insert(out, "blood_pool") end
	elseif killed then
		table.insert(out, "corpse_fade")
	end
	if g >= 3 then
		if t.burn then
			table.insert(out, "burn_mark_body"); if killed then table.insert(out, "char_body"); table.insert(out, "smoke_corpse") end
		elseif kind == "blade" then
			table.insert(out, "slash_mark_body"); table.insert(out, "blood_arc")
		elseif kind == "bullet" or kind == "shotgun" then
			table.insert(out, "wound_mark_body"); table.insert(out, "blood_wall_behind")
			if zone == "head" and killed then table.insert(out, "blood_mist") end
		elseif kind == "explosive" then
			table.insert(out, "wound_mark_body"); table.insert(out, "blood_wall_behind"); table.insert(out, "clothes_scorch")
		end
		if killed and not t.burn and kind ~= "electric" then table.insert(out, "blood_pool_grow") end
	end
	return out
end

-- hit = {damage, kind, zone | part(뼈 이름), dirX, dirZ, facing, attacker, roll(0~1 난수, 없으면 0.5), roll2}
-- 돌려주는 값: {dealt, killed, downed, state, anim, side, zone, knock, fear, effects}
function Vitals.hit(v, hit)
	local zone = hit.zone or (hit.part and Vitals.zoneOf(hit.part)) or "torso"
	local kind = hit.kind or "bullet"
	local t = Vitals.TYPE[kind] or Vitals.TYPE.bullet
	local side = Vitals.side(hit.dirX or 0, hit.dirZ or 0, hit.facing or 0)
	local roll, roll2 = hit.roll or 0.5, hit.roll2 or 0.5
	local res = {dealt = 0, killed = false, downed = false, state = v.state, anim = nil, side = side, zone = zone, knock = 0, fear = t.fear, effects = {}}
	if v.state == "dead" then
		res.effects = Vitals.effects(kind, zone, false)          -- 시체에 맞아도 자국은 남는다
		return res
	end
	local armor = if kind == "laser" or kind == "fire" or kind == "electric" or kind == "fall" then v.armor * 0.5 else v.armor
	local dmg = (hit.damage or 0) * (Vitals.ZONE[zone] or 1) * (1 - math.clamp(armor, 0, 0.9))
	if v.state == "downed" then dmg *= 1.5 end
	res.dealt = dmg
	v.health -= dmg
	table.insert(v.wounds, {zone = zone, kind = kind, side = side})
	if t.burn then v.burn = math.min(4, v.burn + dmg * 0.02) end
	if Vitals.GORE >= 2 and not t.burn and kind ~= "electric" and kind ~= "fall" then v.bleed = math.min(6, v.bleed + dmg * 0.03) end
	if v.health <= 0 then
		-- 팔다리에 맞아 죽을 피해를 입으면(수위 3) 일부는 바로 죽지 않고 쓰러져 기어간다
		local limb = zone == "arm" or zone == "leg"
		if Vitals.GORE >= 3 and v.state == "alive" and limb and not v.seated and kind ~= "explosive" and kind ~= "electric" and roll2 < 0.4 then
			v.state = "downed"; v.health = 1; v.downTimer = 8 + 10 * roll; v.bleed = math.max(v.bleed, 2)
			res.downed = true; res.anim = "fall_wounded"
		else
			res.anim = if Vitals.GORE <= 0 then "collapse" else Vitals.deathClip(kind, zone, side, v, roll)   -- 수위 0: 주저앉은 뒤 사라진다
			v.state = "dead"; v.health = 0; v.cause = kind; v.killer = hit.attacker
			res.killed = true; res.knock = t.knock
		end
	else
		local strong = t.stagger >= 0.8 or dmg >= v.maxHealth * 0.4
		if v.state == "alive" then res.anim = hitClip(zone, side, kind, strong); res.knock = if strong then t.knock * 0.5 else 0 end
	end
	res.state = v.state
	res.effects = Vitals.effects(kind, zone, res.killed)
	return res
end

-- 매 프레임(또는 0.1초마다). 출혈·화상 피해와 쓰러진 사람의 시간 경과를 처리한다.
-- 돌려주는 값: nil 또는 {killed = true, anim = "death_crawl", effects = {...}}
function Vitals.update(v, dt: number)
	if v.state == "dead" then return nil end
	if v.burn > 0 then
		v.health -= 6 * dt; v.burn = math.max(0, v.burn - dt)
	end
	if v.state == "downed" then
		v.downTimer -= dt
		v.health -= v.bleed * dt * 0.5
		if v.downTimer <= 0 or v.health <= 0 then
			v.state = "dead"; v.health = 0; v.cause = v.cause or "bleed"
			return {killed = true, anim = "death_crawl", effects = Vitals.effects("bullet", "torso", true)}
		end
	elseif v.health <= 0 then
		v.state = "dead"; v.health = 0; v.cause = "burn"
		return {killed = true, anim = "death_burn", effects = Vitals.effects("fire", "torso", true)}
	end
	return nil
end

return Vitals
