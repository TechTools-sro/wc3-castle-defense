//===========================================================================
// TechTools Castle Defence -- game logic (hand-written, vanilla JASS 1.27)
// Champion select -> each champion defends his own lane -> destroys his own
// enemy Nexus -> slays the boss that rises from it. The generator puts the globals block, InitData()
// and CreateNeutrals() above this file and config()/main() below it.
//===========================================================================

function Msg takes string s returns nothing
    call DisplayTimedTextToForce(GetPlayersAll(), 12.0, s)
endfunction

function TestLog takes string s returns nothing
    call Msg("|cff00ffff[TEST]|r " + s)
    set gTestLog[gTestLogN] = s
    set gTestLogN = gTestLogN + 1
endfunction

function TestB2S takes boolean b returns string
    if b then
        return "yes"
    endif
    return "no"
endfunction

function TestCheck takes boolean ok, string s returns nothing
    if ok then
        call TestLog("PASS " + s)
    else
        call TestLog("FAIL " + s)
    endif
endfunction


// A lane's or gate's entrance is two gate pieces wide.
function GateSet takes integer L, boolean open returns nothing
    if open then
        call SetDestructableInvulnerable(gGate[L], false)
        call SetDestructableInvulnerable(gGate2[L], false)
        call ModifyGateBJ(bj_GATEOPERATION_OPEN, gGate[L])
        call ModifyGateBJ(bj_GATEOPERATION_OPEN, gGate2[L])
    else
        call ModifyGateBJ(bj_GATEOPERATION_CLOSE, gGate[L])
        call ModifyGateBJ(bj_GATEOPERATION_CLOSE, gGate2[L])
        call SetDestructableInvulnerable(gGate[L], true)
        call SetDestructableInvulnerable(gGate2[L], true)
    endif
endfunction

function IsPlaying takes integer i returns boolean
    return GetPlayerSlotState(Player(i)) == PLAYER_SLOT_STATE_PLAYING
endfunction

function GiveAllGold takes integer gold returns nothing
    local integer i = 0
    loop
        exitwhen i >= 8
        if IsPlaying(i) then
            call SetPlayerState(Player(i), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(i), PLAYER_STATE_RESOURCE_GOLD) + gold)
        endif
        set i = i + 1
    endloop
endfunction

// The highest wave of any lane.
function HighestWave takes nothing returns integer
    local integer L = 0
    local integer w = 0
    loop
        exitwhen L > 11
        if gLaneWave[L] > w then
            set w = gLaneWave[L]
        endif
        set L = L + 1
    endloop
    return w
endfunction

function SideName takes integer p returns string
    if ModuloInteger(p, 2) == 0 then
        return "left"
    endif
    return "right"
endfunction

// First wave of a lane cleared (or its wave 2 starts) -> the champion jumps to level 2.
function GrantLevelTwo takes integer L returns nothing
    if gHero[L] != null and GetHeroLevel(gHero[L]) < 2 then
        call SetHeroLevel(gHero[L], 2, true)
        call DisplayTimedTextToPlayer(Player(L), 0.0, 0.0, 8.0, "|cffffcc00First wave cleared - your champion reached level 2!|r")
    endif
endfunction

//---------------------------------------------------------------------------
// Lane hints: coloured Circle of Power + floating label at the lane entrance,
// minimap ping and a message to the owner.
//---------------------------------------------------------------------------
function LaneName takes integer p returns string
    return gDirName[p / 2] + " front, " + SideName(p) + " lane"
endfunction

function PingLane takes integer p returns nothing
    call PingMinimapForPlayer(Player(p), gLaneMarkX[p], gLaneMarkY[p], 5.0)
    call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 10.0, "Your lane: " + gPlayerColorCode[p] + LaneName(p) + "|r.  Circle = stat shop.")
endfunction

// Arm (faction / roster index) of a lane: lanes 0-7 -> 0-3, the gate lanes 8 (Level 2) -> 4 and 9 (Level 3) -> 5.
function LaneArm takes integer L returns integer
    if L >= 8 then
        return L - 4
    endif
    return L / 2
endfunction

// Current price step of kind s for player p. Hero kinds count per player; castle kinds (type 3/4) count
// globally, because the castle is shared and each castle bonus ability can only be added once.
function KindNext takes integer p, integer s returns integer
    if gKindType[s] >= 3 then
        return gCastleNext[s]
    endif
    return gStatNext[p * 16 + s]
endfunction

// The circle sells the CURRENT price step of every kind; every item has a fixed button position:
// row 1 = Health, Mana, Damage, Armor; row 2 = Strength, Agility, Intelligence, All stats;
// The castle kinds (type 3/4) are sold by the castle itself -> StockCastle.
function StockCircle takes integer p returns nothing
    local integer s = 0
    local integer id
    if gLaneMarker[p] == null then
        return
    endif
    // remove only what this script put in stock, then re-add the current price steps
    loop
        exitwhen s >= gKinds
        if gStocked[p * 16 + s] != 0 then
            call RemoveItemFromStock(gLaneMarker[p], gStocked[p * 16 + s])
            set gStocked[p * 16 + s] = 0
        endif
        set s = s + 1
    endloop
    set s = 0
    loop
        exitwhen s >= gKinds
        if gKindType[s] < 3 and KindNext(p, s) < gStatTiers then
            set id = gStatItem[s * gKindStride + KindNext(p, s)]
            call AddItemToStock(gLaneMarker[p], id, 1, 1)
            set gStocked[p * 16 + s] = id
        endif
        set s = s + 1
    endloop
endfunction

// The castle sells its own upgrades (current global price step). Its stock is tracked in gStocked[128 + s];
// clear those slots whenever a NEW castle unit is created (it starts with an empty stock).
function StockCastle takes nothing returns nothing
    local integer s = 0
    local integer id
    if gCastle == null or GetWidgetLife(gCastle) <= 0.405 then
        return
    endif
    loop
        exitwhen s >= gKinds
        if gStocked[128 + s] != 0 then
            call RemoveItemFromStock(gCastle, gStocked[128 + s])
            set gStocked[128 + s] = 0
        endif
        set s = s + 1
    endloop
    set s = 0
    loop
        exitwhen s >= gKinds
        if gKindType[s] >= 3 and gCastleNext[s] < gStatTiers then
            set id = gStatItem[s * gKindStride + gCastleNext[s]]
            call AddItemToStock(gCastle, id, 1, 1)
            set gStocked[128 + s] = id
        endif
        set s = s + 1
    endloop
endfunction

// Castle Shockwave (bought for a tree): magic damage to every monster near the castle.
function CastleShockwave takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    local integer o
    local integer i = 0
    local real cx = GetUnitX(gCastle)
    local real cy = GetUnitY(gCastle)
    local real dmg = 300.0 + 30.0 * I2R(HighestWave())
    call GroupEnumUnitsInRange(g, cx, cy, 1100.0, null)
    // wave monsters lose a quarter of their max HP, at any wave; anything else (a boss) the fixed amount
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        set o = GetPlayerId(GetOwningPlayer(u))
        if o >= 8 and o <= 11 and GetWidgetLife(u) > 0.405 then
            if IsUnitInGroup(u, gWaveUnits) then
                call UnitDamageTarget(gCastle, u, 0.25 * GetUnitState(u, UNIT_STATE_MAX_LIFE), true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
            else
                call UnitDamageTarget(gCastle, u, dmg, true, false, ATTACK_TYPE_MAGIC, DAMAGE_TYPE_MAGIC, WEAPON_TYPE_WHOKNOWS)
            endif
        endif
    endloop
    call DestroyGroup(g)
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\Thunderclap\\ThunderClapCaster.mdl", cx, cy))
    loop
        exitwhen i >= 12
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Orc\\WarStomp\\WarStompCaster.mdl", cx + 650.0 * Cos(i * 0.5236), cy + 650.0 * Sin(i * 0.5236)))
        set i = i + 1
    endloop
    set g = null
endfunction

// Gives the living champion every circle bonus bought so far: one hidden item-bonus ability per buy (green +N,
// base stats untouched; gStatApplied = how many are on the champion) and pending Experience buys
// (one level's worth of XP each, NeedHeroXP step = 100 x (level + 1)).
function ApplyBought takes integer p returns nothing
    local integer s = 0
    local boolean fx = false
    local unit h = gHero[p]
    if h == null or GetWidgetLife(h) <= 0.405 then
        set h = null
        return
    endif
    loop
        exitwhen s >= gKinds
        if gKindType[s] == 1 then
            loop
                exitwhen gStatApplied[p * 16 + s] >= gStatNext[p * 16 + s]
                call UnitAddAbility(h, gBonusAbil[s * gKindStride + gStatApplied[p * 16 + s]])
                // a morph (Metamorphosis) would drop what is not permanent
                call UnitMakeAbilityPermanent(h, true, gBonusAbil[s * gKindStride + gStatApplied[p * 16 + s]])
                set gStatApplied[p * 16 + s] = gStatApplied[p * 16 + s] + 1
                set fx = true
            endloop
        endif
        set s = s + 1
    endloop
    loop
        exitwhen gXpPending[p] <= 0
        call AddHeroXP(h, 100 * (GetHeroLevel(h) + 1), true)
        set gXpPending[p] = gXpPending[p] - 1
        set fx = true
    endloop
    if fx then
        call DestroyEffect(AddSpecialEffectTarget("Abilities\\Spells\\Items\\AIlm\\AIlmTarget.mdl", h, "origin"))
    endif
    set h = null
endfunction

// A shop item was picked up: add the next hidden bonus ability (hero kinds) or upgrade the castle
// (castle kinds), remove the item, step the price up 5 % and restock.
function AdvanceStatPrice takes integer p, item it returns nothing
    local integer id = GetItemTypeId(it)
    local integer s = 0
    local integer k
    loop
        exitwhen s >= gKinds
        set k = KindNext(p, s)
        if k < gStatTiers and gStatItem[s * gKindStride + k] == id then
            if gKindType[s] >= 3 then
                // castle buy (costs a tree): stacking upgrades (type 4) step a global counter, repair (3) and
                // shockwave (5) are the same item every time; applies even while the champion is dead
                if gKindType[s] == 4 then
                    set gCastleNext[s] = k + 1
                endif
                call RemoveItem(it)
                if GetWidgetLife(gCastle) > 0.405 then
                    if gKindType[s] == 3 then
                        call SetWidgetLife(gCastle, GetWidgetLife(gCastle) + I2R(gKindValue[s]))
                    elseif gKindType[s] == 4 then
                        call UnitAddAbility(gCastle, gBonusAbil[s * gKindStride + k])
                    else
                        call CastleShockwave()
                    endif
                    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Spells\\Human\\Heal\\HealTarget.mdl", gCastle, "origin"))
                endif
                call Msg(gPlayerColorCode[p] + GetPlayerName(Player(p)) + "|r: |cffffcc00" + gKindEffect[s] + "|r")
                call StockCastle()
                return
            endif
            // the buy counts AT ONCE (price +5 %), even while the champion is dead or not picked yet;
            // ApplyBought hands the bonus over as soon as the champion is alive
            set gStatNext[p * 16 + s] = k + 1
            call RemoveItem(it)
            if gKindType[s] == 2 then
                set gXpPending[p] = gXpPending[p] + 1
                call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00+1 level|r")
            else
                call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00+" + I2S(gKindValue[s]) + " " + gKindName[s] + "|r")
            endif
            call ApplyBought(p)
            call StockCircle(p)
            return
        endif
        set s = s + 1
    endloop
endfunction

// Bank: 1 tree buys +gIncomeStep (INCOME_STEP in gen/objects.py, 100) gold income per minute, paid by IncomeTick when BankTick has counted a full minute.
function BuyIncome takes integer p, item it returns nothing
    call RemoveItem(it)
    set gIncome[p] = gIncome[p] + gIncomeStep
    call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 5.0, "|cffffcc00Income +" + I2S(gIncomeStep) + "|r   now " + I2S(gIncome[p]) + " gold/min")
endfunction

// Long Reach: +gReachStep attack range, once, melee champions only (instant level of the range upgrade gReachTech).
// A ranged champion or a second buy is refunded - ranged champions must never outrange the towers.
function TryReach takes integer p, item it returns boolean
    local integer lvl
    if GetItemTypeId(it) != gReachItem or gReachItem == 0 then
        return false
    endif
    call RemoveItem(it)
    set lvl = GetPlayerTechCount(Player(p), gReachTech, true)
    if gHero[p] == null or not IsUnitType(gHero[p], UNIT_TYPE_MELEE_ATTACKER) then
        call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + gReachPrice)
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 5.0, "|cffffcc00Long Reach|r is for melee champions only - refunded")
    elseif lvl >= gReachMax then
        call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + gReachPrice)
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 5.0, "|cffffcc00Long Reach|r: you already have it - refunded")
    else
        call SetPlayerTechResearched(Player(p), gReachTech, lvl + 1)
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 5.0, "|cffffcc00Long Reach|r: +" + I2S(gReachStep) + " attack range")
    endif
    return true
endfunction

function IncomeTick takes integer p returns nothing
    if gIncome[p] > 0 and IsPlaying(p) then
        call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + gIncome[p])
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00+" + I2S(gIncome[p]) + " gold|r income")
    endif
endfunction

// The Bank's clock, per player: one payment per 60 counted seconds. Every wave of his own lane gives it gIncomeWaveSeconds to
// count, and only his next wave renews that, so holding a wave (a stalled last monster, a kill now and then, a long break) pays
// two minutes at most. The final fight has no waves and always counts. Called every second.
function BankTick takes nothing returns nothing
    local integer p = 0
    loop
        exitwhen p >= 8
        if gFinalPhase or gIncomeBudget[p] > 0 then
            set gIncomeClock[p] = gIncomeClock[p] + 1
            if not gFinalPhase then
                set gIncomeBudget[p] = gIncomeBudget[p] - 1
                if gIncomeBudget[p] == 0 and gIncome[p] > 0 then
                    call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 8.0, "|cffffcc00Bank stopped|r until your next wave")
                endif
            endif
            if ModuloInteger(gIncomeClock[p], 60) == 0 then
                call IncomeTick(p)
            endif
        endif
        set p = p + 1
    endloop
endfunction

// A new wave on lane L renews the Bank of that lane's player. A player whose lane is finished has nothing left to hold: any wave renews his.
function BankRenew takes integer L returns nothing
    local integer p = 0
    if L < 8 then
        set gIncomeBudget[L] = gIncomeWaveSeconds
    endif
    loop
        exitwhen p >= 8
        if gLaneState[p] == 2 then
            set gIncomeBudget[p] = gIncomeWaveSeconds
        endif
        set p = p + 1
    endloop
endfunction

// Premium items level up: picking up a shop (Lv 1) premium item while already holding the same item merges
// both into the next level. At the max level the new one is refunded.
function PremiumLevel takes integer id, integer fam returns integer
    local integer L = 1
    loop
        exitwhen L > gPremMax
        if gPremItem[fam * 8 + L] == id then
            return L
        endif
        set L = L + 1
    endloop
    return 0
endfunction

// Premium family of an item type (any level), -1 = not a premium item.
function PremiumFamily takes integer id returns integer
    local integer fam = 0
    loop
        exitwhen fam >= gPremCount
        if PremiumLevel(id, fam) > 0 then
            return fam
        endif
        set fam = fam + 1
    endloop
    return -1
endfunction

// Two premium items of the same family in one inventory merge into one: level = sum of both (Lv 1 bought while
// holding Lv 3 -> Lv 4), capped at gPremMax, any level above the cap is refunded. Event-independent: called on buy,
// on pickup AND every 0.2 s from GrabTick, so it works no matter which shop event the engine fires.
function MergePremium takes unit h returns boolean
    local integer a = 0
    local integer b
    local integer fam
    local integer L
    local item ia
    local item ib
    local player pl
    if h == null or GetWidgetLife(h) <= 0.405 then
        return false
    endif
    set pl = GetOwningPlayer(h)
    loop
        exitwhen a >= 5
        set ia = UnitItemInSlot(h, a)
        set fam = -1
        if ia != null then
            set fam = PremiumFamily(GetItemTypeId(ia))
        endif
        if fam >= 0 then
            set b = a + 1
            loop
                exitwhen b >= 6
                set ib = UnitItemInSlot(h, b)
                if ib != null and ib != ia and PremiumFamily(GetItemTypeId(ib)) == fam then
                    set L = PremiumLevel(GetItemTypeId(ia), fam) + PremiumLevel(GetItemTypeId(ib), fam)
                    call RemoveItem(ib)
                    call RemoveItem(ia)
                    if L > gPremMax then
                        call SetPlayerState(pl, PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(pl, PLAYER_STATE_RESOURCE_GOLD) + gPremPrice * (L - gPremMax))
                        call DisplayTimedTextToPlayer(pl, 0.0, 0.0, 5.0, "|cffffcc00" + gPremName[fam] + "|r is already max rank - refunded")
                        set L = gPremMax
                    else
                        call DisplayTimedTextToPlayer(pl, 0.0, 0.0, 5.0, "|cffffcc00" + gPremName[fam] + "|r |cff4fc3ffRank " + I2S(L) + "|r: " + gPremEffect[fam * 8 + L])
                    endif
                    call UnitAddItemToSlotById(h, gPremItem[fam * 8 + L], a)
                    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Spells\\Items\\AIem\\AIemTarget.mdl", h, "origin"))
                    set ia = null
                    set ib = null
                    set pl = null
                    return true
                endif
                set b = b + 1
            endloop
        endif
        set a = a + 1
    endloop
    set ia = null
    set ib = null
    set pl = null
    return false
endfunction

function MergePremiumAll takes unit h returns nothing
    local integer n = 0
    loop
        exitwhen n >= 6 or not MergePremium(h)
        set n = n + 1
    endloop
endfunction

// Apothecary potions: heal a percent of max HP / mana on use; the same potion stacks into one slot.
function PotionIndex takes integer id returns integer
    local integer i = 0
    loop
        exitwhen i >= gPotCount
        if gPotItem[i] == id then
            return i
        endif
        set i = i + 1
    endloop
    return -1
endfunction

function PotionTokenIndex takes integer id returns integer
    local integer i = 0
    loop
        exitwhen i >= gPotCount
        if gPotToken[i] == id then
            return i
        endif
        set i = i + 1
    endloop
    return -1
endfunction

// A potion token was bought: +1 charge on the potion the champion carries, else a new potion in a free slot, else
// (full inventory, no such potion, or champion dead: his buyer pays) the gold comes back.
function GivePotion takes integer p, integer i returns nothing
    local unit h = gHero[p]
    local integer s = 0
    local item o
    if h != null and GetWidgetLife(h) > 0.405 then
        loop
            exitwhen s >= 6
            set o = UnitItemInSlot(h, s)
            if o != null and GetItemTypeId(o) == gPotItem[i] then
                call SetItemCharges(o, GetItemCharges(o) + 1)
                set o = null
                set h = null
                return
            endif
            set s = s + 1
        endloop
        if UnitInventoryCount(h) < 6 then
            call UnitAddItemById(h, gPotItem[i])
            set h = null
            return
        endif
    endif
    call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + gPotPrice[i])
    if h != null and GetWidgetLife(h) > 0.405 then
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00Inventory full|r - refunded")
    else
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00Champion is dead|r - refunded")
    endif
    set o = null
    set h = null
endfunction

function StackPotion takes unit h, item it returns boolean
    local integer id = GetItemTypeId(it)
    local integer s = 0
    local item o
    if h == null or id == 0 or PotionIndex(id) < 0 then
        return false
    endif
    loop
        exitwhen s >= 6
        set o = UnitItemInSlot(h, s)
        if o != null and o != it and GetItemTypeId(o) == id then
            call SetItemCharges(o, GetItemCharges(o) + IMaxBJ(GetItemCharges(it), 1))
            call RemoveItem(it)
            set o = null
            return true
        endif
        set s = s + 1
    endloop
    set o = null
    return false
endfunction

// Event-independent stacking (Jiri, v3.0: bought potions still took 2 slots): merges every pair of same-type potions
// in the inventory into the first slot. Run every 0.2 s from GrabTick and after every buy.
function MergePotions takes unit h returns nothing
    local integer a = 0
    local integer b
    local item ia
    local item ib
    if h == null or GetWidgetLife(h) <= 0.405 then
        return
    endif
    loop
        exitwhen a >= 5
        set ia = UnitItemInSlot(h, a)
        if ia != null and PotionIndex(GetItemTypeId(ia)) >= 0 then
            set b = a + 1
            loop
                exitwhen b >= 6
                set ib = UnitItemInSlot(h, b)
                if ib != null and ib != ia and GetItemTypeId(ib) == GetItemTypeId(ia) then
                    call SetItemCharges(ia, GetItemCharges(ia) + IMaxBJ(GetItemCharges(ib), 1))
                    call RemoveItem(ib)
                endif
                set b = b + 1
            endloop
        endif
        set a = a + 1
    endloop
    set ia = null
    set ib = null
endfunction

function DrinkPotion takes unit u, item it returns boolean
    local integer i = PotionIndex(GetItemTypeId(it))
    if i < 0 then
        return false
    endif
    if gPotHp[i] > 0 then
        call SetWidgetLife(u, GetWidgetLife(u) + GetUnitState(u, UNIT_STATE_MAX_LIFE) * gPotHp[i] / 100.0)
    endif
    if gPotMp[i] > 0 then
        call SetUnitState(u, UNIT_STATE_MANA, GetUnitState(u, UNIT_STATE_MANA) + GetUnitState(u, UNIT_STATE_MAX_MANA) * gPotMp[i] / 100.0)
    endif
    return true
endfunction

// Neutral shops (grove, castle) fire "item sold". WarCraft does NOT fire "picked up" for a permanent item bought
// from a neutral shop, and a REMOTE purchase leaves the item on the ground at the shop. So here: a Bank buy is
// counted, anything else is handed to the buyer if needed and a premium item is merged (upgrade). An item that the
// pickup handler already handled is gone (type 0) and is left alone - no double count.
function OnItemSold takes nothing returns nothing
    local item it = GetSoldItem()
    local unit b = GetBuyingUnit()
    local integer p = GetPlayerId(GetOwningPlayer(b))
    if p < 8 and GetItemTypeId(it) != 0 then
        if GetItemTypeId(it) == gBankItem then
            call BuyIncome(p, it)
        elseif TryReach(p, it) then
            // Long Reach applied
        elseif PotionTokenIndex(GetItemTypeId(it)) >= 0 then
            call GivePotion(p, PotionTokenIndex(GetItemTypeId(it)))
            call RemoveItem(it)
        elseif gPendN < 64 then
            // NEVER add the item here: when the buyer is in range the game puts it into the inventory right after
            // this event, and adding it too put the SAME item into two slots (verified in-game, v3.3: 1 potion
            // order = 2 slots, then the stack sweep removed it). The 0.2 s sweep (PendingTick) hands over only what
            // is still on the ground (remote buys); MergePotions / MergePremium stack and upgrade afterwards.
            set gPendItem[gPendN] = it
            set gPendP[gPendN] = p
            set gPendN = gPendN + 1
        endif
    endif
    set it = null
    set b = null
endfunction

function OnItemPickup takes nothing returns nothing
    local integer p = GetPlayerId(GetOwningPlayer(GetTriggerUnit()))
    local item it = GetManipulatedItem()
    if p < 8 and GetItemTypeId(it) != 0 and PotionTokenIndex(GetItemTypeId(it)) >= 0 then
        call GivePotion(p, PotionTokenIndex(GetItemTypeId(it)))
        call RemoveItem(it)
        set it = null
        return
    endif
    if GetTriggerEventId() == EVENT_PLAYER_UNIT_USE_ITEM and DrinkPotion(GetTriggerUnit(), it) then
        set it = null
        return
    endif
    if GetTriggerEventId() == EVENT_PLAYER_UNIT_PICKUP_ITEM and StackPotion(GetTriggerUnit(), it) then
        set it = null
        return
    endif
    if p < 8 and GetTriggerUnit() == gHero[p] and PremiumFamily(GetItemTypeId(it)) >= 0 then
        call MergePremiumAll(gHero[p])
        set it = null
        return
    endif
    if p < 8 and TryReach(p, it) then
        set it = null
        return
    endif
    if p < 8 then
        if GetItemTypeId(it) == gBankItem then
            call BuyIncome(p, it)
        else
            call AdvanceStatPrice(p, it)
        endif
    endif
    set it = null
endfunction

// Bought shop items that landed on the ground go straight into the owner's champion (used at once).
function GrabTomeEnum takes nothing returns nothing
    local item it = GetEnumItem()
    local integer id = GetItemTypeId(it)
    local integer p = gGrabP
    local integer s = 0
    loop
        exitwhen s >= gKinds
        if KindNext(p, s) < gStatTiers and gStatItem[s * gKindStride + KindNext(p, s)] == id then
            call UnitAddItem(gHero[p], it)
            set it = null
            return
        endif
        set s = s + 1
    endloop
    set it = null
endfunction

// Bought items from the neutral shops: once the game has delivered them (owned) nothing to do; still on the ground
// (remote buy) -> into the buyer's champion, or next to him when the inventory is full.
function PendingTick takes nothing returns nothing
    local integer i = gPendN - 1
    local item it
    local unit h
    loop
        exitwhen i < 0
        set it = gPendItem[i]
        set h = gHero[gPendP[i]]
        if GetItemTypeId(it) != 0 and not IsItemOwned(it) and h != null and GetWidgetLife(h) > 0.405 then
            if not UnitAddItem(h, it) then
                call SetItemPosition(it, GetUnitX(h), GetUnitY(h))
            endif
        elseif GetItemTypeId(it) != 0 and not IsItemOwned(it) then
            // his champion is dead: a castle buy counts now, anything else waits for him
            call AdvanceStatPrice(gPendP[i], it)
        endif
        if GetItemTypeId(it) == 0 or IsItemOwned(it) or (h != null and GetWidgetLife(h) > 0.405) then
            set gPendN = gPendN - 1
            set gPendItem[i] = gPendItem[gPendN]
            set gPendP[i] = gPendP[gPendN]
            set gPendItem[gPendN] = null
        endif
        set i = i - 1
    endloop
    set it = null
    set h = null
endfunction

// A shop sells only to a nearby living unit with an inventory ("Requires: Nearby Patron"), so a player whose champion
// is dead could not buy at the castle. While he is dead a tiny buyer of his stands in the dark, in the castle shop's
// range. Hidden or with Locust the game does not take it (measured). It must go when he lives: a shop sells to the
// player's closest such unit, and that could be this one. Whatever it still holds goes to him then.
function BuyerTick takes integer p returns nothing
    local integer s = 0
    local item it
    if gHero[p] != null and GetWidgetLife(gHero[p]) <= 0.405 then
        if gBuyer[p] == null or GetUnitTypeId(gBuyer[p]) == 0 then
            set gBuyer[p] = CreateUnit(Player(p), gBuyerType, gBuyerX, gBuyerY, 270.0)
            call SetUnitX(gBuyer[p], gBuyerX)
            call SetUnitY(gBuyer[p], gBuyerY)
        endif
    elseif gBuyer[p] != null then
        loop
            exitwhen s >= 6
            set it = UnitItemInSlot(gBuyer[p], s)
            if it != null then
                call UnitRemoveItem(gBuyer[p], it)
                if gHero[p] != null and not UnitAddItem(gHero[p], it) then
                    call SetItemPosition(it, GetUnitX(gHero[p]), GetUnitY(gHero[p]))
                endif
            endif
            set s = s + 1
        endloop
        call RemoveUnit(gBuyer[p])
        set gBuyer[p] = null
    endif
    set it = null
endfunction

// Champion dead: a circle buy lands on the ground or in the dead champion's inventory and is never "used" ->
// count it directly (price steps at once, the bonus follows on revive via ApplyBought).
function GrabDeadEnum takes nothing returns nothing
    call AdvanceStatPrice(gGrabP, GetEnumItem())
endfunction

function GrabTick takes nothing returns nothing
    local integer p = 0
    local integer s
    call PendingTick()
    loop
        exitwhen p >= 8
        call BuyerTick(p)
        if gHero[p] != null and gCircleRect[p] != null and GetWidgetLife(gHero[p]) <= 0.405 then
            set gGrabP = p
            call EnumItemsInRect(gCircleRect[p], null, function GrabDeadEnum)
            set s = 0
            loop
                exitwhen s >= 6
                if UnitItemInSlot(gHero[p], s) != null then
                    call AdvanceStatPrice(p, UnitItemInSlot(gHero[p], s))
                endif
                set s = s + 1
            endloop
        endif
        if gHero[p] != null then
            call ApplyBought(p)
            call MergePotions(gHero[p])
        endif
        if gHero[p] != null and gCircleRect[p] != null and GetWidgetLife(gHero[p]) > 0.405 then
            set gGrabP = p
            call EnumItemsInRect(gCircleRect[p], null, function GrabTomeEnum)
        endif
        if gHero[p] != null then
            call MergePremiumAll(gHero[p])
        endif
        set p = p + 1
    endloop
endfunction

// Every level-up refills HP and mana. Past the last learnable "Attributes" level the stats come automatically.
// ---- The champions' own triggers, as X Hero Siege 3.28 has them: their abilities are native, only these few need a script.
// Level 20: each champion's extra ability. Any later level-up finds it there, so a jump past 20 gets it too. (gGrant*: hero, ability, ability it replaces, permanent)
function HeroGrants takes unit h returns nothing
    local integer t = GetUnitTypeId(h)
    local integer k = 0
    local boolean gave = false
    if GetHeroLevel(h) < gGrantLevel then
        return
    endif
    if t == gDemonForm then
        set t = gDemonHero
    endif
    loop
        exitwhen k >= gGrantN
        if gGrantHero[k] == t and GetUnitAbilityLevel(h, gGrantAbil[k]) == 0 then
            if gGrantDrop[k] != 0 then
                call UnitRemoveAbility(h, gGrantDrop[k])
            endif
            call UnitAddAbility(h, gGrantAbil[k])
            if gGrantPerm[k] then
                call UnitMakeAbilityPermanent(h, true, gGrantAbil[k])
            endif
            set gave = true
        endif
        set k = k + 1
    endloop
    if gave then
        call DisplayTimedTextToPlayer(GetOwningPlayer(h), 0.0, 0.0, 10.0, "|cffffcc00Hero level " + I2S(gGrantLevel) + ":|r a new ability. One button may not fit on the card until all your skills are at max rank.")
    endif
endfunction

// Thunder Clap and War Stomp strike twice from level 20: the second ability is added when the order is given, and used when the first takes effect.
function OnHeroGlueOrder takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer t = GetUnitTypeId(u)
    if GetUnitLevel(u) >= gGrantLevel then
        if GetIssuedOrderId() == gOrderClap and t == 'Hmkg' then
            call UnitAddAbility(u, 'A04P')
        elseif GetIssuedOrderId() == gOrderStomp and t == 'Otch' and GetUnitAbilityLevel(u, 'B00N') > 0 then
            call UnitAddAbility(u, 'A01O')
        endif
    endif
    set u = null
endfunction

// Storm Bolt and Shockwave strike twice too, Light Frenzy resets its target's cooldowns.
function OnHeroGlueSpell takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local unit tgt = GetSpellTargetUnit()
    local integer a = GetSpellAbilityId()
    local integer t = GetUnitTypeId(u)
    local real x = GetSpellTargetX()
    local real y = GetSpellTargetY()
    if GetUnitLevel(u) >= gGrantLevel then
        if a == 'A010' and t == 'Hpal' then
            call UnitResetCooldown(tgt)
        elseif a == 'AHtc' and t == 'Hmkg' then
            call IssueImmediateOrderById(u, gOrderCreepClap)
            call TriggerSleepAction(0.5)
            call UnitRemoveAbility(u, 'A04P')
        elseif a == 'AHtb' and t == 'Hmkg' then
            call UnitAddAbility(u, 'A02V')
            call TriggerSleepAction(0.1)
            call IssueTargetOrderById(u, gOrderCreepBolt, tgt)
            call TriggerSleepAction(0.5)
            call UnitRemoveAbility(u, 'A02V')
        elseif a == 'AOws' and t == 'Otch' and GetUnitAbilityLevel(u, 'B00N') > 0 then
            call IssueImmediateOrderById(u, gOrderCreepClap)
            call TriggerSleepAction(0.5)
            call UnitRemoveAbility(u, 'A01O')
        elseif a == 'AOsh' and t == 'Otch' and GetUnitAbilityLevel(u, 'B00N') > 0 then
            call UnitAddAbility(u, 'A04Q')
            call TriggerSleepAction(0.1)
            if tgt != null and IsUnitInRange(tgt, u, 1000.0) then
                set x = GetUnitX(tgt)
                set y = GetUnitY(tgt)
            endif
            call IssuePointOrderById(u, gOrderCreepSwarm, x, y)
            call TriggerSleepAction(0.5)
            call UnitRemoveAbility(u, 'A04Q')
        endif
    endif
    set u = null
    set tgt = null
endfunction

// War Drums is an empty placeholder to learn: each level swaps in the real aura.
function OnHeroGlueLearn takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer L
    if GetLearnedSkill() == 'A045' and GetUnitTypeId(u) == 'Obla' then
        set L = GetUnitAbilityLevel(u, 'A045')
        if L > 1 then
            call UnitRemoveAbility(u, gDrumAura[L - 1])
        endif
        call UnitAddAbility(u, gDrumAura[L])
    endif
    set u = null
endfunction

function OnHeroLevel takes nothing returns nothing
    local unit h = GetTriggerUnit()
    call HeroGrants(h)
    if GetHeroLevel(h) > gAttrMaxHeroLevel then
        call SetHeroStr(h, GetHeroStr(h, false) + gAttrPerLevel, true)
        call SetHeroAgi(h, GetHeroAgi(h, false) + gAttrPerLevel, true)
        call SetHeroInt(h, GetHeroInt(h, false) + gAttrPerLevel, true)
    endif
    call SetUnitState(h, UNIT_STATE_LIFE, GetUnitState(h, UNIT_STATE_MAX_LIFE))
    call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Spells\\Human\\HolyBolt\\HolyBoltSpecialArt.mdl", h, "origin"))
    set h = null
endfunction

function ShowLaneHint takes integer p returns nothing
    local texttag tt
    if gLaneMarker[p] == null then
        set gLaneMarker[p] = CreateUnit(Player(p), gCircleType, gLaneMarkX[p], gLaneMarkY[p], 270.0)
        call SetUnitInvulnerable(gLaneMarker[p], true)
        set gCircleRect[p] = Rect(gLaneMarkX[p] - 500.0, gLaneMarkY[p] - 500.0, gLaneMarkX[p] + 500.0, gLaneMarkY[p] + 500.0)
        call StockCircle(p)
        set tt = CreateTextTag()
        call SetTextTagText(tt, gPlayerColorCode[p] + GetPlayerName(Player(p)) + "|r's lane", 0.028)
        call SetTextTagPos(tt, gLaneLabelX[p], gLaneLabelY[p], 60.0)
        call SetTextTagPermanent(tt, true)
        call SetTextTagVisibility(tt, true)
        set tt = null
    endif
    call PingLane(p)
endfunction

//---------------------------------------------------------------------------
// Scoreboard
//---------------------------------------------------------------------------
function BoardSet takes integer row, integer col, string s returns nothing
    local multiboarditem it
    if gBoard == null then
        return
    endif
    set it = MultiboardGetItem(gBoard, row, col)
    call MultiboardSetItemValue(it, s)
    call MultiboardReleaseItem(it)
    set it = null
endfunction

// Game time as m:ss (h:mm:ss after an hour).
function TimeText takes integer s returns string
    local integer h = s / 3600
    local integer m = ModuloInteger(s / 60, 60)
    local integer sec = ModuloInteger(s, 60)
    local string out = I2S(m)
    if h > 0 then
        set out = I2S(h) + ":"
        if m < 10 then
            set out = out + "0"
        endif
        set out = out + I2S(m)
    endif
    if sec < 10 then
        return out + ":0" + I2S(sec)
    endif
    return out + ":" + I2S(sec)
endfunction

// A lane's wave for the scoreboard: "done" once its boss is dead.
function BoardWave takes integer L returns string
    if (L >= 8 and gGateState[L] == 2) or (L < 8 and gLaneState[L] == 2) then
        return "|cff40ff40done|r"
    endif
    return I2S(gLaneWave[L])
endfunction

// Compact scoreboard: the title carries game time + castle HP; one row per player = name, level, his own wave, kills,
// deaths, income (gold per minute from the Bank); an opened gate adds a row with its own wave (BoardAddGate).
function UpdateBoard takes nothing returns nothing
    local integer i
    local string castle
    if gBoard == null then
        return
    endif
    if GetWidgetLife(gCastle) > 0.405 then
        // current / max: max follows the bought Castle Health upgrades
        set castle = I2S(R2I(GetWidgetLife(gCastle))) + " / " + I2S(R2I(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE)))
    else
        set castle = "|cffff0000Fallen|r"
    endif
    if gFinalBoss != null then
        call MultiboardSetTitleText(gBoard, "|cff4fc3ff" + TimeText(gGameTime) + "|r    |cffff4040FINAL BOSS|r  |cffffcc00" + I2S(R2I(GetWidgetLife(gFinalBoss) / 1000.0)) + "k / " + I2S(R2I(GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE) / 1000.0)) + "k|r")
    elseif gFinalPhase then
        call MultiboardSetTitleText(gBoard, "|cff4fc3ff" + TimeText(gGameTime) + "|r    |cffff4040FINAL BOSS awakens...|r")
    else
        call MultiboardSetTitleText(gBoard, "|cff4fc3ff" + TimeText(gGameTime) + "|r    Castle |cffffcc00" + castle + "|r")
    endif
    set i = 0
    loop
        exitwhen i >= 8
        if gBoardRow[i] > 0 then
            if gHero[i] != null then
                call BoardSet(gBoardRow[i], 1, I2S(GetHeroLevel(gHero[i])))
            else
                call BoardSet(gBoardRow[i], 1, "-")
            endif
            call BoardSet(gBoardRow[i], 2, BoardWave(i))
            call BoardSet(gBoardRow[i], 3, I2S(gKills[i]))
            call BoardSet(gBoardRow[i], 4, I2S(gDeaths[i]))
            call BoardSet(gBoardRow[i], 5, "|cffffcc00+" + I2S(gIncome[i]) + "|r")
        endif
        set i = i + 1
    endloop
    loop
        exitwhen i > 11
        if gBoardRow[i] > 0 then
            call BoardSet(gBoardRow[i], 2, BoardWave(i))
        endif
        set i = i + 1
    endloop
endfunction

function BoardWidth takes integer rows, integer col, real w returns nothing
    local integer r = 0
    local multiboarditem it
    loop
        exitwhen r >= rows
        set it = MultiboardGetItem(gBoard, r, col)
        call MultiboardSetItemWidth(it, w)
        call MultiboardReleaseItem(it)
        set r = r + 1
    endloop
    set it = null
endfunction

function BoardStyle takes integer rows returns nothing
    call MultiboardSetItemsStyle(gBoard, true, false)
    call BoardWidth(rows, 0, 0.075)
    call BoardWidth(rows, 1, 0.022)
    call BoardWidth(rows, 2, 0.032)
    call BoardWidth(rows, 3, 0.03)
    call BoardWidth(rows, 4, 0.038)
    call BoardWidth(rows, 5, 0.038)
endfunction

function CreateBoard takes nothing returns nothing
    local integer i
    local integer rows = 1
    set i = 0
    loop
        exitwhen i >= 8
        if IsPlaying(i) then
            set gBoardRow[i] = rows
            set rows = rows + 1
        else
            set gBoardRow[i] = 0
        endif
        set i = i + 1
    endloop
    set gBoard = CreateMultiboard()
    call MultiboardSetRowCount(gBoard, rows)
    call MultiboardSetColumnCount(gBoard, 6)
    set gBoardRows = rows
    call BoardStyle(rows)
    call BoardSet(0, 0, "|cffffcc00Player|r")
    call BoardSet(0, 1, "|cffffcc00Lv|r")
    call BoardSet(0, 2, "|cffffcc00Wave|r")
    call BoardSet(0, 3, "|cffffcc00Kills|r")
    call BoardSet(0, 4, "|cffffcc00Deaths|r")
    call BoardSet(0, 5, "|cffffcc00Income|r")
    set i = 8
    loop
        exitwhen i > 11
        set gBoardRow[i] = 0
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= 8
        if gBoardRow[i] > 0 then
            call BoardSet(gBoardRow[i], 0, gPlayerColorCode[i] + GetPlayerName(Player(i)) + "|r")
        endif
        set i = i + 1
    endloop
    call MultiboardDisplay(gBoard, true)
    call UpdateBoard()
endfunction

// An opened gate gets its own row: its wave is its own too.
function BoardAddGate takes integer L returns nothing
    if gBoard == null then
        return
    endif
    set gBoardRow[L] = gBoardRows
    set gBoardRows = gBoardRows + 1
    call MultiboardSetRowCount(gBoard, gBoardRows)
    call BoardStyle(gBoardRows)
    call BoardSet(gBoardRow[L], 0, gDirColor[LaneArm(L)] + "Level " + I2S(L - 6) + "|r")
    call UpdateBoard()
endfunction

//---------------------------------------------------------------------------
// Setup
//---------------------------------------------------------------------------
function SetupAlliances takes nothing returns nothing
    local integer i
    local integer j
    set i = 8
    loop
        exitwhen i > 11
        call SetPlayerName(Player(i), gFactionName[i - 8])
        call SetPlayerColor(Player(i), ConvertPlayerColor(gFactionColorIdx[i - 8]))
        call SetPlayerState(Player(i), PLAYER_STATE_GIVES_BOUNTY, 1)
        set j = 8
        loop
            exitwhen j > 11
            if i != j then
                call SetPlayerAlliance(Player(i), Player(j), ALLIANCE_PASSIVE, true)
            endif
            set j = j + 1
        endloop
        set j = 0
        loop
            exitwhen j > 7
            call SetPlayerAlliance(Player(i), Player(j), ALLIANCE_PASSIVE, false)
            call SetPlayerAlliance(Player(j), Player(i), ALLIANCE_PASSIVE, false)
            set j = j + 1
        endloop
        call SetPlayerAlliance(Player(i), gKingdom, ALLIANCE_PASSIVE, false)
        call SetPlayerAlliance(gKingdom, Player(i), ALLIANCE_PASSIVE, false)
        set i = i + 1
    endloop
    set j = 0
    loop
        exitwhen j > 7
        call SetPlayerAlliance(gKingdom, Player(j), ALLIANCE_PASSIVE, true)
        call SetPlayerAlliance(Player(j), gKingdom, ALLIANCE_PASSIVE, true)
        call SetPlayerAlliance(gKingdom, Player(j), ALLIANCE_SHARED_VISION, true)
        set j = j + 1
    endloop
    call SetPlayerName(gKingdom, "Kingdom of Lordaeron")
endfunction

// Eternal night + dark fog.
function SetupDarkness takes nothing returns nothing
    call SetFloatGameState(GAME_STATE_TIME_OF_DAY, 0.0)
    call SuspendTimeOfDay(true)
    call SetTerrainFogEx(0, 1900.0, 5500.0, 0.0, 0.02, 0.02, 0.07)
endfunction

function MakeWallInvulnerable takes nothing returns nothing
    call SetDestructableInvulnerable(GetEnumDestructable(), true)
endfunction

// Only the castle: no towers anywhere on our side - the champions are the only defence.
function CreateKingdom takes nothing returns nothing
    set gCastle = CreateUnit(gKingdom, gCastleType, 0.0, 0.0, 270.0)
endfunction

// Every active lane gets its own strong tower + Nexus (the Nexus spawns that lane's waves).
function CreateLaneBase takes integer L returns nothing
    local integer d = LaneArm(L)
    set gTower[L] = CreateUnit(gInvader[d], gTurretType[d], gTowerX[L], gTowerY[L], gDirFace[d])
    set gNexus[L] = CreateUnit(gInvader[d], gBaseType[d], gNexusX[L], gNexusY[L], gDirFace[d])
    set gLaneState[L] = 0
    if d == 0 then
        call SetBlight(gInvader[d], gNexusX[L], gNexusY[L], 600.0, true)
    endif
endfunction

//---------------------------------------------------------------------------
// Waves
//---------------------------------------------------------------------------
// Lane stage (decides WHICH units spawn): 0 = tower standing, 1 = tower destroyed (they come out of the Nexus),
// 2 = Nexus destroyed / boss alive (they come out of the ruins). The Dark Gate (lane 8) only has 0 and 1.
function LaneStage takes integer L returns integer
    if L < 8 and gLaneState[L] == 1 then
        return 2
    endif
    if L >= 8 and gGateState[L] == 1 then
        return 2
    endif
    if GetWidgetLife(gTower[L]) <= 0.405 then
        return 1
    endif
    return 0
endfunction

// ---- Scaling (docs/gameplay.md). n = the lane's own wave - 1: HP x (1 + gWaveHpGrowth n^2), damage x (1 + gWaveDmgGrowth n^2). Gate lanes also
// x their level, and in HP x the team: the champions at the start of the round (gTeamCount), so leaving changes nothing.
function WaveHpFactor takes integer w returns real
    return 1.0 + gWaveHpGrowth * I2R(w - 1) * I2R(w - 1)
endfunction

function WaveDmgFactor takes integer w returns real
    return 1.0 + gWaveDmgGrowth * I2R(w - 1) * I2R(w - 1)
endfunction

function TeamHpFactor takes integer team returns real
    return 1.0 + gTeamHpPer * I2R(team - 1)
endfunction

// HP and damage on top of the unit's own numbers. role: 0 melee, 1 ranged, 2 champion (no stage).
function ObstacleHpFactor takes integer L returns real
    if L >= 8 then
        return WaveHpFactor(gLaneWave[L]) * (1.0 + gGateHpPer * I2R(L - 7)) * TeamHpFactor(gTeamCount)
    endif
    return WaveHpFactor(gLaneWave[L])
endfunction

function ScaleHpBonus takes integer L, integer role, integer st returns integer
    local real base = gRoleHp[role]
    if role < 2 then
        set base = base * gStageHp[st]
    endif
    return R2I(base * (ObstacleHpFactor(L) - 1.0))
endfunction

function ScaleDmgBonus takes integer L, integer role, integer st returns integer
    local real base = gRoleDmg[role]
    local real f = WaveDmgFactor(gLaneWave[L])
    if role < 2 then
        set base = base * gStageDmg[st]
    endif
    if L >= 8 then
        set f = f * (1.0 + gGateDmgPer * I2R(L - 7))
    endif
    return R2I(base * (f - 1.0))
endfunction

// A bonus above the last bit stays at the maximum: it never wraps around to a small number.
function ScaleClamp takes integer value, integer n returns integer
    local integer top = 1
    local integer i = 0
    loop
        exitwhen i >= n
        set top = top * 2
        set i = i + 1
    endloop
    if value > top - 1 then
        return top - 1
    elseif value < 0 then
        return 0
    endif
    return value
endfunction

// Puts exactly this bonus on a unit (in steps; bits it should not have come off), so applying it twice changes nothing.
function ScaleSetBits takes unit u, integer first, integer n, integer value returns nothing
    local integer i = 0
    set value = ScaleClamp(value, n)
    loop
        exitwhen i >= n
        if ModuloInteger(value, 2) == 1 then
            call UnitAddAbility(u, gScaleBit[first + i])
        else
            call UnitRemoveAbility(u, gScaleBit[first + i])
        endif
        set value = value / 2
        set i = i + 1
    endloop
endfunction

// Rule: a rescale never heals. The unit keeps its actual HP (cut only if the new maximum is lower).
function ScaleKeepHp takes unit u, integer hpBonus, integer dmgBonus returns nothing
    local real hp = GetWidgetLife(u)
    call ScaleSetBits(u, 0, gScaleHpBits, hpBonus / gScaleHpStep)
    call ScaleSetBits(u, gScaleHpBits, gScaleDmgBits, dmgBonus / gScaleDmgStep)
    call SetWidgetLife(u, hp)
endfunction

// A shared obstacle as it appears: the team's HP on top of its own, at full health.
function ScaleTeamSpawn takes unit u returns nothing
    call ScaleKeepHp(u, R2I(GetUnitState(u, UNIT_STATE_MAX_LIFE) * (TeamHpFactor(gTeamCount) - 1.0)), 0)
    call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
endfunction

function ScaleListBits takes integer role, integer first, integer n, integer value returns nothing
    local integer i = 0
    set value = ScaleClamp(value, n)
    loop
        exitwhen i >= n
        if ModuloInteger(value, 2) == 1 then
            set gScaleList[role * 32 + gScaleN[role]] = gScaleBit[first + i]
            set gScaleN[role] = gScaleN[role] + 1
        endif
        set value = value / 2
        set i = i + 1
    endloop
endfunction

// The bits of this wave and stage, worked out once per lane: a wave is many units.
function ScalePrepare takes integer L, integer st returns nothing
    local integer role = 0
    loop
        exitwhen role > 2
        set gScaleN[role] = 0
        call ScaleListBits(role, 0, gScaleHpBits, ScaleHpBonus(L, role, st) / gScaleHpStep)
        call ScaleListBits(role, gScaleHpBits, gScaleDmgBits, ScaleDmgBonus(L, role, st) / gScaleDmgStep)
        set role = role + 1
    endloop
endfunction

// Waves come out of the lane's tower; once the tower is destroyed, out of the Nexus (or its ruins). A wave stands in ranks across its lane:
// the anchor is the rear of the army, in front of the building, and forward is the way to the lane's first waypoint (every lane and stage its own).
function WaveAnchor takes integer L returns nothing
    local real dx
    local real dy
    local real len
    set gFormX = gNexusSpawnX[L]
    set gFormY = gNexusSpawnY[L]
    if GetWidgetLife(gTower[L]) > 0.405 then
        set gFormX = gTowerSpawnX[L]
        set gFormY = gTowerSpawnY[L]
    endif
    set dx = gWpX[L * 8 + 1] - gFormX
    set dy = gWpY[L * 8 + 1] - gFormY
    set len = SquareRoot(dx * dx + dy * dy)
    set gFormFX = dx / len
    set gFormFY = dy / len
endfunction

function SpawnWaveUnit takes integer L, integer ut, integer role returns nothing
    local integer d = LaneArm(L)
    local real x = gFormX + gFormFX * gFormForward - gFormFY * gFormSide
    local real y = gFormY + gFormFY * gFormForward + gFormFX * gFormSide
    local unit u
    local integer b = 0
    set u = CreateUnit(gInvader[d], ut, x, y, bj_RADTODEG * Atan2(gFormFY, gFormFX))
    loop
        exitwhen b >= gScaleN[role]
        call UnitAddAbility(u, gScaleList[role * 32 + b])
        set b = b + 1
    endloop
    if L >= 8 then
        call SetUnitVertexColor(u, gGateTintR[L], gGateTintG[L], gGateTintB[L], 255)
    endif
    call SetUnitUserData(u, L * 16 + 1)
    call SetUnitState(u, UNIT_STATE_LIFE, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    if gLaneWave[L] == 1 then
        call GroupAddUnit(gFirstWave, u)
        set gFirstWaveLeft[L] = gFirstWaveLeft[L] + 1
    endif
    call GroupAddUnit(gWaveUnits, u)
    call IssuePointOrder(u, "attack", gWpX[L * 8 + 1], gWpY[L * 8 + 1])
    if gTestMode then
        set gTestLast = u
        if gTestFormN < 8000 then
            set gTestFormU[gTestFormN] = u
            set gTestFormRole[gTestFormN] = role
            set gTestFormLane[gTestFormN] = L
            set gTestFormN = gTestFormN + 1
        endif
    endif
    set u = null
endfunction

// One rank after another, from depth on, centred across the lane. Returns the depth behind the last rank.
function SpawnRanks takes integer L, integer ut, integer role, integer count, integer perRank, real step, real depth returns real
    local integer i = 0
    local integer inRank
    loop
        exitwhen i >= count
        set inRank = count - (i / perRank) * perRank
        if inRank > perRank then
            set inRank = perRank
        endif
        set gFormForward = depth + step * I2R(i / perRank)
        set gFormSide = (I2R(ModuloInteger(i, perRank)) - I2R(inRank - 1) / 2.0) * step
        call SpawnWaveUnit(L, ut, role)
        set i = i + 1
    endloop
    if count <= 0 then
        return depth
    endif
    return depth + step * I2R((count - 1) / perRank + 1)
endfunction

// Standardized waves: the lane STAGE picks the unit types, the lane's own wave number adds units and strength (ScalePrepare).
// Front line (melee) = 4 + 2 x wave, back line (ranged) = 1 x wave (gFrontPer / gBackPer, capped by gFrontMax /
// gBackMax). Every 10th wave: wave/10 wave champions.
function SpawnWave takes integer L returns nothing
    local integer d = LaneArm(L)
    local integer st = LaneStage(L)
    local integer w = gLaneWave[L]
    local integer front = gFrontBase + gFrontPer * w
    local integer back = (gBackPer * w + 1) / 2
    local integer i = 0
    local real depth
    if front > gFrontMax then
        set front = gFrontMax
    endif
    if back > gBackMax then
        set back = gBackMax
    endif
    call ScalePrepare(L, st)
    call WaveAnchor(L)
    if gTestMode and L == 0 and w <= 2 then
        call TestCheck(front == gFrontBase + w and back == (w + 1) / 2, "wave " + I2S(w) + " size: front " + I2S(front) + ", back " + I2S(back))
    endif
    // the ranged at the back, the melee in front of them, the wave champions first of all
    set depth = SpawnRanks(L, gStageUnit[d * 6 + st * 2 + 1], 1, back, gFormRow, gFormStep, 0.0)
    set depth = SpawnRanks(L, gStageUnit[d * 6 + st * 2], 0, front, gFormRow, gFormStep, depth + gFormGap)
    if ModuloInteger(w, gChampEvery) == 0 then
        set i = w / gChampEvery
        if i > gChampMax then
            set i = gChampMax
        endif
        call SpawnRanks(L, gWaveChamp[d], 2, i, gFormChampRow, gFormChampStep, depth + gFormGap)
    endif
    if gTestMode and L == 0 and w <= 2 and st == 0 and gTestLast != null then
        // a real wave unit of this wave (the last one spawned: melee) against the formula, also right after a restart
        call TestCheck(RAbsBJ(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE) - gRoleHp[0] * WaveHpFactor(w)) <= I2R(gScaleHpStep), "wave " + I2S(w) + " round " + I2S(gTestRound) + ": a real melee monster has the formula's HP (" + I2S(R2I(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE))) + ")")
    endif
endfunction

// Every lane in its own thread: a late wave is hundreds of units and a thread has an operation limit.
function SpawnWaveThread takes nothing returns nothing
    call SpawnWave(gSpawnLane)
endfunction

// ---- Every lane has its own wave (gLaneWave): lanes 0-7 the player's, 8-11 the shared gates. A lane's next wave comes when
// THAT lane is clear (OnTick -> OnLaneCleared), so a fast player climbs and a slow one holds back nobody but himself.
function LaneSpawns takes integer L returns boolean
    if L >= 8 then
        return gGateState[L] == 0 or gGateState[L] == 1
    endif
    return gLaneActive[L] and (gLaneState[L] == 0 or gLaneState[L] == 1)
endfunction

// A lane's news goes to its player, a gate's to everyone, and the lane of a player who left to the others (they clear it now).
function LaneMsg takes integer L, string s returns nothing
    if L >= 8 then
        call Msg(s)
    elseif IsPlaying(L) then
        call DisplayTimedTextToPlayer(Player(L), 0.0, 0.0, 12.0, s)
    else
        call Msg(gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r's lane: " + s)
    endif
endfunction

function LaneSound takes integer L, sound s returns nothing
    if L >= 8 or GetLocalPlayer() == Player(L) then
        call StartSound(s)
    endif
endfunction

// The countdown of a lane: only its player sees it. A gate has none.
function LaneDialog takes integer L, boolean on returns nothing
    if L < 8 and gLaneDialog[L] != null and GetLocalPlayer() == Player(L) then
        call TimerDialogDisplay(gLaneDialog[L], on)
    endif
endfunction

function LaneStop takes integer L returns nothing
    call PauseTimer(gLaneTimer[L])
    call LaneDialog(L, false)
endfunction

// The end of a round or the final fight: no lane sends or pays anything more.
function LanesStop takes nothing returns nothing
    local integer L = 0
    loop
        exitwhen L > 11
        set gLaneWaiting[L] = false
        call LaneStop(L)
        set L = L + 1
    endloop
endfunction

function StartLaneWave takes integer L returns nothing
    if gGameOver or gFinalPhase or not LaneSpawns(L) then
        return
    endif
    set gLaneWave[L] = gLaneWave[L] + 1
    call BankRenew(L)
    if L < 8 and gLaneWave[L] == 2 then
        call GrantLevelTwo(L)
    endif
    set gSpawnLane = L
    call ExecuteFunc("SpawnWaveThread")
    if L < 8 then
        call LaneMsg(L, "|cffff4040Wave " + I2S(gLaneWave[L]) + "|r is coming!")
        if ModuloInteger(gLaneWave[L], gChampEvery) == gChampEvery - 1 then
            call LaneMsg(L, "|cffffcc00Champions|r march with the next wave!")
        endif
        call LaneSound(L, bj_questWarningSound)
    endif
    // the lane's next countdown only starts once its monsters are dead (checked in OnTick)
    set gLaneWaiting[L] = true
    call LaneDialog(L, false)
    call UpdateBoard()
endfunction

function OnLaneTimer takes nothing returns nothing
    local timer t = GetExpiredTimer()
    local integer L = 0
    loop
        exitwhen L > 11
        if gLaneTimer[L] == t then
            call StartLaneWave(L)
        endif
        set L = L + 1
    endloop
    set t = null
endfunction

// A lane's next wave comes right away (gWaveInterval, 0 s since v3.5), but a 1 min break after every 10th wave of that lane.
function NextWaveDelay takes integer L returns real
    if ModuloInteger(gLaneWave[L], gBreakEvery) == 0 then
        return gWaveBreak
    endif
    return gWaveInterval
endfunction

// Wave reward, paid when the lane's wave is CLEARED: 100 gold for wave 1, +50 for every next wave (no cap).
function WaveGold takes integer L returns integer
    return 50 + 50 * gLaneWave[L]
endfunction

// Gold + 1 tree: to the lane's player. A shared gate pays everyone, and so does the lane of a player who left.
function LanePay takes integer L returns nothing
    local integer p = 0
    loop
        exitwhen p >= 8
        if IsPlaying(p) and (p == L or L >= 8 or not IsPlaying(L)) then
            call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + WaveGold(L))
            call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_LUMBER, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_LUMBER) + 1)
        endif
        set p = p + 1
    endloop
endfunction

// Shopping break (after every gBreakEvery-th wave of a player's lane): announcement + gold pings and effects on the secret grove.
function ShoppingTime takes integer L returns nothing
    local integer i = 0
    call LaneMsg(L, "|cffffcc00BREAK - Time to go Shopping!|r   Secret grove (SE).   |cffffcc00+" + I2S(WaveGold(L)) + " gold|r  |cff80ff80+1 tree|r   Next wave in " + I2S(R2I(gWaveBreak)) + "s.")
    call LaneSound(L, bj_questHintSound)
    loop
        exitwhen i >= gShopFxCount
        if GetLocalPlayer() == Player(L) then
            call PingMinimapEx(gShopFxX[i], gShopFxY[i], 6.0, 255, 204, 0, true)
        endif
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\Resurrect\\ResurrectTarget.mdl", gShopFxX[i], gShopFxY[i]))
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Items\\ResourceItems\\ResourceEffectTarget.mdl", gShopFxX[i], gShopFxY[i]))
        set i = i + 1
    endloop
endfunction

// A lane's wave is dead: it pays, and its next wave comes (unless its boss is slain: then this was its last).
function OnLaneCleared takes integer L returns nothing
    local real delay = NextWaveDelay(L)
    local string text = "|cff40ff40Wave " + I2S(gLaneWave[L]) + " cleared!|r  |cffffcc00+" + I2S(WaveGold(L)) + " gold|r  |cff80ff80+1 tree|r"
    local boolean more = LaneSpawns(L)
    set gLaneWaiting[L] = false
    call LanePay(L)
    if more then
        call TimerStart(gLaneTimer[L], delay, false, function OnLaneTimer)
        if delay >= 1.0 then
            call LaneDialog(L, true)
        endif
    endif
    if L >= 8 then
        set text = gDirColor[LaneArm(L)] + "LEVEL " + I2S(L - 6) + ":|r " + text
    endif
    if more and L < 8 and ModuloInteger(gLaneWave[L], gBreakEvery) == 0 then
        call ShoppingTime(L)
    elseif not more then
        call LaneMsg(L, text)
    elseif delay < 1.0 then
        call LaneMsg(L, text + "   Next wave now!")
    else
        call LaneMsg(L, text + "   Next wave in " + I2S(R2I(delay)) + "s.")
    endif
endfunction

// A wave monster taken over by a player (Charm, Possession, ...) stops being a wave monster: no more lane
// orders, it no longer blocks the "all monsters dead" check, and it still counts for the first-wave level-up.
function ReleaseWaveUnit takes unit u returns nothing
    local integer L = GetUnitUserData(u) / 16
    call GroupRemoveUnit(gWaveUnits, u)
    if IsUnitInGroup(u, gFirstWave) then
        call GroupRemoveUnit(gFirstWave, u)
        set gFirstWaveLeft[L] = gFirstWaveLeft[L] - 1
        if gFirstWaveLeft[L] <= 0 then
            call GrantLevelTwo(L)
        endif
    endif
    call SetUnitUserData(u, 0)
    call IssueImmediateOrder(u, "stop")
endfunction

// Steers every wave unit along its lane (attack-move from waypoint to waypoint).
function WaveUnitTick takes nothing returns nothing
    local unit u = GetEnumUnit()
    local integer data
    local integer L
    local integer k
    local real dx
    local real dy
    if GetUnitTypeId(u) == 0 or IsUnitType(u, UNIT_TYPE_DEAD) then
        call GroupRemoveUnit(gWaveUnits, u)
        set u = null
        return
    endif
    if GetPlayerId(GetOwningPlayer(u)) < 8 then
        call ReleaseWaveUnit(u)
        set u = null
        return
    endif
    set data = GetUnitUserData(u)
    set L = data / 16
    set gLaneAlive[L] = gLaneAlive[L] + 1
    set k = data - L * 16
    set dx = gWpX[L * 8 + k] - GetUnitX(u)
    set dy = gWpY[L * 8 + k] - GetUnitY(u)
    if k < gWpCount - 1 and dx * dx + dy * dy < 122500.0 then
        set k = k + 1
        call SetUnitUserData(u, L * 16 + k)
        call IssuePointOrder(u, "attack", gWpX[L * 8 + k], gWpY[L * 8 + k])
    elseif GetUnitCurrentOrder(u) == 0 then
        call IssuePointOrder(u, "attack", gWpX[L * 8 + k], gWpY[L * 8 + k])
    endif
    set u = null
endfunction

//---------------------------------------------------------------------------
// Bosses
//---------------------------------------------------------------------------
function BossFindTarget takes unit boss, real range returns unit
    local group g = CreateGroup()
    local unit t
    local unit best = null
    local player p = GetOwningPlayer(boss)
    call GroupEnumUnitsInRange(g, GetUnitX(boss), GetUnitY(boss), range, null)
    loop
        set t = FirstOfGroup(g)
        exitwhen t == null
        call GroupRemoveUnit(g, t)
        if best == null and IsUnitEnemy(t, p) and GetUnitAbilityLevel(t, 'Avul') == 0 and not IsUnitType(t, UNIT_TYPE_DEAD) and not IsUnitType(t, UNIT_TYPE_STRUCTURE) and GetUnitTypeId(t) != 0 then
            set best = t
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    set p = null
    return best
endfunction

// 1.27 has no "set max HP / damage / armor": n "bit" abilities gFinalBit[first..] (+1, +2, +4, ... steps; distinct
// ids stack) add any value. Added before removed high to low would clamp HP: FinalApplyStats restores the HP %.
function FinalBits takes unit u, integer first, integer n, integer value returns nothing
    local integer i = n - 1
    local integer p = 1
    local integer k = 1
    loop
        exitwhen k >= n
        set p = p * 2
        set k = k + 1
    endloop
    if value > p * 2 - 1 then
        set value = p * 2 - 1
    elseif value < 0 then
        set value = 0
    endif
    loop
        exitwhen i < 0
        if value >= p then
            set value = value - p
            call UnitAddAbility(u, gFinalBit[first + i])
        else
            call UnitRemoveAbility(u, gFinalBit[first + i])
        endif
        set i = i - 1
        set p = p / 2
    endloop
endfunction

// A boss as it rises: as strong as ITS lane's wave. HP and attack through the same bits as the monsters; on a gate also the team's HP, and its spells one level up per gate level.
function BossGearItem takes unit b, integer id returns nothing
    local item it = UnitAddItemById(b, id)
    call SetItemDropOnDeath(it, false)
    call SetItemDroppable(it, false)
    call SetItemPawnable(it, false)
    set it = null
endfunction

// slot: where its cooldowns are kept, L for the Nexus boss, L + 12 for the Warden. tier: 0 the Warden, 1 the Nexus boss. The gear goes on first: the wave's and team's factors count it too.
function BossEquip takes integer L, integer slot, unit b, integer unitTier returns nothing
    local integer d = LaneArm(L)
    local integer w = gLaneWave[L]
    local integer tier = 1 + w / 5
    local real n = I2R(w - 1)
    local real hp = 1.0 + gBossHpGrowth * n * n
    local real dmg = 1.0 + gBossDmgGrowth * n * n
    local integer bonus
    if L >= 8 then
        set tier = tier + L - 7
        call BossGearItem(b, gGearHeart[(L - 7) * 2 + unitTier])
    else
        call BossGearItem(b, gGearHeart[unitTier])
    endif
    call BossGearItem(b, gGearHands[unitTier])
    call BossGearItem(b, gGearPlate[unitTier])
    if tier > gBossSpellLevels then
        set tier = gBossSpellLevels
    endif
    if hp > gBossHpMax then
        set hp = gBossHpMax
    endif
    if dmg > gBossDmgMax then
        set dmg = gBossDmgMax
    endif
    set gBossBusy[slot] = 0
    set gBossDue1[slot] = false
    set gBossDue2[slot] = false
    set gBossDue3[slot] = false
    if L >= 8 then
        set hp = hp * TeamHpFactor(gTeamCount)
    endif
    set bonus = R2I(GetUnitState(b, UNIT_STATE_MAX_LIFE) * (hp - 1.0))
    call FinalBits(b, 0, gFinalHpBits, bonus / gFinalHpStep)
    if unitTier == 0 then
        call ScaleKeepHp(b, ModuloInteger(bonus, gFinalHpStep), R2I(gWardenAvgDmg[d] * (dmg - 1.0)))
    else
        call ScaleKeepHp(b, ModuloInteger(bonus, gFinalHpStep), R2I(gBossAvgDmg[d] * (dmg - 1.0)))
    endif
    call SetWidgetLife(b, GetUnitState(b, UNIT_STATE_MAX_LIFE))
    call SetUnitAbilityLevel(b, gBossSpell[d * 2], tier)
    call SetUnitAbilityLevel(b, gBossSpell[d * 2 + 1], tier)
endfunction

// True when the unit took the order. A spell-immune target gets no spell at all, also none on the ground under it: real attacks instead.
function BossCast takes unit boss, string ord, integer kind, unit target returns boolean
    if IsUnitType(target, UNIT_TYPE_MAGIC_IMMUNE) then
        return false
    endif
    if kind == 0 then
        return IssueImmediateOrder(boss, ord)
    elseif kind == 1 then
        return IssueTargetOrder(boss, ord, target)
    endif
    return IssuePointOrder(boss, ord, GetUnitX(target), GetUnitY(target))
endfunction

function BossSummon takes integer L returns nothing
    local integer d = LaneArm(L)
    local integer i = 0
    local unit u
    local real a
    loop
        exitwhen i >= gBossSummonCount[d]
        set a = i * 6.2832 / gBossSummonCount[d]
        set u = CreateUnit(gInvader[d], gBossSummon[d], GetUnitX(gBoss[L]) + 220.0 * Cos(a), GetUnitY(gBoss[L]) + 220.0 * Sin(a), GetUnitFacing(gBoss[L]))
        call ScaleKeepHp(u, R2I(GetUnitState(u, UNIT_STATE_MAX_LIFE) * (ObstacleHpFactor(L) - 1.0)), ScaleDmgBonus(L, 2, 0))
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
        call UnitApplyTimedLife(u, 'BTLF', 40.0)
        call IssuePointOrder(u, "attack", GetUnitX(gBoss[L]), GetUnitY(gBoss[L]))
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Undead\\AnimateDead\\AnimateDeadTarget.mdl", GetUnitX(u), GetUnitY(u)))
        set i = i + 1
    endloop
    set u = null
endfunction

// What a boss does each second, for the Nexus boss (slot L) and the Tower Warden (slot L + 12): its own spells and leash, around its own ruins.
function BossBrain takes integer L, integer slot, unit b, real ax, real ay, real leash returns nothing
    local integer d = LaneArm(L)
    local unit t
    local real dx
    local real dy
    if b == null or GetWidgetLife(b) <= 0.405 then
        return
    endif
    set gBossTick[slot] = gBossTick[slot] + 1
    set dx = GetUnitX(b) - ax
    set dy = GetUnitY(b) - ay
    if ModuloInteger(gBossTick[slot], gBossEvery1) == 0 then
        set gBossDue1[slot] = true
    endif
    if ModuloInteger(gBossTick[slot], gBossEvery2) == 0 then
        set gBossDue2[slot] = true
    endif
    // a Warden fights alone
    if slot < 12 and ModuloInteger(gBossTick[slot], gBossEverySummon) == 0 then
        set gBossDue3[slot] = true
    endif
    // leash: a boss never leaves its ruins for long
    if dx * dx + dy * dy > leash * leash then
        call IssuePointOrder(b, "move", ax, ay)
        return
    endif
    if GetUnitCurrentOrder(b) == OrderId("move") and dx * dx + dy * dy > 90000.0 then
        return
    endif
    set t = BossFindTarget(b, 900.0)
    // adds need no order: they come on time, also during a running spell
    if t != null and gBossDue3[slot] then
        set gBossDue3[slot] = false
        call BossSummon(L)
    endif
    // a running Blizzard or Rain of Fire runs to its end; a spell that comes due meanwhile waits. Only the leash above breaks it.
    if GetUnitCurrentOrder(b) == OrderId("blizzard") or GetUnitCurrentOrder(b) == OrderId("rainoffire") then
        set t = null
        return
    endif
    if t != null then
        // one thing a tick; a cast is given a moment before the next order. A spell that is refused stays due.
        if gBossBusy[slot] > 0 then
            set gBossBusy[slot] = gBossBusy[slot] - 1
        elseif gBossDue1[slot] and BossCast(b, gBossOrd1[d], gBossKind1[d], t) then
            set gBossDue1[slot] = false
            set gBossBusy[slot] = 1
        elseif gBossDue2[slot] and BossCast(b, gBossOrd2[d], gBossKind2[d], t) then
            set gBossDue2[slot] = false
            set gBossBusy[slot] = 1
        elseif GetUnitCurrentOrder(b) == 0 then
            call IssueTargetOrder(b, "attack", t)
        endif
    elseif GetUnitCurrentOrder(b) == 0 and dx * dx + dy * dy > 90000.0 then
        call IssuePointOrder(b, "attack", ax, ay)
    endif
    set t = null
endfunction

function BossTick takes integer L returns nothing
    call BossBrain(L, L, gBoss[L], gNexusX[L], gNexusY[L], gBossLeash)
endfunction

//---------------------------------------------------------------------------
// The FINAL BOSS (v4.0). When every lane boss and all 4 gate levels are done (CheckVictory): waves stop, the castle
// is shielded, and after a warning he rises in the plaza. His death wins the game (OnFinalBossDead).
// Stats follow the game clock (FinalApplyStats, every new minute); stuns are removed at once (FinalImmuneTick);
// he casts Storm Bolt, War Stomp, Shockwave and Inferno on his own schedule (FinalBossTick) and bashes (passive).
//---------------------------------------------------------------------------

// HP factor by the team at the start of the round: 1-2 / 3-5 / 6-8 -> 1 / 2 / 3
function FinalPlayerFactor takes nothing returns integer
    local integer n = gTeamCount
    if n >= 6 then
        return 3
    elseif n >= 3 then
        return 2
    endif
    return 1
endfunction

function FinalMaxHp takes integer m returns integer
    return (gFinalHpBase + gFinalHpPerMin * m) * FinalPlayerFactor()
endfunction

function FinalDamage takes integer m returns integer
    return gFinalDmgBase + gFinalDmgPerMin * m
endfunction

// His stats for the current minute of the game clock. Growing never heals: his actual HP stays, only the first time he is
// full. (Keeping the percentage would give him free HP every minute.) Spell tier +1 every gFinalTierEvery minutes.
function FinalApplyStats takes nothing returns nothing
    local unit b = gFinalBoss
    local integer m = gGameTime / 60
    local integer t = m / gFinalTierEvery
    local integer s = 0
    local real hp = GetWidgetLife(b)
    local boolean fresh = gFinalTier < 0
    call FinalBits(b, 0, gFinalHpBits, (FinalMaxHp(m) - gFinalHpUnit) / gFinalHpStep)
    call FinalBits(b, gFinalHpBits, gFinalDmgBits, gFinalDmgPerMin * m / gFinalDmgStep)
    call FinalBits(b, gFinalHpBits + gFinalDmgBits, gFinalArmorBits, m / gFinalArmorEvery)
    if fresh then
        call SetWidgetLife(b, GetUnitState(b, UNIT_STATE_MAX_LIFE))
    else
        call SetWidgetLife(b, hp)
    endif
    if t > gFinalTiers - 1 then
        set t = gFinalTiers - 1
    endif
    if t != gFinalTier then
        loop
            exitwhen s >= 4
            if gFinalTier >= 0 then
                call UnitRemoveAbility(b, gFinalSpell[gFinalTier * 4 + s])
            endif
            call UnitAddAbility(b, gFinalSpell[t * 4 + s])
            set s = s + 1
        endloop
        set gFinalTier = t
    endif
    set gFinalMinute = m
    set b = null
endfunction

// 0.05 s: no stun holds him (Storm Bolt, War Stomp, Bash - also the item's - all use the Pause buff BPSE).
// No stun holds a boss: the stun buffs come off at once. Everything else of a spell (its damage, a slow) still works.
function StunStrip takes unit u, integer slot returns nothing
    local integer i = 0
    local boolean had = false
    local texttag tt
    loop
        exitwhen i >= gStunN
        if GetUnitAbilityLevel(u, gStunBuff[i]) > 0 then
            call UnitRemoveAbility(u, gStunBuff[i])
            set had = true
        endif
        set i = i + 1
    endloop
    // Impale throws him up for a second and its damage lands then: taking the buff at once would take the damage too. What is left of its stun goes after that.
    if GetUnitAbilityLevel(u, 'BUim') > 0 then
        set gStunImpale[slot] = gStunImpale[slot] + 1
        if gStunImpale[slot] >= 26 then
            call UnitRemoveAbility(u, 'BUim')
            set had = true
            set gStunImpale[slot] = 0
        endif
    else
        set gStunImpale[slot] = 0
    endif
    if had then
        set gTestStunRemoved = gTestStunRemoved + 1
        if gStunShown[slot] != gElapsed then
            set gStunShown[slot] = gElapsed
            set tt = CreateTextTag()
            call SetTextTagText(tt, "Stun immune!", 0.024)
            call SetTextTagPosUnit(tt, u, 150.0)
            call SetTextTagColor(tt, 255, 80, 80, 255)
            call SetTextTagVelocity(tt, 0.0, 0.04)
            call SetTextTagPermanent(tt, false)
            call SetTextTagLifespan(tt, 2.0)
            call SetTextTagFadepoint(tt, 1.0)
            set tt = null
        endif
    endif
endfunction

function FinalImmuneTick takes nothing returns nothing
    local integer L = 0
    if gFinalBoss != null then
        call StunStrip(gFinalBoss, 12)
    endif
    loop
        exitwhen L > 11
        if gBoss[L] != null then
            call StunStrip(gBoss[L], L)
        endif
        if gProtector[L] != null then
            call StunStrip(gProtector[L], L + 20)
        endif
        set L = L + 1
    endloop
endfunction

function SpawnFinalBoss takes nothing returns nothing
    if gGameOver or not gFinalPhase then
        return
    endif
    if gFinalDialog != null then
        call TimerDialogDisplay(gFinalDialog, false)
    endif
    set gFinalBoss = CreateUnit(gInvader[0], gFinalType, gFinalX, gFinalY, 90.0)
    set gFinalTier = -1
    set gFinalTick = 0
    call FinalApplyStats()
    call DestroyEffect(AddSpecialEffect(gFinalFx, gFinalX, gFinalY))
    call StartSound(bj_questWarningSound)
    call PingMinimapEx(gFinalX, gFinalY, 8.0, 255, 0, 0, true)
    call Msg("|cffff2020" + gFinalName + " has risen!|r   " + I2S(FinalMaxHp(gFinalMinute)) + " HP, " + I2S(FinalDamage(gFinalMinute)) + " damage - stronger every minute. |cffffcc00Stuns don't hold him.|r Kill him to |cff40ff40win|r!")
endfunction

function StartFinalBoss takes nothing returns nothing
    set gFinalPhase = true
    call LanesStop()
    call SetUnitInvulnerable(gCastle, true)
    call StartSound(bj_questWarningSound)
    call PingMinimapEx(gFinalX, gFinalY, 8.0, 255, 0, 0, true)
    call Msg("|cffff2020THE FINAL BOSS AWAKENS!|r   Every Nexus has fallen, but |cffffcc00" + gFinalName + "|r rises at the Castle in " + I2S(R2I(gFinalDelay)) + " s. No more waves - get ready!")
    if gFinalDialog == null then
        set gFinalDialog = CreateTimerDialog(gFinalTimer)
        call TimerDialogSetTitle(gFinalDialog, "Final Boss")
    endif
    call TimerStart(gFinalTimer, gFinalDelay, false, function SpawnFinalBoss)
    call TimerDialogDisplay(gFinalDialog, true)
endfunction

// Nearest enemy within range, champions first; never a structure or an invulnerable unit (Invulnerability potion, he
// would stand idle in front of it).
function FinalFindTarget takes unit b, real range returns unit
    local group g = CreateGroup()
    local unit t
    local unit best = null
    local real bestD = 0.0
    local boolean bestHero = false
    local boolean hero
    local real d
    local player p = GetOwningPlayer(b)
    call GroupEnumUnitsInRange(g, GetUnitX(b), GetUnitY(b), range, null)
    loop
        set t = FirstOfGroup(g)
        exitwhen t == null
        call GroupRemoveUnit(g, t)
        if IsUnitEnemy(t, p) and GetWidgetLife(t) > 0.405 and not IsUnitType(t, UNIT_TYPE_STRUCTURE) and GetUnitAbilityLevel(t, 'Avul') == 0 and GetUnitAbilityLevel(t, 'Bvul') == 0 then
            set hero = IsUnitType(t, UNIT_TYPE_HERO)
            set d = (GetUnitX(t) - GetUnitX(b)) * (GetUnitX(t) - GetUnitX(b)) + (GetUnitY(t) - GetUnitY(b)) * (GetUnitY(t) - GetUnitY(b))
            if best == null or (hero and not bestHero) or (hero == bestHero and d < bestD) then
                set best = t
                set bestD = d
                set bestHero = hero
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    set p = null
    return best
endfunction

// Self-test only: which of his spells really went off (gTestFinalCast: Storm Bolt, War Stomp, Shockwave, Inferno).
function OnFinalCastTest takes nothing returns nothing
    local integer k = 0
    if GetTriggerUnit() == gFinalBoss then
        loop
            exitwhen k >= gFinalTiers * 4
            if gFinalSpell[k] == GetSpellAbilityId() then
                set gTestFinalCast[ModuloInteger(k, 4)] = gTestFinalCast[ModuloInteger(k, 4)] + 1
                return
            endif
            set k = k + 1
        endloop
    endif
endfunction

// 1 s (OnTick): grows with the clock, stays around the plaza, and casts on his own schedule.
function FinalBossTick takes nothing returns nothing
    local unit b = gFinalBoss
    local unit t
    local real dx
    local real dy
    local real d2
    if GetWidgetLife(b) <= 0.405 then
        set b = null
        return
    endif
    if gGameTime / 60 != gFinalMinute then
        call FinalApplyStats()
        call Msg("|cffff4040" + gFinalName + " grows stronger:|r   " + I2S(FinalMaxHp(gFinalMinute)) + " HP, " + I2S(FinalDamage(gFinalMinute)) + " damage")
    endif
    set gFinalTick = gFinalTick + 1
    set dx = GetUnitX(b) - gFinalX
    set dy = GetUnitY(b) - gFinalY
    set d2 = dx * dx + dy * dy
    if d2 > gFinalLeash * gFinalLeash then
        call IssuePointOrder(b, "move", gFinalX, gFinalY)
        set b = null
        return
    endif
    if GetUnitCurrentOrder(b) == OrderId("move") and d2 > 250000.0 then
        set b = null
        return
    endif
    set t = FinalFindTarget(b, 900.0)
    if t != null then
        if ModuloInteger(gFinalTick, 6) == 0 then
            call IssueTargetOrder(b, "creepthunderbolt", t)
        elseif ModuloInteger(gFinalTick, 8) == 3 then
            call IssueImmediateOrder(b, "stomp")
        elseif ModuloInteger(gFinalTick, 11) == 5 then
            call IssuePointOrder(b, "shockwave", GetUnitX(t), GetUnitY(t))
        elseif ModuloInteger(gFinalTick, 20) == 10 then
            call IssuePointOrder(b, "inferno", GetUnitX(t), GetUnitY(t))
        elseif GetUnitCurrentOrder(b) == 0 then
            call IssueTargetOrder(b, "attack", t)
        endif
    elseif GetUnitCurrentOrder(b) == 0 and d2 > 250000.0 then
        call IssuePointOrder(b, "attack", gFinalX, gFinalY)
    endif
    set b = null
    set t = null
endfunction

//---------------------------------------------------------------------------
// Periodic tick (1 s)
//---------------------------------------------------------------------------
function OnTick takes nothing returns nothing
    local integer L = 0
    set gElapsed = gElapsed + 1
    if gStarted and not gGameOver then
        set gGameTime = gGameTime + 1     // game clock: from the end of champion select, stops at the end
        call BankTick()
    endif
    loop
        exitwhen L > 11
        set gLaneAlive[L] = 0
        set L = L + 1
    endloop
    // steers every monster and counts the living per lane
    call ForGroup(gWaveUnits, function WaveUnitTick)
    set L = 0
    loop
        exitwhen L > 11
        if gLaneWaiting[L] and gLaneAlive[L] == 0 and not gGameOver then
            call OnLaneCleared(L)
        endif
        if (L < 8 and gLaneState[L] == 1) or (L >= 8 and gGateState[L] == 1) then
            call BossTick(L)
        endif
        set L = L + 1
    endloop
    if gFinalBoss != null then
        call FinalBossTick()
    endif
    if GetWidgetLife(gCastle) > 0.405 and ModuloInteger(gElapsed, 2) == 0 then
        call SetWidgetLife(gCastle, GetWidgetLife(gCastle) + 10.0)
    endif
    call UpdateBoard()
endfunction

//---------------------------------------------------------------------------
// Victory / defeat
//---------------------------------------------------------------------------
// End of a round: everyone gets "Play again" (restart -> champion select) or "Finish game".
function ShowEndDialog takes boolean won returns nothing
    local integer i = 0
    set gGameOver = true
    set gEndWon = won
    call LanesStop()
    call DialogClear(gEndDialog)
    if won then
        call DialogSetMessage(gEndDialog, "VICTORY in " + TimeText(gGameTime) + "!  Play again?")
    else
        call DialogSetMessage(gEndDialog, "The castle has fallen after " + TimeText(gGameTime) + "!  Play again?")
    endif
    set gEndRestart = DialogAddButton(gEndDialog, "Play again", 0)
    set gEndQuit = DialogAddButton(gEndDialog, "Finish game", 0)
    loop
        exitwhen i >= 8
        if IsPlaying(i) then
            call DialogDisplay(Player(i), gEndDialog, true)
        endif
        set i = i + 1
    endloop
endfunction

function CheckVictory takes nothing returns nothing
    local integer L = 0
    if gGameOver then
        return
    endif
    set L = 8
    loop
        exitwhen L > 11
        if gGateState[L] != 2 then
            return
        endif
        set L = L + 1
    endloop
    set L = 0
    loop
        exitwhen L >= 8
        if gLaneState[L] == 0 or gLaneState[L] == 1 then
            return
        endif
        set L = L + 1
    endloop
    // everything is down: not the end yet - the final boss rises
    if not gFinalPhase then
        call StartFinalBoss()
    endif
endfunction

function OnFinalBossDead takes nothing returns nothing
    set gFinalBoss = null
    call SetUnitInvulnerable(gCastle, false)
    call Msg("|cff40ff40VICTORY!|r  |cffffcc00" + gFinalName + "|r is dead, every Nexus is rubble and the castle still stands!")
    call ShowEndDialog(true)
endfunction

function OnCastleDestroyed takes nothing returns nothing
    if gGameOver then
        return
    endif
    call Msg("|cffff0000The Castle of Lordaeron has fallen!|r")
    call ShowEndDialog(false)
endfunction

function DropLoot takes integer level, real x, real y returns nothing
    local integer it = ChooseRandomItemEx(ITEM_TYPE_PERMANENT, level)
    if it > 0 then
        call CreateItem(it, x, y)
    endif
endfunction

// EPIC boss loot: a crown with a huge all-stats bonus, by level (1 = lane boss, 2-5 = gate bosses).
function DropEpic takes integer lvl, real x, real y returns nothing
    call CreateItem(gEpicItem[lvl], x, y)
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\HolyBolt\\HolyBoltSpecialArt.mdl", x, y))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Items\\ResourceItems\\ResourceEffectTarget.mdl", x, y))
    call PingMinimapEx(x, y, 5.0, 163, 53, 238, true)
    call Msg("|cffa335eeEPIC DROP:|r |cffffcc00" + gEpicName[lvl] + "|r")
endfunction

// A lane's tower fell: a Protector (the faction champion, bigger) guards the Nexus, and that lane's next wave
// comes at once - already the stronger Nexus wave. Works for the Dark Gate (lane 8) too.
// Where the tower lay a boss rises: the Tower Warden (gProtector[L], tier 0), a boss of its own beside the later Nexus boss (gBoss[L]). The Nexus can still be attacked past it.
function OnTowerDestroyed takes integer L returns nothing
    local integer d = LaneArm(L)
    local real x = gTowerX[L]
    local real y = gTowerY[L]
    local unit p = CreateUnit(gInvader[d], gBossType[d * 3], x, y, gDirFace[d])
    set gBossTick[L + 12] = 0
    call BossEquip(L, L + 12, p, 0)
    if L >= 8 then
        call SetUnitVertexColor(p, gGateTintR[L], gGateTintG[L], gGateTintB[L], 255)
    endif
    set gProtector[L] = p
    set gProtX[L] = x
    set gProtY[L] = y
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Undead\\AnimateDead\\AnimateDeadTarget.mdl", x, y))
    call PingMinimap(x, y, 3.0)
    if L >= 8 then
        call Msg("The " + gDirColor[d] + gTurretName[d] + "|r has fallen!  Its |cffff4040" + GetUnitName(p) + "|r rises from the ruins - the next wave comes NOW, stronger!")
    else
        call Msg(gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r's " + gTurretName[d] + " has fallen!  Its |cffff4040" + GetUnitName(p) + "|r rises from the ruins - the next wave comes NOW, stronger!")
    endif
    if not gGameOver then
        call SpawnWave(L)
    endif
    set p = null
endfunction

function OnWardenSlain takes integer L returns nothing
    set gProtector[L] = null
    call Msg("|cffff4040" + gTurretName[LaneArm(L)] + " Warden|r is slain!")
endfunction

// The Tower Wardens stay with their ruins (leash), every second.
function ProtectorTick takes nothing returns nothing
    local integer L = 0
    loop
        exitwhen L > 11
        if gProtector[L] != null then
            if GetWidgetLife(gProtector[L]) <= 0.405 then
                set gProtector[L] = null
            else
                call BossBrain(L, L + 12, gProtector[L], gProtX[L], gProtY[L], gWardenLeash)
            endif
        endif
        set L = L + 1
    endloop
endfunction

function OpenGateLane takes integer L, integer opener returns nothing
    local integer d = LaneArm(L)
    if gGateState[L] != -1 or gGameOver then
        return
    endif
    set gGateState[L] = 0
    set gLaneWave[L] = gLaneWave[opener]
    call TimerStart(gLaneTimer[L], gFirstWaveDelay, false, function OnLaneTimer)
    call GateSet(L, true)
    set gTower[L] = CreateUnit(gInvader[d], gTurretType[d], gTowerX[L], gTowerY[L], gDirFace[d])
    set gNexus[L] = CreateUnit(gInvader[d], gBaseType[d], gNexusX[L], gNexusY[L], gDirFace[d])
    call ScaleTeamSpawn(gTower[L])
    call ScaleTeamSpawn(gNexus[L])
    call PingMinimapEx(gGateX[L], gGateY[L], 6.0, 255, 60, 60, true)
    call PingMinimapEx(gNexusX[L], gNexusY[L], 6.0, 255, 60, 60, true)
    call StartSound(bj_questWarningSound)
    call Msg(gDirColor[d] + "LEVEL " + I2S(L - 6) + ":|r " + gDirColor[d] + gFactionName[d] + "|r is open (" + gGateDir[L] + ")!  Wave " + I2S(gLaneWave[L] + 1) + " in " + I2S(R2I(gFirstWaveDelay)) + "s, " + I2S(L - 6) + "x gold per kill!")
    call BoardAddGate(L)
endfunction

// A gate's Nexus fell: its boss rises from the ruins (the level is done when the boss dies), waves keep coming
// from the ruins, and the next level opens.
function OnGateNexusDestroyed takes integer L returns nothing
    local integer d = LaneArm(L)
    set gGateState[L] = 1
    set gBossTick[L] = 0
    set gBoss[L] = CreateUnit(gInvader[d], gBossType[d * 3 + 1], gNexusX[L], gNexusY[L], gDirFace[d])
    call BossEquip(L, L, gBoss[L], 1)
    call DestroyEffect(AddSpecialEffect("Objects\\Spawnmodels\\Other\\NeutralBuildingExplosion\\NeutralBuildingExplosion.mdl", gNexusX[L], gNexusY[L]))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\MassTeleport\\MassTeleportTarget.mdl", gNexusX[L], gNexusY[L]))
    call PingMinimap(gNexusX[L], gNexusY[L], 6.0)
    call StartSound(bj_questWarningSound)
    call Msg("|cff40ff40The " + gBaseName[d] + " is destroyed!|r  From its ruins rises " + gDirColor[d] + gBossName[d] + "|r!   |cffffcc00+" + I2S(gGateGold[L]) + " gold|r")
    call GiveAllGold(gGateGold[L])
    if L < 11 then
        call OpenGateLane(L + 1, L)
    endif
    call UpdateBoard()
endfunction

function OnGateBossSlain takes integer L returns nothing
    local integer d = LaneArm(L)
    set gGateState[L] = 2
    set gBoss[L] = null
    call DropEpic(L - 6, gNexusX[L], gNexusY[L])
    call StartSound(bj_questCompletedSound)
    call Msg(gDirColor[d] + gBossName[d] + "|r is slain - " + gDirColor[d] + "LEVEL " + I2S(L - 6) + "|r cleared!   |cffffcc00+" + I2S(gGateGold[L]) + " gold|r")
    call GiveAllGold(gGateGold[L])
    call LaneStop(L)
    call UpdateBoard()
    call CheckVictory()
endfunction

// Fewer monsters than before v4.3, each worth more: a whole wave pays the gold and XP it paid when it had 4 + 2 x wave melee (at most 40) and
// wave ranged (at most 20). The first waves have as many as then, so nothing changes there.
function WavePayRatio takes integer w returns real
    local integer was = 4 + 2 * w
    local integer ranged = w
    local integer now = gFrontBase + gFrontPer * w
    local integer back = (gBackPer * w + 1) / 2
    if was > 40 then
        set was = 40
    endif
    if ranged > 20 then
        set ranged = 20
    endif
    if now > gFrontMax then
        set now = gFrontMax
    endif
    if back > gBackMax then
        set back = gBackMax
    endif
    return I2R(was + ranged) / I2R(now + back)
endfunction

// The XP the game itself gives for a unit of this level (MiscGame GrantNormalXP 25, formula A1 B5 C5: 25, 40, 60, 85, 115, ...).
function UnitKillXp takes integer level returns integer
    local integer xp = 25
    local integer i = 2
    loop
        exitwhen i > level
        set xp = xp + 5 * i + 5
        set i = i + 1
    endloop
    return xp
endfunction

// Minion kill gold (wave units only; their built-in bounty is 0): gold = its lane's wave x WavePayRatio on the player lanes,
// x level on the gate lanes (Level 2 x2 ... Level 5 x5). Floating +N only the killer sees.
function MinionBounty takes unit u, integer kid returns nothing
    local integer L
    local real ratio
    local integer g
    local texttag tt = CreateTextTag()
    set gTestBountyCalls = gTestBountyCalls + 1
    set L = GetUnitUserData(u) / 16
    set ratio = WavePayRatio(gLaneWave[L])
    // a wave champion is not one of the monsters that got fewer
    if GetUnitTypeId(u) == gWaveChamp[LaneArm(L)] then
        set ratio = 1.0
    endif
    set g = R2I(I2R(gLaneWave[L]) * ratio + 0.5)
    if L >= 8 then
        set g = (L - 6) * g
    endif
    // the XP the game gives for this kill is its own; the rest of what the monster is now worth comes on top
    if ratio > 1.0 and gHero[kid] != null and GetWidgetLife(gHero[kid]) > 0.405 then
        call AddHeroXP(gHero[kid], R2I(I2R(UnitKillXp(GetUnitLevel(u))) * (ratio - 1.0)), true)
    endif
    if g < 1 then
        set g = 1
    endif
    call SetPlayerState(Player(kid), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(kid), PLAYER_STATE_RESOURCE_GOLD) + g)
    call SetTextTagText(tt, "|cffffcc00+" + I2S(g) + "|r", 0.024)
    call SetTextTagPos(tt, GetUnitX(u), GetUnitY(u), 80.0)
    call SetTextTagVelocity(tt, 0.0, 0.03)
    call SetTextTagPermanent(tt, false)
    call SetTextTagLifespan(tt, 2.0)
    call SetTextTagFadepoint(tt, 1.0)
    call SetTextTagVisibility(tt, GetLocalPlayer() == Player(kid))
    set tt = null
endfunction

function OnNexusDestroyed takes integer L returns nothing
    local integer d = LaneArm(L)
    call OpenGateLane(8, L)
    set gLaneState[L] = 1
    set gBossTick[L] = 0
    set gBoss[L] = CreateUnit(gInvader[d], gBossType[d * 3 + 1], gNexusX[L], gNexusY[L], gDirFace[d])
    call BossEquip(L, L, gBoss[L], 1)
    call DestroyEffect(AddSpecialEffect("Objects\\Spawnmodels\\Other\\NeutralBuildingExplosion\\NeutralBuildingExplosion.mdl", gNexusX[L], gNexusY[L]))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\MassTeleport\\MassTeleportTarget.mdl", gNexusX[L], gNexusY[L]))
    call PingMinimap(gNexusX[L], gNexusY[L], 6.0)
    call StartSound(bj_questWarningSound)
    call Msg(gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r destroyed the " + gBaseName[d] + "!   From its ruins rises " + gDirColor[d] + gBossName[d] + "|r!  Kill it!   |cffffcc00+150 gold|r")
    call GiveAllGold(150)
    call UpdateBoard()
endfunction

function OnBossSlain takes integer L returns nothing
    local integer d = LaneArm(L)
    set gLaneState[L] = 2
    set gBoss[L] = null
    call DropEpic(1, gNexusX[L], gNexusY[L])
    call GiveAllGold(250)
    call LaneStop(L)
    call StartSound(bj_questCompletedSound)
    call Msg(gDirColor[d] + gBossName[d] + "|r of " + gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r's lane has been slain!   |cffffcc00+250 gold|r")
    call UpdateBoard()
    call CheckVictory()
endfunction

function OnReviveTimer takes nothing returns nothing
    local timer t = GetExpiredTimer()
    local integer p = 0
    loop
        exitwhen p >= 8
        if gReviveTimer[p] == t and gHero[p] != null and not gGameOver then
            call TimerDialogDisplay(gReviveDialog[p], false)
            if GetWidgetLife(gHero[p]) <= 0.405 then
                call ReviveHero(gHero[p], gHeroX[p], gHeroY[p], true)
                if gTestMode then
                    call TestLog("champion of player " + I2S(p) + " at game time " + I2S(gGameTime) + ": the revive timer, life now " + I2S(R2I(GetWidgetLife(gHero[p]))))
                endif
                call PanCameraToTimedForPlayer(Player(p), gHeroX[p], gHeroY[p], 0.5)
                call SelectUnitForPlayerSingle(gHero[p], Player(p))
                if gFollow[p] then
                    call SetCameraTargetControllerNoZForPlayer(Player(p), gHero[p], 0.0, 0.0, false)
                endif
                call PingLane(p)
            endif
        endif
        set p = p + 1
    endloop
    set t = null
endfunction

function StartRevive takes integer p returns nothing
    local real delay = 4.0 + 2.0 * GetHeroLevel(gHero[p])
    if delay > 24.0 then
        set delay = 24.0
    endif
    call TimerStart(gReviveTimer[p], delay, false, function OnReviveTimer)
    if gReviveDialog[p] == null then
        set gReviveDialog[p] = CreateTimerDialog(gReviveTimer[p])
        call TimerDialogSetTitle(gReviveDialog[p], "Revive in")
    endif
    if GetLocalPlayer() == Player(p) then
        call TimerDialogDisplay(gReviveDialog[p], true)
    endif
    call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 8.0, "Your champion has fallen and will rise again on your Champion's Circle in " + I2S(R2I(delay)) + " seconds.")
endfunction

function OnUnitDeath takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local unit killer = GetKillingUnit()
    local integer oid = GetPlayerId(GetOwningPlayer(u))
    local integer kid = -1
    local integer d
    local integer L
    if killer != null then
        set kid = GetPlayerId(GetOwningPlayer(killer))
    endif
    if u == gFinalBoss and u != null then
        call OnFinalBossDead()
    endif
    if u == gCastle then
        call OnCastleDestroyed()
    elseif oid >= 8 and oid <= 11 then
        set d = oid - 8
        if kid >= 0 and kid < 8 then
            set gKills[kid] = gKills[kid] + 1
            set gTestKills = gTestKills + 1
            if IsUnitInGroup(u, gWaveUnits) then
                call MinionBounty(u, kid)
            endif
        endif
        set L = 8
        loop
            exitwhen L > 11
            if u == gNexus[L] then
                call OnGateNexusDestroyed(L)
            elseif u == gTower[L] then
                call OnTowerDestroyed(L)
            elseif u == gBoss[L] and gBoss[L] != null then
                call OnGateBossSlain(L)
            elseif u == gProtector[L] and gProtector[L] != null then
                call OnWardenSlain(L)
            endif
            set L = L + 1
        endloop
        if IsUnitInGroup(u, gFirstWave) then
            call GroupRemoveUnit(gFirstWave, u)
            set L = GetUnitUserData(u) / 16
            set gFirstWaveLeft[L] = gFirstWaveLeft[L] - 1
            if gFirstWaveLeft[L] <= 0 then
                call GrantLevelTwo(L)
            endif
        endif
        set L = d * 2
        loop
            exitwhen L > d * 2 + 1
            if u == gNexus[L] then
                call OnNexusDestroyed(L)
            elseif u == gBoss[L] then
                call OnBossSlain(L)
            elseif u == gTower[L] then
                call OnTowerDestroyed(L)
                call UpdateBoard()
            elseif u == gProtector[L] and gProtector[L] != null then
                call OnWardenSlain(L)
            endif
            set L = L + 1
        endloop
    elseif oid < 8 and u == gHero[oid] then
        if gTestMode then
            call TestLog("champion of player " + I2S(oid) + " dies at game time " + I2S(gGameTime) + ", killed by " + GetUnitName(killer) + ", invulnerable " + I2S(GetUnitAbilityLevel(u, 'Avul')) + ", hidden " + I2S(IntegerTertiaryOp(IsUnitHidden(u), 1, 0)))
        endif
        set gDeaths[oid] = gDeaths[oid] + 1
        call UpdateBoard()
        call StartRevive(oid)
    endif
    set u = null
    set killer = null
endfunction

function OnPlayerLeave takes nothing returns nothing
    local player p = GetTriggerPlayer()
    local integer i = 0
    call Msg(GetPlayerName(p) + " has left the game.  The other champions can now control their hero.")
    loop
        exitwhen i >= 8
        if Player(i) != p and IsPlaying(i) then
            call SetPlayerAlliance(p, Player(i), ALLIANCE_SHARED_CONTROL, true)
            call SetPlayerAlliance(p, Player(i), ALLIANCE_SHARED_ADVANCED_CONTROL, true)
        endif
        set i = i + 1
    endloop
    set p = null
endfunction

//---------------------------------------------------------------------------
// Chat command:  -zoom 250  (hundreds: 250 = distance 2500)  or  -zoom 2500;  -zoom = normal
//---------------------------------------------------------------------------
function OnZoomChat takes nothing returns nothing
    local player p = GetTriggerPlayer()
    local string s = GetEventPlayerChatString()
    local integer start = 5
    local integer v
    local real dist
    loop
        exitwhen start >= StringLength(s) or SubString(s, start, start + 1) != " "
        set start = start + 1
    endloop
    set v = S2I(SubString(s, start, StringLength(s)))
    if v <= 0 then
        set v = 165
    endif
    if v < 500 then
        set dist = v * 10.0
    else
        set dist = I2R(v)
    endif
    if dist < 800.0 then
        set dist = 800.0
    elseif dist > 3500.0 then
        set dist = 3500.0
    endif
    set gZoom[GetPlayerId(p)] = dist
    if GetLocalPlayer() == p then
        call SetCameraField(CAMERA_FIELD_TARGET_DISTANCE, dist, 0.5)
        call SetCameraField(CAMERA_FIELD_FARZ, dist + 4000.0, 0.5)
        call SetTerrainFogEx(0, dist + 250.0, dist + 3850.0, 0.0, 0.02, 0.02, 0.07)
    endif
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 5.0, "Camera distance: " + I2S(R2I(dist)) + "   (-zoom 165 = normal)")
    set p = null
endfunction

//---------------------------------------------------------------------------
// Camera follow: Esc (or -cam) toggles "camera follows my champion". (1.27 scripts cannot see Space.)
//---------------------------------------------------------------------------
function ApplyZoom takes integer p returns nothing
    local real dist = gZoom[p]
    if dist < 800.0 then
        set dist = 1650.0
    endif
    if GetLocalPlayer() == Player(p) then
        call SetCameraField(CAMERA_FIELD_TARGET_DISTANCE, dist, 0.0)
        call SetCameraField(CAMERA_FIELD_FARZ, dist + 4000.0, 0.0)
        call SetTerrainFogEx(0, dist + 250.0, dist + 3850.0, 0.0, 0.02, 0.02, 0.07)
    endif
endfunction

function SetFollow takes integer p, boolean on returns nothing
    set gFollow[p] = on and gHero[p] != null
    if gFollow[p] then
        call SetCameraTargetControllerNoZForPlayer(Player(p), gHero[p], 0.0, 0.0, false)
        call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "Camera follows your champion  (|cffffcc00Esc|r or -cam to release)")
    else
        call ResetToGameCameraForPlayer(Player(p), 0.0)
        if gHero[p] != null then
            call PanCameraToTimedForPlayer(Player(p), GetUnitX(gHero[p]), GetUnitY(gHero[p]), 0.0)
        endif
    endif
    call ApplyZoom(p)
endfunction

// Space: WarCraft's Space jumps to the "quick position" - keep it on the local player's champion.
function SpaceTick takes nothing returns nothing
    local integer p = GetPlayerId(GetLocalPlayer())
    if p < 8 and gHero[p] != null then
        call SetCameraQuickPosition(GetUnitX(gHero[p]), GetUnitY(gHero[p]))
    endif
endfunction

function OnFollowToggle takes nothing returns nothing
    local integer p = GetPlayerId(GetTriggerPlayer())
    if p < 8 then
        call SetFollow(p, not gFollow[p])
    endif
endfunction

//---------------------------------------------------------------------------
// Quest log (F9)
//---------------------------------------------------------------------------
function AddQuest takes string title, string text, string icon, boolean required returns nothing
    local quest q = CreateQuest()
    call QuestSetTitle(q, title)
    call QuestSetDescription(q, text)
    call QuestSetIconPath(q, icon)
    call QuestSetRequired(q, required)
    call QuestSetDiscovered(q, true)
    call QuestSetCompleted(q, false)
    set q = null
endfunction

function CreateQuests takes nothing returns nothing
    call AddQuest("Defend your lane", "Pick a champion: click a hall and click a hero. You then defend |cffffcc00your own lane|r - every player has one lane, and a lane only sends monsters when its player is in the game.\n\nYour wave is your own: your next wave comes as soon as your lane is clear, so clearing fast means more gold and stronger monsters (1 min shopping break after every 10th wave). Keep the |cffffcc00Castle of Lordaeron|r alive - if it falls, everyone loses.", "ReplaceableTextures\\CommandButtons\\BTNCastle.blp", true)
    call AddQuest("Destroy your Nexus", "At the end of |cffffcc00your lane|r stands your own enemy Nexus, guarded by a strong tower. The Nexus sends the waves of your lane. Destroy it and your lane goes quiet - but its boss rises from the ruins.", "ReplaceableTextures\\CommandButtons\\BTNDemonGate.blp", true)
    call AddQuest("Slay the bosses", "Kill the boss of every lane and of all 4 gates. Then the |cffff4040final boss|r rises at the Castle: he cannot be stunned and grows stronger every minute. Kill him to |cff40ff40win|r!", "ReplaceableTextures\\CommandButtons\\BTNPitLord.blp", true)
    call AddQuest("Tips", "- Killing monsters gives gold and experience; every wave also pays gold.\n- |cffffcc00Secret grove|r: the narrow passage at the south-east corner of the plaza leads to the Fountain of Power (HP + mana), the Premium Armory (1000-gold items) and the Apothecary.\n- Your champion appears and revives on the circle in your colour at your lane - click the circle to |cffffcc00buy stats|r instantly (each buy costs 3% more).\n- Type |cffffcc00-help|r for the command list.\n- |cffffcc00Space|r = jump to your champion (hold to keep him centred); |cffffcc00Esc|r or -cam = camera follows him.\n- Skills are on |cffffcc00Q W E R T|r. Clearing your first wave gives level 2.\n- Staff of Teleportation lets you jump back to the castle or to a friend.\n- Type |cffffcc00-zoom 250|r to zoom out (any value, e.g. -zoom 200; -zoom 165 = normal).", "ReplaceableTextures\\CommandButtons\\BTNSnazzyScroll.blp", false)
endfunction

//---------------------------------------------------------------------------
// Self-test (only in the *_TEST build): revealed map + scripted run through
// base -> lord -> victory.
//---------------------------------------------------------------------------
function TestKillEnum takes nothing returns nothing
    call KillUnit(GetEnumUnit())
endfunction

// Test build: results go to the screen AND to <game>\TestResults\cd_test.txt (Preload file writer), so a run can be
// checked by reading a file instead of screenshots. One line per check: "PASS ..." / "FAIL ...".
function TestFlush takes nothing returns nothing
    local integer i = 0
    call PreloadGenClear()
    call PreloadGenStart()
    loop
        exitwhen i >= gTestLogN
        call Preload(gTestLog[i])
        set i = i + 1
    endloop
    call PreloadGenEnd("TestResults\\cd_test.txt")
endfunction

// slots holding item type id, and their total charges
function TestSlots takes unit h, integer id returns integer
    local integer s = 0
    local integer n = 0
    loop
        exitwhen s >= 6
        if GetItemTypeId(UnitItemInSlot(h, s)) == id then
            set n = n + 1
        endif
        set s = s + 1
    endloop
    return n
endfunction

function TestCharges takes unit h, integer id returns integer
    local integer s = 0
    local integer n = 0
    loop
        exitwhen s >= 6
        if GetItemTypeId(UnitItemInSlot(h, s)) == id then
            set n = n + GetItemCharges(UnitItemInSlot(h, s))
        endif
        set s = s + 1
    endloop
    return n
endfunction

function TestPremLevel takes unit h returns integer
    local integer s = 0
    local integer best = 0
    loop
        exitwhen s >= 6
        if UnitItemInSlot(h, s) != null and PremiumLevel(GetItemTypeId(UnitItemInSlot(h, s)), 0) > best then
            set best = PremiumLevel(GetItemTypeId(UnitItemInSlot(h, s)), 0)
        endif
        set s = s + 1
    endloop
    return best
endfunction

// Round-0 edge cases, one step per second (TestStep holds meanwhile), then the restart into round 1.
// ---- The 12 champions, real units and real casts. Heroes of empty slots (1 = most of them, 2 = the Tauren, 3 = the Demon Hunter), each in its own closed lane.
// Paused foes with a lot of HP show the damage; a wounded friend shows the heal. Levels, mana and cooldowns are fixtures; the casts, summons and effects are the game's.
function TestSpellCount takes unit u, integer a returns integer
    return LoadInteger(gTestHT, GetHandleId(u), a)
endfunction

function OnTestSpell takes nothing returns nothing
    local integer h = GetHandleId(GetTriggerUnit())
    local integer a = GetSpellAbilityId()
    call SaveInteger(gTestHT, h, a, LoadInteger(gTestHT, h, a) + 1)
endfunction

function TestArenaX takes integer c returns real
    if c <= 6 then
        return gHeroX[c + 1]
    elseif c <= 10 then
        return gWpX[(c + 1) * 8 + 1]
    endif
    return gWpX[1 * 8]
endfunction

function TestArenaY takes integer c returns real
    if c <= 6 then
        return gHeroY[c + 1]
    elseif c <= 10 then
        return gWpY[(c + 1) * 8 + 1]
    endif
    return gWpY[1 * 8]
endfunction

function TestHeroOwner takes integer c returns player
    if c == 2 then
        return Player(2)
    elseif c == 10 then
        return Player(3)
    endif
    return Player(1)
endfunction

function TestFoe takes real x, real y returns unit
    local unit u = CreateUnit(Player(8), gStageUnit[0], x, y, 0.0)
    call GroupRemoveUnit(gWaveUnits, u)
    call PauseUnit(u, true)
    call ScaleKeepHp(u, 300000, 0)
    call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    set bj_lastCreatedUnit = u
    set u = null
    return bj_lastCreatedUnit
endfunction

// Fresh foes and a wounded friend for hero c.
function TestHeroProps takes integer c returns nothing
    local integer i = 0
    local real x = TestArenaX(c)
    local real y = TestArenaY(c)
    loop
        exitwhen i >= 4
        if gTestFoe[c * 4 + i] != null then
            call RemoveUnit(gTestFoe[c * 4 + i])
        endif
        set gTestFoe[c * 4 + i] = TestFoe(x + 150.0 * Cos(i * 1.5708), y + 150.0 * Sin(i * 1.5708))
        set i = i + 1
    endloop
    if gTestFriend[c] != null then
        call RemoveUnit(gTestFriend[c])
    endif
    set gTestFriend[c] = CreateUnit(TestHeroOwner(c), 'hfoo', x + 150.0, y + 150.0, 0.0)
    call PauseUnit(gTestFriend[c], true)
    call SetWidgetLife(gTestFriend[c], 20.0)
endfunction

function TestFoeLife takes integer c returns real
    local integer i = 0
    local real v = 0.0
    loop
        exitwhen i >= 4
        set v = v + GetWidgetLife(gTestFoe[c * 4 + i])
        set i = i + 1
    endloop
    return v
endfunction

function OnTestSummon takes nothing returns nothing
    local unit s = GetSummoningUnit()
    local integer c = 0
    loop
        exitwhen c >= gHeroPoolCount
        if gTestH[c] == s then
            set gTestSumU[gTestSumN] = GetSummonedUnit()
            set gTestSumC[gTestSumN] = c
            set gTestSumN = gTestSumN + 1
        endif
        set c = c + 1
    endloop
    set s = null
endfunction

// What hero c has summoned and is alive; id 0 = anything.
function TestSummons takes integer c, integer id returns integer
    local integer i = 0
    local integer n = 0
    loop
        exitwhen i >= gTestSumN
        if gTestSumC[i] == c and GetWidgetLife(gTestSumU[i]) > 0.405 and (id == 0 or GetUnitTypeId(gTestSumU[i]) == id) then
            set n = n + 1
        endif
        set i = i + 1
    endloop
    return n
endfunction

function TestOwnedOfType takes integer c, integer id returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    call GroupEnumUnitsOfPlayer(g, TestHeroOwner(c), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetUnitTypeId(u) == id and GetWidgetLife(u) > 0.405 then
            set n = n + 1
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

// A hero's images: units of his own type, of his owner, that are illusions.
function TestImages takes integer c, boolean remove returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    call GroupEnumUnitsOfPlayer(g, TestHeroOwner(c), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if IsUnitIllusion(u) and GetUnitTypeId(u) == GetUnitTypeId(gTestH[c]) and GetWidgetLife(u) > 0.405 then
            set n = n + 1
            if remove then
                call RemoveUnit(u)
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

// What a cast left behind goes, only what this hero made, so the next one starts clean.
function TestClearSummons takes integer c returns nothing
    local integer i = 0
    loop
        exitwhen i >= gTestSumN
        if gTestSumC[i] == c and gTestSumU[i] != null then
            call RemoveUnit(gTestSumU[i])
            set gTestSumU[i] = null
        endif
        set i = i + 1
    endloop
    call TestImages(c, true)
endfunction

// A hero from level 1: nothing of level 20 yet, then the level, every skill to its maximum, and his level 20 ability.
function TestHeroSetupOne takes nothing returns nothing
    local integer c = gTestC
    local integer s = 0
    local integer k = 0
    local integer got = 0
    local integer maxed = 0
    local unit h = CreateUnit(TestHeroOwner(c), gHeroPool[c], TestArenaX(c), TestArenaY(c), 0.0)
    set gTestH[c] = h
    call TestHeroProps(c)
    call SetHeroLevel(h, 19, false)
    loop
        exitwhen k >= gGrantN
        if gGrantHero[k] == gHeroPool[c] and GetUnitAbilityLevel(h, gGrantAbil[k]) > 0 then
            set got = got + 1
        endif
        set k = k + 1
    endloop
    call TestCheck(got == 0, GetUnitName(h) + ": nothing of level 20 at level 19")
    call SetHeroLevel(h, 20, false)
    set got = 0
    set k = 0
    loop
        exitwhen k >= gGrantN
        if gGrantHero[k] == gHeroPool[c] and GetUnitAbilityLevel(h, gGrantAbil[k]) > 0 then
            set got = got + 1
        endif
        set k = k + 1
    endloop
    call TestCheck(got > 0, GetUnitName(h) + ": level 20 gives his ability")
    loop
        exitwhen s >= gSkillsPerHero
        set k = 0
        loop
            exitwhen k >= 4
            call SelectHeroSkill(h, gHeroSkill[c * gSkillsPerHero + s])
            set k = k + 1
        endloop
        if GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero + s]) >= 2 then
            set maxed = maxed + 1
        endif
        set s = s + 1
    endloop
    call TestCheck(maxed == gSkillsPerHero, GetUnitName(h) + ": all 5 skills learned (" + I2S(GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero])) + "/" + I2S(GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero + 1])) + "/" + I2S(GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero + 2])) + "/" + I2S(GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero + 3])) + "/" + I2S(GetUnitAbilityLevel(h, gHeroSkill[c * gSkillsPerHero + 4])) + "), points left " + I2S(GetHeroSkillPoints(h)))
    call SetHeroInt(h, GetHeroInt(h, false) + 400, true)
    // nothing fights back: the foes are paused. (The Demon Hunter's Roar does not take an invulnerable target, and the others' fixtures need none either way.)
    if c != 10 then
        call SetUnitInvulnerable(h, true)
    endif
    if c != 0 then
        call UnitRemoveAbility(h, 'Aatk')
    endif
    set h = null
endfunction

// Row n of the cast table: the order as a player gives it.
function TestCastOne takes nothing returns nothing
    local integer n = gTestN
    local integer c = gCastHero[n]
    local unit h = gTestH[c]
    local unit f = gTestFoe[c * 4]
    local integer kind = gCastTarget[n]
    local boolean ok = false
    call TestHeroProps(c)
    set f = gTestFoe[c * 4]
    if gCastAbil[n] == 'ANdo' then
        // the real melee monster, at the Doom level this row has learned
        call RemoveUnit(gTestFoe[c * 4])
        set gTestFoe[c * 4] = CreateUnit(Player(8), 'q00m', GetUnitX(h) + 150.0, GetUnitY(h), 0.0)
        call ScaleKeepHp(gTestFoe[c * 4], 300000, 0)
        call SetWidgetLife(gTestFoe[c * 4], GetUnitState(gTestFoe[c * 4], UNIT_STATE_MAX_LIFE))
        set f = gTestFoe[c * 4]
    endif
    if gCastAbil[n] == 'AUim' or gCastAbil[n] == 'ANdo' then
        // a paused unit is no fair target for these two: free foes, they cannot hurt him anyway
        call PauseUnit(gTestFoe[c * 4], false)
        call PauseUnit(gTestFoe[c * 4 + 1], false)
        call PauseUnit(gTestFoe[c * 4 + 2], false)
        call PauseUnit(gTestFoe[c * 4 + 3], false)
    endif
    call UnitResetCooldown(h)
    call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
    set gTestLifeBefore[c] = TestFoeLife(c)
    set gTestFriendBefore[c] = GetWidgetLife(gTestFriend[c])
    set gTestCountBefore[c] = TestSpellCount(h, gCastAbil[n])
    set gTestManaBefore[c] = GetUnitState(h, UNIT_STATE_MANA)
    if kind == 0 then
        set ok = IssueImmediateOrder(h, gCastOrder[n])
    elseif kind == 1 then
        set ok = IssueTargetOrder(h, gCastOrder[n], f)
    elseif kind == 2 then
        set ok = IssuePointOrder(h, gCastOrder[n], GetUnitX(f), GetUnitY(f))
    elseif kind == 3 then
        set ok = IssueTargetOrder(h, gCastOrder[n], gTestFriend[c])
    elseif kind == 4 then
        set ok = IssueTargetOrder(h, gCastOrder[n], h)
    else
        // a real corpse: a wave monster, dead for a moment
        set f = CreateUnit(Player(8), gStageUnit[0], GetUnitX(h) + 200.0, GetUnitY(h), 0.0)
        call GroupRemoveUnit(gWaveUnits, f)
        call KillUnit(f)
        // its death takes about 5 s, only then it is a corpse
        call TriggerSleepAction(5.5)
        set ok = IssueTargetOrder(h, gCastOrder[n], f)
        if not ok then
            set ok = IssueImmediateOrder(h, "carrionscarabsinstant")
        endif
    endif
    set gTestOrderOk[c] = ok
    set h = null
    set f = null
endfunction

function TestCastCheck takes nothing returns nothing
    local integer n = gTestN
    local integer c = gCastHero[n]
    local unit h = gTestH[c]
    local integer e = gCastEffect[n]
    local integer seen = TestSpellCount(h, gCastAbil[n]) - gTestCountBefore[c]
    local real lost = gTestLifeBefore[c] - TestFoeLife(c)
    local integer images = TestImages(c, false)
    local string who = GetUnitName(h) + " " + gCastName[n]
    local boolean good = false
    local string what = ""
    if e == 1 then
        set good = lost > 1.0
        set what = "damage " + I2S(R2I(lost))
    elseif e == 2 then
        set good = GetWidgetLife(gTestFriend[c]) > gTestFriendBefore[c] + 1.0
        set what = "healed " + I2S(R2I(GetWidgetLife(gTestFriend[c]) - gTestFriendBefore[c]))
    elseif e == 3 then
        set good = TestSummons(c, gCastUnit[n]) == gCastCount[n]
        set what = I2S(TestSummons(c, gCastUnit[n])) + " of the " + I2S(gCastCount[n]) + " summons, " + I2S(TestSummons(c, 0)) + " in all"
    elseif e == 8 then
        set good = GetUnitAbilityLevel(gTestFoe[c * 4], gCastUnit[n]) > 0
        set what = "its buff on the enemy"
    elseif e == 9 then
        set good = GetUnitAbilityLevel(gTestFriend[c], gCastUnit[n]) > 0
        set what = "its buff on the friend"
    elseif e == 10 then
        set good = images == gCastCount[n]
        set what = I2S(images) + " images"
    elseif e == 4 then
        set good = GetUnitAbilityLevel(h, gCastUnit[n]) > 0
        set what = "buff on him"
    elseif e == 5 then
        set good = GetUnitTypeId(h) == gCastUnit[n]
        set what = "now " + GetUnitName(h)
    else
        set good = true
        set what = "mana " + I2S(R2I(gTestManaBefore[c] - GetUnitState(h, UNIT_STATE_MANA)))
    endif
    // no attack is left to fake it: the order must be taken and the game must report the spell
    call TestCheck(good and gTestOrderOk[c] and (seen > 0 or e == 5), who + ": order " + TestB2S(gTestOrderOk[c]) + ", spell " + I2S(seen) + ", " + what)
    if e != 5 then
        call IssueImmediateOrder(h, "unimmolation")
        call IssueImmediateOrder(h, "stop")
        call TestClearSummons(c)
    endif
    set h = null
endfunction

// ---- Dryad: what Multiple Arrows really does. Every hit on a foe is timed; a burst = hits less than 0.15 s apart.
function OnTestArrowHit takes nothing returns nothing
    // her poison ticks and empty events are not spears: this hero has no poison, and only real damage counts
    if GetEventDamageSource() == gTestScene and GetEventDamage() > 0.5 and gTestHitN < 900 then
        set gTestHitT[gTestHitN] = TimerGetElapsed(gTestClockT)
        set gTestHitU[gTestHitN] = GetTriggerUnit()
        set gTestHitD[gTestHitN] = GetEventDamage()
        set gTestHitN = gTestHitN + 1
    endif
endfunction

function TestSceneFoes takes integer n, real r returns nothing
    local integer i = 0
    local real x = GetUnitX(gTestScene)
    local real y = GetUnitY(gTestScene)
    loop
        exitwhen i >= 16
        if gTestSceneFoe[i] != null then
            call RemoveUnit(gTestSceneFoe[i])
            set gTestSceneFoe[i] = null
        endif
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= n
        set gTestSceneFoe[i] = TestFoe(x + r * Cos(i * 6.2832 / I2R(n)), y + r * Sin(i * 6.2832 / I2R(n)))
        call TriggerRegisterUnitEvent(gTestHitTrig, gTestSceneFoe[i], EVENT_UNIT_DAMAGED)
        set i = i + 1
    endloop
    set gTestHitN = 0
endfunction

// Bursts of the hits so far: count, biggest, smallest, and how many had all different targets.
function TestSceneBursts takes string label returns integer
    local integer i = 0
    local integer j
    local integer bursts = 0
    local integer most = 0
    local integer fewest = 999
    local integer size
    local integer distinct = 0
    local integer k
    local boolean same
    local real first = 0.0
    local real last = 0.0
    local real spread = 0.0
    local real dmgLow = 1000000.0
    local real dmgHigh = 0.0
    loop
        exitwhen i >= gTestHitN
        set j = i
        loop
            exitwhen j + 1 >= gTestHitN or gTestHitT[j + 1] - gTestHitT[j] >= 0.15
            set j = j + 1
        endloop
        set size = j - i + 1
        set bursts = bursts + 1
        if bursts == 1 then
            set first = gTestHitT[i]
        endif
        set last = gTestHitT[i]
        if size > most then
            set most = size
        endif
        if size < fewest then
            set fewest = size
        endif
        if gTestHitT[j] - gTestHitT[i] > spread then
            set spread = gTestHitT[j] - gTestHitT[i]
        endif
        set same = false
        set k = i
        loop
            exitwhen k > j
            set size = k + 1
            loop
                exitwhen size > j
                if gTestHitU[size] == gTestHitU[k] then
                    set same = true
                endif
                set size = size + 1
            endloop
            if gTestHitD[k] < dmgLow then
                set dmgLow = gTestHitD[k]
            endif
            if gTestHitD[k] > dmgHigh then
                set dmgHigh = gTestHitD[k]
            endif
            set k = k + 1
        endloop
        if not same then
            set distinct = distinct + 1
        endif
        set i = j + 1
    endloop
    set gTestBurstMost = most
    set gTestBurstFewest = fewest
    set gTestBurstDistinct = distinct
    set gTestBurstEvery = 0.0
    if bursts > 1 then
        set gTestBurstEvery = (last - first) / I2R(bursts - 1)
    endif
    set gTestBurstSpread = spread
    set gTestBurstDmgLow = dmgLow
    set gTestBurstDmgHigh = dmgHigh
    if gTestHitN == 0 then
        set gTestBurstDmgLow = 0.0
        set gTestBurstFewest = 0
    endif
    call TestLog("arrows " + label + ": " + I2S(gTestHitN) + " hits in " + I2S(bursts) + " bursts, " + I2S(fewest) + " to " + I2S(most) + " per burst, every " + R2SW(gTestBurstEvery, 1, 2) + " s, one burst lands within " + R2SW(spread, 1, 3) + " s, damage " + I2S(R2I(dmgLow)) + " to " + I2S(R2I(dmgHigh)) + ", bursts on all different targets " + I2S(distinct))
    return bursts
endfunction

function TestOwnedOfTypeP0 takes integer id returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    call GroupEnumUnitsOfPlayer(g, Player(0), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetUnitTypeId(u) == id then
            set n = n + 1
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

// Doom at both levels, clean: a fresh invulnerable Pit Lord without his attack, one free monster, nothing else around. Level 2 on a monster of the creep race lives on the ability table's one changed cell (build.py).
function TestDoomCount takes unit caster returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    call GroupEnumUnitsOfPlayer(g, GetOwningPlayer(caster), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetUnitTypeId(u) == 'nba2' then
            set n = n + 1
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

function TestDoomClear takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    call GroupEnumUnitsOfPlayer(g, Player(1), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        call RemoveUnit(u)
    endloop
    call DestroyGroup(g)
    set g = null
    if gTestDoomFoe != null then
        call RemoveUnit(gTestDoomFoe)
        set gTestDoomFoe = null
    endif
endfunction

function TestDoomOnSpell takes nothing returns nothing
    if GetSpellAbilityId() == 'ANdo' then
        set gTestDoomSpell = gTestDoomSpell + 1
    endif
endfunction

function TestDoomOne takes integer level, integer ut returns nothing
    local unit h
    local unit u
    call TestDoomClear()
    set h = CreateUnit(Player(1), gHeroPool[3], gWpX[2 * 8 + 1], gWpY[2 * 8 + 1], 0.0)
    set gTestDoomHero = h
    call SetHeroLevel(h, 20, false)
    call UnitRemoveAbility(h, 'Aatk')
    call SetUnitInvulnerable(h, true)
    call SelectHeroSkill(h, 'ANdo')
    if level == 2 then
        call SelectHeroSkill(h, 'ANdo')
    endif
    call SetHeroInt(h, GetHeroInt(h, false) + 400, true)
    call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
    set u = CreateUnit(Player(8), ut, GetUnitX(h) + 300.0, GetUnitY(h), 180.0)
    call GroupRemoveUnit(gWaveUnits, u)
    call ScaleKeepHp(u, 30000, 0)
    call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    set gTestDoomFoe = u
    set gTestDoomLife = GetWidgetLife(u)
    set gTestDoomSpell = 0
    set gTestDoomOrder = IssueTargetOrder(h, "doom", u)
    set h = null
    set u = null
endfunction

function TestDoomTick takes nothing returns nothing
    local integer r
    local integer step
    local integer level
    local real lost
    set gTestDoomStep = gTestDoomStep + 1
    set r = (gTestDoomStep - 1) / 7
    set step = ModuloInteger(gTestDoomStep - 1, 7)
    if r >= 5 then
        call TestDoomClear()
        call DestroyTrigger(gTestDoomTrig)
        set gTestDoomDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
        return
    endif
    if step == 0 then
        if r == 0 then
            call TestDoomOne(1, 'q00m')
        elseif r == 1 then
            call TestDoomOne(2, 'q00m')
        elseif r == 2 then
            call TestDoomOne(2, 'nogm')
        elseif r == 3 then
            call TestDoomOne(2, 'njga')
        else
            call TestDoomOne(1, 'njga')
        endif
    elseif step == 3 then
        set lost = gTestDoomLife - GetWidgetLife(gTestDoomFoe)
        set level = GetUnitAbilityLevel(gTestDoomHero, 'ANdo')
        if r <= 2 then
            call TestCheck(gTestDoomOrder and gTestDoomSpell == 1 and GetUnitAbilityLevel(gTestDoomFoe, 'BNdo') > 0 and lost >= 1200.0 * level and lost <= 1800.0 * level, "Doom level " + I2S(level) + " on " + GetUnitName(gTestDoomFoe) + " (level " + I2S(GetUnitLevel(gTestDoomFoe)) + "): order, spell, buff, " + I2S(R2I(lost)) + " damage in 3 s")
            call SetWidgetLife(gTestDoomFoe, 50.0)
        else
            call TestCheck(not gTestDoomOrder and gTestDoomSpell == 0 and lost <= 0.0, "Doom level " + I2S(level) + " still refuses " + GetUnitName(gTestDoomFoe) + " (level " + I2S(GetUnitLevel(gTestDoomFoe)) + "): the game's own limit")
        endif
    elseif step == 6 and r <= 2 then
        set level = GetUnitAbilityLevel(gTestDoomHero, 'ANdo')
        call TestCheck(GetWidgetLife(gTestDoomFoe) <= 0.405 and TestDoomCount(gTestDoomHero) == level, "Doom level " + I2S(level) + ": the monster dies, " + I2S(TestDoomCount(gTestDoomHero)) + " Doom Guards rise")
        call TestFlush()
    endif
endfunction

// The prices the circle really takes: +5 % a buy, compound, rounded, from the first step to the last.
function TestPriceBuy takes integer k returns nothing
    call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 500000)
    set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
    call TestLog("price step " + I2S(k) + ": order " + TestB2S(IssueImmediateOrderById(gLaneMarker[0], gStatItem[k])))
endfunction

function TestPriceCheck takes integer k returns nothing
    local integer price = gTestGold - GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
    call TestCheck(price == R2I(100.0 * Pow(1.05, I2R(k)) + 0.5), "price step " + I2S(k) + " costs " + I2S(price) + " gold, 100 x 1.05^" + I2S(k))
endfunction

// A real selection for each of the 12, one round each: restart, tavern, AssignHero, the round starts. The first one once more: the same champion sells again.
// After them, the sales that must not stay: outside a selection, with a champion and without.
function TestPickTick takes nothing returns nothing
    local integer s
    local integer want
    set gTestPickStep = gTestPickStep + 1
    if gTestPickC <= gHeroPoolCount then
        set s = ModuloInteger(gTestPickStep - 1, 7)
        set want = gHeroPool[ModuloInteger(gTestPickC, gHeroPoolCount)]
        if s == 0 then
            set gTestPickBuy = want
            set gTestSoldType = 0
            call ExecuteFunc("CDRestart")
        elseif s == 6 then
            call TestCheck(GetUnitTypeId(gHero[0]) == want and gTestSoldType == want and gStarted and not gSelecting and gSoul[0] == null and TestOwnedOfTypeP0(want) == 1, "selection " + I2S(gTestPickC + 1) + " of 13: " + GetObjectName(want) + " bought, on his circle, the soul gone, the round runs (" + GetUnitName(gHero[0]) + ")")
            set gTestPickC = gTestPickC + 1
            call TestFlush()
        endif
        return
    endif
    set s = gTestPickStep - 7 * (gHeroPoolCount + 1)
    set want = gHeroPool[4]
    if s == 1 then
        set gTestPickBuy = 0
        call TestPriceBuy(0)
    elseif s == 2 then
        call TestPriceCheck(0)
        call TestPriceBuy(1)
    elseif s == 3 then
        call TestPriceCheck(1)
        call TestPriceBuy(2)
    elseif s == 4 then
        call TestPriceCheck(2)
        // the last of the price steps
        set gStatNext[0] = gStatTiers - 1
        set gStatApplied[0] = gStatTiers - 1
        call StockCircle(0)
    elseif s == 5 then
        call TestPriceBuy(gStatTiers - 1)
    elseif s == 6 then
        call TestPriceCheck(gStatTiers - 1)
        call TestCheck(KindNext(0, 0) == gStatTiers, "after the last price step nothing more of that kind (" + I2S(KindNext(0, 0)) + " of " + I2S(gStatTiers) + ")")
    elseif s == 7 then
        set gSoul[0] = CreateUnit(Player(0), gSoulType, gHallX, gHallY + gHallSoulDY, 90.0)
    elseif s == 11 then
        set gTestPickOld = gHero[0]
        set gTestSoldType = 0
        call TestLog("outside the selection, with a champion: order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gTavern[0], want)) + ", sold " + I2S(gTestSoldType) + ", heroes in the same instant " + I2S(TestOwnedOfTypeP0(want)))
    elseif s == 12 then
        call TestCheck(gTestSoldType == want and TestOwnedOfTypeP0(want) == 0 and gHero[0] == gTestPickOld and not gSelecting, "the round runs, the player has a champion: a second one sold does not stay (" + I2S(TestOwnedOfTypeP0(want)) + " left, sold " + I2S(gTestSoldType) + ", the same champion " + TestB2S(gHero[0] == gTestPickOld) + ")")
        call RemoveUnit(gHero[0])
        set gHero[0] = null
        set gTestSoldType = 0
        call TestLog("outside the selection, no champion: order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gTavern[0], want)) + ", sold " + I2S(gTestSoldType) + ", heroes in the same instant " + I2S(TestOwnedOfTypeP0(want)))
    elseif s == 13 then
        call TestCheck(gTestSoldType == want and TestOwnedOfTypeP0(want) == 0 and gHero[0] == null and not gSelecting, "the round runs, the player has no champion: one sold outside the selection does not stay (" + I2S(TestOwnedOfTypeP0(want)) + " left, sold " + I2S(gTestSoldType) + ")")
        call RemoveUnit(gSoul[0])
        set gSoul[0] = null
        set gTestPickOld = null
        set gTestPicksDone = true
        call TestFlush()
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

function TestSceneTick takes nothing returns nothing
    local integer t
    local integer b
    set gTestSceneT = gTestSceneT + 1
    set t = gTestSceneT
    if t == 1 then
        // the reference's learn levels: Evasion 1/3/5/7, Multiple Arrows 1/4/7/10, Critical Arrows 8/10/12/14, Trueshot 10/12/14/16, Endurance 5/7/9/11
        set gTestScene = CreateUnit(Player(1), gHeroPool[0], gNexusSpawnX[5], gNexusSpawnY[5], 0.0)
        call UnitModifySkillPoints(gTestScene, 30)
        call SelectHeroSkill(gTestScene, gHeroSkill[2])
        call TestCheck(GetUnitAbilityLevel(gTestScene, gHeroSkill[2]) == 0, "Dryad: Critical Arrows not learnable at level 1")
        call SelectHeroSkill(gTestScene, gHeroSkill[1])
        call SelectHeroSkill(gTestScene, gHeroSkill[1])
        call TestCheck(GetUnitAbilityLevel(gTestScene, gHeroSkill[1]) == 1, "Dryad: Multiple Arrows level 1 at hero level 1, not yet level 2")
        call SetHeroLevel(gTestScene, 4, false)
        call SelectHeroSkill(gTestScene, gHeroSkill[1])
        call TestCheck(GetUnitAbilityLevel(gTestScene, gHeroSkill[1]) == 2, "Dryad: Multiple Arrows level 2 at hero level 4")
        call SetHeroLevel(gTestScene, 10, false)
        call TestCheck(GetUnitAbilityLevel(gTestScene, 'A027') == 0, "Dryad: no Spell Immunity before level 20")
        // the control: a fresh Dryad of the same level who never learned it. Neither she nor the next one has her poison: only spears are counted here.
        call RemoveUnit(gTestScene)
        set gTestScene = CreateUnit(Player(1), gHeroPool[0], gNexusSpawnX[5], gNexusSpawnY[5], 0.0)
        call SetHeroLevel(gTestScene, 10, false)
        call UnitRemoveAbility(gTestScene, 'ACvs')
        call SetUnitInvulnerable(gTestScene, true)
        call TestSceneFoes(12, 450.0)
    elseif t == 7 then
        call TestSceneBursts("no skill, the control")
        set gTestWeapon = gTestBurstDmgHigh
        call TestCheck(gTestHitN > 0 and gTestBurstMost == 1, "Dryad without the skill: one spear at a time (" + I2S(gTestHitN) + " hits in 6 s, " + I2S(R2I(gTestBurstDmgHigh)) + " damage)")
        set gTestSceneControl = gTestHitN
        call SelectHeroSkill(gTestScene, gHeroSkill[1])
        call TestCheck(GetUnitAbilityLevel(gTestScene, gHeroSkill[1]) == 1, "the same Dryad learns Multiple Arrows")
        set gTestHitN = 0
    elseif t == 13 then
        call TestSceneBursts("level 1")
        // what the game really throws, attack by attack: more than the field's 2 / 4 / 6 / 8
        call TestCheck(gTestBurstMost == 4 and gTestBurstFewest == 4 and gTestBurstDistinct > 0, "Dryad level 1: 4 spears at once, at different enemies (field 2)")
        call TestCheck(gTestBurstDmgHigh > 0.0 and gTestBurstDmgHigh < 250.0, "Dryad: a spear does the damage of her weapon, not the 250 of the field (" + I2S(R2I(gTestBurstDmgLow)) + " to " + I2S(R2I(gTestBurstDmgHigh)) + ")")
        call SetUnitAbilityLevel(gTestScene, gHeroSkill[1], 2)
        set gTestHitN = 0
    elseif t == 19 then
        call TestSceneBursts("level 2")
        call TestCheck(gTestBurstMost == 6 and gTestBurstFewest == 6 and gTestBurstDistinct > 0, "Dryad level 2: 6 spears at once (field 4)")
        call SetUnitAbilityLevel(gTestScene, gHeroSkill[1], 3)
        set gTestHitN = 0
    elseif t == 25 then
        call TestSceneBursts("level 3")
        call TestCheck(gTestBurstMost == 8 and gTestBurstFewest >= 6 and gTestBurstDistinct > 0, "Dryad level 3: 8 spears at once (field 6)")
        call SetUnitAbilityLevel(gTestScene, gHeroSkill[1], 4)
        // the visible proof: the runner films the next seconds of the hidden display
        call PanCameraToTimed(GetUnitX(gTestScene), GetUnitY(gTestScene), 0.0)
        call TestLog("VIDEO dryad-volley 8")
        call TestFlush()
        set gTestHitN = 0
    elseif t == 33 then
        set b = TestSceneBursts("level 4")
        call TestCheck(gTestBurstMost == 10 and gTestBurstDistinct > 0, "Dryad level 4: " + I2S(gTestBurstMost) + " spears at once out of 12 enemies, each at another (field 8)")
        call TestCheck(gTestBurstEvery > 0.0 and gTestBurstSpread < 0.2, "Dryad: all spears of one volley land together, a volley every " + R2SW(gTestBurstEvery, 1, 2) + " s")
        set gTestSceneEvery = gTestBurstEvery
        // her weapon carries the spears: more Agility, more damage on every spear
        set gTestWeapon = gTestBurstDmgHigh
        call SetHeroAgi(gTestScene, GetHeroAgi(gTestScene, false) + 200, true)
        set gTestHitN = 0
    elseif t == 34 then
        // a spear thrown before the Agility can still land in that first moment (46 in 20261102-232634-b-7ad4)
        set gTestHitN = 0
    elseif t == 39 then
        set b = TestSceneBursts("+200 Agility")
        call TestCheck(gTestBurstDmgLow > gTestWeapon, "Dryad: stats raise every spear (" + I2S(R2I(gTestWeapon)) + " -> " + I2S(R2I(gTestBurstDmgLow)) + ")")
        call TestCheck(gTestBurstEvery < gTestSceneEvery - 0.2, "Dryad: a volley comes with her attack: faster attacks, more volleys (every " + R2SW(gTestSceneEvery, 1, 2) + " s -> " + R2SW(gTestBurstEvery, 1, 2) + " s)")
        call SetHeroAgi(gTestScene, GetHeroAgi(gTestScene, false) - 200, true)
        call TestSceneFoes(12, 450.0)
    elseif t >= 40 and t <= 45 then
        set b = 0
        loop
            exitwhen b >= 10
            call IssueImmediateOrder(gTestScene, "stop")
            set b = b + 1
        endloop
    elseif t == 46 then
        set b = TestSceneBursts("stop orders")
        call TestLog("Dryad under stop orders: " + I2S(gTestHitN) + " hits, at most " + I2S(gTestBurstMost) + " in a volley: a volley with " + I2S(b) + " bursts in 6 s")
        call TestCheck(gTestBurstMost <= 10, "Dryad: stop orders add no spears")
        call IssuePointOrder(gTestScene, "move", GetUnitX(gTestScene) - 200.0, GetUnitY(gTestScene))
        set gTestHitN = 0
    elseif t == 49 then
        set b = TestSceneBursts("while she walks")
        call TestLog("Dryad while walking: " + I2S(gTestHitN) + " hits")
        call IssueImmediateOrder(gTestScene, "stop")
        call SetUnitPosition(gTestScene, gNexusSpawnX[5], gNexusSpawnY[5])
        call TestSceneFoes(1, 450.0)
    elseif t == 55 then
        set b = TestSceneBursts("one enemy, level 4")
        call TestLog("Dryad at level 4 on one enemy: " + I2S(gTestHitN) + " hits in 6 s, most at once " + I2S(gTestBurstMost))
        call TestSceneFoes(4, 800.0)
        call IssueImmediateOrder(gTestScene, "holdposition")
    elseif t == 61 then
        set b = TestSceneBursts("enemies out of reach")
        call TestCheck(gTestHitN == 0, "Dryad: no spear at enemies 800 away (" + I2S(gTestHitN) + " hits)")
        // the critical hit skill beside it: what the two do together, as the original has them
        call SelectHeroSkill(gTestScene, gHeroSkill[2])
        call SetUnitAbilityLevel(gTestScene, gHeroSkill[2], 4)
        call TestSceneFoes(12, 450.0)
    elseif t == 73 then
        set b = TestSceneBursts("with Critical Arrows level 4")
        call TestLog("Dryad with Critical Arrows: " + I2S(gTestHitN) + " hits in 12 s, " + I2S(b) + " bursts, damage " + I2S(R2I(gTestBurstDmgLow)) + " to " + I2S(R2I(gTestBurstDmgHigh)))
        // her whole kit: her poison back, on a Dryad as the tavern sells her
        call UnitAddAbility(gTestScene, 'ACvs')
        call TestSceneFoes(1, 300.0)
    elseif t >= 74 and t <= 79 then
        if GetUnitAbilityLevel(gTestSceneFoe[0], 'Bpoi') > 0 or GetUnitAbilityLevel(gTestSceneFoe[0], 'Bpsd') > 0 then
            set gTestScenePoison = true
        endif
    elseif t == 80 then
        call TestCheck(gTestScenePoison, "Dryad: her hits poison (Envenomed Spears)")
        call TestSceneFoes(0, 0.0)
        set gTestSceneDone = true
        call TestFlush()
    endif
endfunction

// ---- The Tauren's Reincarnation through the production death path: ready, then on cooldown.
function TestTauren takes nothing returns nothing
    local unit h = gTestH[2]
    set gTestTaurenT = gTestTaurenT + 1
    if gTestTaurenT == 1 then
        call SetUnitInvulnerable(h, false)
        set gHero[2] = h
        call SetUnitState(h, UNIT_STATE_LIFE, 100.0)
        set gTestDeathsBefore = gDeaths[2]
        call UnitDamageTarget(gTestFoe[2 * 4], h, 1000000.0, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
    elseif gTestTaurenT == 3 then
        call TestLog("Reincarnation ready, 2 s after the blow: alive " + TestB2S(GetWidgetLife(h) > 0.405) + ", deaths counted " + I2S(gDeaths[2] - gTestDeathsBefore) + ", revive running " + TestB2S(TimerGetRemaining(gReviveTimer[2]) > 0.0))
    elseif gTestTaurenT == 8 then
        call TestCheck(GetWidgetLife(h) > 0.405, "Reincarnation: the Tauren is back after 5 s")
        call TestLog("Reincarnation: deaths counted " + I2S(gDeaths[2] - gTestDeathsBefore) + ", revive running " + TestB2S(TimerGetRemaining(gReviveTimer[2]) > 0.0))
        // on cooldown now: a normal death
        set gTestDeathsBefore = gDeaths[2]
        call UnitDamageTarget(gTestFoe[2 * 4], h, 1000000.0, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
    elseif gTestTaurenT == 10 then
        call TestCheck(gDeaths[2] == gTestDeathsBefore + 1 and GetWidgetLife(h) <= 0.405 and TimerGetRemaining(gReviveTimer[2]) > 0.0, "Reincarnation on cooldown: a real death, the normal revive runs (" + I2S(R2I(TimerGetRemaining(gReviveTimer[2]))) + " s)")
    elseif gTestTaurenT == 36 then
        call TestCheck(GetWidgetLife(h) > 0.405, "the Tauren revived normally after that death")
        call SetUnitInvulnerable(h, true)
        set gHero[2] = null
        set gTestTaurenDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set h = null
endfunction

function TestCountEnemy takes integer id returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    local integer o = 8
    loop
        exitwhen o > 11
        call GroupEnumUnitsOfPlayer(g, Player(o), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            if GetUnitTypeId(u) == id and GetWidgetLife(u) > 0.405 then
                set n = n + 1
                set gTestEnemyFound = u
            endif
        endloop
        set o = o + 1
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

function TestFirstEnemy takes integer id returns unit
    call TestCountEnemy(id)
    return gTestEnemyFound
endfunction

// ---- A lane boss in the second round, at wave 20: real units, real spells. Its own lane's wave made it; what a stun does; what it casts; what it pays.
function TestBossSpell takes nothing returns nothing
    local integer h = GetHandleId(GetTriggerUnit())
    local integer a = GetSpellAbilityId()
    if gTestHT != null then
        call SaveInteger(gTestHT, h, a, LoadInteger(gTestHT, h, a) + 1)
    endif
endfunction

function TestStunner takes integer c, real dist returns unit
    local unit b = gBoss[0]
    local unit h = CreateUnit(Player(1), gHeroPool[c], GetUnitX(b) + dist, GetUnitY(b), 0.0)
    local integer s = 0
    local integer k
    call SetHeroLevel(h, 20, false)
    loop
        exitwhen s >= gSkillsPerHero
        set k = 0
        loop
            exitwhen k >= 4
            call SelectHeroSkill(h, gHeroSkill[c * gSkillsPerHero + s])
            set k = k + 1
        endloop
        set s = s + 1
    endloop
    call SetHeroInt(h, GetHeroInt(h, false) + 400, true)
    call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
    call SetUnitInvulnerable(h, true)
    call UnitRemoveAbility(h, 'Aatk')
    set bj_lastCreatedUnit = h
    set b = null
    set h = null
    return bj_lastCreatedUnit
endfunction

function TestBossTick takes nothing returns nothing
    local integer t
    local unit b = gBoss[0]
    local integer d = LaneArm(0)
    local real v
    set gTestBossT = gTestBossT + 1
    set t = gTestBossT
    if t == 1 then
        call PanCameraToTimed(GetUnitX(b), GetUnitY(b), 0.0)
        call IssuePointOrder(b, "move", GetUnitX(b), GetUnitY(b) - 1400.0 * gDirSign0)
        set gTestBossX = GetUnitX(b)
        set gTestBossY = GetUnitY(b)
    elseif t == 2 then
        set gTestBossX = GetUnitX(b)
        set gTestBossY = GetUnitY(b)
    elseif t == 3 then
        set v = SquareRoot((GetUnitX(b) - gTestBossX) * (GetUnitX(b) - gTestBossX) + (GetUnitY(b) - gTestBossY) * (GetUnitY(b) - gTestBossY))
        call TestCheck(v >= 450.0, "the boss runs " + I2S(R2I(v)) + " a second (speed " + I2S(R2I(GetUnitMoveSpeed(b))) + ", it was 240)")
        set gTestBossHero = TestStunner(1, 300.0)
    elseif t == 5 then
        set gTestBossLife = GetWidgetLife(b)
        set gTestStunRemoved = 0
        call TestLog("boss: Storm Bolt order " + TestB2S(IssueTargetOrder(gTestBossHero, "thunderbolt", b)))
    elseif t == 7 then
        call TestCheck(gTestStunRemoved > 0 and not IsUnitType(b, UNIT_TYPE_STUNNED) and GetWidgetLife(b) < gTestBossLife, "Storm Bolt: the boss takes the damage (" + I2S(R2I(gTestBossLife - GetWidgetLife(b))) + ") and shakes off the stun at once")
        call RemoveUnit(gTestBossHero)
        set gTestBossHero = TestStunner(2, 300.0)
        set gTestBossLife = GetWidgetLife(b)
        set gTestStunRemoved = 0
        call TestLog("boss: War Stomp order " + TestB2S(IssueImmediateOrder(gTestBossHero, "stomp")))
    elseif t == 9 then
        call TestCheck(gTestStunRemoved > 0 and not IsUnitType(b, UNIT_TYPE_STUNNED) and GetWidgetLife(b) < gTestBossLife, "War Stomp: damage (" + I2S(R2I(gTestBossLife - GetWidgetLife(b))) + "), no stun on the boss")
        call RemoveUnit(gTestBossHero)
        set gTestBossHero = TestStunner(9, 400.0)
        set gTestBossLife = GetWidgetLife(b)
        set gTestStunRemoved = 0
        call TestLog("boss: Impale order " + TestB2S(IssuePointOrder(gTestBossHero, "impale", GetUnitX(b), GetUnitY(b))))
    elseif t == 12 then
        call TestCheck(not IsUnitType(b, UNIT_TYPE_STUNNED) and GetWidgetLife(b) < gTestBossLife - 500.0, "Impale: its damage lands (" + I2S(R2I(gTestBossLife - GetWidgetLife(b))) + "), the boss is not left stunned (" + I2S(gTestStunRemoved) + " removed)")
        call RemoveUnit(gTestBossHero)
        set gTestBossHero = TestStunner(4, 300.0)
        set gTestBossLife = GetWidgetLife(b)
        set gTestStunRemoved = 0
        call TestLog("boss: Frost Bolt order " + TestB2S(IssueTargetOrder(gTestBossHero, "thunderbolt", b)))
    elseif t == 14 then
        call TestCheck(gTestStunRemoved > 0 and not IsUnitType(b, UNIT_TYPE_STUNNED) and GetWidgetLife(b) < gTestBossLife, "Frost Bolt: damage (" + I2S(R2I(gTestBossLife - GetWidgetLife(b))) + "), no stun")
        call RemoveUnit(gTestBossHero)
        // a target it may really hit: its spells take no invulnerable one
        set gTestBossHero = TestStunner(1, 300.0)
        call SetUnitInvulnerable(gTestBossHero, false)
        call FinalBits(gTestBossHero, 0, gFinalHpBits, 500)
        call SetWidgetLife(gTestBossHero, GetUnitState(gTestBossHero, UNIT_STATE_MAX_LIFE))
        set gTestBossLife = GetWidgetLife(gTestBossHero)
        call TestFlush()
    elseif t == 40 then
        // the boss has had a target beside it for half a minute
        call TestLog("the target took " + I2S(R2I(gTestBossLife - GetWidgetLife(gTestBossHero))) + " in 26 s")
        call TestCheck(LoadInteger(gTestHT, GetHandleId(b), gBossSpell[d * 2]) >= 2, "the boss casts its first spell: " + I2S(LoadInteger(gTestHT, GetHandleId(b), gBossSpell[d * 2])) + " times")
        call TestCheck(LoadInteger(gTestHT, GetHandleId(b), gBossSpell[d * 2 + 1]) >= 1, "the boss casts its second spell: " + I2S(LoadInteger(gTestHT, GetHandleId(b), gBossSpell[d * 2 + 1])) + " times")
        call TestCheck(TestCountEnemy(gBossSummon[d]) > 0, "the boss summons: " + I2S(TestCountEnemy(gBossSummon[d])) + " adds")
        call TestCheck(GetUnitState(TestFirstEnemy(gBossSummon[d]), UNIT_STATE_MAX_LIFE) > 2000.0, "its adds are as strong as the wave: " + I2S(R2I(GetUnitState(TestFirstEnemy(gBossSummon[d]), UNIT_STATE_MAX_LIFE))) + " HP")
        // the real kill: a player's champion, below 192 s of game clock in the stun throttle's old way: only the boss's own reward
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestBountyCalls = 0
        call UnitDamageTarget(gHero[0], b, 100000000.0, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
        call TestCheck(gBoss[0] == null and gTestBountyCalls == 0, "a boss is no wave monster: killed by a champion, no monster bounty")
        call TestLog("boss killed: gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + " (250 for the boss, its own bounty)")
        call RemoveUnit(gTestBossHero)
        call TestFlush()
        set gTestHold = false
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set b = null
endfunction

// ---- Castle Regeneration: the name says what was bought; buying really heals.
function TestCastleRegen takes nothing returns nothing
    local integer s = gTestRegenKind
    set gTestRegenT = gTestRegenT + 1
    if gTestRegenT <= 3 then
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 5)
        call TestCheck(GetObjectName(gStatItem[s * gKindStride + gCastleNext[s]]) == "Castle Regeneration +" + I2S(gCastleNext[s] * 10) + " HP/s", "the shop's name after " + I2S(gCastleNext[s]) + " buys: " + GetObjectName(gStatItem[s * gKindStride + gCastleNext[s]]))
        call TestLog("regeneration buy order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gCastle, gStatItem[s * gKindStride + gCastleNext[s]])))
    elseif gTestRegenT == 5 then
        call TestCheck(gCastleNext[s] == 3, "3 buys counted: " + I2S(gCastleNext[s]))
        call TestCheck(GetObjectName(gStatItem[s * gKindStride + gCastleNext[s]]) == "Castle Regeneration +30 HP/s", "the name now: " + GetObjectName(gStatItem[s * gKindStride + gCastleNext[s]]))
        call SetWidgetLife(gCastle, 1000.0)
        set gTestRegenLife = GetWidgetLife(gCastle)
    elseif gTestRegenT == 15 then
        set gTestRegenLife = GetWidgetLife(gCastle) - gTestRegenLife
        call TestCheck(gTestRegenLife > 250.0 and gTestRegenLife < 450.0, "the castle really heals: " + I2S(R2I(gTestRegenLife)) + " HP in 10 s (bought +30 HP/s, its own +5 HP/s)")
        call TestFlush()
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

// Light Frenzy resets its target's cooldowns: Fan of Light on cooldown, Frenzy on him, and Fan of Light goes again at once.
function TestPaladin takes nothing returns nothing
    local unit h = gTestH[6]
    set gTestPalT = gTestPalT + 1
    if gTestPalT == 1 then
        call SetUnitInvulnerable(h, false)
        call UnitResetCooldown(h)
        call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
        call IssueImmediateOrder(h, "fanofknives")
    elseif gTestPalT == 2 then
        set gTestPalCount = TestSpellCount(h, 'A00A')
        call TestLog("Light Frenzy on himself: order " + TestB2S(IssueTargetOrder(h, "cripple", h)))
    elseif gTestPalT == 4 then
        call TestCheck(TestSpellCount(h, 'A010') > 0, "Light Frenzy cast on the Paladin")
        call IssueImmediateOrder(h, "fanofknives")
    elseif gTestPalT == 6 then
        call TestCheck(TestSpellCount(h, 'A00A') > gTestPalCount, "Light Frenzy reset his cooldown: Fan of Light again within 4 s of its 5 s cooldown")
        call SetUnitInvulnerable(h, true)
        set gTestPalDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set h = null
endfunction

// Frost Arrows hang on the attack: a Lich of her own, with hers, and a foe away from the others. The slow lasts 1.5 s: watched every second.
function TestLichArrows takes nothing returns nothing
    local integer s = 0
    local integer k
    set gTestLichT = gTestLichT + 1
    if gTestLichT == 1 then
        set gTestLichHero = CreateUnit(Player(4), gHeroPool[5], gHeroX[4], gHeroY[4] + 400.0, 0.0)
        call SetHeroLevel(gTestLichHero, 20, false)
        loop
            exitwhen s >= gSkillsPerHero
            set k = 0
            loop
                exitwhen k >= 4
                call SelectHeroSkill(gTestLichHero, gHeroSkill[5 * gSkillsPerHero + s])
                set k = k + 1
            endloop
            set s = s + 1
        endloop
        call SetHeroInt(gTestLichHero, GetHeroInt(gTestLichHero, false) + 400, true)
        call SetUnitState(gTestLichHero, UNIT_STATE_MANA, GetUnitState(gTestLichHero, UNIT_STATE_MAX_MANA))
        call SetUnitInvulnerable(gTestLichHero, true)
        set gTestLichFoe = TestFoe(GetUnitX(gTestLichHero) + 300.0, GetUnitY(gTestLichHero))
        call TestLog("Frost Arrows: order " + TestB2S(IssueTargetOrder(gTestLichHero, "coldarrowstarg", gTestLichFoe)))
        // the Demon Hunter's Roar on one as the tavern sells him: with his attack, not invulnerable
        set gTestDhFresh = CreateUnit(Player(4), gHeroPool[10], gHeroX[5], gHeroY[5] + 400.0, 0.0)
        call SetUnitState(gTestDhFresh, UNIT_STATE_MANA, GetUnitState(gTestDhFresh, UNIT_STATE_MAX_MANA))
        call TestLog("Roar: order " + TestB2S(IssueImmediateOrder(gTestDhFresh, "roar")))
    elseif gTestLichT >= 2 and gTestLichT <= 6 then
        if GetUnitAbilityLevel(gTestLichFoe, 'BHca') > 0 or GetUnitAbilityLevel(gTestLichFoe, 'Bcsd') > 0 then
            set gTestLichSeen = true
        endif
        if GetUnitAbilityLevel(gTestDhFresh, 'Broa') > 0 then
            set gTestDhRoar = true
        endif
    elseif gTestLichT == 7 then
        call TestCheck(gTestLichSeen, "Frost Arrows: the Lich's attack puts its slow on the enemy")
        call TestCheck(gTestDhRoar, "Roar: the buff is on the Demon Hunter")
        call RemoveUnit(gTestDhFresh)
        call RemoveUnit(gTestLichHero)
        call RemoveUnit(gTestLichFoe)
        set gTestLichDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

// ---- The champions' own triggers at level 20 and the rest of the kits, after every cast: what the casts above could not show alone.
function TestGlueChecks takes nothing returns nothing
    local unit mk = gTestH[1]
    local unit tc = gTestH[2]
    local unit bm = gTestH[7]
    call TestCheck(TestSpellCount(mk, 'A04P') > 0, "Mountain King, level 20: Thunder Clap strikes twice (" + I2S(TestSpellCount(mk, 'AHtc')) + " + " + I2S(TestSpellCount(mk, 'A04P')) + ")")
    call TestCheck(TestSpellCount(mk, 'A02V') > 0, "Mountain King, level 20: Storm Bolt strikes twice (" + I2S(TestSpellCount(mk, 'AHtb')) + " + " + I2S(TestSpellCount(mk, 'A02V')) + ")")
    call TestCheck(GetUnitAbilityLevel(mk, 'A04P') == 0 and GetUnitAbilityLevel(mk, 'A02V') == 0, "Mountain King: the second strikes' abilities are gone again")
    call TestCheck(TestSpellCount(tc, 'A01O') > 0, "Tauren, level 20 with Roar on: War Stomp strikes twice")
    call TestCheck(TestSpellCount(tc, 'A04Q') > 0, "Tauren, level 20 with Roar on: Shockwave strikes twice")
    call TestCheck(GetUnitAbilityLevel(tc, 'ACro') == 0 and GetUnitAbilityLevel(tc, 'AOre') > 0 and GetUnitAbilityLevel(tc, 'A03Q') > 0, "Tauren, level 20: the old Roar is replaced, Reincarnation is on")
    call TestCheck(GetUnitAbilityLevel(bm, 'A048') > 0 and GetUnitAbilityLevel(bm, 'A033') == 0 and GetUnitAbilityLevel(bm, 'A046') == 0 and GetUnitAbilityLevel(bm, 'A047') == 0, "Blademaster: War Drums level 4 has swapped in the real aura")
    set mk = null
    set tc = null
    set bm = null
endfunction

// ---- All 12 through the real tavern sale, one after the other.
// One sale at a time, with room around it: the shop keeps its last buyer for a moment, and that one was removed.
// The tooltip tour (CD_TEST_ONLY=tour): a row of the build's list per picture. Only a champion on the card, then one line that asks the runner to look.
function TestTourTick takes nothing returns nothing
    local integer n = gTestTourN
    local integer s
    local integer r
    local integer i
    set gTestTourStep = gTestTourStep + 1
    if n >= gTourN then
        call TestLog("SELFTEST DONE")
        call TestFlush()
        call PauseTimer(GetExpiredTimer())
        return
    endif
    if gTestTourStep == 1 then
        call ForceUICancel()
        call ClearTextMessages()
        if gTestTourHero != null then
            call RemoveUnit(gTestTourHero)
            set gTestTourHero = null
        endif
        if gTourKind[n] == 1 then
            call SelectUnitForPlayerSingle(gTavern[0], Player(0))
        elseif gTourKind[n] == 2 then
            call SelectUnitForPlayerSingle(gArmoryShop, Player(0))
        elseif gTourKind[n] == 4 then
            call SelectUnitForPlayerSingle(gLaneMarker[0], Player(0))
        else
            set gTestTourHero = CreateUnit(Player(0), gHeroPool[gTourHero[n]], gHallX, gHallY - 200.0, 270.0)
            call SetUnitInvulnerable(gTestTourHero, true)
            // "keep": the order a game has: the skills first, the level 20 ability last, points left
            if gTourOrder[n] == "keep" then
                call SetHeroLevel(gTestTourHero, gTourLevel[n] - 1, false)
            else
                call SetHeroLevel(gTestTourHero, gTourLevel[n], false)
            endif
            set s = 0
            loop
                exitwhen s >= gSkillsPerHero
                set r = 0
                loop
                    exitwhen r >= gTourRank[n * 5 + s]
                    call SelectHeroSkill(gTestTourHero, gHeroSkill[gTourHero[n] * gSkillsPerHero + s])
                    set r = r + 1
                endloop
                set s = s + 1
            endloop
            if gTourOrder[n] == "keep" then
                call SetHeroLevel(gTestTourHero, gTourLevel[n], false)
            endif
            if gTourItem[n] != 0 then
                call UnitAddItemById(gTestTourHero, gTourItem[n])
            endif
            // the learn card needs a point left, the plain card none: with one the Learn button pushes the buttons around
            if gTourKind[n] != 3 and gTourOrder[n] != "keep" then
                call UnitModifySkillPoints(gTestTourHero, -GetHeroSkillPoints(gTestTourHero))
            endif
            call SetUnitState(gTestTourHero, UNIT_STATE_MANA, GetUnitState(gTestTourHero, UNIT_STATE_MAX_MANA))
            call SelectUnitForPlayerSingle(gTestTourHero, Player(0))
        endif
    elseif gTestTourStep == 2 then
        if gTourKind[n] == 3 then
            call ForceUIKey("O")
        elseif gTourOrder[n] != "" and gTourOrder[n] != "keep" then
            call TestLog("tour " + gTourName[n] + ": order " + gTourOrder[n] + " " + TestB2S(IssueImmediateOrder(gTestTourHero, gTourOrder[n])))
        endif
    elseif gTestTourStep == 3 then
        if gTestTourHero != null then
            set s = 0
            set r = gTourHero[n] * gSkillsPerHero
            call TestLog("tour " + gTourName[n] + ": " + GetUnitName(gTestTourHero) + " level " + I2S(GetHeroLevel(gTestTourHero)) + ", points " + I2S(GetHeroSkillPoints(gTestTourHero)) + ", ranks " + I2S(GetUnitAbilityLevel(gTestTourHero, gHeroSkill[r])) + " " + I2S(GetUnitAbilityLevel(gTestTourHero, gHeroSkill[r + 1])) + " " + I2S(GetUnitAbilityLevel(gTestTourHero, gHeroSkill[r + 2])) + " " + I2S(GetUnitAbilityLevel(gTestTourHero, gHeroSkill[r + 3])) + " " + I2S(GetUnitAbilityLevel(gTestTourHero, gHeroSkill[r + 4])))
        endif
        call TestLog("HOVER " + gTourName[n] + " " + I2S(gTourX[n]) + " " + I2S(gTourY[n]))
        call TestFlush()
    elseif gTestTourStep >= 6 then
        set gTestTourStep = 0
        set gTestTourN = n + 1
    endif
endfunction

// A split champion: control, purchases and what comes back. Player 1's own champion, because only a real player buys through the real shop path.
function TestSplit takes nothing returns nothing
    local integer t
    local integer n
    local group g
    local unit u
    set gTestSplitT = gTestSplitT + 1
    set t = gTestSplitT
    if t == 1 then
        call RemoveUnit(gHero[0])
        set gHero[0] = CreateUnit(Player(0), gHeroPool[7], gHeroX[0], gHeroY[0], 0.0)
        call SetHeroLevel(gHero[0], 20, false)
        call SetHeroInt(gHero[0], GetHeroInt(gHero[0], false) + 400, true)
        call SetUnitState(gHero[0], UNIT_STATE_MANA, GetUnitState(gHero[0], UNIT_STATE_MAX_MANA))
        call SelectUnitForPlayerSingle(gHero[0], Player(0))
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 5000)
        call TestLog("split: order accepted " + TestB2S(IssueImmediateOrder(gHero[0], "elementalfury")))
    elseif t == 3 then
        set n = TestOwnedOfTypeP0('n00D')
        call TestCheck(IsUnitHidden(gHero[0]) and n == 3, "Partition: the Blademaster is gone, 3 warriors in his place (" + I2S(n) + ")")
        // the reference's split is real: can a warrior be selected, and what does a shop do for a hidden champion?
        set gTestStatBefore = gStatNext[0]
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("split: circle buy order accepted " + TestB2S(IssueImmediateOrderById(gLaneMarker[0], gStatItem[KindNext(0, 0)])))
    elseif t == 5 then
        call TestLog("split: after the buy, price step " + I2S(gTestStatBefore) + " -> " + I2S(gStatNext[0]) + ", gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ", hero alive " + TestB2S(GetWidgetLife(gHero[0]) > 0.405) + ", hidden " + TestB2S(IsUnitHidden(gHero[0])))
        // all three die: what becomes of him?
        set gTestDeathsSplit = gDeaths[0]
        set g = CreateGroup()
        call GroupEnumUnitsOfPlayer(g, Player(0), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            if GetUnitTypeId(u) == 'n00D' then
                call KillUnit(u)
            endif
        endloop
        call DestroyGroup(g)
        set g = null
    elseif t == 8 then
        call TestLog("split: all 3 dead, hero hidden " + TestB2S(IsUnitHidden(gHero[0])) + ", alive " + TestB2S(GetWidgetLife(gHero[0]) > 0.405) + ", deaths counted " + I2S(gDeaths[0] - gTestDeathsSplit) + ", revive running " + TestB2S(TimerGetRemaining(gReviveTimer[0]) > 0.0))
        call TestCheck(not IsUnitHidden(gHero[0]) or GetWidgetLife(gHero[0]) <= 0.405, "Partition over: the champion is not left hidden and alive")
        call TestLog("split: stat bonuses on him " + I2S(gStatApplied[0]) + " of " + I2S(gStatNext[0]))
        call TestFlush()
        // the Beastmaster's Terror Wolf: its second listed form does not exist in the reference either
        call SetUnitInvulnerable(gTestH[8], true)
        call SetUnitState(gTestH[8], UNIT_STATE_MANA, GetUnitState(gTestH[8], UNIT_STATE_MAX_MANA))
        call UnitResetCooldown(gTestH[8])
        call TestLog("Terror Wolf: order accepted " + TestB2S(IssueImmediateOrder(gTestH[8], "elementalfury")))
    elseif t == 11 then
        call TestCheck(TestOwnedOfType(8, 'n00M') == 1 and IsUnitHidden(gTestH[8]), "Terror Wolf: the Beastmaster is gone, one wolf in his place (" + I2S(TestOwnedOfType(8, 'n00M')) + ")")
        call TestFlush()
        set gTestSplitDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

// ---- A wave's ranks, on all 12 lanes and all three stages, at wave 23, 44 and 60: where the engine really put every unit, and where they go from there.
// Level 5 marches through Level 4's lane and opens only when Level 4's Nexus has fallen: it has its own passes in that state. All 12 at stage 0 is a labelled stress pass.
function TestFormSpawnOne takes nothing returns nothing
    call SpawnWave(gTestC)
endfunction

function TestFormMeasure takes string label, boolean moved returns nothing
    local integer L = gTestFormFirst
    local integer i
    local unit u
    local real p
    local real q
    local real ax
    local real ay
    local real meleeMin
    local real meleeSum
    local real rangedMax
    local real rangedSum
    local integer melee
    local integer ranged
    local integer out
    local integer wall
    local real sideMax
    local integer stuck
    loop
        exitwhen L > gTestFormLast
        set stuck = 0
        set meleeMin = 1000000.0
        set rangedMax = -1000000.0
        set meleeSum = 0.0
        set rangedSum = 0.0
        set melee = 0
        set ranged = 0
        set out = 0
        set wall = 0
        set sideMax = 0.0
        set ax = gTestFormAX[L]
        set ay = gTestFormAY[L]
        set i = 0
        loop
            exitwhen i >= gTestFormN
            if gTestFormLane[i] == L and GetWidgetLife(gTestFormU[i]) > 0.405 then
                set u = gTestFormU[i]
                set p = (GetUnitX(u) - ax) * gTestFormFX[L] + (GetUnitY(u) - ay) * gTestFormFY[L]
                set q = RAbsBJ((GetUnitX(u) - ax) * gTestFormFY[L] - (GetUnitY(u) - ay) * gTestFormFX[L])
                if q > sideMax then
                    set sideMax = q
                endif
                if q > 640.0 then
                    set out = out + 1
                endif
                if IsTerrainPathable(GetUnitX(u), GetUnitY(u), PATHING_TYPE_WALKABILITY) and not IsUnitType(u, UNIT_TYPE_FLYING) then
                    set wall = wall + 1
                endif
                if moved then
                    set gTestFormStill[i] = (GetUnitX(u) - gTestFormStartX[i]) * (GetUnitX(u) - gTestFormStartX[i]) + (GetUnitY(u) - gTestFormStartY[i]) * (GetUnitY(u) - gTestFormStartY[i]) < 10000.0
                    if gTestFormStill[i] then
                        set stuck = stuck + 1
                        call TestLog(label + " lane " + I2S(L) + ": stands still: " + GetUnitName(u) + ", role " + I2S(gTestFormRole[i]) + " at " + I2S(R2I(GetUnitX(u))) + ", " + I2S(R2I(GetUnitY(u))) + ", " + I2S(R2I(p)) + " forward, order " + OrderId2String(GetUnitCurrentOrder(u)))
                    endif
                    set gTestFormStartX[i] = GetUnitX(u)
                    set gTestFormStartY[i] = GetUnitY(u)
                else
                    set gTestFormStartX[i] = GetUnitX(u)
                    set gTestFormStartY[i] = GetUnitY(u)
                endif
                if gTestFormRole[i] == 1 then
                    set ranged = ranged + 1
                    set rangedSum = rangedSum + p
                    if p > rangedMax then
                        set rangedMax = p
                    endif
                else
                    set melee = melee + 1
                    set meleeSum = meleeSum + p
                    if p < meleeMin then
                        set meleeMin = p
                    endif
                endif
            endif
            set i = i + 1
        endloop
        if not moved then
            call TestCheck(melee > 0 and ranged > 0 and meleeMin > rangedMax and out == 0 and wall == 0, label + " lane " + I2S(L) + ": " + I2S(melee) + " melee from " + I2S(R2I(meleeMin)) + ", " + I2S(ranged) + " ranged up to " + I2S(R2I(rangedMax)) + " on the way forward, furthest off the middle " + I2S(R2I(sideMax)) + ", off the lane " + I2S(out) + ", in a wall " + I2S(wall))
            set gTestFormStart[L] = (meleeSum + rangedSum) / I2R(melee + ranged)
        else
            call TestCheck(melee > 0 and ranged > 0 and (meleeSum + rangedSum) / I2R(melee + ranged) > gTestFormStart[L] + 200.0 and wall == 0, label + " lane " + I2S(L) + ": the army walks on: " + I2S(R2I((meleeSum + rangedSum) / I2R(melee + ranged) - gTestFormStart[L])) + " forward on the first stretch, stood still " + I2S(stuck) + ", in a wall " + I2S(wall) + " (melee ahead of ranged by " + I2S(R2I(meleeSum / I2R(melee) - rangedSum / I2R(ranged))) + ": fliers may pass, the ranks are for the start)")
        endif
        set L = L + 1
    endloop
    call TestFlush()
endfunction

// Who stood still after 7 s has had 7 s more: a queue has moved on, an obstruction has not.
function TestFormLater takes string label returns nothing
    local integer i = 0
    local integer waited = 0
    local integer still = 0
    local unit u
    loop
        exitwhen i >= gTestFormN
        set u = gTestFormU[i]
        if gTestFormStill[i] and GetWidgetLife(u) > 0.405 then
            set waited = waited + 1
            if (GetUnitX(u) - gTestFormStartX[i]) * (GetUnitX(u) - gTestFormStartX[i]) + (GetUnitY(u) - gTestFormStartY[i]) * (GetUnitY(u) - gTestFormStartY[i]) < 10000.0 then
                set still = still + 1
                call TestLog(label + " lane " + I2S(gTestFormLane[i]) + ": still there: " + GetUnitName(u) + " at " + I2S(R2I(GetUnitX(u))) + ", " + I2S(R2I(GetUnitY(u))) + ", order " + OrderId2String(GetUnitCurrentOrder(u)))
            endif
        endif
        set i = i + 1
    endloop
    call TestCheck(still == 0, label + ": of " + I2S(waited) + " who stood still after 7 s, " + I2S(still) + " still stand after 14 s")
    call TestFlush()
    set u = null
endfunction

function TestFormClear takes nothing returns nothing
    local integer i = 0
    loop
        exitwhen i >= gTestFormN
        call GroupRemoveUnit(gWaveUnits, gTestFormU[i])
        call RemoveUnit(gTestFormU[i])
        set i = i + 1
    endloop
    set gTestFormN = 0
endfunction

function TestFormSpawnAll takes integer wave, integer first, integer last returns nothing
    local integer L = first
    set gTestFormN = 0
    set gTestFormFirst = first
    set gTestFormLast = last
    loop
        exitwhen L > last
        set gLaneWave[L] = wave
        call WaveAnchor(L)
        set gTestFormAX[L] = gFormX
        set gTestFormAY[L] = gFormY
        set gTestFormFX[L] = gFormFX
        set gTestFormFY[L] = gFormFY
        set gTestC = L
        call ExecuteFunc("TestFormSpawnOne")
        set L = L + 1
    endloop
endfunction

function TestFormEmptyMap takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    local integer o = 0
    loop
        exitwhen o > 11
        call GroupEnumUnitsOfPlayer(g, Player(o), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            if not IsUnitType(u, UNIT_TYPE_STRUCTURE) and u != gLaneMarker[o] then
                call RemoveUnit(u)
            endif
        endloop
        set o = o + 1
    endloop
    call DestroyGroup(g)
    set g = null
    call GroupClear(gWaveUnits)
    set gHero[0] = null
endfunction

// A lane in a stage: 0 tower and Nexus stand, 1 the tower is gone, 2 both are.
function TestFormStage takes integer L, integer stage returns nothing
    local integer d = LaneArm(L)
    if stage > 0 then
        call RemoveUnit(gTower[L])
        set gTower[L] = null
    elseif GetWidgetLife(gTower[L]) <= 0.405 then
        set gTower[L] = CreateUnit(gInvader[d], gTurretType[d], gTowerX[L], gTowerY[L], 0.0)
    endif
    if stage > 1 then
        call RemoveUnit(gNexus[L])
        set gNexus[L] = null
    elseif GetWidgetLife(gNexus[L]) <= 0.405 then
        set gNexus[L] = CreateUnit(gInvader[d], gBaseType[d], gNexusX[L], gNexusY[L], 0.0)
    endif
    if L < 8 then
        if stage > 1 then
            set gLaneState[L] = 1
        else
            set gLaneState[L] = 0
        endif
    elseif stage > 1 then
        set gGateState[L] = 1
    else
        set gGateState[L] = 0
    endif
endfunction

function TestFormStages takes integer first, integer last, integer stage returns nothing
    local integer L = first
    loop
        exitwhen L > last
        call TestFormStage(L, stage)
        set L = L + 1
    endloop
endfunction

// The passes: lanes 0 to 10 through their stages, Level 5 behind a fallen Level 4, then all 12 at once.
function TestFormPass takes integer p, integer step returns nothing
    local integer wave = 60
    local integer first = 0
    local integer last = 11
    local string label
    if p == 0 then
        set wave = 23
        set last = 10
        set label = "wave 23, stage 0"
        if step == 0 then
            call TestFormStages(0, 11, 0)
        endif
    elseif p == 1 then
        set wave = 44
        set last = 10
        set label = "wave 44, stage 1"
        if step == 0 then
            call TestFormStages(0, 10, 1)
        endif
    elseif p == 2 then
        set label = "wave 60, stage 2, Level 5 at stage 0"
        if step == 0 then
            call TestFormStages(0, 10, 2)
        endif
    elseif p == 3 then
        set wave = 44
        set first = 10
        set label = "wave 44, Level 4 in its boss stage, Level 5 at stage 1"
        if step == 0 then
            call TestFormStage(11, 1)
        endif
    elseif p == 4 then
        set first = 10
        set label = "wave 60, Level 4 and 5 in their boss stage"
        if step == 0 then
            call TestFormStage(11, 2)
        endif
    else
        set label = "stress, not a real state: all 12 at stage 0, Level 5 behind a standing Level 4"
        if step == 0 then
            call TestFormStages(0, 11, 0)
        endif
    endif
    if step == 1 then
        call TestFormSpawnAll(wave, first, last)
        call TestFormMeasure(label, false)
        if p == 0 then
            call PanCameraToTimed(gTowerSpawnX[4], gTowerSpawnY[4], 0.0)
            call TestLog("VIDEO formation 9")
            call TestFlush()
        endif
    elseif step == 8 then
        call TestFormMeasure(label + ", after 7 s", true)
    elseif step == 15 then
        call TestFormLater(label)
        call TestFormClear()
    endif
endfunction

function TestFormTick takes nothing returns nothing
    local integer t
    local integer L = 0
    local integer i
    set gTestFormT = gTestFormT + 1
    set t = gTestFormT
    if t == 1 then
        call TestFormEmptyMap()
        // every gate open, as a game has them late on
        loop
            exitwhen L > 11
            call GateSet(L, true)
            set L = L + 1
        endloop
    elseif t <= 97 then
        call TestFormPass((t - 2) / 16, ModuloInteger(t - 2, 16))
    elseif t == 98 then
        // a wave against a pack of summons standing where the boss stage spawns: nobody ends up in a wall or on another lane
        call TestFormStages(0, 11, 2)
        set i = 0
        loop
            exitwhen i >= 12
            call PauseUnit(CreateUnit(Player(1), 'n005', gNexusSpawnX[3] + 100.0 * Cos(i * 0.5236), gNexusSpawnY[3] + 100.0 * Sin(i * 0.5236), 0.0), true)
            set i = i + 1
        endloop
        call TestFormSpawnAll(60, 0, 11)
        call TestFormMeasure("wave 60, summons in the way on lane 3", false)
    elseif t == 99 then
        call TestFormClear()
        set gTestFormDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

// ---- The Tower Warden: a real tower death on each faction and a gate: one boss on the ruins with its gear, the Nexus and its boss apart.
function TestWardenCount takes integer L returns integer
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    call GroupEnumUnitsOfPlayer(g, gInvader[LaneArm(L)], null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetUnitTypeId(u) == gBossType[LaneArm(L) * 3] and GetWidgetLife(u) > 0.405 then
            set n = n + 1
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    return n
endfunction

// Its three items, exactly those, and bound.
function TestGearCount takes unit b, integer L, integer tier returns integer
    local integer s = 0
    local integer n = 0
    local integer id
    local integer heart = gGearHeart[tier]
    local item it
    if L >= 8 then
        set heart = gGearHeart[(L - 7) * 2 + tier]
    endif
    loop
        exitwhen s >= 6
        set it = UnitItemInSlot(b, s)
        if it != null then
            set id = GetItemTypeId(it)
            if (id == heart or id == gGearHands[tier] or id == gGearPlate[tier]) and not IsItemPawnable(it) and not IsItemPowerup(it) then
                set n = n + 1
            else
                set n = n - 10
            endif
        endif
        set s = s + 1
    endloop
    set it = null
    return n
endfunction

function TestWaveClearEnum takes nothing returns nothing
    call RemoveUnit(GetEnumUnit())
endfunction

function TestWaveClear takes nothing returns nothing
    call ForGroup(gWaveUnits, function TestWaveClearEnum)
    call GroupClear(gWaveUnits)
endfunction

function TestItemNear takes nothing returns nothing
    set gTestWardenItems = gTestWardenItems + 1
endfunction

function TestWardenTick takes nothing returns nothing
    local integer s
    local integer r
    local integer L
    local integer d
    local integer li
    local real n
    local real expect
    local real dx
    local real dy
    local rect re
    set gTestWardenStep = gTestWardenStep + 1
    set r = (gTestWardenStep - 1) / 11
    set s = ModuloInteger(gTestWardenStep - 1, 11)
    if r >= 5 then
        call TestFormEmptyMap()
        set gTestWardenDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
        return
    endif
    set L = r * 2
    if r == 4 then
        set L = 8
    endif
    set d = LaneArm(L)
    set li = 0
    if L >= 8 then
        set li = L - 7
    endif
    if s == 0 then
        call LanesStop()
        call TestFormEmptyMap()
        set gLaneWave[L] = 10
        call GateSet(L, true)
        call TestFormStage(L, 0)
        set gProtector[L] = null
    elseif s == 1 then
        set gTestWardenAt = TimerGetElapsed(gTestPremClock)
        call KillUnit(gTower[L])
    elseif s == 2 then
        call TestWaveClear()
        set dx = GetUnitX(gProtector[L]) - gTowerX[L]
        set dy = GetUnitY(gProtector[L]) - gTowerY[L]
        set n = I2R(gLaneWave[L] - 1)
        set expect = gBossBaseHp[li * 2] * (1.0 + gBossHpGrowth * n * n)
        call TestLog("Warden lane " + I2S(L) + ": " + GetUnitName(gProtector[L]) + " " + I2S(GetUnitTypeId(gProtector[L])) + " at " + I2S(R2I(GetUnitX(gProtector[L]))) + ", " + I2S(R2I(GetUnitY(gProtector[L]))) + ", " + I2S(R2I(SquareRoot(dx * dx + dy * dy))) + " from the ruins, HP " + I2S(R2I(GetUnitState(gProtector[L], UNIT_STATE_MAX_LIFE))) + " of " + I2S(R2I(expect)) + ", " + R2SW(TimerGetElapsed(gTestPremClock) - gTestWardenAt, 1, 1) + " s after the death")
        call TestCheck(gProtector[L] != null and GetWidgetLife(gProtector[L]) > 0.405 and TestWardenCount(L) == 1 and GetUnitTypeId(gProtector[L]) == gBossType[d * 3] and GetOwningPlayer(gProtector[L]) == gInvader[d], "lane " + I2S(L) + ": the tower's death brings exactly one Tower Warden, alive, its faction's, on the right owner")
        call TestCheck(dx * dx + dy * dy < 40000.0 and not IsTerrainPathable(GetUnitX(gProtector[L]), GetUnitY(gProtector[L]), PATHING_TYPE_WALKABILITY), "lane " + I2S(L) + ": it stands on the ruins of the tower, on floor")
        call TestCheck(RAbsBJ(GetUnitState(gProtector[L], UNIT_STATE_MAX_LIFE) - expect) < 200.0, "lane " + I2S(L) + ": base HP + Heart of Ruin, then the wave's growth (" + I2S(R2I(GetUnitState(gProtector[L], UNIT_STATE_MAX_LIFE))) + ")")
        call TestCheck(TestGearCount(gProtector[L], L, 0) == 3, "lane " + I2S(L) + ": its three items on it, bound (" + I2S(TestGearCount(gProtector[L], L, 0)) + ")")
        // level 1 + wave / 5 + the gate's level
        call TestCheck(GetUnitAbilityLevel(gProtector[L], gBossSpell[d * 2]) == 3 + li, "lane " + I2S(L) + ": its spell at level " + I2S(3 + li) + " for wave 10 (" + I2S(GetUnitAbilityLevel(gProtector[L], gBossSpell[d * 2])) + ")")
        call TestCheck(gBoss[L] == null and GetWidgetLife(gNexus[L]) > 0.405, "lane " + I2S(L) + ": the Nexus stands, no Nexus boss yet")
        // something to fight, near it
        set gTestWardenDummy = CreateUnit(Player(1), 'hfoo', gTowerX[L] + 450.0, gTowerY[L], 0.0)
        call ScaleKeepHp(gTestWardenDummy, 300000, 0)
        call SetWidgetLife(gTestWardenDummy, GetUnitState(gTestWardenDummy, UNIT_STATE_MAX_LIFE))
        set gTestWardenLife = GetWidgetLife(gTestWardenDummy)
    elseif s == 6 then
        call TestCheck(GetWidgetLife(gTestWardenDummy) < gTestWardenLife, "lane " + I2S(L) + ": it goes for an enemy near its ruins, " + I2S(R2I(gTestWardenLife - GetWidgetLife(gTestWardenDummy))) + " damage in 4 s")
        call RemoveUnit(gTestWardenDummy)
        set gTestWardenDummy = null
        if r == 0 then
            set gTestWardenBolt = CreateUnit(Player(1), gHeroPool[1], GetUnitX(gProtector[L]) + 300.0, GetUnitY(gProtector[L]), 180.0)
            call SetUnitInvulnerable(gTestWardenBolt, true)
            call SetHeroLevel(gTestWardenBolt, 1, false)
            call SelectHeroSkill(gTestWardenBolt, 'AHtb')
            call SetUnitState(gTestWardenBolt, UNIT_STATE_MANA, GetUnitState(gTestWardenBolt, UNIT_STATE_MAX_MANA))
            set gTestWardenLife = GetWidgetLife(gProtector[L])
            call TestLog("Warden: Storm Bolt order " + TestB2S(IssueTargetOrder(gTestWardenBolt, "thunderbolt", gProtector[L])))
        endif
    elseif s == 8 then
        if r == 0 then
            call TestCheck(GetWidgetLife(gProtector[L]) < gTestWardenLife - 500.0 and GetUnitAbilityLevel(gProtector[L], 'BPSE') == 0, "a real Storm Bolt hurts the Warden, its stun is gone (" + I2S(R2I(gTestWardenLife - GetWidgetLife(gProtector[L]))) + " lost)")
            call RemoveUnit(gTestWardenBolt)
            set gTestWardenBolt = null
            // the Nexus falls with the Warden alive: two bosses, apart
            call KillUnit(gNexus[L])
        endif
    elseif s == 9 then
        if r == 0 then
            call TestWaveClear()
            call TestCheck(gBoss[L] != null and gBoss[L] != gProtector[L] and GetWidgetLife(gBoss[L]) > 0.405 and GetWidgetLife(gProtector[L]) > 0.405 and GetUnitTypeId(gBoss[L]) == gBossType[d * 3 + 1] and TestGearCount(gBoss[L], L, 1) == 3, "the Nexus falls: its boss rises beside the Warden, with its own gear")
        endif
        call KillUnit(gProtector[L])
    elseif s == 10 then
        set gTestWardenItems = 0
        set re = Rect(gTowerX[L] - 600.0, gTowerY[L] - 600.0, gTowerX[L] + 600.0, gTowerY[L] + 600.0)
        call EnumItemsInRect(re, null, function TestItemNear)
        call RemoveRect(re)
        set re = null
        call TestCheck(gProtector[L] == null and TestWardenCount(L) == 0 and gTestWardenItems == 0, "lane " + I2S(L) + ": the Warden dies, bookkeeping clear, no second one, nothing dropped (" + I2S(gTestWardenItems) + ")")
        if r == 0 then
            call TestCheck(gBoss[L] != null and GetWidgetLife(gBoss[L]) > 0.405, "its death does not touch the Nexus boss")
        endif
        call TestFlush()
    endif
endfunction

// ---- The Premium Armory, in real attacks: what a rank really gives, on a fresh champion with one item and nothing else. Tradeoffs of the engine are logged as they are.
function TestPremAfter takes nothing returns nothing
    set gTestPremHeal = gTestPremHeal + GetWidgetLife(gTestPremHero) - gTestPremLife
    if GetUnitAbilityLevel(gTestPremFoe[0], 'BPSE') > 0 then
        set gTestPremStuns = gTestPremStuns + 1
    endif
    if GetUnitAbilityLevel(gTestPremFoe[0], 'Bpoi') > 0 then
        set gTestPremPoison = gTestPremPoison + 1
    endif
endfunction

function TestPremOnHit takes nothing returns nothing
    local real d = GetEventDamage()
    local real now = TimerGetElapsed(gTestPremClock)
    local integer i = 0
    if d <= 0.0 or GetEventDamageSource() != gTestPremHero then
        return
    endif
    // distinct foes hit by weapon damage in one volley (poison ticks are far smaller than the threshold)
    if gTestPremVolleyMin > 0.0 and d >= gTestPremVolleyMin then
        if now - gTestPremVolleyAt > 0.15 then
            set gTestPremVolleyAt = now
            set gTestPremVolleyId = gTestPremVolleyId + 1
            set gTestPremVolleyN = 0
        endif
        loop
            exitwhen i >= 8
            if gTestPremFoe[i] == GetTriggerUnit() and gTestPremFoeVolley[i] != gTestPremVolleyId then
                set gTestPremFoeVolley[i] = gTestPremVolleyId
                set gTestPremVolleyN = gTestPremVolleyN + 1
                if gTestPremVolleyN > gTestPremVolleyBest then
                    set gTestPremVolleyBest = gTestPremVolleyN
                endif
            endif
            set i = i + 1
        endloop
    endif
    if gTestPremHits == 0 then
        set gTestPremFirst = now
    endif
    set gTestPremLast = now
    if gTestPremHits < 400 then
        set gTestPremD[gTestPremHits] = d
    endif
    set gTestPremHits = gTestPremHits + 1
    set gTestPremDamage = gTestPremDamage + d
    set gTestPremLife = GetWidgetLife(gTestPremHero)
    call TimerStart(gTestPremTimer, 0.0, false, function TestPremAfter)
endfunction

function TestPremOnAttacked takes nothing returns nothing
    if GetTriggerUnit() == gTestPremHero then
        set gTestPremAttacked = gTestPremAttacked + 1
    endif
endfunction

function TestPremOnHurt takes nothing returns nothing
    if GetEventDamage() > 0.0 then
        set gTestPremHurt = gTestPremHurt + 1
    endif
endfunction

// How long one stun lasts: unbroken stretches of the buff, sampled every 0.05 s. A second bash in a stun makes a stretch longer, so the shortest is the one to read.
function TestStunPoll takes nothing returns nothing
    if GetUnitAbilityLevel(gTestPremFoe[0], 'BPSE') > 0 then
        set gTestStunNow = gTestStunNow + 0.05
    elseif gTestStunNow > 0.0 then
        set gTestStunRuns = gTestStunRuns + 1
        if gTestStunNow < gTestStunShortest then
            set gTestStunShortest = gTestStunNow
        endif
        set gTestStunNow = 0.0
    endif
endfunction

function TestPremClear takes nothing returns nothing
    local integer i = 0
    if gTestPremHero != null then
        call RemoveUnit(gTestPremHero)
        set gTestPremHero = null
    endif
    loop
        exitwhen i >= 8
        if gTestPremFoe[i] != null then
            call RemoveUnit(gTestPremFoe[i])
            set gTestPremFoe[i] = null
        endif
        set i = i + 1
    endloop
    if gTestPremTrig != null then
        call DestroyTrigger(gTestPremTrig)
        set gTestPremTrig = null
    endif
    if gTestPremTrig2 != null then
        call DestroyTrigger(gTestPremTrig2)
        set gTestPremTrig2 = null
    endif
endfunction

// A champion with this item rank (0 none); foes = how many stand around him, free unless paused. strength: his primary stat raised, so one hit weighs more than a second of regeneration.
function TestPremStart takes integer hero, integer fam, integer rank, integer foes, boolean paused, integer agi returns nothing
    local integer i = 0
    local unit u
    call TestPremClear()
    set gTestPremHits = 0
    set gTestPremDamage = 0.0
    set gTestPremHeal = 0.0
    set gTestPremStuns = 0
    set gTestPremPoison = 0
    set gTestPremAttacked = 0
    set gTestPremHurt = 0
    set gTestPremVolleyMin = 0.0
    set gTestPremVolleyBest = 0
    set gTestPremHero = CreateUnit(Player(1), gHeroPool[hero], gWpX[2 * 8 + 1], gWpY[2 * 8 + 1], 0.0)
    set gTestPremX = GetUnitX(gTestPremHero)
    set gTestPremY = GetUnitY(gTestPremHero)
    call SetHeroStr(gTestPremHero, 300, true)
    call SetHeroInt(gTestPremHero, 300, true)
    if agi > 0 then
        call SetHeroAgi(gTestPremHero, agi, true)
    endif
    call UnitModifySkillPoints(gTestPremHero, -GetHeroSkillPoints(gTestPremHero))
    if rank > 0 then
        call UnitAddItemById(gTestPremHero, gPremItem[fam * 8 + rank])
    endif
    set gTestPremTrig = CreateTrigger()
    call TriggerAddAction(gTestPremTrig, function TestPremOnHit)
    loop
        exitwhen i >= foes
        set u = CreateUnit(Player(8), 'q00m', gTestPremX + 170.0 * Cos(i * 6.2832 / I2R(foes)), gTestPremY + 170.0 * Sin(i * 6.2832 / I2R(foes)), 0.0)
        call GroupRemoveUnit(gWaveUnits, u)
        call ScaleKeepHp(u, 300000, 0)
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
        if paused then
            call PauseUnit(u, true)
        endif
        call TriggerRegisterUnitEvent(gTestPremTrig, u, EVENT_UNIT_DAMAGED)
        set gTestPremFoe[i] = u
        set i = i + 1
    endloop
    set u = null
endfunction

function TestPremAttack takes nothing returns nothing
    if not gTestPremAttackOff and gTestPremHero != null and gTestPremFoe[0] != null and GetUnitCurrentOrder(gTestPremHero) == 0 then
        call IssueTargetOrder(gTestPremHero, "attack", gTestPremFoe[0])
    endif
endfunction

function TestPremLowest takes nothing returns real
    local integer i = 0
    local real m = 1000000.0
    loop
        exitwhen i >= gTestPremHits or i >= 400
        if gTestPremD[i] < m then
            set m = gTestPremD[i]
        endif
        set i = i + 1
    endloop
    return m
endfunction

function TestPremBelow takes real threshold returns integer
    local integer i = 0
    local integer n = 0
    loop
        exitwhen i >= gTestPremHits or i >= 400
        if gTestPremD[i] < threshold then
            set n = n + 1
        endif
        set i = i + 1
    endloop
    return n
endfunction

function TestPremAbove takes real threshold returns integer
    local integer i = 0
    local integer n = 0
    loop
        exitwhen i >= gTestPremHits or i >= 400
        if gTestPremD[i] >= threshold then
            set n = n + 1
        endif
        set i = i + 1
    endloop
    return n
endfunction

function TestPremReset takes nothing returns nothing
    set gTestPremHits = 0
    set gTestPremDamage = 0.0
endfunction

function TestPremKit takes string name, integer abil, real small, real big returns nothing
    local integer i = 0
    local real plainLow = 1000000.0
    local real plainHigh = 0.0
    loop
        exitwhen i >= gTestPremHits or i >= 400
        if gTestPremD[i] >= small and gTestPremD[i] < big then
            if gTestPremD[i] < plainLow then
                set plainLow = gTestPremD[i]
            endif
            if gTestPremD[i] > plainHigh then
                set plainHigh = gTestPremD[i]
            endif
        endif
        set i = i + 1
    endloop
    call TestCheck(GetUnitAbilityLevel(gTestPremHero, abil) == 4, name + ": the ability really is at rank 4 (" + I2S(GetUnitAbilityLevel(gTestPremHero, abil)) + ")")
    call TestLog("KIT " + name + ": hero level " + I2S(GetHeroLevel(gTestPremHero)) + ", rank " + I2S(GetUnitAbilityLevel(gTestPremHero, abil)) + ", points " + I2S(GetHeroSkillPoints(gTestPremHero)) + ": " + I2S(gTestPremHits) + " events, plain " + I2S(R2I(plainLow)) + " to " + I2S(R2I(plainHigh)) + ", " + I2S(TestPremBelow(small)) + " small, " + I2S(TestPremAbove(big)) + " big")
endfunction

function TestPremCrit takes string name returns nothing
    local real v = TestPremLowest()
    call TestCheck(GetUnitAbilityLevel(gTestPremHero, 'Xhcr') == 4, name + ": the ability really is at rank 4 (" + I2S(GetUnitAbilityLevel(gTestPremHero, 'Xhcr')) + ")")
    call TestLog("KIT " + name + ": hero level " + I2S(GetHeroLevel(gTestPremHero)) + ", rank " + I2S(GetUnitAbilityLevel(gTestPremHero, 'Xhcr')) + ", points " + I2S(GetHeroSkillPoints(gTestPremHero)) + ": " + I2S(gTestPremHits) + " hits, plainest " + I2S(R2I(v)) + ", " + I2S(TestPremAbove(v * 1.7)) + " at 2x or more, " + I2S(TestPremAbove(v * 3.0)) + " at 3x or more, " + I2S(TestPremAbove(v * 4.5)) + " at 5x")
endfunction

function TestPremFang takes string name, integer pct returns nothing
    local real ratio = 0.0
    if gTestPremDamage > 0.0 then
        set ratio = gTestPremHeal / gTestPremDamage
    endif
    call TestCheck(gTestPremHits >= 3 and RAbsBJ(ratio - pct * 0.01) <= pct * 0.0025 + 0.012, name + ", Vampire Fang " + I2S(pct) + "%: " + I2S(gTestPremHits) + " hits, " + I2S(R2I(gTestPremDamage)) + " damage, healed " + I2S(R2I(gTestPremHeal)) + " at the hits: " + R2SW(ratio * 100.0, 1, 1) + "%")
endfunction

function TestPremiumTick2 takes integer t returns nothing
    local real v
    local real dx
    local real dy
    if t == 272 then
        call IssuePointOrder(gTestPremHero, "move", gWpX[2 * 8 + 4], gWpY[2 * 8 + 4])
    elseif t == 275 then
        set dx = GetUnitX(gTestPremHero) - gTestPremX2
        set dy = GetUnitY(gTestPremHero) - gTestPremBase2
        set gTestPremBase = SquareRoot(dx * dx + dy * dy) / 2.0
        call TestPremStart(1, 5, 5, 0, false, 0)
    elseif t == 276 then
        call IssuePointOrder(gTestPremHero, "move", gWpX[2 * 8 + 4], gWpY[2 * 8 + 4])
    elseif t == 279 then
        set dx = GetUnitX(gTestPremHero) - gTestPremX2
        set dy = GetUnitY(gTestPremHero) - gTestPremBase2
        set v = SquareRoot(dx * dx + dy * dy) / 2.0
        call TestCheck(v - gTestPremBase >= 35.0 and v - gTestPremBase <= 65.0, "Winged Boots +50: " + I2S(R2I(gTestPremBase)) + " per second without, " + I2S(R2I(v)) + " with, the engine reads " + I2S(R2I(GetUnitMoveSpeed(gTestPremHero))))
        call TestPremStart(1, 6, 0, 0, false, 0)
        call SetWidgetLife(gTestPremHero, GetUnitState(gTestPremHero, UNIT_STATE_MAX_LIFE) * 0.3)
        set gTestPremLife = GetWidgetLife(gTestPremHero)
    elseif t == 284 then
        set gTestPremBase = (GetWidgetLife(gTestPremHero) - gTestPremLife) / 5.0
        call TestPremStart(1, 6, 5, 0, false, 0)
        call SetWidgetLife(gTestPremHero, GetUnitState(gTestPremHero, UNIT_STATE_MAX_LIFE) * 0.3)
        set gTestPremLife = GetWidgetLife(gTestPremHero)
    elseif t == 289 then
        set v = (GetWidgetLife(gTestPremHero) - gTestPremLife) / 5.0
        call TestCheck(v - gTestPremBase >= 7.5 and v - gTestPremBase <= 12.5, "Troll Heart +10 HP/s: " + R2SW(gTestPremBase, 1, 1) + " per second without, " + R2SW(v, 1, 1) + " with")
        call TestPremStart(1, 7, 0, 0, false, 0)
        call SetUnitState(gTestPremHero, UNIT_STATE_MANA, 0.0)
    elseif t == 297 then
        set gTestPremBase = GetUnitState(gTestPremHero, UNIT_STATE_MANA) / 8.0
        call TestPremStart(1, 7, 5, 0, false, 0)
        call SetUnitState(gTestPremHero, UNIT_STATE_MANA, 0.0)
    elseif t == 305 then
        set v = GetUnitState(gTestPremHero, UNIT_STATE_MANA) / 8.0
        call TestCheck(v / gTestPremBase >= 1.2 and v / gTestPremBase <= 1.7, "Arcane Mask +50%: " + R2SW(gTestPremBase, 2, 2) + " mana per second without, " + R2SW(v, 2, 2) + " with")
        call TestPremClear()
        call TestFlush()
        set gTestPremDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

function TestPremiumTick takes nothing returns nothing
    local integer t
    local real v
    set gTestPremT = gTestPremT + 1
    set t = gTestPremT
    call TestPremAttack()
    // lifesteal, clean: no spell learned, an ordinary monster, HP room for the heal
    if t == 1 then
        call LanesStop()
        call TestFormEmptyMap()
        set gTestPremAttackOff = false
    endif
    if t == 2 or t == 11 or t == 20 or t == 29 or t == 38 or t == 47 then
        if t == 2 then
            call TestPremStart(1, 0, 0, 1, true, 0)
        elseif t == 11 then
            call TestPremStart(1, 0, 1, 1, true, 0)
        elseif t == 20 then
            call TestPremStart(1, 0, 5, 1, true, 0)
        elseif t == 29 then
            call TestPremStart(4, 0, 0, 1, true, 0)
        elseif t == 38 then
            call TestPremStart(4, 0, 1, 1, true, 0)
        else
            call TestPremStart(4, 0, 5, 1, true, 0)
        endif
        call SetWidgetLife(gTestPremHero, GetUnitState(gTestPremHero, UNIT_STATE_MAX_LIFE) * 0.3)
    elseif t == 10 then
        call TestPremFang("Mountain King, no item", 0)
    elseif t == 19 then
        call TestPremFang("Mountain King", 5)
    elseif t == 28 then
        call TestPremFang("Mountain King", 30)
    elseif t == 37 then
        call TestPremFang("Archmage, no item", 0)
    elseif t == 46 then
        call TestPremFang("Archmage", 5)
    elseif t == 55 then
        call TestPremFang("Archmage", 30)
        // the Dryad's whole kit with the Fang: what the engine makes of it, logged
        call TestPremStart(0, 0, 5, 8, true, 400)
        set gTestPremVolleyMin = 200.0
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, gHeroSkill[1])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[1])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[1])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[1])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[2])
        call SetWidgetLife(gTestPremHero, GetUnitState(gTestPremHero, UNIT_STATE_MAX_LIFE) * 0.3)
    elseif t == 67 then
        call TestCheck(GetUnitAbilityLevel(gTestPremHero, gHeroSkill[1]) == 4, "the Dryad's Multiple Arrows really are at rank 4 (" + I2S(GetUnitAbilityLevel(gTestPremHero, gHeroSkill[1])) + ")")
        call TestLog("KIT Dryad, Multiple Arrows, Critical Arrows, poison, Vampire Fang 30%: " + I2S(gTestPremHits) + " damage events, HP " + I2S(R2I(GetWidgetLife(gTestPremHero))) + " of " + I2S(R2I(GetUnitState(gTestPremHero, UNIT_STATE_MAX_LIFE))))
        call TestCheck(gTestPremVolleyBest >= 6 and gTestPremPoison > 0, "with the Fang the Dryad's spears still hit " + I2S(gTestPremVolleyBest) + " different foes in one volley, her poison seen " + I2S(gTestPremPoison) + " times")
        call TestFlush()
        // attack speed: seconds between hits, in plain attacks
        call TestPremStart(1, 1, 0, 1, true, 0)
    elseif t == 79 then
        set gTestPremBase = (gTestPremLast - gTestPremFirst) / I2R(gTestPremHits - 1)
        call TestPremStart(1, 1, 5, 1, true, 0)
    elseif t == 91 then
        set v = (gTestPremLast - gTestPremFirst) / I2R(gTestPremHits - 1)
        call TestCheck(gTestPremBase / v >= 1.05 and gTestPremBase / v <= 1.35, "Fury Gloves +25% attack speed: a hit every " + R2SW(gTestPremBase, 2, 2) + " s without, " + R2SW(v, 2, 2) + " s with them")
        // critical strike, many hits
        call TestPremStart(1, 2, 5, 1, true, 400)
    elseif t == 106 then
        set v = TestPremLowest()
        call TestCheck(gTestPremHits >= 20 and TestPremAbove(v * 1.7) * 100 >= gTestPremHits * 5 and TestPremAbove(v * 1.7) * 100 <= gTestPremHits * 40 and TestPremAbove(v * 2.5) == 0, "Executioner's Axe 20%, 2x: " + I2S(TestPremAbove(v * 1.7)) + " of " + I2S(gTestPremHits) + " hits are critical, none above 2x")
        call TestFlush()
        // bash: free foe, for the stun
        call TestPremStart(1, 3, 5, 1, false, 400)
        call SetUnitInvulnerable(gTestPremHero, true)
        set gTestStunRuns = 0
        set gTestStunShortest = 1000.0
        set gTestStunNow = 0.0
        call TimerStart(gTestStunTimer, 0.05, true, function TestStunPoll)
    elseif t == 121 then
        // the engine deals a bash's bonus as a damage event of its own, after the armor: +25 reads about 22
        set v = TestPremLowest()
        call TestCheck(gTestPremHits >= 20 and TestPremBelow(40.0) * 100 >= (gTestPremHits - TestPremBelow(40.0)) * 3 and TestPremBelow(40.0) * 100 <= (gTestPremHits - TestPremBelow(40.0)) * 35 and v >= 15.0 and v <= 30.0, "Stormhammer 15%, +25: " + I2S(TestPremBelow(40.0)) + " bashes in " + I2S(gTestPremHits - TestPremBelow(40.0)) + " hits, a bash's own damage event " + I2S(R2I(v)))
        call TestCheck(gTestStunRuns > 0 and gTestStunShortest >= 0.35 and gTestStunShortest <= 0.75, "Stormhammer's stun is 0.5 s: " + I2S(gTestStunRuns) + " stuns, the shortest " + R2SW(gTestStunShortest, 2, 2) + " s")
        call PauseTimer(gTestStunTimer)
        // with his own Bash, the item first: logged, it is the engine's rule what they do together
        call TestPremStart(1, 3, 5, 1, false, 400)
        call SetUnitInvulnerable(gTestPremHero, true)
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
    elseif t == 136 then
        call TestPremKit("Mountain King, Stormhammer 5 first, then Bash", 'Xhbh', 40.0, 1000.0)
        // his Bash alone, on the same champion then with the item, then with it gone
        call TestPremStart(1, 3, 0, 1, false, 400)
        call SetUnitInvulnerable(gTestPremHero, true)
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
        call SelectHeroSkill(gTestPremHero, 'Xhbh')
    elseif t == 146 then
        call TestPremKit("Mountain King, Bash alone", 'Xhbh', 40.0, 1000.0)
        set gTestPremItem = UnitAddItemById(gTestPremHero, gPremItem[3 * 8 + 5])
        call TestPremReset()
    elseif t == 156 then
        call TestPremKit("Mountain King, Bash, Stormhammer 5 added", 'Xhbh', 40.0, 1000.0)
        call RemoveItem(gTestPremItem)
        set gTestPremItem = null
        call TestPremReset()
    elseif t == 166 then
        call TestPremKit("Mountain King, Bash, the item gone again", 'Xhbh', 40.0, 1000.0)
        call TestFlush()
        // the Blademaster's own crit with the Axe, item first
        call TestPremStart(7, 2, 5, 1, true, 400)
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
    elseif t == 181 then
        call TestPremCrit("Blademaster, Executioner's Axe 5 first, then Critical Strike")
        // his crit alone, on the same champion then with the item, then with it gone
        call TestPremStart(7, 2, 0, 1, true, 400)
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
        call SelectHeroSkill(gTestPremHero, 'Xhcr')
    elseif t == 191 then
        call TestPremCrit("Blademaster, Critical Strike alone")
        set gTestPremItem = UnitAddItemById(gTestPremHero, gPremItem[2 * 8 + 5])
        call TestPremReset()
    elseif t == 201 then
        call TestPremCrit("Blademaster, Critical Strike, Executioner's Axe 5 added")
        call RemoveItem(gTestPremItem)
        set gTestPremItem = null
        call TestPremReset()
    elseif t == 211 then
        call TestPremCrit("Blademaster, Critical Strike, the item gone again")
        call TestFlush()
        call TestPremClear()
        // dodge: real attackers
        call TestPremStart(1, 4, 0, 8, false, 0)
        set gTestPremTrig2 = CreateTrigger()
        call TriggerRegisterAnyUnitEventBJ(gTestPremTrig2, EVENT_PLAYER_UNIT_ATTACKED)
        call TriggerAddAction(gTestPremTrig2, function TestPremOnAttacked)
        call DestroyTrigger(gTestPremTrig3)
        set gTestPremTrig3 = CreateTrigger()
        call TriggerRegisterUnitEvent(gTestPremTrig3, gTestPremHero, EVENT_UNIT_DAMAGED)
        call TriggerAddAction(gTestPremTrig3, function TestPremOnHurt)
        set gTestPremAttackOff = true
    elseif t == 231 then
        call TestLog("Cloak: without it " + I2S(gTestPremHurt) + " hits of " + I2S(gTestPremAttacked) + " attacks")
        set gTestPremBase = I2R(gTestPremHurt) / I2R(gTestPremAttacked)
        call TestPremStart(1, 4, 5, 8, false, 0)
        set gTestPremTrig2 = CreateTrigger()
        call TriggerRegisterAnyUnitEventBJ(gTestPremTrig2, EVENT_PLAYER_UNIT_ATTACKED)
        call TriggerAddAction(gTestPremTrig2, function TestPremOnAttacked)
        call DestroyTrigger(gTestPremTrig3)
        set gTestPremTrig3 = CreateTrigger()
        call TriggerRegisterUnitEvent(gTestPremTrig3, gTestPremHero, EVENT_UNIT_DAMAGED)
        call TriggerAddAction(gTestPremTrig3, function TestPremOnHurt)
    elseif t == 251 then
        set v = I2R(gTestPremHurt) / I2R(gTestPremAttacked)
        call TestCheck(v < gTestPremBase - 0.03 and v > gTestPremBase - 0.30, "Phantom Cloak 15%: " + I2S(gTestPremHurt) + " hits of " + I2S(gTestPremAttacked) + " attacks, " + R2SW(gTestPremBase * 100.0, 1, 0) + "% without it, " + R2SW(v * 100.0, 1, 0) + "% with")
        call TestFlush()
        // the Dryad's own Evasion with the Cloak: logged
        call TestPremStart(0, 4, 5, 8, false, 0)
        call SetHeroLevel(gTestPremHero, 20, false)
        call SelectHeroSkill(gTestPremHero, gHeroSkill[0])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[0])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[0])
        call SelectHeroSkill(gTestPremHero, gHeroSkill[0])
        set gTestPremTrig2 = CreateTrigger()
        call TriggerRegisterAnyUnitEventBJ(gTestPremTrig2, EVENT_PLAYER_UNIT_ATTACKED)
        call TriggerAddAction(gTestPremTrig2, function TestPremOnAttacked)
        call DestroyTrigger(gTestPremTrig3)
        set gTestPremTrig3 = CreateTrigger()
        call TriggerRegisterUnitEvent(gTestPremTrig3, gTestPremHero, EVENT_UNIT_DAMAGED)
        call TriggerAddAction(gTestPremTrig3, function TestPremOnHurt)
    elseif t == 271 then
        call TestCheck(GetUnitAbilityLevel(gTestPremHero, gHeroSkill[0]) == 4, "the Dryad's Evasion really is at rank 4 (" + I2S(GetUnitAbilityLevel(gTestPremHero, gHeroSkill[0])) + ")")
        call TestLog("KIT Dryad, Evasion (30%) and Phantom Cloak 5 (15%): " + I2S(gTestPremHurt) + " hits of " + I2S(gTestPremAttacked) + " attacks")
        call DestroyTrigger(gTestPremTrig3)
        set gTestPremTrig3 = null
        set gTestPremAttackOff = false
        // speed, regeneration: nobody around
        call TestPremStart(1, 5, 0, 0, false, 0)
        call SetUnitPathing(gTestPremHero, true)
    elseif t == 273 or t == 277 then
        set gTestPremBase2 = GetUnitY(gTestPremHero)
        set gTestPremX2 = GetUnitX(gTestPremHero)
    endif
    call TestPremiumTick2(t)
endfunction

function TestLearnWhen takes integer r returns string
    if ModuloInteger(r, 2) == 1 then
        return "after rank 1"
    endif
    return "before learning"
endfunction

// ---- A real purchase and learning, both ways round, every hero whose skill shares its code with a premium item: all four ranks must be learnable with the item in the bag.
function TestLearnTick takes nothing returns nothing
    local integer r
    local integer s
    local integer hero
    local integer fam
    local integer slot
    local integer abil
    local integer i
    set gTestLearnStep = gTestLearnStep + 1
    set r = (gTestLearnStep - 1) / 5
    set s = ModuloInteger(gTestLearnStep - 1, 5)
    if r == 10 then
        // the fullest card in a game's order: five skills at rank 1, then hero level 20. No twelve buttons hold it all. The order only shows the ability exists, not that a player has a button for it.
        if s == 0 then
            call TestFormEmptyMap()
            set gHero[0] = CreateUnit(Player(0), gHeroPool[5], gHallX, gHallY - 200.0, 270.0)
            call SetUnitInvulnerable(gHero[0], true)
            call SetHeroLevel(gHero[0], 19, false)
            set i = 0
            loop
                exitwhen i >= gSkillsPerHero
                call SelectHeroSkill(gHero[0], gHeroSkill[5 * gSkillsPerHero + i])
                set i = i + 1
            endloop
            call SetHeroLevel(gHero[0], 20, false)
            call SetUnitState(gHero[0], UNIT_STATE_MANA, GetUnitState(gHero[0], UNIT_STATE_MAX_MANA))
        elseif s == 2 then
            call TestCheck(GetUnitAbilityLevel(gHero[0], 'A006') == 1 and GetHeroSkillPoints(gHero[0]) > 0 and IssuePointOrder(gHero[0], "deathanddecay", GetUnitX(gHero[0]) + 300.0, GetUnitY(gHero[0])), "the Lich's level 20 ability exists while the Learn button stands: rank " + I2S(GetUnitAbilityLevel(gHero[0], 'A006')) + ", " + I2S(GetHeroSkillPoints(gHero[0])) + " points left, it takes an order")
        endif
        return
    endif
    if r >= 11 then
        call TestFormEmptyMap()
        set gTestLearnDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
        return
    endif
    set hero = 1
    set fam = 3
    set slot = 2
    if r / 2 == 1 then
        set hero = 7
        set fam = 2
        set slot = 1
    elseif r / 2 == 2 then
        set hero = 0
        set fam = 2
        set slot = 2
    elseif r / 2 == 3 then
        set hero = 0
        set fam = 4
        set slot = 0
    elseif r / 2 == 4 then
        set hero = 10
        set fam = 4
        set slot = 2
    endif
    set abil = gHeroSkill[hero * gSkillsPerHero + slot]
    if s == 0 then
        call TestFormEmptyMap()
        set gHero[0] = CreateUnit(Player(0), gHeroPool[hero], gHallX, gHallY - 200.0, 270.0)
        call SetUnitInvulnerable(gHero[0], true)
        call SetHeroLevel(gHero[0], 20, false)
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 20000)
        if ModuloInteger(r, 2) == 1 then
            call SelectHeroSkill(gHero[0], abil)
        endif
    elseif s == 2 then
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog(GetUnitName(gHero[0]) + ", rank " + I2S(GetUnitAbilityLevel(gHero[0], abil)) + " before the buy: order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[fam * 8 + 1])))
    elseif s == 3 then
        set i = 0
        loop
            exitwhen i >= 4
            call SelectHeroSkill(gHero[0], abil)
            set i = i + 1
        endloop
        call TestCheck(gTestGold - GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gPremPrice and UnitItemInSlot(gHero[0], 0) != null and GetUnitAbilityLevel(gHero[0], abil) == 4, GetUnitName(gHero[0]) + ", " + gPremName[fam] + " bought " + TestLearnWhen(r) + ": all ranks learned (" + I2S(GetUnitAbilityLevel(gHero[0], abil)) + " of 4), points left " + I2S(GetHeroSkillPoints(gHero[0])))
        call TestFlush()
    endif
endfunction

// ---- What a boss's gear really does: the same boss type, without and with its items, the same blows.
function TestGearBoss takes boolean geared returns unit
    local unit b = CreateUnit(Player(8), gBossType[1], gWpX[2 * 8 + 1] + 200.0, gWpY[2 * 8 + 1], 180.0)
    call GroupRemoveUnit(gWaveUnits, b)
    if geared then
        call BossGearItem(b, gGearHeart[1])
        call BossGearItem(b, gGearHands[1])
        call BossGearItem(b, gGearPlate[1])
    endif
    return b
endfunction

function TestGearHits takes unit attacker, unit victim returns nothing
    call TestPremClear()
    set gTestPremHits = 0
    set gTestPremDamage = 0.0
    set gTestPremHero = attacker
    set gTestPremFoe[0] = victim
    set gTestPremTrig = CreateTrigger()
    call TriggerAddAction(gTestPremTrig, function TestPremOnHit)
    call TriggerRegisterUnitEvent(gTestPremTrig, victim, EVENT_UNIT_DAMAGED)
endfunction

function TestGearHero takes nothing returns unit
    local unit h = CreateUnit(Player(1), gHeroPool[1], gWpX[2 * 8 + 1], gWpY[2 * 8 + 1], 0.0)
    call SetUnitInvulnerable(h, true)
    call SetHeroStr(h, 300, true)
    call SetHeroLevel(h, 1, false)
    call SelectHeroSkill(h, 'AHtb')
    call SetUnitState(h, UNIT_STATE_MANA, GetUnitState(h, UNIT_STATE_MAX_MANA))
    return h
endfunction

function TestGearTick takes nothing returns nothing
    local integer t
    local unit u
    local real v
    set gTestGearT = gTestGearT + 1
    set t = gTestGearT
    call TestPremAttack()
    // his blows on it: physical, then one Storm Bolt, without its items
    if t == 1 then
        set u = TestGearBoss(false)
        call PauseUnit(u, true)
        call TestGearHits(TestGearHero(), u)
    elseif t == 9 then
        set gTestGearPlain = gTestPremDamage / I2R(gTestPremHits)
        set gTestPremAttackOff = true
        call UnitRemoveAbility(gTestPremHero, 'Aatk')
        set gTestPremHits = 0
        set gTestPremDamage = 0.0
        call TestLog("gear: Storm Bolt order " + TestB2S(IssueTargetOrder(gTestPremHero, "thunderbolt", gTestPremFoe[0])))
    elseif t == 11 then
        set gTestGearBolt = gTestPremDamage
        call TestLog("gear: the bolt without the Warplate, " + I2S(gTestPremHits) + " damage event, " + I2S(R2I(gTestPremDamage)))
        set gTestGearBoltHits = gTestPremHits
        set gTestPremAttackOff = false
        // and with them
        set u = TestGearBoss(true)
        call PauseUnit(u, true)
        call TestGearHits(TestGearHero(), u)
    elseif t == 19 then
        set v = gTestPremDamage / I2R(gTestPremHits)
        call TestCheck(gTestGearPlain > 0.0 and v / gTestGearPlain >= 0.25 and v / gTestGearPlain <= 0.45, "Runic Warplate +40 armor: a hit does " + I2S(R2I(gTestGearPlain)) + " without, " + I2S(R2I(v)) + " with")
        set gTestPremAttackOff = true
        call UnitRemoveAbility(gTestPremHero, 'Aatk')
        set gTestPremHits = 0
        set gTestPremDamage = 0.0
        call TestLog("gear: Storm Bolt order " + TestB2S(IssueTargetOrder(gTestPremHero, "thunderbolt", gTestPremFoe[0])))
    elseif t == 21 then
        call TestCheck(gTestGearBoltHits == 1 and gTestPremHits == 1 and gTestGearBolt > 0.0 and gTestPremDamage / gTestGearBolt >= 0.67 and gTestPremDamage / gTestGearBolt <= 0.83, "Runic Warplate 25% less spell damage: a Storm Bolt does " + I2S(R2I(gTestGearBolt)) + " without, " + I2S(R2I(gTestPremDamage)) + " with")
        set gTestPremAttackOff = false
        // its blows: seconds between them, how many critical, on one big target
        set u = CreateUnit(Player(1), 'hfoo', gWpX[2 * 8 + 1], gWpY[2 * 8 + 1], 0.0)
        call ScaleKeepHp(u, 3000000, 0)
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
        call PauseUnit(u, true)
        call TestGearHits(TestGearBoss(false), u)
    elseif t == 33 then
        set gTestGearEvery = (gTestPremLast - gTestPremFirst) / I2R(gTestPremHits - 1)
        set v = TestPremLowest()
        call TestLog("gear: without it a blow every " + R2SW(gTestGearEvery, 2, 2) + " s, " + I2S(TestPremAbove(v * 1.7)) + " of " + I2S(gTestPremHits) + " critical")
        set u = CreateUnit(Player(1), 'hfoo', gWpX[2 * 8 + 1], gWpY[2 * 8 + 1], 0.0)
        call ScaleKeepHp(u, 3000000, 0)
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
        call PauseUnit(u, true)
        call TestGearHits(TestGearBoss(true), u)
    elseif t == 58 then
        set v = (gTestPremLast - gTestPremFirst) / I2R(gTestPremHits - 1)
        call TestCheck(gTestPremHits >= 20 and gTestGearEvery / v >= 1.7 and gTestGearEvery / v <= 2.3, "Executioner Gauntlets +100% attack speed: a blow every " + R2SW(gTestGearEvery, 2, 2) + " s without, " + R2SW(v, 2, 2) + " s with")
        set v = TestPremLowest()
        call TestCheck(gTestPremHits >= 20 and TestPremAbove(v * 1.7) * 100 >= gTestPremHits * 8 and TestPremAbove(v * 1.7) * 100 <= gTestPremHits * 50 and TestPremAbove(v * 3.2) == 0, "Executioner Gauntlets 25%, 2x: " + I2S(TestPremAbove(v * 1.7)) + " of " + I2S(gTestPremHits) + " blows critical, none above 2x")
        call TestPremClear()
        call TestFlush()
        set gTestGearDone = true
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set u = null
endfunction



// The whole phase, one step a second. Cast rows run at the same time in all 12 lanes.
function TestHeroes takes nothing returns nothing
    local integer t
    local integer c = 0
    local integer n
    local integer r
    local integer hero
    set gTestHeroT = gTestHeroT + 1
    set t = gTestHeroT
    if t == 1 then
        set gTestHT = InitHashtable()
        set gTestHitTrig = CreateTrigger()
        call TriggerAddAction(gTestHitTrig, function OnTestArrowHit)
        set gTestClockT = CreateTimer()
        call TimerStart(gTestClockT, 100000.0, false, null)
        set gTestSpellTrig = CreateTrigger()
        set c = 1
        loop
            exitwhen c >= 8
            call TriggerRegisterPlayerUnitEvent(gTestSpellTrig, Player(c), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)
            set c = c + 1
        endloop
        call TriggerAddAction(gTestSpellTrig, function OnTestSpell)
        set gTestSummonTrig = CreateTrigger()
        set c = 1
        loop
            exitwhen c >= 8
            call TriggerRegisterPlayerUnitEvent(gTestSummonTrig, Player(c), EVENT_PLAYER_UNIT_SUMMON, null)
            set c = c + 1
        endloop
        call TriggerAddAction(gTestSummonTrig, function OnTestSummon)
        set c = 0
        loop
            exitwhen c >= gHeroPoolCount
            set gTestC = c
            call ExecuteFunc("TestHeroSetupOne")
            set c = c + 1
        endloop
        // the rows: every hero's casts in table order
        set n = 0
        set hero = -1
        set r = 0
        set gTestRows = 0
        loop
            exitwhen n >= gCastN
            if gCastHero[n] != hero then
                set hero = gCastHero[n]
                set r = 0
            endif
            if gCastEffect[n] == 6 then
                set gTestRowOf[n] = 0
            else
                set r = r + 1
                set gTestRowOf[n] = r
                if r > gTestRows then
                    set gTestRows = r
                endif
            endif
            set n = n + 1
        endloop
        // the Demon Hunter holds a bought bonus: it must survive his demon form and its end
        set gHero[3] = gTestH[10]
        set gStatNext[3 * 16] = 1
        set gStatApplied[3 * 16] = 0
        call ApplyBought(3)
        set gTestDhLife = GetUnitState(gHero[3], UNIT_STATE_MAX_LIFE)
        call TestCheck(GetUnitAbilityLevel(gHero[3], gBonusAbil[0]) > 0, "Demon Hunter: a bought bonus is on him (max HP " + I2S(R2I(gTestDhLife)) + ")")
        call TestFlush()
    elseif t == 3 then
        set gTestSceneT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestSceneTick)
    elseif t >= 5 and t < 5 + 9 * gTestRows and ModuloInteger(t - 5, 9) == 0 then
        set gTestRow = (t - 5) / 9 + 1
        set n = 0
        loop
            exitwhen n >= gCastN
            if gTestRowOf[n] == gTestRow then
                set gTestN = n
                call ExecuteFunc("TestCastOne")
            endif
            set n = n + 1
        endloop
    elseif t >= 5 and t < 5 + 9 * gTestRows and ModuloInteger(t - 5, 9) == 7 then
        set n = 0
        loop
            exitwhen n >= gCastN
            if gTestRowOf[n] == gTestRow then
                set gTestN = n
                call ExecuteFunc("TestCastCheck")
            endif
            set n = n + 1
        endloop
        if GetUnitTypeId(gHero[3]) == gDemonForm and gTestDhMorphT == 0 then
            set gTestDhMorphT = t
            call TestCheck(GetUnitAbilityLevel(gHero[3], gBonusAbil[0]) > 0, "Demon form: the bought bonus is still on him")
            call TestCheck(GetUnitAbilityLevel(gHero[3], 'A02K') > 0, "Demon form: his level 20 ability is still on him")
        endif
        call TestFlush()
    elseif t == 6 + 9 * gTestRows then
        call TestGlueChecks()
        set gTestPalT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestPaladin)
        set gTestLichT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestLichArrows)
        set gTestTaurenT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestTauren)
        set gTestSplitT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestSplit)
    elseif t > 6 + 9 * gTestRows and gTestSplitDone and gTestTaurenDone and gTestPalDone and gTestLichDone and gTestSceneDone and gTestDhMorphT > 0 and t >= gTestDhMorphT + 95 and not gTestDhChecked then
        set gTestDhChecked = true
        call TestCheck(GetUnitTypeId(gHero[3]) == gDemonHero, "Metamorphosis ends: back to the Demon Hunter (" + GetUnitName(gHero[3]) + ")")
        call TestCheck(GetUnitAbilityLevel(gHero[3], gBonusAbil[0]) > 0 and GetUnitAbilityLevel(gHero[3], 'A02K') > 0, "back from the demon form: bought bonus and level 20 ability still there")
        call TestFlush()
        set gTestCardDue = true
    elseif gTestCardDue and gTestCardT == 0 then
        // the fullest card there is: the Lich has 7 buttons to press. With points left, with none, and past level 20.
        set gTestCardT = t
        call RemoveUnit(gHero[0])
        set gHero[0] = CreateUnit(Player(0), gHeroPool[5], gHeroX[0], gHeroY[0], 0.0)
        call SetHeroLevel(gHero[0], 20, false)
        set n = 0
        loop
            exitwhen n >= 25
            call SelectHeroSkill(gHero[0], gHeroSkill[5 * gSkillsPerHero + ModuloInteger(n, gSkillsPerHero)])
            set n = n + 1
        endloop
        call SetUnitInvulnerable(gHero[0], true)
        call SelectUnitForPlayerSingle(gHero[0], Player(0))
        call PanCameraToTimed(gHeroX[0], gHeroY[0], 0.0)
        call TestLog("VIDEO card 13")
        call TestLog("Lich card: points left " + I2S(GetHeroSkillPoints(gHero[0])))
        call TestFlush()
    elseif gTestCardT > 0 and t == gTestCardT + 6 then
        call UnitModifySkillPoints(gHero[0], -GetHeroSkillPoints(gHero[0]))
        call TestLog("Lich card: no points left " + I2S(GetHeroSkillPoints(gHero[0])))
    elseif gTestCardT > 0 and t == gTestCardT + 10 then
        call SetHeroLevel(gHero[0], 25, false)
        call TestLog("Lich card: level 25, points " + I2S(GetHeroSkillPoints(gHero[0])))
    elseif gTestCardT > 0 and t == gTestCardT + 14 then
        call RemoveUnit(gHero[0])
        set gHero[0] = null
        set gTestFormT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestFormTick)
    elseif gTestFormDone and not gTestWardenStarted then
        set gTestWardenStarted = true
        call TimerStart(gTestPremClock, 100000.0, false, null)
        call TimerStart(CreateTimer(), 1.0, true, function TestWardenTick)
    elseif gTestWardenDone and not gTestPremStarted then
        set gTestPremStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function TestPremiumTick)
    elseif gTestPremDone and not gTestGearStarted then
        set gTestGearStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function TestGearTick)
    elseif gTestGearDone and not gTestLearnStarted then
        set gTestLearnStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function TestLearnTick)
    elseif gTestLearnDone and not gTestDoomStarted then
        call TestDoomClear()
        set gTestDoomTrig = CreateTrigger()
        call TriggerRegisterAnyUnitEventBJ(gTestDoomTrig, EVENT_PLAYER_UNIT_SPELL_EFFECT)
        call TriggerAddAction(gTestDoomTrig, function TestDoomOnSpell)
        call TimerStart(CreateTimer(), 1.0, true, function TestDoomTick)
        set gTestDoomStarted = true
    elseif gTestDoomDone and not gTestPickStarted then
        set gTestPickStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function TestPickTick)
    elseif gTestPicksDone then
        call TestFlush()
        set gTestHold = false
        set gTestRound = 1
        call ExecuteFunc("CDRestart")
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
endfunction

// A Storm Bolt at the final boss: it can be refused for a moment, his own spells going on around the caster. Say why, and ask again.
function TestFinalBolt takes nothing returns nothing
    local unit h = gHero[0]
    local boolean ok
    set gTestBoltTries = gTestBoltTries + 1
    // the fixture's caster: a dead one cannot cast, the order is refused (life 0 in 20261102-234502-b-f89d, probably also v4.4's unexplained refusal)
    if GetWidgetLife(h) <= 0.405 then
        call TestLog("the caster is dead at game time " + I2S(gGameTime) + ", deaths " + I2S(gDeaths[0]) + ", revive timer " + I2S(R2I(TimerGetRemaining(gReviveTimer[0]))) + ", revived now " + TestB2S(ReviveHero(h, gFinalX + 600.0, gFinalY, false)) + ", life " + I2S(R2I(GetWidgetLife(h))))
        call SetUnitInvulnerable(h, true)
    endif
    set ok = IssueTargetOrder(h, "creepthunderbolt", gFinalBoss)
    call TestLog("Storm Bolt order at the final boss, try " + I2S(gTestBoltTries) + ": " + TestB2S(ok) + ", " + GetUnitName(h) + ", ACtb rank " + I2S(GetUnitAbilityLevel(h, 'ACtb')) + ", mana " + I2S(R2I(GetUnitState(h, UNIT_STATE_MANA))) + ", life " + I2S(R2I(GetWidgetLife(h))) + ", order " + OrderId2String(GetUnitCurrentOrder(h)) + ", stunned " + TestB2S(GetUnitAbilityLevel(h, 'BPSE') > 0) + ", " + I2S(R2I(SquareRoot((GetUnitX(h) - gFinalX) * (GetUnitX(h) - gFinalX) + (GetUnitY(h) - gFinalY) * (GetUnitY(h) - gFinalY)))) + " away")
    if ok or gTestBoltTries >= 6 then
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set h = null
endfunction

function TestBoltLabSpell takes nothing returns nothing
    if GetTriggerUnit() == gHero[0] and GetSpellAbilityId() == 'ACtb' and GetSpellTargetUnit() == gFinalBoss then
        set gTestBoltSpells = gTestBoltSpells + 1
        call TestLog("LAB Storm Bolt spell effect on the final boss, life " + I2S(R2I(GetWidgetLife(gFinalBoss))))
    endif
endfunction

function TestBoltLabAfter takes nothing returns nothing
    if GetUnitAbilityLevel(gFinalBoss, 'BPSE') > 0 then
        set gTestBoltStunned = gTestBoltStunned + 1
    endif
endfunction

function TestBoltLabHit takes nothing returns nothing
    if GetEventDamageSource() == gHero[0] and GetEventDamage() > 0.0 then
        set gTestBoltHits = gTestBoltHits + 1
        set gTestBoltLife = gTestBoltLife + GetEventDamage()
        call TimerStart(gTestBoltTimer, 0.1, false, function TestBoltLabAfter)
    endif
endfunction

// CD_TEST_ONLY=finalbolt: nothing else on the map: a champion, the final boss, three real Storm Bolts. Each one: the order taken, the spell's effect, damage, the stun gone.
function TestBoltLab takes nothing returns nothing
    local trigger tr
    local integer s
    set gTestBoltT = gTestBoltT + 1
    if gTestBoltT == 1 then
        call LanesStop()
        call TestFormEmptyMap()
        set gHero[0] = CreateUnit(Player(0), gHeroPool[4], gFinalX + 600.0, gFinalY, 180.0)
        call SetUnitInvulnerable(gHero[0], true)
        call UnitRemoveAbility(gHero[0], 'Aatk')
        call UnitAddAbility(gHero[0], 'ACtb')
        call SetUnitState(gHero[0], UNIT_STATE_MANA, GetUnitState(gHero[0], UNIT_STATE_MAX_MANA))
        set tr = CreateTrigger()
        call TriggerRegisterAnyUnitEventBJ(tr, EVENT_PLAYER_UNIT_SPELL_EFFECT)
        call TriggerAddAction(tr, function TestBoltLabSpell)
        set tr = null
        set gFinalPhase = true
        call SpawnFinalBoss()
        set tr = CreateTrigger()
        call TriggerRegisterUnitEvent(tr, gFinalBoss, EVENT_UNIT_DAMAGED)
        call TriggerAddAction(tr, function TestBoltLabHit)
        set tr = null
    endif
    set s = ModuloInteger(gTestBoltT - 3, 8)
    if gTestBoltT >= 3 and gTestBoltT < 27 then
        if s == 0 then
            set gTestStunRemoved = 0
            set gTestBoltSpells = 0
            set gTestBoltLife = 0.0
            set gTestBoltHits = 0
            set gTestBoltStunned = 0
            call SetUnitState(gHero[0], UNIT_STATE_MANA, GetUnitState(gHero[0], UNIT_STATE_MAX_MANA))
            call UnitResetCooldown(gHero[0])
            set gTestBoltTries = 0
            call TimerStart(CreateTimer(), 0.5, true, function TestFinalBolt)
        elseif s == 7 then
            call TestCheck(gTestBoltSpells == 1 and gTestBoltHits == 1 and gTestBoltLife > 0.0 and gTestStunRemoved > 0 and gTestBoltStunned == 0 and GetUnitAbilityLevel(gFinalBoss, 'BPSE') == 0, "final boss, a real Storm Bolt: order taken on try " + I2S(gTestBoltTries) + ", spell effect " + I2S(gTestBoltSpells) + ", " + I2S(gTestBoltHits) + " hit, 0.1 s later stunned " + I2S(gTestBoltStunned) + ", " + I2S(R2I(gTestBoltLife)) + " damage in the damage event, the stun removed " + I2S(gTestStunRemoved) + " times, stunned now " + TestB2S(GetUnitAbilityLevel(gFinalBoss, 'BPSE') > 0))
            call TestFlush()
        endif
    elseif gTestBoltT >= 27 then
        call TestLog("SELFTEST DONE")
        call TestFlush()
        call PauseTimer(GetExpiredTimer())
    endif
endfunction

// the first slot that holds this item type, -1 if none
function TestFirstSlot takes unit h, integer id returns integer
    local integer k = 0
    loop
        exitwhen k >= 6
        if GetItemTypeId(UnitItemInSlot(h, k)) == id then
            return k
        endif
        set k = k + 1
    endloop
    return -1
endfunction

// CD_TEST_ONLY=deadbuy: a player whose champion is dead, in the fog of a real game. The game's own answer: the button's tooltip in a picture, and what a real sale does.
function TestBuyCastle takes integer s returns nothing
    set gTestBuyStep = gCastleNext[s]
    set gTestBuyLumber = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)
    set gTestBuyOrder = IssueNeutralImmediateOrderById(Player(0), gCastle, gStatItem[s * gKindStride + gCastleNext[s]])
endfunction

function TestBuyCheck takes integer s, integer more, string what returns nothing
    call TestCheck(gTestBuyOrder and gCastleNext[s] == gTestBuyStep + more and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER) == gTestBuyLumber - 1, what + ": order taken " + TestB2S(gTestBuyOrder) + ", step " + I2S(gTestBuyStep) + " -> " + I2S(gCastleNext[s]) + ", trees " + I2S(gTestBuyLumber) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)))
endfunction

function TestBuyLab takes nothing returns nothing
    local integer t
    local integer kq = 0
    local integer kw = 0
    local integer ke = 0
    local integer kr = 0
    local integer ka = 0
    local integer s = 0
    loop
        exitwhen s >= gKinds
        if gKindType[s] == 4 then
            if kq == 0 then
                set kq = s
            elseif kw == 0 then
                set kw = s
            else
                set ke = s
            endif
        elseif gKindType[s] == 3 then
            set kr = s
        elseif gKindType[s] == 5 then
            set ka = s
        endif
        set s = s + 1
    endloop
    set gTestBuyT = gTestBuyT + 1
    set t = gTestBuyT
    if t == 1 then
        call FogEnable(true)
        call FogMaskEnable(true)
        set gHero[0] = CreateUnit(Player(0), gHeroPool[5], GetUnitX(gCastle) + 700.0, GetUnitY(gCastle) - 700.0, 90.0)
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 20)
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 5000)
        call SelectUnitForPlayerSingle(gCastle, Player(0))
    elseif t == 4 then
        call TestLog("HOVER deadbuy-alive-castle " + I2S(gTourX[0]) + " " + I2S(gTourY[0]))
        call TestFlush()
    elseif t == 7 then
        set gTestBuyMaxHp = GetUnitState(gCastle, UNIT_STATE_MAX_LIFE)
        call TestBuyCastle(kq)
    elseif t == 9 then
        call TestBuyCheck(kq, 1, "champion alive, Castle Health")
        call TestCheck(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE) == gTestBuyMaxHp + 1000.0, "the castle has 1000 more max HP: " + I2S(R2I(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE))))
        // the castle stays selected through his death. At that instant no buyer stands there yet: what every version before this one did
        call KillUnit(gHero[0])
        call PauseTimer(gReviveTimer[0])
        set gTestBuyOrder = IssueNeutralImmediateOrderById(Player(0), gCastle, gStatItem[kq * gKindStride + gCastleNext[kq]])
        call TestCheck(not gTestBuyOrder and gBuyer[0] == null, "the moment he dies, nobody to sell to: order refused " + TestB2S(not gTestBuyOrder))
        call TestFlush()
    elseif t == 10 then
        call TestCheck(gBuyer[0] != null and GetOwningPlayer(gBuyer[0]) == Player(0) and GetUnitAbilityLevel(gBuyer[0], 'Avul') > 0 and GetUnitX(gBuyer[0]) == gBuyerX and GetUnitY(gBuyer[0]) == gBuyerY and IsUnitInRange(gBuyer[0], gCastle, gCastleShopRange), "he is dead: an invulnerable buyer of his at " + I2S(R2I(GetUnitX(gBuyer[0]))) + ", " + I2S(R2I(GetUnitY(gBuyer[0]))))
        call TestLog("HOVER deadbuy-dead-castle " + I2S(gTourX[0]) + " " + I2S(gTourY[0]))
        call TestFlush()
    elseif t == 13 then
        set gTestBuyMaxHp = GetUnitState(gCastle, UNIT_STATE_MAX_LIFE)
        call TestBuyCastle(kq)
    elseif t == 15 then
        call TestBuyCheck(kq, 1, "champion dead, castle selected before he died, Castle Health")
        call TestCheck(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE) == gTestBuyMaxHp + 1000.0, "the castle has 1000 more max HP: " + I2S(R2I(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE))))
        call TestBuyCastle(kw)
    elseif t == 17 then
        call TestBuyCheck(kw, 1, "champion dead, Castle Armor")
        call TestBuyCastle(ke)
    elseif t == 19 then
        call TestBuyCheck(ke, 1, "champion dead, Castle Regeneration")
        call SetWidgetLife(gCastle, 3000.0)
        call TestBuyCastle(kr)
    elseif t == 21 then
        call TestBuyCheck(kr, 0, "champion dead, Repair Castle")
        call TestCheck(GetWidgetLife(gCastle) >= 5000.0, "2000 HP repaired: " + I2S(R2I(GetWidgetLife(gCastle))))
        call TestBuyCastle(ka)
    elseif t == 23 then
        call TestBuyCheck(ka, 0, "champion dead, Shockwave")
        call TestFlush()
        // selected only now, after his death
        call SelectUnitForPlayerSingle(gLaneMarker[0], Player(0))
    elseif t == 24 then
        call SelectUnitForPlayerSingle(gCastle, Player(0))
    elseif t == 26 then
        call TestLog("HOVER deadbuy-dead-castle-reselected " + I2S(gTourX[0]) + " " + I2S(gTourY[0]))
        call TestFlush()
    elseif t == 29 then
        call TestBuyCastle(kq)
    elseif t == 31 then
        call TestBuyCheck(kq, 1, "champion dead, castle selected after he died, Castle Health")
        // no tree, no buy
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 0)
        call TestBuyCastle(kq)
    elseif t == 33 then
        call TestCheck(not gTestBuyOrder and gCastleNext[kq] == gTestBuyStep, "no tree: no buy, the step stays " + I2S(gCastleNext[kq]))
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 20)
        call TestFlush()
        // the same buyer serves the grove: a premium item waits for him, a potion cannot, the Bank needs nobody
        call SelectUnitForPlayerSingle(gArmoryShop, Player(0))
    elseif t == 35 then
        call TestLog("HOVER deadbuy-dead-armory " + I2S(gTourX[0]) + " " + I2S(gTourY[0]))
        call TestFlush()
    elseif t == 38 then
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("Fang order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])))
    elseif t == 40 then
        // the armory stands near the buyer: the item goes straight into the buyer's bag
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestBuyGold - 1000 and TestSlots(gBuyer[0], gPremItem[1]) == 1, "champion dead, Vampire Fang: 1000 gold paid (" + I2S(gTestBuyGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + "), in the buyer's bag " + I2S(TestSlots(gBuyer[0], gPremItem[1])))
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("potion order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[0])))
    elseif t == 42 then
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestBuyGold, "champion dead, a potion: the gold comes back (" + I2S(gTestBuyGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        set gTestBuyIncome = gIncome[0]
        set gTestBuyLumber = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)
        call TestLog("Bank order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gBankShop, gBankItem)))
    elseif t == 44 then
        call TestCheck(gIncome[0] == gTestBuyIncome + gIncomeStep and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER) == gTestBuyLumber - 1, "champion dead, the Bank: income " + I2S(gTestBuyIncome) + " -> " + I2S(gIncome[0]) + ", trees " + I2S(gTestBuyLumber) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)))
        // no income of its own in the gold checks below
        set gIncome[0] = gTestBuyIncome
        set gTestBuyStat = gStatNext[0]
        call TestLog("circle order " + TestB2S(IssueImmediateOrderById(gLaneMarker[0], gStatItem[KindNext(0, 0)])))
    elseif t == 46 then
        call TestCheck(gStatNext[0] == gTestBuyStat + 1 and gStatApplied[0] < gStatNext[0], "champion dead, his circle: counted at once, step " + I2S(gTestBuyStat) + " -> " + I2S(gStatNext[0]) + ", on him " + I2S(gStatApplied[0]))
        call TestFlush()
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("Boots order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gApoShop, 'bspd')))
    elseif t == 47 then
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) < gTestBuyGold and TestSlots(gBuyer[0], 'bspd') == 1, "champion dead, the Apothecary's Boots: paid (" + I2S(gTestBuyGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + "), " + I2S(TestSlots(gBuyer[0], 'bspd')) + " in the buyer's bag")
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("second Fang order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])))
    elseif t == 48 then
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestBuyGold - 1000 and TestSlots(gBuyer[0], gPremItem[1]) == 2, "a second Fang while dead: paid, " + I2S(TestSlots(gBuyer[0], gPremItem[1])) + " in the buyer's bag")
        // a full bag: the shop refuses a normal item, nothing is paid
        loop
            exitwhen UnitInventoryCount(gBuyer[0]) >= 6
            call UnitAddItemById(gBuyer[0], 'ratc')
        endloop
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestBuyOrder = IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
    elseif t == 50 then
        call TestCheck(not gTestBuyOrder and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestBuyGold, "the buyer's bag full: order refused " + TestB2S(not gTestBuyOrder) + ", nothing paid (" + I2S(gTestBuyGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        loop
            exitwhen TestSlots(gBuyer[0], 'ratc') == 0
            call RemoveItem(UnitItemInSlot(gBuyer[0], TestFirstSlot(gBuyer[0], 'ratc')))
        endloop
        // what the buyer may hold goes to him
        call UnitAddItemById(gBuyer[0], gPremItem[8 + 1])
        call TestLog("in the buyer's bag now: " + I2S(UnitInventoryCount(gBuyer[0])))
        call ReviveHero(gHero[0], GetUnitX(gCastle) + 700.0, GetUnitY(gCastle) - 700.0, false)
    elseif t == 51 then
        call TestCheck(gBuyer[0] == null, "he is back: the buyer is gone")
    elseif t == 54 then
        call TestCheck(TestSlots(gHero[0], gPremItem[1]) == 0 and TestPremLevel(gHero[0]) == 2, "the two Fangs bought while dead reach him, merged: rank " + I2S(TestPremLevel(gHero[0])))
        call TestCheck(TestSlots(gHero[0], gPremItem[8 + 1]) == 1 and TestSlots(gHero[0], 'bspd') == 1, "what the buyer held is in his inventory (Gloves " + I2S(TestSlots(gHero[0], gPremItem[8 + 1])) + ", Boots " + I2S(TestSlots(gHero[0], 'bspd')) + ")")
        call TestCheck(gStatApplied[0] == gStatNext[0], "the circle's bonus is on him (" + I2S(gStatApplied[0]) + " of " + I2S(gStatNext[0]) + ")")
        call SelectUnitForPlayerSingle(gCastle, Player(0))
    elseif t == 56 then
        call TestBuyCastle(kq)
    elseif t == 58 then
        call TestBuyCheck(kq, 1, "alive again, Castle Health")
        call TestLog("Fang order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])))
    elseif t == 60 then
        call TestCheck(TestPremLevel(gHero[0]) == 3, "alive again, the Armory sells to him, nobody else: the Fang is rank " + I2S(TestPremLevel(gHero[0])))
        call TestFlush()
        // his inventory full, a second death
        loop
            exitwhen UnitInventoryCount(gHero[0]) >= 6
            call UnitAddItemById(gHero[0], 'ratc')
        endloop
        call KillUnit(gHero[0])
        call PauseTimer(gReviveTimer[0])
    elseif t == 61 then
        call TestCheck(gBuyer[0] != null, "a second death: the buyer is back")
    elseif t == 64 then
        call TestBuyCastle(kq)
    elseif t == 66 then
        call TestBuyCheck(kq, 1, "a second death, Castle Health")
        set gTestBuyGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("Gloves order, his inventory full " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[8 + 1])))
    elseif t == 68 then
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestBuyGold - 1000, "the Gloves paid (" + I2S(gTestBuyGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        call ReviveHero(gHero[0], GetUnitX(gCastle) + 700.0, GetUnitY(gCastle) - 700.0, false)
    elseif t == 71 then
        set gTestBuyRect = Rect(GetUnitX(gHero[0]) - 200.0, GetUnitY(gHero[0]) - 200.0, GetUnitX(gHero[0]) + 200.0, GetUnitY(gHero[0]) + 200.0)
        set gTestWardenItems = 0
        call EnumItemsInRect(gTestBuyRect, null, function TestItemNear)
        call RemoveRect(gTestBuyRect)
        set gTestBuyRect = null
        call TestCheck(gBuyer[0] == null and UnitInventoryCount(gHero[0]) == 6 and gTestWardenItems >= 1, "his inventory full: what he bought waits at his feet (" + I2S(gTestWardenItems) + " on the ground), the buyer is gone")
        // a champion hidden by a form of his: does the castle take him? Logged as it is
        call TestFlush()
        call ShowUnit(gHero[0], false)
    elseif t == 74 then
        call TestBuyCastle(kq)
        call TestLog("a hidden, living champion at the castle: order taken " + TestB2S(gTestBuyOrder))
        call ShowUnit(gHero[0], true)
    elseif t == 76 then
        call TestLog("SELFTEST DONE")
        call TestFlush()
        call PauseTimer(GetExpiredTimer())
    endif
endfunction

function TestEdge takes nothing returns nothing
    local unit h = gHero[0]
    local integer s
    set gTestEdgeT = gTestEdgeT + 1
    if gTestEdgeT == 1 then
        // his champion is dead: a buyer of his stands in the shop's range, and the castle sells
        call TestCheck(gBuyer[0] != null and IsUnitInRange(gBuyer[0], gCastle, gCastleShopRange) and GetUnitAbilityLevel(gBuyer[0], 'Avul') > 0, "champion dead: an invulnerable buyer of his in the castle's range")
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 5)
        set gTestBuyMaxHp = GetUnitState(gCastle, UNIT_STATE_MAX_LIFE)
        call TestBuyCastle(9)
        // a potion while the champion is dead: no potion, and the gold comes back
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestDeadOrder = IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[2])
        call TestLog("dead remote buy: order accepted = " + TestB2S(gTestDeadOrder) + ", gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)))
    elseif gTestEdgeT == 2 then
        call TestBuyCheck(9, 1, "champion dead, Castle Health")
        call TestCheck(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE) == gTestBuyMaxHp + 1000.0, "champion dead: the castle has 1000 more max HP: " + I2S(R2I(GetUnitState(gCastle, UNIT_STATE_MAX_LIFE))))
    elseif gTestEdgeT == 3 then
        call ReviveHero(h, gHeroX[0], gHeroY[0], false)
    elseif gTestEdgeT == 6 then
        // (the game refuses shop orders for about a second after a revive - wait 3 s)
        call TestCheck(gBuyer[0] == null, "champion back: the buyer is gone")
        if GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) >= gTestGold then
            call TestCheck(TestSlots(h, 'pres') == 0, "remote potion while dead: no potion, no gold taken")
        else
            call TestCheck(TestSlots(h, 'pres') == 1, "remote buy while dead: paid and arrives (slots " + I2S(TestSlots(h, 'pres')) + ")")
        endif
        call TestCheck(gStatApplied[0] == gStatNext[0], "dead circle buy applied after the revive (" + I2S(gStatApplied[0]) + " of " + I2S(gStatNext[0]) + ")")
        // a 6th premium buy at Lv 5 is refunded (restock first: the 5 earlier buys emptied the stock)
        call AddItemToStock(gArmoryShop, gPremItem[1], 5, 5)
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestDeadOrder = IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
        call TestLog("6th Vampire Fang order accepted = " + TestB2S(gTestDeadOrder))
        // a different premium item must NOT merge with the Fang
        call TestLog("Fury Gloves order accepted = " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[8 + 1])))
    elseif gTestEdgeT == 7 then
        if gTestDeadOrder then
            call TestCheck(TestPremLevel(h) == 5 and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestGold - 1000, "6th Vampire Fang at Lv 5: refunded, stays Lv 5; only the Gloves (1000) paid (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        else
            call TestLog("6th Vampire Fang: shop out of stock (AddItemToStock does not restock a neutral shop) - refund not exercised")
        endif
        call TestCheck(TestSlots(h, gPremItem[8 + 1]) == 1 and TestPremLevel(h) == 5, "Fury Gloves stay a separate item, the Fang stays Lv 5")
        // a 6th Fang reaching the inventory at Lv 5 (picked up) merges into a refund
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call UnitAddItemById(h, gPremItem[1])
        call TestCheck(TestPremLevel(h) == 5 and TestSlots(h, gPremItem[1]) == 0 and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestGold + 1000, "a 6th Fang at Lv 5: merged away, +1000 refund (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        // fill the inventory to 6, then buy a potion that can stack
        loop
            exitwhen UnitInventoryCount(h) >= 6
            call UnitAddItemById(h, 'ratc')
        endloop
        call TestLog("inventory items before the full-inventory buy: " + I2S(UnitInventoryCount(h)))
        call TestLog("full-inventory Healing Potion order accepted = " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[0])))
    elseif gTestEdgeT == 8 then
        call TestCheck(TestSlots(h, 'phea') == 1 and TestCharges(h, 'phea') == 3, "full inventory: a 3rd Healing Potion still stacks (slots " + I2S(TestSlots(h, 'phea')) + ", charges " + I2S(TestCharges(h, 'phea')) + ")")
        // full inventory, a potion it does NOT carry: refunded
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        call TestLog("full-inventory Invulnerability order accepted = " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[3])))
    elseif gTestEdgeT == 9 then
        call TestCheck(TestSlots(h, 'pnvl') == 0 and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) >= gTestGold, "full inventory + new potion type: refunded (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        // drink one: +50 % of max HP, one charge used, the stack stays
        call SetWidgetLife(h, 10.0)
        set s = 0
        loop
            exitwhen s >= 6
            if GetItemTypeId(UnitItemInSlot(h, s)) == 'phea' then
                call UnitUseItem(h, UnitItemInSlot(h, s))
            endif
            set s = s + 1
        endloop
    elseif gTestEdgeT == 10 then
        call TestCheck(GetWidgetLife(h) >= GetUnitState(h, UNIT_STATE_MAX_LIFE) * 0.45, "Healing Potion heals 50% (HP " + I2S(R2I(GetWidgetLife(h))) + " / " + I2S(R2I(GetUnitState(h, UNIT_STATE_MAX_LIFE))) + ")")
        call TestCheck(TestCharges(h, 'phea') == 2 and TestSlots(h, 'phea') == 1, "one charge used, stack kept (charges " + I2S(TestCharges(h, 'phea')) + ")")
    elseif gTestEdgeT == 11 then
        // STRESS: 4 waves of wave-20 size on lane 0 (4 x 60 units) against the Dryad's real spears
        set gTestKills = 0
        set gLaneWave[0] = 20
        set s = 0
        loop
            exitwhen s >= 4
            call SpawnWave(0)
            set s = s + 1
        endloop
        set gTestSpawned = 4 * (gFrontMax + gBackMax)
        call TestLog("stress: spawned 4 waves of wave 20 on lane 0")
    elseif gTestEdgeT == 30 then
        call TestCheck(true, "stress: 4 waves of wave 20 on one lane, 19 s later the game runs (" + I2S(gTestKills) + " killed)")
    elseif gTestEdgeT == 31 then
        call TestFlush()
        // the 12 champions; the round restarts at the end of it
        set gTestHeroT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestHeroes)
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
    endif
    set h = null
endfunction

// How many "bits" of a final-boss stat he holds (see FinalBits): the stat's value in steps.
function TestFinalBitSum takes integer first, integer n returns integer
    local integer i = 0
    local integer p = 1
    local integer v = 0
    loop
        exitwhen i >= n
        if GetUnitAbilityLevel(gFinalBoss, gFinalBit[first + i]) > 0 then
            set v = v + p
        endif
        set p = p * 2
        set i = i + 1
    endloop
    return v
endfunction

// The bonus a unit really carries, in steps (no game function reads a unit's damage).
function TestScaleBits takes unit u, integer first, integer n returns integer
    local integer i = n - 1
    local integer v = 0
    loop
        exitwhen i < 0
        set v = v * 2
        if GetUnitAbilityLevel(u, gScaleBit[first + i]) > 0 then
            set v = v + 1
        endif
        set i = i - 1
    endloop
    return v
endfunction

// A monster's death must not touch the Bank's budget: the death handler reads nothing of it, this keeps the check explicit.
function OnUnitDeathBudgetCheck takes nothing returns nothing
    local unit u = CreateUnit(Player(8), gStageUnit[0], gHallX, gHallY - 2200.0, 0.0)
    call KillUnit(u)
    set u = null
endfunction

// Scaling rules on a real unit, far from the fight. State tests: nothing here is a fight. Team sizes are the formula's values,
// not real players (a hidden run has one), and a real player leaving is not exercised here.
function TestScaling takes nothing returns nothing
    local unit u = CreateUnit(Player(8), gStageUnit[0], gHallX, gHallY - 2000.0, 0.0)
    local real base = GetUnitState(u, UNIT_STATE_MAX_LIFE)
    local real one
    local integer goldBefore = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
    local integer incomeBefore = gIncome[0]
    local integer budgetBefore = gIncomeBudget[0]
    local integer clockBefore = gIncomeClock[0]
    local integer waveBefore = gLaneWave[0]
    local integer gateBefore = gLaneWave[8]
    local integer teamBefore = gTeamCount
    local integer hpBits
    local integer dmgBits
    call PauseUnit(u, true)
    call TestCheck(RAbsBJ(WaveHpFactor(1) - 1.0) < 0.001 and RAbsBJ(WaveDmgFactor(1) - 1.0) < 0.001, "wave 1 scales nothing")
    call TestCheck(WaveHpFactor(2) > WaveDmgFactor(2) and WaveHpFactor(20) > WaveHpFactor(10) and WaveDmgFactor(20) > WaveDmgFactor(10), "HP grows faster than damage: wave 10 x" + R2SW(WaveHpFactor(10), 1, 2) + " / x" + R2SW(WaveDmgFactor(10), 1, 2))
    call TestCheck(RAbsBJ(TeamHpFactor(1) - 1.0) < 0.001 and RAbsBJ(TeamHpFactor(2) - 1.35) < 0.001 and RAbsBJ(TeamHpFactor(4) - 2.05) < 0.001 and RAbsBJ(TeamHpFactor(8) - 3.45) < 0.001, "shared HP for 1 / 2 / 4 / 8 players: formula values")
    call TestCheck(gTeamCount == 1, "team count in this hidden run: " + I2S(gTeamCount))
    if gTestRound == 0 then
        call TestCheck(gHero[1] == null and GetUnitTypeId(gTestPreLeft) == 0 and not gLaneActive[1], "picked and left before the round (state): no champion, no lane, not counted")
    endif
    call ScaleKeepHp(u, 1000, 50)
    set one = GetUnitState(u, UNIT_STATE_MAX_LIFE)
    call ScaleKeepHp(u, 1000, 50)
    call TestCheck(RAbsBJ(one - (base + 1000.0)) < 1.0 and RAbsBJ(GetUnitState(u, UNIT_STATE_MAX_LIFE) - one) < 1.0, "applying a scale twice changes nothing: max HP " + I2S(R2I(one)))
    call SetWidgetLife(u, 100.0)
    call ScaleKeepHp(u, 3000, 50)
    call TestCheck(GetUnitState(u, UNIT_STATE_MAX_LIFE) > one and RAbsBJ(GetWidgetLife(u) - 100.0) < 1.0, "a wounded unit that grows does not heal: HP " + I2S(R2I(GetWidgetLife(u))) + " of " + I2S(R2I(GetUnitState(u, UNIT_STATE_MAX_LIFE))))
    call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    call ScaleKeepHp(u, 0, 0)
    call TestCheck(RAbsBJ(GetUnitState(u, UNIT_STATE_MAX_LIFE) - base) < 1.0 and GetWidgetLife(u) <= base + 1.0, "scaling back down cuts HP to the new maximum")
    // saturation: far above the last bit it holds the maximum, HP read back, damage by the bits themselves
    call ScaleKeepHp(u, 2000000000, 2000000000)
    set one = GetUnitState(u, UNIT_STATE_MAX_LIFE)
    call TestCheck(RAbsBJ(one - (base + I2R(ScaleClamp(2000000000, gScaleHpBits) * gScaleHpStep))) < 1.0 and GetUnitAbilityLevel(u, gScaleBit[gScaleHpBits + gScaleDmgBits - 1]) > 0 and GetUnitAbilityLevel(u, gScaleBit[gScaleHpBits]) > 0, "a bonus past the last bit saturates, no wrap: max HP " + I2S(R2I(one)))
    call ScaleKeepHp(u, ScaleClamp(2000000000, gScaleHpBits) * gScaleHpStep + gScaleHpStep, 0)
    call TestCheck(RAbsBJ(GetUnitState(u, UNIT_STATE_MAX_LIFE) - one) < 1.0, "one step above the maximum: still the maximum")
    call RemoveUnit(u)
    set u = null
    // real units through the production path: a personal lane, then a shared gate with a simulated team of 4
    set gLaneWave[0] = 30
    set gLaneWave[8] = 30
    set gFormForward = 0.0
    set gFormSide = 0.0
    call WaveAnchor(0)
    call ScalePrepare(0, 0)
    call SpawnWaveUnit(0, gStageUnit[0], 0)
    set one = gRoleHp[0] * WaveHpFactor(30)
    set hpBits = ScaleHpBonus(0, 0, 0) / gScaleHpStep
    set dmgBits = ScaleDmgBonus(0, 0, 0) / gScaleDmgStep
    call TestCheck(hpBits > 1 and dmgBits > 1 and RAbsBJ(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE) - one) <= I2R(gScaleHpStep) and TestScaleBits(gTestLast, gScaleHpBits, gScaleDmgBits) == dmgBits, "wave 30, own lane, a spawned melee monster: HP " + I2S(R2I(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE))) + " of formula " + I2S(R2I(one)) + ", damage bonus " + I2S(dmgBits * gScaleDmgStep))
    call GroupRemoveUnit(gWaveUnits, gTestLast)
    call RemoveUnit(gTestLast)
    set gTeamCount = 4
    call WaveAnchor(8)
    call ScalePrepare(8, 1)
    call SpawnWaveUnit(8, gStageUnit[8 * 0 + 4 * 6 + 2], 0)
    set one = gRoleHp[0] * gStageHp[1] * WaveHpFactor(30) * (1.0 + gGateHpPer) * TeamHpFactor(4)
    set dmgBits = ScaleDmgBonus(8, 0, 1) / gScaleDmgStep
    call TestCheck(RAbsBJ(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE) - one) <= I2R(gScaleHpStep) and TestScaleBits(gTestLast, gScaleHpBits, gScaleDmgBits) == dmgBits, "wave 30, Level 2, stage 1, team of 4 (simulated): HP " + I2S(R2I(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE))) + " of formula " + I2S(R2I(one)))
    call GroupRemoveUnit(gWaveUnits, gTestLast)
    call RemoveUnit(gTestLast)
    set gTestLast = null
    set gLaneWave[0] = waveBefore
    set gLaneWave[8] = gateBefore
    set gTeamCount = teamBefore
    // the Bank's clock, in state: it counts exactly the budget, kills do not renew it, the next wave does, the minute pays once
    set gIncome[0] = 100
    set gIncomeBudget[0] = 2
    set gIncomeClock[0] = 58
    call BankTick()
    call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == goldBefore and gIncomeClock[0] == 59 and gIncomeBudget[0] == 1, "Bank: a counted second, no payment yet")
    call BankTick()
    call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == goldBefore + 100 and gIncomeClock[0] == 60 and gIncomeBudget[0] == 0, "Bank: the last second of the budget pays the full minute once")
    call BankTick()
    call BankTick()
    call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == goldBefore + 100 and gIncomeClock[0] == 60, "Bank: a used-up budget stands still, no gold")
    call OnUnitDeathBudgetCheck()
    call TestCheck(gIncomeBudget[0] == 0, "Bank: a kill does not renew the budget")
    set gFinalPhase = true
    call BankTick()
    call TestCheck(gIncomeClock[0] == 61, "Bank: the final fight always counts")
    set gFinalPhase = false
    call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, goldBefore)
    set gIncome[0] = incomeBefore
    set gIncomeBudget[0] = budgetBefore
    set gIncomeClock[0] = clockBefore
endfunction

function TestKillLaneEnum takes nothing returns nothing
    if GetUnitUserData(GetEnumUnit()) / 16 == gTestKillLane then
        call KillUnit(GetEnumUnit())
    endif
endfunction

function TestKillLane takes integer L returns nothing
    set gTestKillLane = L
    call ForGroup(gWaveUnits, function TestKillLaneEnum)
endfunction

function TestWaveSum takes nothing returns integer
    local integer L = 0
    local integer n = 0
    loop
        exitwhen L > 11
        set n = n + gLaneWave[L]
        set L = L + 1
    endloop
    return n
endfunction

// Two lanes side by side, each with its own wave. Real units and the real clear check; lane 1 is a SIMULATED second player: a hidden
// run has one, nobody plays in that slot, so its clear pays like the lane of a player who left. 1 s steps while TestStep holds.
function TestLanes takes nothing returns nothing
    local integer w
    set gTestLanesT = gTestLanesT + 1
    if gTestLanesT == 1 then
        // the champion must not earn anything here
        call SetUnitInvulnerable(gHero[0], true)
        call PauseUnit(gHero[0], true)
        // a slow lane: one monster of lane 0 stays alive, far from everything, so lane 0 cannot clear
        set gFormForward = 0.0
        set gFormSide = 0.0
        call WaveAnchor(0)
        call ScalePrepare(0, LaneStage(0))
        call SpawnWaveUnit(0, gStageUnit[0], 0)
        set gTestSentinel = gTestLast
        call SetUnitPosition(gTestSentinel, gHallX, gHallY - 2000.0)
        call PauseUnit(gTestSentinel, true)
        set gTestW0 = gLaneWave[0]
        // a fast lane, further along
        set gLaneActive[1] = true
        call CreateLaneBase(1)
        set gLaneWave[1] = 4
        call StartLaneWave(1)
        call TestCheck(gLaneWave[1] == 5 and gLaneWave[0] == gTestW0, "lane 2 starts its wave 5 while lane 1 stays at wave " + I2S(gTestW0))
        call TestCheck(RAbsBJ(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE) - gRoleHp[0] * WaveHpFactor(5)) <= I2R(gScaleHpStep), "a real monster of lane 2 has the HP of ITS wave 5: " + I2S(R2I(GetUnitState(gTestLast, UNIT_STATE_MAX_LIFE))))
    elseif gTestLanesT == 2 then
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestTrees = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)
        call TestKillLane(1)
    elseif gTestLanesT == 4 then
        call TestCheck(gLaneWave[1] == 6 and gLaneWave[0] == gTestW0, "lane 2 clear: its wave 6 came, lane 1 still at wave " + I2S(gLaneWave[0]))
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestGold + 300 and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER) == gTestTrees + 1, "the clear of a lane whose player is gone pays the others: +300 gold, +1 tree (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestTrees = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER)
        call PauseUnit(gTestSentinel, false)
        call TestKillLane(0)
    elseif gTestLanesT == 6 then
        call TestCheck(gLaneWave[0] == gTestW0 + 1 and gLaneWave[1] == 6, "lane 1 clear: its next wave came, lane 2 stays at wave 6 while its monsters live")
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) == gTestGold + 50 + 50 * gTestW0 and GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER) == gTestTrees + 1, "a player's own clear pays him for HIS wave " + I2S(gTestW0) + ": +" + I2S(50 + 50 * gTestW0) + " gold, +1 tree (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        // the break belongs to the lane (state)
        set w = gLaneWave[1]
        set gLaneWave[1] = 20
        call TestCheck(RAbsBJ(NextWaveDelay(1) - gWaveBreak) < 0.01 and RAbsBJ(NextWaveDelay(0) - gWaveInterval) < 0.01, "after its 10th or 20th wave only that lane pauses")
        set gLaneWave[1] = w
        // the Bank of a player: his own wave renews it, a gate's only once his lane is finished (state)
        set gIncomeBudget[0] = 5
        set gLaneState[1] = 2
        set gIncomeBudget[1] = 5
        call BankRenew(8)
        call TestCheck(gIncomeBudget[0] == 5 and gIncomeBudget[1] == gIncomeWaveSeconds, "Bank: a gate's wave renews only a player whose lane is finished")
        call BankRenew(0)
        call TestCheck(gIncomeBudget[0] == gIncomeWaveSeconds, "Bank: his own wave renews a player's Bank")
        set gLaneState[1] = 0
    elseif gTestLanesT == 7 then
        // lane 1 goes away again; the round goes on from here: the tower falls (TestStep's next step goes on with the Nexus)
        call LaneStop(1)
        set gLaneWaiting[1] = false
        set gLaneActive[1] = false
        set gLaneState[1] = -1
        call TestKillLane(1)
        call RemoveUnit(gTower[1])
        call RemoveUnit(gNexus[1])
        set gTower[1] = null
        set gNexus[1] = null
        set gLaneWave[1] = 0
        set gIncomeBudget[1] = 0
        call StartLaneWave(1)
        call TestCheck(gLaneWave[1] == 0 and not gLaneWaiting[1], "a lane without a player sends nothing")
        call PauseTimer(GetExpiredTimer())
        call DestroyTimer(GetExpiredTimer())
        call PauseUnit(gHero[0], false)
        call SetUnitInvulnerable(gHero[0], false)
        call KillUnit(gTower[0])
        call TestFlush()
        set gTestHold = false
    endif
endfunction

function TestStep takes nothing returns nothing
    local integer L
    local integer c
    local unit u
    if gTestHold or not gStarted then
        return
    endif
    set gTestClock = gTestClock + 5
    call Msg("|cff00ffff[TEST]|r t=" + I2S(gTestClock) + "  wave=" + I2S(gLaneWave[0]))
    if gTestOnly == "finalbolt" and gTestClock == 10 then
        set gTestHold = true
        call TimerStart(CreateTimer(), 1.0, true, function TestBoltLab)
        return
    endif
    if gTestOnly == "deadbuy" and gTestClock == 10 then
        set gTestHold = true
        call LanesStop()
        call TestFormEmptyMap()
        call SetUnitInvulnerable(gCastle, true)
        call TimerStart(CreateTimer(), 1.0, true, function TestBuyLab)
        return
    endif
    if gTestOnly == "tour" and gTestClock == 10 then
        set gTestHold = true
        call LanesStop()
        call TestFormEmptyMap()
        call TimerStart(CreateTimer(), 1.0, true, function TestTourTick)
        return
    endif
    if gTestClock == 5 then
        call FogEnable(false)
        call FogMaskEnable(false)
        // test fixture only: the mechanical checks need the round to last, and their fixtures do not defend the castle
        call SetUnitInvulnerable(gCastle, true)
    elseif gTestClock == 10 then
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 2000)
        call SelectUnitForPlayerSingle(gLaneMarker[0], Player(0))
        if IssueImmediateOrderById(gLaneMarker[0], gStatItem[0]) then
            call Msg("[TEST] tome #1 via shop order: accepted")
        elseif IssueNeutralImmediateOrderById(Player(0), gLaneMarker[0], gStatItem[0]) then
            call Msg("[TEST] tome #1 via neutral order: accepted")
        else
            call Msg("|cffff0000[TEST] tome #1: both orders REJECTED|r")
        endif
        if gTestRound == 1 then
            call TestCheck(GetUnitTypeId(gHero[0]) == gHeroPool[4], "round 2: the Archmage bought through the tavern (" + GetUnitName(gHero[0]) + ")")
            call SetHeroLevel(gHero[0], 9, false)
            set L = 0
            loop
                exitwhen L >= 5
                set u = CreateUnit(Player(8), 'hfoo', GetUnitX(gHero[0]) + 300.0 * Cos(L * 0.6), GetUnitY(gHero[0]) + 300.0 * Sin(L * 0.6), 0.0)
                set L = L + 1
            endloop
            call IssueTargetOrder(gHero[0], "attack", u)
        endif
        if gTestRound == 0 then
            call TestCheck(GetUnitTypeId(gHero[0]) == gHeroPool[0], "champion is the Dryad (" + GetUnitName(gHero[0]) + ")")
            call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, 20000)
            call SetHeroLevel(gHero[0], 16, false)
            // Multiple Arrows, Evasion, Critical Arrows and Endurance to level 4: 16 points at level 16
            set L = 0
            loop
                exitwhen L >= 4
                call SelectHeroSkill(gHero[0], gHeroSkill[1])
                call SelectHeroSkill(gHero[0], gHeroSkill[0])
                call SelectHeroSkill(gHero[0], gHeroSkill[2])
                call SelectHeroSkill(gHero[0], gHeroSkill[4])
                set L = L + 1
            endloop
            if IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[0]) then
                call TestLog("potion order 1 accepted")
            else
                call TestLog("potion order 1 REJECTED")
            endif
            call TestLog("potions after order 1: slots " + I2S(TestSlots(gHero[0], 'phea')) + " charges " + I2S(TestCharges(gHero[0], 'phea')))
            if IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[0]) then
                call TestLog("potion order 2 accepted")
            else
                call TestLog("potion order 2 REJECTED")
            endif
            call IssueNeutralImmediateOrderById(Player(0), gApoShop, gPotToken[1])
            call IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
        endif
    elseif gTestClock == 15 then
        call TestScaling()
        if IssueImmediateOrderById(gLaneMarker[0], gStatItem[1]) then
            call Msg("[TEST] tome #2 via shop order: accepted")
        elseif IssueNeutralImmediateOrderById(Player(0), gLaneMarker[0], gStatItem[1]) then
            call Msg("[TEST] tome #2 via neutral order: accepted")
        else
            call Msg("|cffff0000[TEST] tome #2: both orders REJECTED|r")
        endif
        if gTestRound == 0 then
            call TestCheck(GetUnitAbilityLevel(gHero[0], gHeroSkill[1]) == 4, "Multiple Arrows level 4 (is " + I2S(GetUnitAbilityLevel(gHero[0], gHeroSkill[1])) + ")")
            set L = 0
            loop
                exitwhen L >= 6
                if UnitItemInSlot(gHero[0], L) != null then
                    call TestLog("slot " + I2S(L) + ": " + GetItemName(UnitItemInSlot(gHero[0], L)) + " x" + I2S(GetItemCharges(UnitItemInSlot(gHero[0], L))))
                endif
                set L = L + 1
            endloop
            call TestCheck(TestSlots(gHero[0], 'phea') == 1 and TestCharges(gHero[0], 'phea') == 2, "2 healing potions stack in 1 slot (slots " + I2S(TestSlots(gHero[0], 'phea')) + ", charges " + I2S(TestCharges(gHero[0], 'phea')) + ")")
            call TestCheck(TestSlots(gHero[0], 'pman') == 1, "mana potion bought (slots " + I2S(TestSlots(gHero[0], 'pman')) + ")")
            call TestCheck(TestPremLevel(gHero[0]) == 1, "1 Vampire Fang buy = Lv 1 (is Lv " + I2S(TestPremLevel(gHero[0])) + ")")
            set L = 0
            loop
                exitwhen L >= 4
                call IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
                set L = L + 1
            endloop
            call TestLog("Bank order before death accepted = " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gBankShop, gBankItem)))
            set gTestLvl = GetHeroLevel(gHero[0])
            if IssueImmediateOrderById(gLaneMarker[0], gStatItem[8 * gKindStride + KindNext(0, 8)]) then
                call TestLog("XP buy order accepted")
            else
                call TestLog("FAIL XP buy order rejected")
            endif
        endif
    elseif gTestClock == 30 then
        if gTestRound == 1 then
            set gTestRegenT = 0
            call TimerStart(CreateTimer(), 1.0, true, function TestCastleRegen)
        endif
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 5)
        call SelectUnitForPlayerSingle(gCastle, Player(0))
        if IssueNeutralImmediateOrderById(Player(0), gCastle, gStatItem[9 * gKindStride]) then
            call Msg("[TEST] castle buy via neutral order: accepted")
        elseif IssueImmediateOrderById(gCastle, gStatItem[9 * gKindStride]) then
            call Msg("[TEST] castle buy via shop order: accepted")
        else
            call Msg("|cffff0000[TEST] castle buy: both orders REJECTED|r")
        endif
        // Bank, bought remotely (the hero is far from the grove)
        if IssueNeutralImmediateOrderById(Player(0), gBankShop, gBankItem) then
            call Msg("[TEST] bank buy (remote): accepted")
        else
            call Msg("|cffff0000[TEST] bank buy (remote): REJECTED|r")
        endif
        // Long Reach bought remotely -> range upgrade level 1
        call IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gReachItem)
        // premium item bought twice remotely -> must merge into Lv 2
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) + 3000)
        call IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
        call IssueNeutralImmediateOrderById(Player(0), gArmoryShop, gPremItem[1])
    elseif gTestClock == 20 then
        call PanCameraToTimed(gNexusX[0], gNexusY[0] - 650.0, 0.0)
        call ForGroup(gFirstWave, function TestKillEnum)
        if gTestRound == 0 then
            call TestCheck(GetHeroLevel(gHero[0]) == gTestLvl + 1, "Experience buy = +1 level (" + I2S(gTestLvl) + " -> " + I2S(GetHeroLevel(gHero[0])) + ")")
            call TestCheck(TestPremLevel(gHero[0]) == 5, "4 more Vampire Fang buys (stock 5) = Lv 5 (is Lv " + I2S(TestPremLevel(gHero[0])) + ")")
            call TestCheck(TestSlots(gHero[0], 'phea') == 1 and TestCharges(gHero[0], 'phea') == 2, "potions still stacked: slots " + I2S(TestSlots(gHero[0], 'phea')) + ", charges " + I2S(TestCharges(gHero[0], 'phea')))
            // buy a stat while the champion is dead: the price must step at once
            set gTestNext = gStatNext[0]
            call KillUnit(gHero[0])
            if IssueImmediateOrderById(gLaneMarker[0], gStatItem[KindNext(0, 0)]) then
                call TestLog("dead buy: shop order accepted")
            elseif IssueNeutralImmediateOrderById(Player(0), gLaneMarker[0], gStatItem[KindNext(0, 0)]) then
                call TestLog("dead buy: neutral order accepted")
            else
                call TestLog("dead buy: both orders rejected (no buyer while dead)")
            endif
        endif
    elseif gTestClock == 25 then
        if gTestRound == 0 then
            call TestCheck(gStatNext[0] == gTestNext + 1 or gStatNext[0] == gTestNext, "dead buy: price step " + I2S(gTestNext) + " -> " + I2S(gStatNext[0]) + " (same = the shop refused the buy, nothing paid)")
            call TestCheck(gStatApplied[0] <= gStatNext[0], "dead buy: bonus waits for the revive (applied " + I2S(gStatApplied[0]) + " of " + I2S(gStatNext[0]) + ")")
            call TestFlush()
            set gTestHold = true
            set gTestEdgeT = 0
            call TimerStart(CreateTimer(), 1.0, true, function TestEdge)
            return
        endif
        // two lanes side by side first; the tower falls at the end of it
        set gTestHold = true
        set gTestLanesT = 0
        call TimerStart(CreateTimer(), 1.0, true, function TestLanes)
    elseif gTestClock == 35 then
        // the boss rises at this lane's wave
        set gLaneWave[0] = 20
        call KillUnit(gNexus[0])
        call TestCheck(RAbsBJ(GetUnitState(gBoss[0], UNIT_STATE_MAX_LIFE) - gBossBaseHp[1] * (1.0 + gBossHpGrowth * 361.0)) < 200.0, "a lane boss at wave 20: " + I2S(R2I(GetUnitState(gBoss[0], UNIT_STATE_MAX_LIFE))) + " HP (its base 60000)")
        call TestCheck(GetUnitAbilityLevel(gBoss[0], gBossSpell[0]) == 5, "its spells at level " + I2S(GetUnitAbilityLevel(gBoss[0], gBossSpell[0])) + " of " + I2S(gBossSpellLevels))
        set gTestGateWave = gLaneWave[8]
        call TestCheck(gGateState[8] == 0 and gLaneWave[8] == gLaneWave[0] and MultiboardGetRowCount(gBoard) == 3, "Level 2 opens at the wave of the lane that opened it (" + I2S(gLaneWave[8]) + "), with its own scoreboard row")
        // what it does: everything measured in a real fight of 40 s, with the round held
        set gTestHold = true
        set gTestHT = InitHashtable()
        set gTestBossT = 0
        set gTestSpellTrig = CreateTrigger()
        set L = 8
        loop
            exitwhen L > 11
            call TriggerRegisterPlayerUnitEvent(gTestSpellTrig, Player(L), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)
            set L = L + 1
        endloop
        call TriggerAddAction(gTestSpellTrig, function TestBossSpell)
        call TimerStart(CreateTimer(), 1.0, true, function TestBossTick)
    elseif gTestClock == 40 then
        call PanCameraToTimed(gGateX[8] + 800.0, gGateY[8], 0.0)
        call TestLog("round 2: gate L2=" + I2S(gGateState[8]) + " L3=" + I2S(gGateState[9]) + " income=" + I2S(gIncome[0]))
        call TestFlush()
        call Msg("[TEST] gate states L2=" + I2S(gGateState[8]) + " L3=" + I2S(gGateState[9]) + "   income=" + I2S(gIncome[0]) + "   Fang Lv2 slot=" + I2S(GetInventoryIndexOfItemTypeBJ(gHero[0], gPremItem[2])) + "   reach=" + I2S(GetPlayerTechCount(Player(0), gReachTech, true)))
    elseif gTestClock == 45 then
        set gTestW0 = gLaneWave[0]
    elseif gTestClock == 50 then
        call TestCheck(gLaneWave[8] == gTestGateWave + 1 and gLaneAlive[8] > 0, "Level 2's first wave is one above its start: wave " + I2S(gLaneWave[8]) + ", " + I2S(gLaneAlive[8]) + " monsters")
        set gTestGold = GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)
        set gTestGateWave = gLaneWave[8]
        call TestKillLane(8)
        set L = 1
        loop
            exitwhen L >= 8
            if gLaneState[L] == 0 then
                call KillUnit(gTower[L])
                call KillUnit(gNexus[L])
            endif
            set L = L + 1
        endloop
    elseif gTestClock == 55 then
        call TestCheck(gLaneWave[8] == gTestGateWave + 1 or ModuloInteger(gTestGateWave, gBreakEvery) == 0, "Level 2 clear: its own next wave came (wave " + I2S(gLaneWave[8]) + ")")
        call TestCheck(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD) >= gTestGold + 50 + 50 * gTestGateWave, "a gate's clear pays the players: at least " + I2S(50 + 50 * gTestGateWave) + " gold (gold " + I2S(gTestGold) + " -> " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_GOLD)) + ")")
        call TestCheck(gLaneState[0] == 2 and gLaneWave[0] == gTestW0, "a finished lane sends no more waves: lane 1 stays at wave " + I2S(gLaneWave[0]))
        call PanCameraToTimed(0.0, 0.0, 0.0)
        set L = 1
        loop
            exitwhen L >= 8
            if gLaneState[L] == 1 then
                call KillUnit(gBoss[L])
            endif
            set L = L + 1
        endloop
        call KillUnit(gTower[8])
        call KillUnit(gNexus[8])
        call TestCheck(gGateState[9] == 0 and gLaneWave[9] == gLaneWave[8], "Level 3 goes on from Level 2's wave " + I2S(gLaneWave[9]))
    elseif gTestClock >= 60 and gTestClock <= 75 then
        // one gate level per step: kill the previous level's boss, then this level's tower + Nexus (boss rises)
        set L = 8 + (gTestClock - 60) / 5
        call Msg("[TEST] gates L2=" + I2S(gGateState[8]) + " L3=" + I2S(gGateState[9]) + " L4=" + I2S(gGateState[10]) + " L5=" + I2S(gGateState[11]))
        if L == 11 then
            call SetUnitInvulnerable(gCastle, false)    // the fixture ends right before the last boss falls
        endif
        if gBoss[L] != null then
            call KillUnit(gBoss[L])
        endif
        if L < 11 then
            call PanCameraToTimed(gNexusX[L + 1], gNexusY[L + 1], 0.0)
            call KillUnit(gTower[L + 1])
            call KillUnit(gNexus[L + 1])
        else
            call TestCheck(gFinalPhase and not gGameOver, "every lane boss + all 4 gate levels cleared -> the final boss awakens, no victory yet")
            // the final phase shields the castle by itself (StartFinalBoss): nothing of the fixture may be left to prove that
            call TestFlush()
        endif
    elseif gTestClock == 80 then
        call TestCheck(gFinalBoss != null and GetWidgetLife(gFinalBoss) > 0.405 and not gGameOver, "the final boss rose after the warning: " + GetUnitName(gFinalBoss))
        set gTestFinalHp = GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE)
        call TestCheck(RAbsBJ(gTestFinalHp - I2R(FinalMaxHp(gFinalMinute))) <= I2R(gFinalHpStep), "his max HP follows the minute: " + I2S(R2I(gTestFinalHp)) + " at minute " + I2S(gFinalMinute) + " (formula " + I2S(FinalMaxHp(gFinalMinute)) + ")")
        set gTestFinalCastle = GetWidgetLife(gCastle)
        call UnitDamageTarget(gFinalBoss, gCastle, 5000.0, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
        call TestCheck(GetWidgetLife(gCastle) >= gTestFinalCastle, "the castle is shielded while he lives")
        set gTestFinalWave = TestWaveSum()
        // targets for his spells: paused Taurens outside his stomp; our hero (invulnerable, he must ignore it) gets a Storm Bolt
        set L = 0
        loop
            exitwhen L >= 16
            set u = CreateUnit(Player(1), 'otau', gFinalX + 800.0 * Cos(L * 0.39), gFinalY + 800.0 * Sin(L * 0.39), 0.0)
            call PauseUnit(u, true)
            set L = L + 1
        endloop
        call TestLog("the caster before the fixture, game time " + I2S(gGameTime) + ": life " + I2S(R2I(GetWidgetLife(gHero[0]))) + ", revive timer " + I2S(R2I(TimerGetRemaining(gReviveTimer[0]))))
        if GetWidgetLife(gHero[0]) <= 0.405 then
            call TestLog("the caster revived: " + TestB2S(ReviveHero(gHero[0], gFinalX + 600.0, gFinalY, false)) + ", life " + I2S(R2I(GetWidgetLife(gHero[0]))))
        endif
        call SetUnitInvulnerable(gHero[0], true)
        call SetUnitPosition(gHero[0], gFinalX + 600.0, gFinalY)
        call UnitAddAbility(gHero[0], 'ACtb')
        call SetUnitState(gHero[0], UNIT_STATE_MANA, GetUnitState(gHero[0], UNIT_STATE_MAX_MANA))
        call PanCameraToTimed(gFinalX, gFinalY, 0.0)
        call TestFlush()
    elseif gTestClock == 85 then
        set gTestStunRemoved = 0
        set gTestBoltTries = 0
        call TimerStart(CreateTimer(), 0.5, true, function TestFinalBolt)
    elseif gTestClock == 90 then
        call TestCheck(gTestStunRemoved > 0 and GetUnitAbilityLevel(gFinalBoss, 'BPSE') == 0, "stun immune: a real Storm Bolt hit him, the stun was gone at once (" + I2S(gTestStunRemoved) + " removed)")
        // half HP, then jump the game clock 5 minutes: he must grow and his actual HP must not jump
        call SetWidgetLife(gFinalBoss, GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE) * 0.5)
        set gTestFinalLife = GetWidgetLife(gFinalBoss)
        set gTestFinalTier = gFinalTier
        set gTestFinalHp = GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE)
        set gGameTime = gGameTime + 300
        call TestFlush()
    elseif gTestClock == 95 then
        call TestCheck(GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE) > gTestFinalHp, "5 minutes later his max HP grew: " + I2S(R2I(gTestFinalHp)) + " -> " + I2S(R2I(GetUnitState(gFinalBoss, UNIT_STATE_MAX_LIFE))) + " (minute " + I2S(gFinalMinute) + ")")
        // 5 s of his 500 HP/s regeneration are allowed; keeping the percentage would add 625 000 HP
        call TestCheck(GetWidgetLife(gFinalBoss) <= gTestFinalLife + 5000.0, "growing did not heal him: HP " + I2S(R2I(gTestFinalLife)) + " -> " + I2S(R2I(GetWidgetLife(gFinalBoss))))
        call TestCheck(gFinalTier == gTestFinalTier + 1, "his spells went up a tier (" + I2S(gTestFinalTier) + " -> " + I2S(gFinalTier) + ")")
        call TestCheck(TestFinalBitSum(gFinalHpBits, gFinalDmgBits) * gFinalDmgStep == gFinalDmgPerMin * gFinalMinute, "his damage follows the minute: +" + I2S(TestFinalBitSum(gFinalHpBits, gFinalDmgBits) * gFinalDmgStep))
        call TestCheck(TestFinalBitSum(gFinalHpBits + gFinalDmgBits, gFinalArmorBits) == gFinalMinute / gFinalArmorEvery, "his armor follows the minute: +" + I2S(TestFinalBitSum(gFinalHpBits + gFinalDmgBits, gFinalArmorBits)))
        call TestCheck(gTestFinalCast[0] > 0 and gTestFinalCast[1] > 0 and gTestFinalCast[2] > 0 and gTestFinalCast[3] > 0, "his own spells went off: Storm Bolt " + I2S(gTestFinalCast[0]) + ", War Stomp " + I2S(gTestFinalCast[1]) + ", Shockwave " + I2S(gTestFinalCast[2]) + ", Inferno " + I2S(gTestFinalCast[3]))
        call TestCheck(TestWaveSum() == gTestFinalWave, "no more waves on any lane in the final phase")
        call TestFlush()
        // the end dialog pauses a single-player game: no timer runs after this, so check in this same thread
        call KillUnit(gFinalBoss)
        call TestCheck(gGameOver and gEndWon, "the final boss is dead -> victory")
        call TestFlush()
        // Play again must clear the final phase; the test ends here (tools/run_test.sh closes the game on this line)
        set gTestRound = 2
        set gTestHold = true
        call ExecuteFunc("CDRestart")
        call TestCheck(not gFinalPhase and gFinalBoss == null and GetUnitAbilityLevel(gCastle, 'Avul') == 0, "Play again clears the final phase")
        call TestCheck(TestWaveSum() == 0, "Play again: every lane's wave starts over")
        call TestLog("SELFTEST DONE")
        call TestFlush()
    endif
endfunction

//---------------------------------------------------------------------------
// Game start (after champion select)
//---------------------------------------------------------------------------
function StartGame takes nothing returns nothing
    local integer i = 0
    if gStarted then
        return
    endif
    set gStarted = true
    set gGameTime = 0
    set gTeamCount = 0
    loop
        exitwhen i >= 8
        set gLaneActive[i] = IsPlaying(i)
        set gIncomeClock[i] = 0
        set gIncomeBudget[i] = 0
        if gLaneActive[i] then
            set gTeamCount = gTeamCount + 1
            set gIncomeBudget[i] = gIncomeWaveSeconds
        elseif gHero[i] != null then
            // picked, then left before the round began: no lane and not counted, so no champion either
            call RemoveUnit(gHero[i])
            set gHero[i] = null
        endif
        set i = i + 1
    endloop
    if gTeamCount < 1 then
        set gTeamCount = 1
    endif
    set i = 0
    loop
        exitwhen i >= 8
        if gLaneActive[i] then
            call GateSet(i, true)
        endif
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= 8
        if gLaneActive[i] then
            call CreateLaneBase(i)
            call TimerStart(gLaneTimer[i], gFirstWaveDelay, false, function OnLaneTimer)
            if gLaneDialog[i] == null then
                set gLaneDialog[i] = CreateTimerDialog(gLaneTimer[i])
                call TimerDialogSetTitle(gLaneDialog[i], "Next wave in")
            endif
            call LaneDialog(i, true)
        else
            set gLaneState[i] = -1
        endif
        set i = i + 1
    endloop
    if not gTickStarted then
        set gTickStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function OnTick)
        if gTestMode then
            call TimerStart(CreateTimer(), 5.0, true, function TestStep)
        endif
    endif
    call CreateBoard()
    call Msg("|cffffcc00Defend your lane!|r   |cffffcc00-help|r = commands")
    call Msg("|cff4fc3ffSpend your gold now|r at your Champion's Circle: the first wave is strong.")
    call Msg("|cff4fc3ffEvery lane has its own wave:|r clear yours fast for more gold.")
endfunction

//---------------------------------------------------------------------------
// Champion select
//---------------------------------------------------------------------------
// Big gold "Select a Champion" floating over the hall, shown only to players who haven't picked yet.
// Text tags are anchored at their LEFT edge, so x is shifted by about half the text width.
function HidePickTag takes integer p returns nothing
    if gPickTag[p] != null then
        call DestroyTextTag(gPickTag[p])
        set gPickTag[p] = null
    endif
endfunction

function ShowPickTags takes nothing returns nothing
    local integer i = 0
    local texttag tt
    loop
        exitwhen i >= 8
        call HidePickTag(i)
        if IsPlaying(i) and gHero[i] == null then
            set tt = CreateTextTag()
            call SetTextTagText(tt, "Select a Champion", 0.06)
            call SetTextTagPos(tt, gHallX - 470.0, gHallY + 450.0, 0.0)
            call SetTextTagColor(tt, 255, 204, 0, 255)
            call SetTextTagPermanent(tt, true)
            call SetTextTagVisibility(tt, GetLocalPlayer() == Player(i))
            set gPickTag[i] = tt
        endif
        set i = i + 1
    endloop
    set tt = null
endfunction

function AssignHero takes integer p, unit h returns nothing
    local integer j = 0
    local integer id = GetUnitTypeId(h)
    set gHero[p] = h
    call HidePickTag(p)
    if gSoul[p] != null then
        call RemoveUnit(gSoul[p])
        set gSoul[p] = null
    endif
    call SetUnitPosition(h, gHeroX[p], gHeroY[p])
    call SetUnitFacing(h, bj_RADTODEG * Atan2(gNexusY[p] - gHeroY[p], gNexusX[p] - gHeroX[p]))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\MassTeleport\\MassTeleportTarget.mdl", gHeroX[p], gHeroY[p]))
    call ShowLaneHint(p)
    call PanCameraToTimedForPlayer(Player(p), gHeroX[p], gHeroY[p], 0.0)
    call SelectUnitForPlayerSingle(h, Player(p))
    // any number of players may play the same champion (12 champions, up to 8 players)
    loop
        exitwhen j >= gHeroPoolCount
        if gHeroPool[j] == id then
            set gHeroTaken[j] = true
        endif
        set j = j + 1
    endloop
    call Msg(gPlayerColorCode[p] + GetPlayerName(Player(p)) + "|r plays |cffffcc00" + GetUnitName(h) + "|r on the " + gDirName[p / 2] + " front (" + SideName(p) + " lane).")
endfunction

function EndChampionSelect takes nothing returns nothing
    local integer i = 0
    local integer pick
    local integer tries
    if not gSelecting then
        return
    endif
    set gSelecting = false
    call PauseTimer(gSelectTimer)
    call TimerDialogDisplay(gSelectDialog, false)
    loop
        exitwhen i >= 8
        if IsPlaying(i) and gHero[i] == null then
            set pick = GetRandomInt(0, gHeroPoolCount - 1)
            set tries = 0
            loop
                exitwhen not gHeroTaken[pick] or tries >= gHeroPoolCount
                set pick = ModuloInteger(pick + 1, gHeroPoolCount)
                set tries = tries + 1
            endloop
            call AssignHero(i, CreateUnit(Player(i), gHeroPool[pick], gHeroX[i], gHeroY[i], gDirFace[i / 2]))
        endif
        set i = i + 1
    endloop
    call StartGame()
endfunction

function AllChosen takes nothing returns boolean
    local integer i = 0
    loop
        exitwhen i >= 8
        if IsPlaying(i) and gHero[i] == null then
            return false
        endif
        set i = i + 1
    endloop
    return true
endfunction

function IsPoolHero takes integer id returns boolean
    local integer j = 0
    loop
        exitwhen j >= gHeroPoolCount
        if gHeroPool[j] == id then
            return true
        endif
        set j = j + 1
    endloop
    return false
endfunction

// One champion per player per round is this rule's job. The game's own hero limit counts native heroes ever hired, also after they are gone: Play again would be refused.
function OnUnitSold takes nothing returns nothing
    local unit h = GetSoldUnit()
    local integer p = GetPlayerId(GetOwningPlayer(h))
    if p < 8 and IsUnitType(h, UNIT_TYPE_HERO) then
        set gTestSoldType = GetUnitTypeId(h)
        if gSelecting and IsPlaying(p) and gHero[p] == null and GetSellingUnit() == gTavern[0] and IsPoolHero(GetUnitTypeId(h)) then
            call AssignHero(p, h)
            if AllChosen() then
                call EndChampionSelect()
            endif
        else
            call RemoveUnit(h)
        endif
    endif
    set h = null
endfunction

// Test build: player 1 buys a hero through the real tavern sale path.
function TestBuyReal takes nothing returns nothing
    // round 1: the Dryad; round 2: the Archmage (a standard hero through the real tavern sale)
    call TestLog("round " + I2S(gTestRound + 1) + ": soul " + I2S(R2I(GetWidgetLife(gSoul[0]))) + " in range " + TestB2S(IsUnitInRange(gSoul[0], gTavern[0], 600.0)) + ", selecting " + TestB2S(gSelecting) + ", heroes " + I2S(GetPlayerTechCount(Player(0), 'HERO', true)) + "/" + I2S(GetPlayerTechCount(Player(0), 'HERO', false)) + " of " + I2S(GetPlayerTechMaxAllowed(Player(0), 'HERO')) + ", this one " + I2S(GetPlayerTechCount(Player(0), gHeroPool[gTestRound * 4], true)) + " of " + I2S(GetPlayerTechMaxAllowed(Player(0), gHeroPool[gTestRound * 4])) + ", tokens " + I2S(GetPlayerState(Player(0), PLAYER_STATE_RESOURCE_HERO_TOKENS)))
    call TestLog("round " + I2S(gTestRound + 1) + ": tavern order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gTavern[0], gHeroPool[gTestRound * 4])) + ", hero after it " + GetUnitName(gHero[0]))
endfunction

// A moment after the second sale of the selection: he must be gone, the first one and the selection untouched. Then the real purchase of the round.
function TestBuyDuplicateCheck takes nothing returns nothing
    local integer want = gHeroPool[gTestRound * 4]
    call TestCheck(gTestSoldType == want and TestOwnedOfTypeP0(want) == 0 and gHero[0] == gTestPickOld and gSelecting and GetWidgetLife(gSoul[0]) > 0.405, "the selection runs and the player has a champion: a second one sold does not stay (" + I2S(TestOwnedOfTypeP0(want)) + " left, sold " + I2S(gTestSoldType) + ", the same champion " + TestB2S(gHero[0] == gTestPickOld) + ")")
    call DestroyTimer(GetExpiredTimer())
    call RemoveUnit(gTestPickOld)
    set gTestPickOld = null
    set gHero[0] = null
    call TestBuyReal()
endfunction

function TestBuyOrder takes nothing returns nothing
    if gTestPickBuy != 0 then
        call TestLog("selection: tavern order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gTavern[0], gTestPickBuy)))
        return
    endif
    // the state of a player who picked and left before the round: a champion on a slot that is not playing
    if gTestRound == 0 then
        set gHero[1] = CreateUnit(Player(1), gHeroPool[1], gHeroX[1], gHeroY[1], 0.0)
        set gTestPreLeft = gHero[1]
    endif
    if gTestRound == 1 then
        // already has a champion, the selection still runs
        set gHero[0] = CreateUnit(Player(0), gHeroPool[1], gHeroX[0], gHeroY[0], 0.0)
        set gTestPickOld = gHero[0]
        set gTestSoldType = 0
        call TestLog("in the selection, with a champion: order " + TestB2S(IssueNeutralImmediateOrderById(Player(0), gTavern[0], gHeroPool[gTestRound * 4])) + ", sold " + I2S(gTestSoldType) + ", heroes in the same instant " + I2S(TestOwnedOfTypeP0(gHeroPool[gTestRound * 4])))
        call TimerStart(CreateTimer(), 1.0, false, function TestBuyDuplicateCheck)
        return
    endif
    call TestBuyReal()
endfunction

function TestBuyHero takes nothing returns nothing
    if gTestRound == 0 and gTestPickBuy == 0 then
        // the whole tavern card, filmed before the buy
        call TestLog("VIDEO tavern 5")
        call TestFlush()
        call TimerStart(CreateTimer(), 4.0, false, function TestBuyOrder)
    else
        call TimerStart(CreateTimer(), 2.0, false, function TestBuyOrder)
    endif
endfunction

function SetupChampionSelect takes nothing returns nothing
    local integer i = 0
    loop
        exitwhen i >= 8
        if IsPlaying(i) then
            set gSoulTmp = 0
            loop
                exitwhen gSoulTmp >= 16
                set gStatNext[i * 16 + gSoulTmp] = 0
                set gStatApplied[i * 16 + gSoulTmp] = 0
                set gCastleNext[gSoulTmp] = 0
                set gSoulTmp = gSoulTmp + 1
            endloop
            set gXpPending[i] = 0
            call StockCircle(i)
            set gSoul[i] = CreateUnit(Player(i), gSoulType, gHallX, gHallY + gHallSoulDY, 90.0)
            call SetPlayerState(Player(i), PLAYER_STATE_RESOURCE_HERO_TOKENS, 1)
            call SetPlayerState(Player(i), PLAYER_STATE_RESOURCE_GOLD, 1000)
            call SetPlayerState(Player(i), PLAYER_STATE_RESOURCE_LUMBER, 0)
            call FogModifierStart(CreateFogModifierRadius(Player(i), FOG_OF_WAR_VISIBLE, gHallX, gHallY, 1400.0, true, false))
            call PanCameraToTimedForPlayer(Player(i), gHallX, gHallY, 0.0)
            call SelectUnitForPlayerSingle(gTavern[0], Player(i))
        endif
        set i = i + 1
    endloop
    call StockCastle()
    set gSelecting = true
    call TimerStart(gSelectTimer, gSelectTime, false, function EndChampionSelect)
    if gTestMode then
        call TimerStart(CreateTimer(), 2.0, false, function TestBuyHero)
    endif
    if gSelectDialog == null then
        set gSelectDialog = CreateTimerDialog(gSelectTimer)
        call TimerDialogSetTitle(gSelectDialog, "Choose your champion")
    endif
    call TimerDialogDisplay(gSelectDialog, true)
    call ShowPickTags()
endfunction

//---------------------------------------------------------------------------
// Restart: wipe the round and go back to champion select ("Play again" in the end dialog).
//---------------------------------------------------------------------------
function RemoveEnumItemCB takes nothing returns nothing
    call RemoveItem(GetEnumItem())
endfunction

function CDRestart takes nothing returns nothing
    local integer i
    local integer j
    local group g = CreateGroup()
    local unit u
    if gSelecting then
        return
    endif
    call LanesStop()
    set gFinalPhase = false
    set gFinalBoss = null
    set gFinalTier = -1
    set gFinalMinute = -1
    call PauseTimer(gFinalTimer)
    if gFinalDialog != null then
        call TimerDialogDisplay(gFinalDialog, false)
    endif
    call PauseTimer(gSelectTimer)
    set i = 8
    loop
        exitwhen i > 11
        call GroupEnumUnitsOfPlayer(g, Player(i), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            call RemoveUnit(u)
        endloop
        set i = i + 1
    endloop
    call GroupClear(gWaveUnits)
    call GroupClear(gFirstWave)
    set i = 0
    loop
        exitwhen i >= 8
        call PauseTimer(gReviveTimer[i])
        if gReviveDialog[i] != null then
            call TimerDialogDisplay(gReviveDialog[i], false)
        endif
        call DialogDisplay(Player(i), gEndDialog, false)
        call GroupEnumUnitsOfPlayer(g, Player(i), null)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            if u != gLaneMarker[i] then
                call RemoveUnit(u)
            endif
        endloop
        if gFollow[i] then
            set gFollow[i] = false
            call ResetToGameCameraForPlayer(Player(i), 0.0)
            call ApplyZoom(i)
        endif
        set gHero[i] = null
        set gSoul[i] = null
        set gKills[i] = 0
        set gDeaths[i] = 0
        set gIncome[i] = 0
        call SetPlayerTechResearched(Player(i), gReachTech, 0)
        set gFirstWaveLeft[i] = 0
        set gLaneState[i] = -1
        set gLaneActive[i] = false
        set gNexus[i] = null
        set gTower[i] = null
        set gBoss[i] = null
        set gProtector[i] = null
        call GateSet(i, false)
        set i = i + 1
    endloop
    // the Dark Gate closes again (its units were removed with the invaders' units above)
    set j = 8
    loop
        exitwhen j > 11
        set gGateState[j] = -1
        set gNexus[j] = null
        set gTower[j] = null
        set gBoss[j] = null
        set gProtector[j] = null
        call GateSet(j, false)
        set j = j + 1
    endloop
    set j = 0
    loop
        exitwhen j >= gHeroPoolCount
        set gHeroTaken[j] = false
        call AddUnitToStock(gTavern[gHeroTavern[j]], gHeroPool[j], 8, 8)
        set j = j + 1
    endloop
    call EnumItemsInRect(GetWorldBounds(), null, function RemoveEnumItemCB)
    // always a fresh castle, so bought castle upgrades start over too (its shop stock starts empty)
    if gCastle != null then
        call RemoveUnit(gCastle)
    endif
    set gCastle = CreateUnit(gKingdom, gCastleType, 0.0, 0.0, 270.0)
    set j = 0
    loop
        exitwhen j >= 16
        set gStocked[128 + j] = 0
        set j = j + 1
    endloop
    if gBoard != null then
        call MultiboardDisplay(gBoard, false)
        call DestroyMultiboard(gBoard)
        set gBoard = null
    endif
    set i = 0
    loop
        exitwhen i > 11
        set gLaneWave[i] = 0
        set i = i + 1
    endloop
    set gStarted = false
    set gGameOver = false
    set gTestClock = 0
    call DestroyGroup(g)
    set g = null
    call Msg("|cffffcc00Restart!|r  Everybody back to the Hall of Champions.")
    call SetupChampionSelect()
endfunction

function OnEndClick takes nothing returns nothing
    local player p = GetTriggerPlayer()
    if GetClickedButton() == gEndRestart then
        call CDRestart()
    elseif gEndWon then
        call CustomVictoryBJ(p, true, true)
    else
        call CustomDefeatBJ(p, "The castle has fallen!")
    endif
    set p = null
endfunction

// Chat "-help": the command list, shown only to the player who asked.
function OnHelpChat takes nothing returns nothing
    local player p = GetTriggerPlayer()
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cffffcc00Commands|r")
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cff4fc3ff-zoom 250|r   |cffc8c8c8zoom out|r")
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cff4fc3ff-cam|r   |cffc8c8c8camera follows your hero|r")
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cff4fc3ffSpace|r   |cffc8c8c8jump to your hero|r")
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cff4fc3ff-break 60|r   |cffc8c8c8shopping break length (s)|r")
    call DisplayTimedTextToPlayer(p, 0.0, 0.0, 15.0, "|cff4fc3ff-wave 5|r   |cffc8c8c8seconds between waves|r")
    set p = null
endfunction

//---------------------------------------------------------------------------
// Hidden developer cheats (not in -help; only for DEV_NAMES in build.py):
//   -addmoney 500   -addwood 10 / -addtree 10   -lvl 5   (no number = 1000 gold / 10 trees / 1 level)
//---------------------------------------------------------------------------
function IsDev takes player p returns boolean
    local integer i = 0
    loop
        exitwhen i >= gDevCount
        if GetPlayerName(p) == gDevName[i] then
            return true
        endif
        set i = i + 1
    endloop
    return false
endfunction

function DevArg takes string m, integer cmdLen, integer def returns integer
    local string rest = SubString(m, cmdLen, StringLength(m))
    loop
        exitwhen StringLength(rest) == 0 or SubString(rest, 0, 1) != " "
        set rest = SubString(rest, 1, StringLength(rest))
    endloop
    if StringLength(rest) == 0 or S2I(rest) <= 0 then
        return def
    endif
    return S2I(rest)
endfunction

// -wave / -break argument: -1 = no number (show the current values). Unlike DevArg, "0" is a real value here.
function PaceArg takes string m, integer cmdLen returns integer
    local string rest = SubString(m, cmdLen, StringLength(m))
    loop
        exitwhen StringLength(rest) == 0 or SubString(rest, 0, 1) != " "
        set rest = SubString(rest, 1, StringLength(rest))
    endloop
    if StringLength(rest) == 0 or (S2I(rest) == 0 and SubString(rest, 0, 1) != "0") then
        return -1
    endif
    return S2I(rest)
endfunction

function OnDevChat takes nothing returns nothing
    local player p = GetTriggerPlayer()
    local integer id = GetPlayerId(p)
    local string m = GetEventPlayerChatString()
    local integer n
    if not IsDev(p) then
        set p = null
        return
    endif
    if SubString(m, 0, 9) == "-addmoney" then
        set n = DevArg(m, 9, 1000)
        call SetPlayerState(p, PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(p, PLAYER_STATE_RESOURCE_GOLD) + n)
        call DisplayTimedTextToPlayer(p, 0.0, 0.0, 4.0, "|cffffcc00[dev] +" + I2S(n) + " gold|r")
    elseif SubString(m, 0, 8) == "-addwood" or SubString(m, 0, 8) == "-addtree" then
        set n = DevArg(m, 8, 10)
        call SetPlayerState(p, PLAYER_STATE_RESOURCE_LUMBER, GetPlayerState(p, PLAYER_STATE_RESOURCE_LUMBER) + n)
        call DisplayTimedTextToPlayer(p, 0.0, 0.0, 4.0, "|cff80ff80[dev] +" + I2S(n) + " trees|r")
    elseif SubString(m, 0, 4) == "-lvl" and gHero[id] != null then
        set n = DevArg(m, 4, 1)
        call SetHeroLevel(gHero[id], GetHeroLevel(gHero[id]) + n, true)
        call DisplayTimedTextToPlayer(p, 0.0, 0.0, 4.0, "|cff4fc3ff[dev] level " + I2S(GetHeroLevel(gHero[id])) + "|r")
    endif
    set p = null
endfunction

//---------------------------------------------------------------------------
// Pace settings (any player, announced to everyone):
//   -break 60   shopping-break length (5-300 s)      -wave 5   seconds between waves (0-60 s, default 0)
// Without a number they show the current value. A running countdown of any lane that is longer is shortened at once.
//---------------------------------------------------------------------------
function OnConfigChat takes nothing returns nothing
    local player p = GetTriggerPlayer()
    local string m = GetEventPlayerChatString()
    local string who = gPlayerColorCode[GetPlayerId(p)] + GetPlayerName(p) + "|r"
    local integer n
    local integer L = 0
    local boolean isBreak = SubString(m, 0, 6) == "-break"
    if not isBreak and SubString(m, 0, 5) != "-wave" then
        set p = null
        return
    endif
    if isBreak then
        set n = PaceArg(m, 6)
    else
        set n = PaceArg(m, 5)
    endif
    if n < 0 then
        call DisplayTimedTextToPlayer(p, 0.0, 0.0, 6.0, "Break |cffffcc00" + I2S(R2I(gWaveBreak)) + "s|r   Wave gap |cffffcc00" + I2S(R2I(gWaveInterval)) + "s|r")
        set p = null
        return
    endif
    if isBreak then
        if n < 5 then
            set n = 5
        elseif n > 300 then
            set n = 300
        endif
        set gWaveBreak = I2R(n)
        call Msg(who + " set the shopping break to |cffffcc00" + I2S(n) + "s|r")
    else
        if n < 0 then
            set n = 0
        elseif n > 60 then
            set n = 60
        endif
        set gWaveInterval = I2R(n)
        call Msg(who + " set the wave gap to |cffffcc00" + I2S(n) + "s|r")
    endif
    // a countdown that is running now gets shortened if it is longer than the new setting
    loop
        exitwhen L > 11
        if gStarted and not gGameOver and not gFinalPhase and LaneSpawns(L) and not gLaneWaiting[L] and gLaneWave[L] > 0 and TimerGetRemaining(gLaneTimer[L]) > NextWaveDelay(L) then
            call TimerStart(gLaneTimer[L], NextWaveDelay(L), false, function OnLaneTimer)
        endif
        set L = L + 1
    endloop
    set p = null
endfunction

function InitGame takes nothing returns nothing
    local trigger t
    local integer i = 0
    call InitData()
    set gKingdom = Player(14)
    set gWaveUnits = CreateGroup()
    set gFirstWave = CreateGroup()
    set gSelectTimer = CreateTimer()
    call SetupAlliances()
    call SetupDarkness()
    call EnumDestructablesInRect(GetWorldBounds(), null, function MakeWallInvulnerable)
    call FogEnable(false)
    call FogMaskEnable(false)
    loop
        exitwhen i > 11
        set gLaneTimer[i] = CreateTimer()
        set gGate[i] = CreateDestructable(gGateType[i], gGateX[i], gGateY[i], gGateFace[i], 1.0, 0)
        set gGate2[i] = CreateDestructable(gGateType[i], gGateX2[i], gGateY2[i], gGateFace[i], 1.0, 0)
        call SetDestructableInvulnerable(gGate[i], true)
        call SetDestructableInvulnerable(gGate2[i], true)
        set i = i + 1
    endloop
    set i = 0
    call CreateKingdom()
    call CreateNeutrals()
    loop
        exitwhen i >= 8
        set gReviveTimer[i] = CreateTimer()
        set gKills[i] = 0
        set gDeaths[i] = 0
        set i = i + 1
    endloop
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_DEATH)
    call TriggerAddAction(t, function OnUnitDeath)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SELL)
    call TriggerAddAction(t, function OnUnitSold)

    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerEvent(t, Player(i), EVENT_PLAYER_LEAVE)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnPlayerLeave)
    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-zoom", false)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnZoomChat)
    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerEvent(t, Player(i), EVENT_PLAYER_END_CINEMATIC)
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-cam", true)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnFollowToggle)
    call TimerStart(CreateTimer(), 0.1, true, function SpaceTick)
    call TimerStart(CreateTimer(), 0.2, true, function GrabTick)
    call TimerStart(CreateTimer(), 0.05, true, function FinalImmuneTick)
    if gTestMode then
        set t = CreateTrigger()
        call TriggerRegisterPlayerUnitEvent(t, Player(8), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)
        call TriggerAddAction(t, function OnFinalCastTest)
    endif
    call TimerStart(CreateTimer(), 1.0, true, function UpdateBoard)
    call TimerStart(CreateTimer(), 1.0, true, function ProtectorTick)
    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-help", true)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnHelpChat)
    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-addmoney", false)
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-addwood", false)
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-addtree", false)
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-lvl", false)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnDevChat)
    set t = CreateTrigger()
    set i = 0
    loop
        exitwhen i >= 8
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-break", false)
        call TriggerRegisterPlayerChatEvent(t, Player(i), "-wave", false)
        set i = i + 1
    endloop
    call TriggerAddAction(t, function OnConfigChat)
    set gEndDialog = DialogCreate()
    set t = CreateTrigger()
    call TriggerRegisterDialogEvent(t, gEndDialog)
    call TriggerAddAction(t, function OnEndClick)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_PICKUP_ITEM)
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_USE_ITEM)
    call TriggerAddAction(t, function OnItemPickup)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SELL_ITEM)
    call TriggerAddAction(t, function OnItemSold)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_HERO_LEVEL)
    call TriggerAddAction(t, function OnHeroLevel)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_ISSUED_ORDER)
    call TriggerAddAction(t, function OnHeroGlueOrder)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_EFFECT)
    call TriggerAddAction(t, function OnHeroGlueSpell)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_HERO_SKILL)
    call TriggerAddAction(t, function OnHeroGlueLearn)
    call CreateQuests()
    call TimerStart(CreateTimer(), 0.5, false, function SetupChampionSelect)
    set t = null
endfunction
