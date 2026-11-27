--!nonstrict
-- 배틀로얄의 아이템. Roblox API를 쓰지 않는 순수 모듈.
-- 하는 일: (1) 아이템 표, (2) 건물의 아이템 자리(manifest의 loot)에 무엇을 놓을지 뽑기, (3) 전장 전체의 수량 맞추기,
--          (4) 보급 상자, (5) 소지품 규칙(줍기, 바꾸기, 탄약 한도, 방어구, 회복, 죽을 때 떨어뜨리기).
-- 난수는 0~1을 돌려주는 함수(rand)로 받는다. 같은 난수면 같은 결과가 나온다.
local Loot = {}

-- cat: weapon(총) melee(근접) ammo(탄약) armor(방탄복) helmet(헬멧) heal(회복) throw(던지는 것) cyber(사이버웨어 팔)
-- tier: 1 흔함, 2 보통, 3 드묾, 4 보급 상자에서만. w = 같은 종류 안에서 뽑힐 무게.
-- 총: ammo = 탄약 종류, mag = 탄창. 모델 이름은 id와 같다(blender/out/weapons/<id>).
Loot.ITEMS = {
	pistol = {cat = "weapon", tier = 1, w = 10, ammo = "light", mag = 12},
	smg = {cat = "weapon", tier = 1, w = 9, ammo = "light", mag = 30},
	shotgun_double = {cat = "weapon", tier = 1, w = 6, ammo = "shell", mag = 2},
	revolver = {cat = "weapon", tier = 2, w = 5, ammo = "heavy", mag = 6},
	shotgun = {cat = "weapon", tier = 2, w = 6, ammo = "shell", mag = 6},
	rifle = {cat = "weapon", tier = 2, w = 8, ammo = "heavy", mag = 30},
	shotgun_auto = {cat = "weapon", tier = 3, w = 3, ammo = "shell", mag = 8},
	dmr = {cat = "weapon", tier = 3, w = 4, ammo = "heavy", mag = 10},
	lmg = {cat = "weapon", tier = 3, w = 2.5, ammo = "heavy", mag = 75},
	sniper = {cat = "weapon", tier = 3, w = 1.5, ammo = "long", mag = 5},

	knife = {cat = "melee", tier = 1, w = 8}, baton = {cat = "melee", tier = 1, w = 7}, knuckles = {cat = "melee", tier = 1, w = 6},
	hammer = {cat = "melee", tier = 2, w = 4}, katana = {cat = "melee", tier = 3, w = 2},

	ammo_light = {cat = "ammo", tier = 1, w = 12, ammo = "light", count = 30},
	ammo_heavy = {cat = "ammo", tier = 1, w = 10, ammo = "heavy", count = 30},
	ammo_shell = {cat = "ammo", tier = 1, w = 7, ammo = "shell", count = 10},
	ammo_long = {cat = "ammo", tier = 2, w = 2, ammo = "long", count = 5},

	-- reduce = 그 부위로 들어오는 피해를 줄이는 비율(Vitals의 armor 값), hp = 버티는 양
	armor_1 = {cat = "armor", tier = 1, w = 10, level = 1, reduce = 0.25, hp = 60},
	armor_2 = {cat = "armor", tier = 2, w = 6, level = 2, reduce = 0.40, hp = 90},
	armor_3 = {cat = "armor", tier = 3, w = 2, level = 3, reduce = 0.55, hp = 130},
	helmet_1 = {cat = "helmet", tier = 1, w = 10, level = 1, reduce = 0.30, hp = 40},
	helmet_2 = {cat = "helmet", tier = 2, w = 6, level = 2, reduce = 0.45, hp = 60},
	helmet_3 = {cat = "helmet", tier = 3, w = 2, level = 3, reduce = 0.60, hp = 90},

	-- heal = 채우는 양, cap = 이 아이템으로 채울 수 있는 한도, time = 쓰는 데 걸리는 시간(초), stack = 가질 수 있는 수
	bandage = {cat = "heal", tier = 1, w = 12, heal = 15, cap = 75, time = 3, stack = 5, count = 2},
	medkit = {cat = "heal", tier = 2, w = 4, heal = 100, cap = 100, time = 6, stack = 2, count = 1},
	stim = {cat = "heal", tier = 2, w = 4, heal = 0, cap = 100, time = 2, stack = 3, count = 1, regen = 1.0, regenTime = 30, speed = 1.06},   -- 30초 동안 초당 1 회복, 조금 빨라진다

	grenade = {cat = "throw", tier = 1, w = 8, stack = 3, count = 1},
	grenade_emp = {cat = "throw", tier = 2, w = 4, stack = 3, count = 1},     -- 사이버웨어 팔과 포탑·차를 잠깐 멈춘다

	-- 사이버웨어 팔(한 번에 하나). 다는 데 4초. 모델: samples/cyber-arm(블레이드), blender/out/cyber_arms/<이름>
	cw_blade = {cat = "cyber", tier = 2, w = 6, arm = "blade", time = 4},
	cw_power = {cat = "cyber", tier = 2, w = 6, arm = "power", time = 4},
	cw_nanowire = {cat = "cyber", tier = 3, w = 3, arm = "nanowire", time = 4},
	cw_launcher = {cat = "cyber", tier = 4, w = 2, arm = "launcher", time = 4},
	cw_laser = {cat = "cyber", tier = 4, w = 2, arm = "laser", time = 4},
}

Loot.IDS = {}
for id in Loot.ITEMS do table.insert(Loot.IDS, id) end
table.sort(Loot.IDS)

-- 자리 하나에서 종류가 뽑힐 무게
Loot.CATS = {"weapon", "melee", "ammo", "armor", "helmet", "heal", "throw", "cyber"}
Loot.CAT_W = {weapon = 22, melee = 5, ammo = 24, armor = 9, helmet = 9, heal = 16, throw = 8, cyber = 4}
-- 자리의 종류(manifest loot.kind)에 따른 배수: 상자 위에는 총이, 사물함 앞에는 방어구가 잘 나온다
Loot.KIND_W = {
	floor = {},
	crate_top = {weapon = 1.6, cyber = 1.6, ammo = 1.2},
	by_locker = {armor = 2.4, helmet = 2.2, weapon = 1.2},
	table = {ammo = 1.4, heal = 1.2},
	counter = {heal = 1.6, throw = 1.3},
	bed = {heal = 1.4, melee = 1.6},
	sofa = {melee = 1.5, ammo = 1.2},
	by_shelf = {ammo = 1.4, throw = 1.5},
}
-- 건물 등급: 큰 건물일수록 좋은 것이 나온다. 값 = 아이템 tier별 배수(tier 4는 건물에서 나오지 않는다)
Loot.GRADE = {shack = 1, rowhouse = 1, shop = 2, apartment = 2, warehouse = 3, office = 3}
Loot.TIER_W = {{1, 0.45, 0.10, 0}, {1, 0.75, 0.25, 0}, {0.8, 1.0, 0.55, 0}}
Loot.SUPPLY_TIER_W = {0, 0.3, 1.0, 1.6}
Loot.FILL = 0.6            -- 한 판에 자리의 이 비율에만 아이템을 놓는다
-- 전장 전체에서 한 사람 몫으로 있어야 하는 최소 수(Loot.balance가 맞춘다)
Loot.PER_PLAYER = {weapon = 2.0, armor = 0.8, helmet = 0.8, heal = 2.5, cyber = 0.4}
-- 소지 한도
Loot.AMMO_CAP = {light = 180, heavy = 150, shell = 40, long = 20}
Loot.GUN_SLOTS = 2

local function pick(rand, list, weightOf)
	local total = 0
	for _, k in list do total += weightOf(k) end
	if total <= 0 then return nil end
	local r = rand() * total
	for _, k in list do
		r -= weightOf(k)
		if r < 0 then return k end
	end
	return list[#list]
end

-- 아이템 하나를 뽑는다. kind = 자리 종류, grade = 건물 등급(1~3) 또는 "supply", cat = 종류를 정해 두고 뽑을 때.
function Loot.roll(rand, kind: string?, grade, cat: string?): string
	local tw = if grade == "supply" then Loot.SUPPLY_TIER_W else Loot.TIER_W[math.clamp(grade or 1, 1, 3)]
	local kw = Loot.KIND_W[kind or "floor"] or {}
	local function catWeight(c)
		local any = false
		for _, id in Loot.IDS do
			local it = Loot.ITEMS[id]
			if it.cat == c and tw[it.tier] > 0 then any = true; break end
		end
		return if any then Loot.CAT_W[c] * (kw[c] or 1) else 0
	end
	cat = cat or pick(rand, Loot.CATS, catWeight)
	local id = pick(rand, Loot.IDS, function(i)
		local it = Loot.ITEMS[i]
		return if it.cat == cat then it.w * tw[it.tier] else 0
	end)
	return id or "bandage"
end

-- 자리에 놓을 묶음: 총은 그 총의 탄약과 함께 놓는다.
function Loot.bundle(id: string)
	local it = Loot.ITEMS[id]
	local items = {{id = id, count = it.count or 1}}
	if it.cat == "weapon" then
		local a = "ammo_" .. it.ammo
		table.insert(items, {id = a, count = Loot.ITEMS[a].count})
	end
	return items
end

-- 건물 한 채의 아이템 자리(spots = manifest의 loot 목록)를 채운다. opts = {grade, ratio, building}
-- 돌려주는 것: {{spot = 번호, pos, kind, items = {{id, count}, ...}}, ...}
-- 자리가 6곳 이상인 건물에는 총이 적어도 하나 나온다.
function Loot.fill(spots, rand, opts)
	opts = opts or {}
	local grade = opts.grade or Loot.GRADE[opts.building or ""] or 1
	local ratio = opts.ratio or Loot.FILL
	local order = {}
	for i = 1, #spots do order[i] = i end
	for i = #order, 2, -1 do          -- 섞기
		local j = math.floor(rand() * i) + 1
		order[i], order[j] = order[j], order[i]
	end
	local n = math.clamp(math.floor(#spots * ratio + 0.5), math.min(1, #spots), #spots)
	local drops, hasGun = {}, false
	for k = 1, n do
		local s = spots[order[k]]
		local id = Loot.roll(rand, s.kind, grade)
		hasGun = hasGun or Loot.ITEMS[id].cat == "weapon"
		table.insert(drops, {spot = order[k], pos = s.pos, kind = s.kind, items = Loot.bundle(id)})
	end
	if not hasGun and #spots >= 6 and #drops > 0 then
		local d = drops[math.floor(rand() * #drops) + 1]
		d.items = Loot.bundle(Loot.roll(rand, d.kind, grade, "weapon"))
	end
	table.sort(drops, function(a, b) return a.spot < b.spot end)
	return drops
end

function Loot.count(drops)
	local c = {}
	for _, cat in Loot.CATS do c[cat] = 0 end
	for _, d in drops do
		local it = Loot.ITEMS[d.items[1].id]
		c[it.cat] += 1
	end
	return c
end

-- 전장 전체의 자리 목록(여러 건물의 fill 결과를 이어 붙인 것)을 인원에 맞춘다.
-- 모자란 종류가 있으면 탄약·근접·던지는 것이 놓인 자리를 그 종류로 바꾼다. 그래도 모자라면 short에 적어 돌려준다(건물을 더 놓아야 한다).
function Loot.balance(drops, rand, players: number, grade)
	local c = Loot.count(drops)
	local spare = {}
	for i, d in drops do
		local cat = Loot.ITEMS[d.items[1].id].cat
		if cat == "ammo" or cat == "melee" or cat == "throw" then table.insert(spare, i) end
	end
	local short = {}
	for _, cat in {"weapon", "armor", "helmet", "heal", "cyber"} do
		local need = math.ceil(players * Loot.PER_PLAYER[cat])
		while c[cat] < need and #spare > 0 do
			local k = math.floor(rand() * #spare) + 1
			local d = drops[spare[k]]
			spare[k] = spare[#spare]; spare[#spare] = nil
			c[Loot.ITEMS[d.items[1].id].cat] -= 1
			d.items = Loot.bundle(Loot.roll(rand, d.kind, grade or 2, cat))
			c[cat] += 1
		end
		if c[cat] < need then short[cat] = need - c[cat] end
	end
	return {counts = c, short = short}
end

-- 보급 상자 하나에 든 것: 좋은 총과 탄약 두 묶음, 3단계 방어구 하나, 구급 상자, 사이버웨어 팔.
function Loot.supply(rand)
	local gun = Loot.roll(rand, nil, "supply", "weapon")
	local ammo = "ammo_" .. Loot.ITEMS[gun].ammo
	return {
		{id = gun, count = 1}, {id = ammo, count = Loot.ITEMS[ammo].count * 2},
		{id = if rand() < 0.5 then "armor_3" else "helmet_3", count = 1}, {id = "medkit", count = 1},
		{id = Loot.roll(rand, nil, "supply", "cyber"), count = 1},
	}
end

-- ---------------------------------------------------------------- 소지품
function Loot.newInventory()
	return {guns = {}, active = 1, melee = nil, cyber = nil, armor = nil, helmet = nil,
		ammo = {light = 0, heavy = 0, shell = 0, long = 0}, items = {}}
end

-- 줍기. opts = {slot = 바꿀 총 칸, hp = 떨어져 있던 방어구의 남은 양, force = 더 나쁜 방어구도 바꿔 입기}
-- 돌려주는 것: {ok, taken = 가진 수, left = 바닥에 남는 수, dropped = {바닥에 떨어뜨릴 것들}, reason, time = 다는 데 걸리는 시간}
function Loot.pickup(inv, id: string, count: number?, opts)
	local it = Loot.ITEMS[id]
	opts = opts or {}; count = count or 1
	local res = {ok = false, taken = 0, left = count, dropped = {}}
	if not it then res.reason = "unknown"; return res end
	if it.cat == "weapon" then
		local slot = nil
		for i = 1, Loot.GUN_SLOTS do
			if not inv.guns[i] then slot = i; break end
		end
		if not slot then
			slot = math.clamp(opts.slot or inv.active or 1, 1, Loot.GUN_SLOTS)
			table.insert(res.dropped, {id = inv.guns[slot], count = 1})
		end
		inv.guns[slot] = id; res.slot = slot
	elseif it.cat == "melee" or it.cat == "cyber" then
		local key = it.cat
		if inv[key] == id then res.reason = "same"; return res end
		if inv[key] then table.insert(res.dropped, {id = inv[key], count = 1}) end
		inv[key] = id; res.time = it.time
	elseif it.cat == "armor" or it.cat == "helmet" then
		local cur, hp = inv[it.cat], opts.hp or it.hp
		if cur and not opts.force then
			local curLevel = Loot.ITEMS[cur.id].level
			if curLevel > it.level or (curLevel == it.level and cur.hp >= hp) then res.reason = "worse"; return res end
		end
		if cur then table.insert(res.dropped, {id = cur.id, count = 1, hp = cur.hp}) end
		inv[it.cat] = {id = id, hp = hp}
	elseif it.cat == "ammo" then
		local room = Loot.AMMO_CAP[it.ammo] - inv.ammo[it.ammo]
		local n = math.max(0, math.min(count, room))
		if n == 0 then res.reason = "full"; return res end
		inv.ammo[it.ammo] += n; res.ok = true; res.taken = n; res.left = count - n
		return res
	else      -- heal, throw
		local have = inv.items[id] or 0
		local n = math.max(0, math.min(count, it.stack - have))
		if n == 0 then res.reason = "full"; return res end
		inv.items[id] = have + n; res.ok = true; res.taken = n; res.left = count - n
		return res
	end
	res.ok = true; res.taken = 1; res.left = count - 1
	return res
end

-- 맞은 부위의 방어 비율: Vitals.hit을 부르기 전에 v.armor에 넣는다. 머리 = 헬멧, 몸통 = 방탄복, 나머지 = 0.
function Loot.protection(inv, zone: string): number
	local piece = if zone == "head" then inv.helmet elseif zone == "torso" then inv.armor else nil
	return if piece and piece.hp > 0 then Loot.ITEMS[piece.id].reduce else 0
end

-- 피해를 받은 뒤: 방어구가 막아 준 만큼 닳는다. 다 닳으면 없어진다. raw = 방어구가 없었다면 받았을 피해.
function Loot.absorb(inv, zone: string, raw: number)
	local key = if zone == "head" then "helmet" elseif zone == "torso" then "armor" else nil
	local piece = key and inv[key]
	if not piece then return {absorbed = 0, broken = false} end
	local a = raw * Loot.ITEMS[piece.id].reduce
	piece.hp -= a
	if piece.hp <= 0 then
		inv[key] = nil
		return {absorbed = a, broken = true, id = piece.id}
	end
	return {absorbed = a, broken = false}
end

-- 회복 아이템을 쓸 수 있는가. 쓸 수 있으면 걸리는 시간을 돌려준다(그 시간 동안 맞거나 움직이면 취소하는 것은 게임 쪽에서).
function Loot.canUse(inv, id: string, health: number)
	local it = Loot.ITEMS[id]
	if not it or it.cat ~= "heal" then return false, "not_usable" end
	if (inv.items[id] or 0) <= 0 then return false, "none" end
	if it.heal > 0 and health >= it.cap then return false, "healthy" end
	return true, it.time
end

-- 다 쓴 뒤: 하나 줄이고 새 체력을 돌려준다. stim은 {regen, regenTime, speed}를 함께 돌려준다.
function Loot.applyUse(inv, id: string, health: number)
	local ok, why = Loot.canUse(inv, id, health)
	if not ok then return {ok = false, reason = why, health = health} end
	local it = Loot.ITEMS[id]
	inv.items[id] -= 1
	return {ok = true, health = math.max(health, math.min(it.cap, health + it.heal)), regen = it.regen, regenTime = it.regenTime, speed = it.speed}
end

-- 재장전: 총의 탄약 종류에서 want발을 꺼낸다. 꺼낸 수를 돌려준다.
function Loot.takeAmmo(inv, gun: string, want: number): number
	local kind = Loot.ITEMS[gun].ammo
	local n = math.min(want, inv.ammo[kind])
	inv.ammo[kind] -= n
	return n
end

-- 던지는 것 하나를 쓴다.
function Loot.takeItem(inv, id: string): boolean
	if (inv.items[id] or 0) <= 0 then return false end
	inv.items[id] -= 1
	return true
end

-- 죽었을 때: 가진 것을 전부 떨어뜨릴 목록으로 돌려주고 소지품을 비운다.
function Loot.deathDrop(inv)
	local out = {}
	for i = 1, Loot.GUN_SLOTS do
		if inv.guns[i] then table.insert(out, {id = inv.guns[i], count = 1}) end
	end
	if inv.melee then table.insert(out, {id = inv.melee, count = 1}) end
	if inv.cyber then table.insert(out, {id = inv.cyber, count = 1}) end
	if inv.armor then table.insert(out, {id = inv.armor.id, count = 1, hp = inv.armor.hp}) end
	if inv.helmet then table.insert(out, {id = inv.helmet.id, count = 1, hp = inv.helmet.hp}) end
	for _, kind in {"heavy", "light", "long", "shell"} do
		if inv.ammo[kind] > 0 then table.insert(out, {id = "ammo_" .. kind, count = inv.ammo[kind]}) end
	end
	for _, id in Loot.IDS do
		if (inv.items[id] or 0) > 0 then table.insert(out, {id = id, count = inv.items[id]}) end
	end
	inv.guns = {}; inv.active = 1; inv.melee = nil; inv.cyber = nil; inv.armor = nil; inv.helmet = nil
	inv.ammo = {light = 0, heavy = 0, shell = 0, long = 0}; inv.items = {}
	return out
end

return Loot
