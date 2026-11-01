//---------------------------------------------------------------------------
// Balance probe. Only in `build.py --probe` maps, never in a release: see docs/balance.md.
// It plays the production game with ordinary orders: it buys the champion in the tavern, learns skills, buys in the
// real shops with the real gold, moves, attacks and casts its champion's spells. During a fight it never sets HP, gold, level, time or
// invulnerability and never kills or pauses anything. It only reads and logs. A lost fight is data.
// One labelled exception: mode 3 kills the lane's tower and Nexus once, to bring a boss on at the wave asked for (the bot does not push).
//---------------------------------------------------------------------------
function ProbeNow takes nothing returns string
    return R2SW(TimerGetElapsed(gPrClock), 1, 1)
endfunction

function ProbeLog takes string s returns nothing
    call TestLog("M t=" + ProbeNow() + " " + s)
endfunction

function ProbeGold takes nothing returns integer
    return GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
endfunction

function ProbeDist takes real ax, real ay, real bx, real by returns real
    return SquareRoot((ax - bx) * (ax - bx) + (ay - by) * (ay - by))
endfunction

// Level-ups refill HP (OnHeroLevel). This trigger is registered first, so it sees the HP before that heal.
function ProbeOnLevel takes nothing returns nothing
    local unit h = GetTriggerUnit()
    if h == gHero[0] then
        if GetWidgetLife(h) < gPrHpMin then
            set gPrHpMin = GetWidgetLife(h)
        endif
        call ProbeLog("event=level level=" + I2S(GetHeroLevel(h)) + " hp_before_heal=" + I2S(R2I(GetWidgetLife(h))) + " maxhp=" + I2S(R2I(GetUnitState(h, UNIT_STATE_MAX_LIFE))) + " xp=" + I2S(GetHeroXP(h)))
    endif
    set h = null
endfunction

function ProbeEarly takes nothing returns nothing
    local trigger t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_HERO_LEVEL)
    call TriggerAddAction(t, function ProbeOnLevel)
    set t = null
endfunction

// The damage event fires before the HP drop, so pre - damage is the HP right after this hit.
function ProbeOnHeroHit takes nothing returns nothing
    local real d = GetEventDamage()
    local real post = GetWidgetLife(GetTriggerUnit()) - d
    if d <= 0.0 then
        return
    endif
    if post < 0.0 then
        set post = 0.0
    endif
    if post < gPrHpMin then
        set gPrHpMin = post
    endif
    set gPrTaken = gPrTaken + d
    set gPrTakenAll = gPrTakenAll + d
    set gPrHits = gPrHits + 1
    if gPrFirstHit < 0.0 then
        set gPrFirstHit = TimerGetElapsed(gPrClock)
    endif
    if GetEventDamageSource() == gTower[0] then
        set gPrTowerHits = gPrTowerHits + 1
        set gPrFromTower = gPrFromTower + d
        call ProbeLog("event=tower_hit damage=" + I2S(R2I(d)) + " hp_before=" + I2S(R2I(GetWidgetLife(GetTriggerUnit()))) + " maxhp=" + I2S(R2I(GetUnitState(GetTriggerUnit(), UNIT_STATE_MAX_LIFE))))
    elseif GetEventDamageSource() == gNexus[0] then
        set gPrNexusHits = gPrNexusHits + 1
        set gPrFromNexus = gPrFromNexus + d
        call ProbeLog("event=nexus_hit damage=" + I2S(R2I(d)) + " hp_before=" + I2S(R2I(GetWidgetLife(GetTriggerUnit()))))
    elseif GetEventDamageSource() == gBoss[0] and gBoss[0] != null then
        set gPrFromBoss = gPrFromBoss + d
    elseif IsUnitInGroup(GetEventDamageSource(), gWaveUnits) then
        set gPrFromWave = gPrFromWave + d
    else
        set gPrFromOther = gPrFromOther + d
    endif
endfunction

function ProbeOnHeroDeath takes nothing returns nothing
    set gPrHpMin = 0.0
    set gPrDeathsWave = gPrDeathsWave + 1
    call ProbeLog("event=death level=" + I2S(GetHeroLevel(gHero[0])) + " maxhp=" + I2S(R2I(GetUnitState(gHero[0], UNIT_STATE_MAX_LIFE))))
endfunction

function ProbeOtherDamage takes integer id, real d returns nothing
    local integer i = 0
    loop
        exitwhen i >= gPrOtherN
        if gPrOtherType[i] == id then
            set gPrOtherDmg[i] = gPrOtherDmg[i] + d
            return
        endif
        set i = i + 1
    endloop
    if gPrOtherN < 16 then
        set gPrOtherType[gPrOtherN] = id
        set gPrOtherDmg[gPrOtherN] = d
        set gPrOtherN = gPrOtherN + 1
    endif
endfunction

// Raw = the damage events (after armor, overkill included). Hp = what the target really lost. Neither is DPS by itself.
// hero_wave: the champion on wave monsters. hero_other: the champion on towers, Nexus, bosses, Protectors.
// other: damage by any other unit of a player (summons), by type in event=other_damage; never expected from an ally in a solo probe.
function ProbeOnEnemyHit takes nothing returns nothing
    local real d = GetEventDamage()
    local unit s = GetEventDamageSource()
    local unit t = GetTriggerUnit()
    local real lost = GetWidgetLife(t)
    if lost > d then
        set lost = d
    endif
    if d > 0.0 and s != null and GetPlayerId(GetOwningPlayer(s)) < 8 then
        if s == gHero[0] then
            if IsUnitInGroup(t, gWaveUnits) then
                set gPrHeroWaveRaw = gPrHeroWaveRaw + d
                set gPrHeroWaveHp = gPrHeroWaveHp + lost
            else
                set gPrHeroOtherRaw = gPrHeroOtherRaw + d
                set gPrHeroOtherHp = gPrHeroOtherHp + lost
            endif
            if gPrFirstDeal < 0.0 then
                set gPrFirstDeal = TimerGetElapsed(gPrClock)
            endif
        else
            set gPrOtherRaw = gPrOtherRaw + d
            set gPrOtherHp = gPrOtherHp + lost
            call ProbeOtherDamage(GetUnitTypeId(s), d)
        endif
    endif
    set s = null
    set t = null
endfunction

function ProbeOnEnter takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer o = GetPlayerId(GetOwningPlayer(u))
    if o >= 8 and o <= 11 then
        call TriggerRegisterUnitEvent(gPrDealTrig, u, EVENT_UNIT_DAMAGED)
    endif
    set u = null
endfunction

// Who really takes part: the playing slots and the champions in the game.
function ProbeTeam takes nothing returns string
    local integer i = 0
    local string r = "playing="
    loop
        exitwhen i >= 12
        if IsPlaying(i) then
            set r = r + I2S(i) + ","
        endif
        set i = i + 1
    endloop
    set r = r + " heroes="
    set i = 0
    loop
        exitwhen i >= 8
        if gHero[i] != null then
            set r = r + I2S(i) + ","
        endif
        set i = i + 1
    endloop
    return r
endfunction

function ProbeStats takes string tag returns nothing
    local unit h = gHero[0]
    call ProbeLog("event=" + tag + " hero=" + GetUnitName(h) + " level=" + I2S(GetHeroLevel(h)) + " xp=" + I2S(GetHeroXP(h)) + " str=" + I2S(GetHeroStr(h, true)) + " agi=" + I2S(GetHeroAgi(h, true)) + " int=" + I2S(GetHeroInt(h, true)) + " hp=" + I2S(R2I(GetWidgetLife(h))) + " maxhp=" + I2S(R2I(GetUnitState(h, UNIT_STATE_MAX_LIFE))) + " gold=" + I2S(ProbeGold()) + " spent=" + I2S(gPrSpent) + " earned=" + I2S(ProbeGold() + gPrSpent - 1000))
    set h = null
endfunction

function ProbeAliveEnum takes nothing returns nothing
    if GetWidgetLife(GetEnumUnit()) > 0.405 then
        set gPrAlive = gPrAlive + 1
    endif
endfunction

// The monsters really alive. gWaveUnits itself holds the dead until the next 1 s tick, which starts the next wave.
function ProbeAlive takes nothing returns integer
    set gPrAlive = 0
    call ForGroup(gWaveUnits, function ProbeAliveEnum)
    return gPrAlive
endfunction

function ProbeState takes nothing returns string
    return "level=" + I2S(GetHeroLevel(gHero[0])) + " xp=" + I2S(GetHeroXP(gHero[0])) + " kills=" + I2S(gKills[0]) + " deaths=" + I2S(gDeaths[0]) + " castle=" + I2S(R2I(GetWidgetLife(gCastle))) + " gold=" + I2S(ProbeGold()) + " spent=" + I2S(gPrSpent) + " earned=" + I2S(ProbeGold() + gPrSpent - 1000) + " pending=" + I2S(gPrPendType) + " income=" + I2S(gIncome[0]) + " trees=" + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)) + " alive=" + I2S(ProbeAlive()) + " casts=" + I2S(gPrCasts)
endfunction

// One summary per wave, written once, when it is cleared or when the run ends with it still open. The engine's Preload
// cuts a line at 259 characters: a record is several short lines with the same wave number (the parser requires them all).
function ProbeWaveLine takes string why returns nothing
    local string w = "wave=" + I2S(gPrWave)
    call ProbeLog("event=wave " + w + " why=" + why + " spawned_at=" + R2SW(gPrWaveAt, 1, 1) + " spawned=" + I2S(gPrWaveCount) + " first_hit=" + R2SW(gPrFirstHit, 1, 1) + " first_deal=" + R2SW(gPrFirstDeal, 1, 1) + " hp_min=" + I2S(R2I(gPrHpMin)) + " deaths_wave=" + I2S(gPrDeathsWave))
    call ProbeLog("event=incoming " + w + " taken=" + I2S(R2I(gPrTaken)) + " from_wave=" + I2S(R2I(gPrFromWave)) + " from_tower=" + I2S(R2I(gPrFromTower)) + " from_nexus=" + I2S(R2I(gPrFromNexus)) + " from_boss=" + I2S(R2I(gPrFromBoss)) + " from_other=" + I2S(R2I(gPrFromOther)) + " hits=" + I2S(gPrHits))
    call ProbeLog("event=dealt " + w + " hero_wave_raw=" + I2S(R2I(gPrHeroWaveRaw)) + " hero_wave_hp=" + I2S(R2I(gPrHeroWaveHp)) + " hero_other_raw=" + I2S(R2I(gPrHeroOtherRaw)) + " hero_other_hp=" + I2S(R2I(gPrHeroOtherHp)) + " other_raw=" + I2S(R2I(gPrOtherRaw)) + " other_hp=" + I2S(R2I(gPrOtherHp)))
    call ProbeLog("event=state " + w + " " + ProbeState())
    call ProbeLog("event=team " + w + " " + ProbeTeam())
    call TestFlush()
endfunction

function ProbeResetWave takes nothing returns nothing
    set gPrFirstHit = -1.0
    set gPrFirstDeal = -1.0
    set gPrTaken = 0.0
    set gPrFromWave = 0.0
    set gPrFromTower = 0.0
    set gPrFromNexus = 0.0
    set gPrFromBoss = 0.0
    set gPrFromOther = 0.0
    set gPrHeroWaveRaw = 0.0
    set gPrHeroWaveHp = 0.0
    set gPrHeroOtherRaw = 0.0
    set gPrHeroOtherHp = 0.0
    set gPrOtherRaw = 0.0
    set gPrOtherHp = 0.0
    set gPrHits = 0
    set gPrDeathsWave = 0
    set gPrHpMin = GetWidgetLife(gHero[0])
endfunction

// What the champion has learned, in the order of his card.
function ProbeRanks takes nothing returns nothing
    local integer i = 0
    local string r = "event=ranks"
    loop
        exitwhen i >= gSkillsPerHero
        set r = r + " r" + I2S(i) + "=" + I2S(GetUnitAbilityLevel(gHero[0], gHeroSkill[gPrHero * gSkillsPerHero + i]))
        set i = i + 1
    endloop
    call ProbeLog(r)
endfunction

// Who else of the player did damage, by unit type (summons, or anything else he owns).
function ProbeOthers takes nothing returns nothing
    local integer i = 0
    loop
        exitwhen i >= gPrOtherN
        call ProbeLog("event=other_damage type=" + I2S(gPrOtherType[i]) + " raw=" + I2S(R2I(gPrOtherDmg[i])))
        set i = i + 1
    endloop
endfunction

function ProbeFinish takes string why returns nothing
    if gPrDone then
        return
    endif
    set gPrDone = true
    if gPrPendType != 0 then
        call ProbeLog("event=buy_pending_at_end item=" + gPrPendName + " price=" + I2S(gPrPendPrice) + " gold_before=" + I2S(gPrPendGold) + " gold=" + I2S(ProbeGold()))
    endif
    if gPrWaveOpen then
        call ProbeWaveLine("open_at_end")
    endif
    call ProbeStats("final")
    call ProbeRanks()
    call ProbeOthers()
    call ProbeLog("event=end why=" + why + " tower_hits=" + I2S(gPrTowerHits) + " nexus_hits=" + I2S(gPrNexusHits) + " wave=" + I2S(gLaneWave[0]) + " deaths=" + I2S(gDeaths[0]) + " taken_total=" + I2S(R2I(gPrTakenAll)))
    call ProbeLog("event=team " + ProbeTeam())
    call TestLog("PASS probe finished: " + why)
    call TestLog("SELFTEST DONE")
    call TestFlush()
endfunction

// The castle's end dialog pauses the game, so this logs in the death event itself.
function ProbeOnCastleDeath takes nothing returns nothing
    call ProbeLog("event=castle_destroyed")
    call ProbeFinish("castle_destroyed")
endfunction

function ProbeKind takes string c returns integer
    local string keys = "QWERASDFZ"
    local integer i = 0
    loop
        exitwhen i >= 9
        if SubString(keys, i, i + 1) == c then
            return i
        endif
        set i = i + 1
    endloop
    return -1
endfunction

function ProbePrice takes integer s, integer k returns integer
    local real base = gPrPriceBase
    if s == 8 then
        set base = gPrPriceXp
    endif
    return R2I(base * Pow(gPrPriceGrowth, I2R(k)) + 0.5)
endfunction

function ProbePotions takes nothing returns integer
    local integer s = 0
    local integer n = 0
    local item it
    loop
        exitwhen s >= 6
        set it = UnitItemInSlot(gHero[0], s)
        if it != null and GetItemTypeId(it) == gPotItem[0] then
            set n = n + GetItemCharges(it)
        endif
        set s = s + 1
    endloop
    set it = null
    return n
endfunction

// A purchase counts only when its effect is seen: the shop step moved, the potion is there, the income rose.
// An order the shop refused or refunded costs nothing and is logged as such. Returns true when nothing is pending.
function ProbeResolve takes nothing returns boolean
    local boolean done = false
    if gPrPendType == 0 then
        return true
    endif
    if gPrPendType == 1 then
        set done = KindNext(0, gPrPendKind) > gPrPendStep
    elseif gPrPendType == 2 then
        set done = ProbePotions() > gPrPendStep
    else
        set done = gIncome[0] > gPrPendStep
    endif
    if done then
        set gPrSpent = gPrSpent + gPrPendPrice
        call ProbeLog("event=buy_ok item=" + gPrPendName + " step=" + I2S(gPrPendStep) + " price=" + I2S(gPrPendPrice) + " gold_before=" + I2S(gPrPendGold) + " gold_after=" + I2S(ProbeGold()))
        set gPrPendType = 0
        return true
    endif
    if TimerGetElapsed(gPrClock) > gPrPendAt + 2.0 then
        call ProbeLog("event=buy_failed item=" + gPrPendName + " gold_before=" + I2S(gPrPendGold) + " gold_after=" + I2S(ProbeGold()))
        set gPrPendType = 0
        return true
    endif
    return false
endfunction

function ProbePend takes integer kind, integer step, integer price, string name, integer g, integer t returns nothing
    set gPrPendKind = kind
    set gPrPendStep = step
    set gPrPendPrice = price
    set gPrPendName = name
    set gPrPendGold = g
    set gPrPendAt = TimerGetElapsed(gPrClock)
    set gPrPendType = t
endfunction

// One ordinary purchase. Returns true when the order was given and now waits for ProbeResolve.
function ProbeBuy takes string c returns boolean
    local integer s
    local integer k
    local integer price
    local integer g = ProbeGold()
    if not ProbeResolve() then
        return false
    endif
    if c == "P" then
        if g < gPrPotionPrice then
            return false
        endif
        set k = ProbePotions()
        if IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[0]) then
            call ProbePend(0, k, gPrPotionPrice, "healing_potion", g, 2)
            return true
        endif
        call ProbeLog("event=buy_refused item=healing_potion gold=" + I2S(g))
        return false
    endif
    set s = ProbeKind(c)
    if s < 0 then
        return false
    endif
    set k = KindNext(0, s)
    set price = ProbePrice(s, k)
    if k >= gStatTiers or g < price then
        return false
    endif
    if IssueImmediateOrderById(gLaneMarker[0], gStatItem[s * gKindStride + k]) then
        call ProbePend(s, k, price, c, g, 1)
        return true
    endif
    call ProbeLog("event=buy_refused item=" + c + " step=" + I2S(k) + " gold=" + I2S(g))
    return false
endfunction

// Every point into the next skill that takes it, the bot's order: its ultimate (R) first, then the others in turn.
// The Dryad has nothing to cast: her Multiple Arrows go first, as far as her levels allow them, or the run would not measure what she is.
function ProbeLearn takes unit h returns nothing
    local integer tries = 0
    local integer before
    loop
        exitwhen GetHeroSkillPoints(h) <= 0 or tries >= 10
        set before = GetHeroSkillPoints(h)
        if gPrHero == 0 then
            call SelectHeroSkill(h, gHeroSkill[gPrHero * gSkillsPerHero + 1])
        endif
        if GetHeroSkillPoints(h) == before then
            call SelectHeroSkill(h, gHeroSkill[gPrHero * gSkillsPerHero + 3])
        endif
        if GetHeroSkillPoints(h) == before then
            call SelectHeroSkill(h, gHeroSkill[gPrHero * gSkillsPerHero + ModuloInteger(gPrSkillNext, gSkillsPerHero)])
            set gPrSkillNext = gPrSkillNext + 1
        endif
        set tries = tries + 1
    endloop
endfunction

function ProbeDrink takes unit h returns nothing
    local integer s = 0
    local item it
    if TimerGetElapsed(gPrClock) < gPrPotionAt + 10.0 then
        return
    endif
    loop
        exitwhen s >= 6
        set it = UnitItemInSlot(h, s)
        if it != null and GetItemTypeId(it) == gPotItem[0] then
            if UnitUseItem(h, it) then
                set gPrPotionAt = TimerGetElapsed(gPrClock)
                call ProbeLog("event=potion hp=" + I2S(R2I(GetWidgetLife(h))) + " maxhp=" + I2S(R2I(GetUnitState(h, UNIT_STATE_MAX_LIFE))))
            endif
            set it = null
            return
        endif
        set s = s + 1
    endloop
    set it = null
endfunction

// Campaign mode: spend what is there on the build's cycle; a tree goes to the Bank.
function ProbeSpend takes nothing returns nothing
    local string c
    local integer before
    if not ProbeResolve() then
        return
    endif
    if GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER) >= 1 then
        // read before the order: a grove sale happens inside the order itself. A tree is its price, the income its proof.
        set before = gIncome[0]
        if IssueNeutralImmediateOrderById(Player(0), gBankShop, gBankItem) then
            call ProbePend(0, before, 0, "income", ProbeGold(), 3)
        endif
        return
    endif
    if StringLength(gPrCycle) == 0 then
        return
    endif
    set c = SubString(gPrCycle, ModuloInteger(gPrCycleAt, StringLength(gPrCycle)), ModuloInteger(gPrCycleAt, StringLength(gPrCycle)) + 1)
    if ProbeBuy(c) then
        set gPrCycleAt = gPrCycleAt + 1
    endif
endfunction

function ProbeOrderTo takes unit h, string ord, real x, real y returns nothing
    if TimerGetElapsed(gPrClock) >= gPrOrderAt + 1.0 then
        set gPrOrderAt = TimerGetElapsed(gPrClock)
        call IssuePointOrder(h, ord, x, y)
    endif
endfunction

// Damage of one raw hit on this champion after armor (WarCraft: reduction = 0.06 a / (1 + 0.06 a); chaos on a hero 100 %).
// A bot policy, not a game rule: push when the champion can take gPrPushHits hits of the target. Time spent waiting for
// that threshold is this bot's choice, not a required progression.
function ProbeHitOn takes unit h, real raw returns real
    local real a = gPrBaseArmor + 0.30 * I2R(GetHeroAgi(h, true)) + gPrArmorStep * I2R(KindNext(0, 3))
    if a <= 0.0 then
        return raw
    endif
    return raw / (1.0 + 0.06 * a)
endfunction

function ProbePushTarget takes unit h returns unit
    local real hp = GetUnitState(h, UNIT_STATE_MAX_LIFE)
    if GetWidgetLife(gTower[0]) > 0.405 then
        if hp >= gPrPushHits * ProbeHitOn(h, gPrTowerHit) then
            return gTower[0]
        endif
        return null
    endif
    if gNexus[0] != null and GetWidgetLife(gNexus[0]) > 0.405 then
        if hp >= gPrPushHits * ProbeHitOn(h, gPrNexusHit) then
            return gNexus[0]
        endif
        return null
    endif
    if gBoss[0] != null and GetWidgetLife(gBoss[0]) > 0.405 then
        if hp >= gPrPushHits * ProbeHitOn(h, gPrBossHit) then
            return gBoss[0]
        endif
    endif
    return null
endfunction

function ProbeProgress takes nothing returns nothing
    if not gPrTowerDown and GetWidgetLife(gTower[0]) <= 0.405 then
        set gPrTowerDown = true
        call ProbeStats("tower_destroyed")
    endif
    if gPrTowerDown and not gPrNexusDown and GetWidgetLife(gNexus[0]) <= 0.405 then
        set gPrNexusDown = true
        call ProbeStats("nexus_destroyed")
    endif
    if gPrNexusDown and not gPrBossDown and gBoss[0] == null then
        set gPrBossDown = true
        call ProbeStats("boss_slain")
    endif
endfunction

// A spell around the champion only when the enemy is inside its radius, at the level learned: no mana for an empty clap.
function ProbeReaches takes unit h, unit tgt, integer n returns boolean
    local real area
    if gCastTarget[n] != 0 or gCastEffect[n] != 1 then
        return true
    endif
    set area = gCastArea[n * 6 + GetUnitAbilityLevel(h, gCastAbil[n])]
    return area <= 0.0 or ProbeDist(GetUnitX(h), GetUnitY(h), GetUnitX(tgt), GetUnitY(tgt)) <= area
endfunction

// The champion's kit: every second the next spell it has learned that takes the order, at the nearest enemy.
function ProbeCast takes unit h, unit tgt returns nothing
    local real now = TimerGetElapsed(gPrClock)
    local integer tries = 0
    local integer n
    local boolean ok
    if now < gPrCastAt + 1.0 or tgt == null or GetWidgetLife(tgt) <= 0.405 then
        return
    endif
    // the last spell is still on its way to the target
    if gPrCastOrder != 0 and GetUnitCurrentOrder(h) == gPrCastOrder and now < gPrCastAt + 3.0 then
        return
    endif
    loop
        exitwhen tries >= gCastN
        set gPrCastRow = ModuloInteger(gPrCastRow + 1, gCastN)
        set n = gPrCastRow
        set tries = tries + 1
        if gCastHero[n] == gPrHero and gCastEffect[n] != 6 and GetUnitAbilityLevel(h, gCastAbil[n]) > 0 and ProbeReaches(h, tgt, n) then
            if gCastTarget[n] == 1 then
                set ok = IssueTargetOrder(h, gCastOrder[n], tgt)
            elseif gCastTarget[n] == 2 then
                set ok = IssuePointOrder(h, gCastOrder[n], GetUnitX(tgt), GetUnitY(tgt))
            elseif gCastTarget[n] == 3 or gCastTarget[n] == 4 then
                set ok = IssueTargetOrder(h, gCastOrder[n], h)
            else
                set ok = IssueImmediateOrder(h, gCastOrder[n])
            endif
            if ok then
                set gPrCastAt = now
                set gPrOrderAt = now
                set gPrCastOrder = OrderId(gCastOrder[n])
                return
            endif
        endif
    endloop
endfunction

// A spell of the champion's own kit, not a potion.
function ProbeOwnSpell takes integer id returns boolean
    local integer n = 0
    loop
        exitwhen n >= gCastN
        if gCastHero[n] == gPrHero and gCastAbil[n] == id then
            return true
        endif
        set n = n + 1
    endloop
    return false
endfunction

function ProbeOnSpell takes nothing returns nothing
    local integer id = GetSpellAbilityId()
    if GetTriggerUnit() == gHero[0] and ProbeOwnSpell(id) then
        set gPrCasts = gPrCasts + 1
        call ProbeLog("event=cast id=" + I2S(id) + " level=" + I2S(GetUnitAbilityLevel(gHero[0], id)) + " wave=" + I2S(gLaneWave[0]))
    endif
endfunction

function ProbeOnChannel takes nothing returns nothing
    if GetTriggerUnit() == gHero[0] and ProbeOwnSpell(GetSpellAbilityId()) then
        set gPrChannel = true
        set gPrChannelAt = TimerGetElapsed(gPrClock)
    endif
endfunction

// How long a spell really ran: what a channel is worth. Instant ones stay out of the log.
function ProbeOnEndCast takes nothing returns nothing
    if GetTriggerUnit() == gHero[0] then
        if gPrChannel and TimerGetElapsed(gPrClock) - gPrChannelAt >= 1.0 then
            call ProbeLog("event=channel id=" + I2S(GetSpellAbilityId()) + " start=" + R2SW(gPrChannelAt, 1, 1) + " seconds=" + R2SW(TimerGetElapsed(gPrClock) - gPrChannelAt, 1, 1))
        endif
        set gPrChannel = false
    endif
endfunction

function ProbeOnSummon takes nothing returns nothing
    if GetSummoningUnit() == gHero[0] then
        call ProbeLog("event=summon type=" + I2S(GetUnitTypeId(GetSummonedUnit())) + " wave=" + I2S(gLaneWave[0]))
    endif
endfunction

// A spell that is running stays running: every ordinary order would end a Blizzard or a Stampede. Only low HP or the tower's range break it, in the log.
function ProbeKeepChannel takes unit h, real hp, real mx, real x, real y returns boolean
    if not gPrChannel or GetUnitCurrentOrder(h) == 0 then
        set gPrChannel = false
        return false
    endif
    if hp >= mx * 0.25 and (GetWidgetLife(gTower[0]) <= 0.405 or ProbeDist(x, y, GetUnitX(gTower[0]), GetUnitY(gTower[0])) >= gPrSafeDist) then
        return true
    endif
    set gPrChannel = false
    call ProbeLog("event=channel_cancelled hp=" + I2S(R2I(hp)) + " maxhp=" + I2S(R2I(mx)))
    return false
endfunction

// Mode 3: the wave asked for is reached: the tower and the Nexus go, the boss of this lane's wave rises and the champion goes for it.
function ProbeBossFight takes unit h returns boolean
    local real now = TimerGetElapsed(gPrClock)
    if gPrBossAt < 0.0 then
        set gPrBossAt = now
        call ProbeLog("event=boss_fixture wave=" + I2S(gLaneWave[0]) + " " + ProbeState())
        call KillUnit(gTower[0])
        call KillUnit(gNexus[0])
        set gPrBoss = gBoss[0]
        set gPrBossMax = GetUnitState(gPrBoss, UNIT_STATE_MAX_LIFE)
        set gPrDeathsAtBoss = gDeaths[0]
        call ProbeLog("event=boss_start hp=" + I2S(R2I(gPrBossMax)) + " spell_level=" + I2S(GetUnitAbilityLevel(gPrBoss, gBossSpell[0])) + " speed=" + I2S(R2I(GetUnitMoveSpeed(gPrBoss))))
    endif
    if gPrBoss == null or GetWidgetLife(gPrBoss) <= 0.405 then
        return false
    endif
    if ProbeDist(GetUnitX(h), GetUnitY(h), GetUnitX(gPrBoss), GetUnitY(gPrBoss)) < 900.0 then
        call ProbeCast(h, gPrBoss)
    endif
    if GetUnitCurrentOrder(h) == 0 or now >= gPrOrderAt + 4.0 then
        set gPrOrderAt = now
        call IssueTargetOrder(h, "attack", gPrBoss)
    endif
    return true
endfunction

function ProbeNearestEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    local real d
    if GetWidgetLife(u) > 0.405 then
        set d = ProbeDist(GetUnitX(gHero[0]), GetUnitY(gHero[0]), GetUnitX(u), GetUnitY(u))
        if d < gPrBest and (GetWidgetLife(gTower[0]) <= 0.405 or ProbeDist(GetUnitX(u), GetUnitY(u), GetUnitX(gTower[0]), GetUnitY(gTower[0])) >= gPrSafeDist) then
            set gPrBest = d
            set gPrBestX = GetUnitX(u)
            set gPrBestY = GetUnitY(u)
            set gPrBestU = u
        endif
    endif
    set u = null
endfunction

function ProbeHero takes nothing returns nothing
    local unit h = gHero[0]
    local real hp
    local real mx
    local real x
    local real y
    local unit tgt
    if h == null or GetWidgetLife(h) <= 0.405 then
        set h = null
        return
    endif
    set hp = GetWidgetLife(h)
    set mx = GetUnitState(h, UNIT_STATE_MAX_LIFE)
    set x = GetUnitX(h)
    set y = GetUnitY(h)
    if hp < gPrHpMin then
        set gPrHpMin = hp
    endif
    call ProbeLearn(h)
    if ProbeKeepChannel(h, hp, mx, x, y) then
        set h = null
        return
    endif
    if hp < mx * 0.4 then
        call ProbeDrink(h)
    endif
    if gPrMode == 3 and (gPrBossAt >= 0.0 or gLaneWave[0] >= gPrStallWave) then
        if ProbeBossFight(h) then
            set h = null
            return
        endif
    endif
    if gPrMode == 2 and gLaneWave[0] >= gPrStallWave and (gPrStalling or ProbeAlive() <= gPrStallAlive) then
        // the stall: leave the last monsters alive, stay away from them for good and let the clock run
        if not gPrStalling then
            set gPrStalling = true
            call ProbeLog("event=stall_start wave=" + I2S(gLaneWave[0]) + " " + ProbeState())
        endif
        if GetUnitCurrentOrder(h) != 851986 and ProbeDist(x, y, gPrFarX, gPrFarY) > 200.0 then
            call IssuePointOrder(h, "move", gPrFarX, gPrFarY)
        endif
        set h = null
        return
    endif
    if gPrMode == 1 and gPrPushHits > 0.0 then
        // experimental, off by default: a real push needs a player's judgement, this is not a campaign bot
        set tgt = ProbePushTarget(h)
        if tgt != null then
            if TimerGetElapsed(gPrClock) >= gPrOrderAt + 1.0 and GetUnitCurrentOrder(h) != 851983 then
                set gPrOrderAt = TimerGetElapsed(gPrClock)
                call IssueTargetOrder(h, "attack", tgt)
            endif
            set tgt = null
            set h = null
            return
        endif
    endif
    if GetWidgetLife(gTower[0]) > 0.405 and ProbeDist(x, y, GetUnitX(gTower[0]), GetUnitY(gTower[0])) < gPrSafeDist then
        // at once, not through the order limiter: one second of walking would take a chasing champion into the tower's range
        if GetUnitCurrentOrder(h) != 851986 then
            call IssuePointOrder(h, "move", gPrEX, gPrEY)
            set gPrOrderAt = TimerGetElapsed(gPrClock)
        endif
        set h = null
        return
    endif
    // like a player: go after the nearest monster the tower does not cover; no new order while the champion is
    // fighting, because every order would restart his swing
    set gPrBest = 1000000.0
    set gPrBestU = null
    call ForGroup(gWaveUnits, function ProbeNearestEnum)
    if gPrBest < 900.0 then
        call ProbeCast(h, gPrBestU)
    endif
    if gPrBest < 1000000.0 then
        if GetUnitCurrentOrder(h) == 0 or (gPrBest > 900.0 and TimerGetElapsed(gPrClock) >= gPrOrderAt + 3.0) then
            set gPrOrderAt = -100.0
            call ProbeOrderTo(h, "attack", gPrBestX, gPrBestY)
        endif
    elseif ProbeAlive() > 0 then
        // monsters alive, but all inside the tower's reach: back to the circle, out of their sight, so they march on
        // down the lane and come out to him. Ranged ones would otherwise stand and shoot from inside the safe zone.
        if ProbeDist(x, y, gHeroX[0], gHeroY[0]) > 150.0 and GetUnitCurrentOrder(h) != 851986 then
            call IssuePointOrder(h, "move", gHeroX[0], gHeroY[0])
            set gPrOrderAt = TimerGetElapsed(gPrClock)
        endif
    elseif GetUnitCurrentOrder(h) == 0 and ProbeDist(x, y, gPrEX, gPrEY) > 150.0 then
        call ProbeOrderTo(h, "attack", gPrEX, gPrEY)
    endif
    set h = null
endfunction

function ProbeTick takes nothing returns nothing
    local real now = TimerGetElapsed(gPrClock)
    if gPrDone then
        return
    endif
    call ProbeResolve()
    if gLaneWave[0] != gPrWave then
        if gPrWaveOpen then
            call ProbeWaveLine("next_wave_before_clear")
        endif
        set gPrWave = gLaneWave[0]
        set gPrWaveAt = now
        set gPrWaveCount = CountUnitsInGroup(gWaveUnits)
        set gPrWaveOpen = true
        call ProbeResetWave()
    elseif gPrWaveOpen and ProbeAlive() == 0 then
        set gPrWaveOpen = false
        call ProbeWaveLine("cleared")
    endif
    call ProbeHero()
    call ProbeProgress()
    // the run's limit first: no new purchase then, and the end waits until the last one has settled (ProbeResolve gives up after 2 s)
    if now >= gPrDuration or (gPrMaxWave > 0 and gLaneWave[0] > gPrMaxWave) then
        if ProbeResolve() then
            call ProbeFinish("limit")
        endif
        return
    endif
    if (gPrMode == 1 or gPrMode == 3) and gPrBuyDone and now >= gPrSpendAt + 1.0 and gHero[0] != null and GetWidgetLife(gHero[0]) > 0.405 then
        set gPrSpendAt = now
        call ProbeSpend()
    endif
    if gPrMode == 3 and gPrBossAt >= 0.0 and now >= gPrBossLogAt + 5.0 then
        set gPrBossLogAt = now
        if gPrBoss != null and GetWidgetLife(gPrBoss) > 0.405 then
            call ProbeLog("event=boss_tick life=" + I2S(R2I(GetWidgetLife(gPrBoss))) + " hero_hp=" + I2S(R2I(GetWidgetLife(gHero[0]))) + " deaths=" + I2S(gDeaths[0] - gPrDeathsAtBoss) + " casts=" + I2S(gPrCasts))
        elseif not gPrBossLogged then
            set gPrBossLogged = true
            call ProbeLog("event=boss_dead fight_s=" + R2SW(now - gPrBossAt, 1, 0) + " deaths=" + I2S(gDeaths[0] - gPrDeathsAtBoss) + " casts=" + I2S(gPrCasts))
            call ProbeFinish("boss_dead")
            return
        endif
    endif
    if now >= gPrBeatAt + 30.0 then
        set gPrBeatAt = now
        call ProbeLog("event=beat wave=" + I2S(gLaneWave[0]) + " " + ProbeState())
        call TestFlush()
    endif
endfunction

function ProbeBuyStep takes nothing returns nothing
    local string c
    if not ProbeResolve() then
        return
    endif
    if gPrBuyAt < StringLength(gPrBuy) then
        set c = SubString(gPrBuy, gPrBuyAt, gPrBuyAt + 1)
        set gPrBuyAt = gPrBuyAt + 1
        call ProbeBuy(c)
    else
        set gPrBuyDone = true
        call DestroyTimer(GetExpiredTimer())
        call ProbeStats("ready")
    endif
endfunction

// The champion is on his circle and the first-wave countdown runs.
function ProbeStart takes nothing returns nothing
    local trigger t
    local integer i
    local real tx = GetUnitX(gTower[0])
    local real ty = GetUnitY(gTower[0])
    local real d = ProbeDist(tx, ty, gHeroX[0], gHeroY[0])
    // the fallback point lies on the line tower -> circle, outside the tower's range and outside the champion's own
    // attack + acquire reach of the tower, so he never starts on the tower by himself
    set gPrSafeDist = gPrTowerRange + 300.0
    set gPrEngage = gPrSafeDist + 250.0
    set gPrEX = tx + (gHeroX[0] - tx) * gPrEngage / d
    set gPrEY = ty + (gHeroY[0] - ty) * gPrEngage / d
    set gPrFarX = gHallX
    set gPrFarY = gHallY - 1200.0
    call ProbeLog("event=start hero=" + GetUnitName(gHero[0]) + " tower_distance=" + I2S(R2I(d)) + " safe=" + I2S(R2I(gPrSafeDist)) + " fallback=" + I2S(R2I(gPrEngage)) + " " + ProbeTeam())
    if GetUnitTypeId(gHero[0]) != gHeroPool[gPrHero] then
        set gPrDone = true
        call TestLog("FAIL probe: the requested champion was not bought, got " + GetUnitName(gHero[0]))
        call TestLog("SELFTEST DONE")
        call TestFlush()
        return
    endif
    set i = 1
    loop
        exitwhen i >= 8
        if gHero[i] != null then
            set gPrDone = true
            call TestLog("FAIL probe: another champion in a solo sample, player " + I2S(i))
            call TestLog("SELFTEST DONE")
            call TestFlush()
            return
        endif
        set i = i + 1
    endloop
    call TriggerRegisterUnitEvent(gPrDealTrig, gTower[0], EVENT_UNIT_DAMAGED)
    call TriggerRegisterUnitEvent(gPrDealTrig, gNexus[0], EVENT_UNIT_DAMAGED)
    set gPrHpMin = GetWidgetLife(gHero[0])
    set t = CreateTrigger()
    call TriggerRegisterUnitEvent(t, gHero[0], EVENT_UNIT_DAMAGED)
    call TriggerAddAction(t, function ProbeOnHeroHit)
    set t = CreateTrigger()
    call TriggerRegisterUnitEvent(t, gHero[0], EVENT_UNIT_DEATH)
    call TriggerAddAction(t, function ProbeOnHeroDeath)
    set t = CreateTrigger()
    call TriggerRegisterUnitEvent(t, gCastle, EVENT_UNIT_DEATH)
    call TriggerAddAction(t, function ProbeOnCastleDeath)
    set t = null
    call ProbeLearn(gHero[0])
    call ProbeStats("naked")
    call IssuePointOrder(gHero[0], "attack", gPrEX, gPrEY)
    call TimerStart(CreateTimer(), 0.5, true, function ProbeBuyStep)
    call TimerStart(CreateTimer(), 0.25, true, function ProbeTick)
endfunction

function ProbeWaitHero takes nothing returns nothing
    if gHero[0] != null and gStarted then
        call DestroyTimer(GetExpiredTimer())
        call TimerStart(gPrClock, 100000.0, false, null)
        call ProbeStart()
    endif
endfunction

function ProbeBuyHero takes nothing returns nothing
    if gHero[0] != null or not gSelecting then
        call DestroyTimer(GetExpiredTimer())
        return
    endif
    set gPrTavernTries = gPrTavernTries + 1
    if IssueNeutralImmediateOrderById(Player(0), gTavern[0], gHeroPool[gPrHero]) then
        call TestLog("M tavern order accepted, try " + I2S(gPrTavernTries))
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

function ProbeBoot takes nothing returns nothing
    local trigger t = CreateTrigger()
    local region rg = CreateRegion()
    local rect rr = GetWorldBounds()
    call RegionAddRect(rg, rr)
    call RemoveRect(rr)
    call TriggerRegisterEnterRegion(t, rg, null)
    call TriggerAddAction(t, function ProbeOnEnter)
    set gPrDealTrig = CreateTrigger()
    call TriggerAddAction(gPrDealTrig, function ProbeOnEnemyHit)
    set t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)
    call TriggerAddAction(t, function ProbeOnSpell)
    set t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SUMMON, null)
    call TriggerAddAction(t, function ProbeOnSummon)
    set t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SPELL_CHANNEL, null)
    call TriggerAddAction(t, function ProbeOnChannel)
    set t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SPELL_ENDCAST, null)
    call TriggerAddAction(t, function ProbeOnEndCast)
    set gPrClock = CreateTimer()
    if gTestMode then
        call TestLog("FAIL probe: a test build is not a measurement")
        call TestLog("SELFTEST DONE")
        call TestFlush()
        set gPrDone = true
        return
    endif
    call SetRandomSeed(gPrSeed)
    call TestLog("M config mode=" + I2S(gPrMode) + " hero_index=" + I2S(gPrHero) + " buy=" + gPrBuy + " cycle=" + gPrCycle + " seed=" + I2S(gPrSeed) + " duration=" + I2S(R2I(gPrDuration)) + " " + ProbeTeam())
    call TimerStart(CreateTimer(), 0.5, true, function ProbeBuyHero)
    call TimerStart(CreateTimer(), 0.1, true, function ProbeWaitHero)
    set t = null
    set rg = null
    set rr = null
endfunction
