//===========================================================================
// TechTools Castle Defence -- game logic (hand-written, vanilla JASS 1.27)
// Champion select -> each champion defends his own lane -> destroys his own
// enemy Nexus -> slays the boss that rises from it. The generator puts the globals block, InitData()
// and CreateNeutrals() above this file and config()/main() below it.
//===========================================================================

function Msg takes string s returns nothing
    call DisplayTimedTextToForce(GetPlayersAll(), 12.0, s)
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

function SideName takes integer p returns string
    if ModuloInteger(p, 2) == 0 then
        return "left"
    endif
    return "right"
endfunction

// First wave of a lane cleared (or wave 2 starts) -> the champion jumps to level 2.
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
            set id = gStatItem[s * 64 + KindNext(p, s)]
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
            set id = gStatItem[s * 64 + gCastleNext[s]]
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
    local real dmg = 300.0 + 30.0 * I2R(gWave)
    call GroupEnumUnitsInRange(g, cx, cy, 1100.0, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        set o = GetPlayerId(GetOwningPlayer(u))
        if o >= 8 and o <= 11 and GetWidgetLife(u) > 0.405 then
            call UnitDamageTarget(gCastle, u, dmg, true, false, ATTACK_TYPE_MAGIC, DAMAGE_TYPE_MAGIC, WEAPON_TYPE_WHOKNOWS)
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
                call UnitAddAbility(h, gBonusAbil[s * 64 + gStatApplied[p * 16 + s]])
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
// (castle kinds), remove the item, step the price up 10 % and restock.
function AdvanceStatPrice takes integer p, item it returns nothing
    local integer id = GetItemTypeId(it)
    local integer s = 0
    local integer k
    loop
        exitwhen s >= gKinds
        set k = KindNext(p, s)
        if k < gStatTiers and gStatItem[s * 64 + k] == id then
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
                        call UnitAddAbility(gCastle, gBonusAbil[s * 64 + k])
                    else
                        call CastleShockwave()
                    endif
                    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Spells\\Human\\Heal\\HealTarget.mdl", gCastle, "origin"))
                endif
                call Msg(gPlayerColorCode[p] + GetPlayerName(Player(p)) + "|r: |cffffcc00" + gKindEffect[s] + "|r")
                call StockCastle()
                return
            endif
            // the buy counts AT ONCE (price +10 %), even while the champion is dead or not picked yet;
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

// Bank: 1 tree buys +gIncomeStep (10) gold income per minute, paid by IncomeTick on every full minute of the
// game clock (called from OnTick).
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

function IncomeTick takes nothing returns nothing
    local integer p = 0
    loop
        exitwhen p >= 8
        if gIncome[p] > 0 and IsPlaying(p) then
            call SetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(Player(p), PLAYER_STATE_RESOURCE_GOLD) + gIncome[p])
            call DisplayTimedTextToPlayer(Player(p), 0.0, 0.0, 4.0, "|cffffcc00+" + I2S(gIncome[p]) + " gold|r income")
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
                if ib != null and PremiumFamily(GetItemTypeId(ib)) == fam then
                    set L = PremiumLevel(GetItemTypeId(ia), fam) + PremiumLevel(GetItemTypeId(ib), fam)
                    call RemoveItem(ib)
                    call RemoveItem(ia)
                    if L > gPremMax then
                        call SetPlayerState(pl, PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(pl, PLAYER_STATE_RESOURCE_GOLD) + gPremPrice * (L - gPremMax))
                        call DisplayTimedTextToPlayer(pl, 0.0, 0.0, 5.0, "|cffffcc00" + gPremName[fam] + "|r is already max level - refunded")
                        set L = gPremMax
                    else
                        call DisplayTimedTextToPlayer(pl, 0.0, 0.0, 5.0, "|cffffcc00" + gPremName[fam] + "|r |cff4fc3ffLv " + I2S(L) + "|r: " + gPremEffect[fam * 8 + L])
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
        elseif StackPotion(b, it) then
            // potion merged into the one the champion already carries
        else
            // a premium item always goes to the champion (whoever the shop picked as buyer)
            if gHero[p] != null and PremiumFamily(GetItemTypeId(it)) >= 0 then
                set b = gHero[p]
            endif
            if GetItemTypeId(it) != 0 and not UnitHasItem(b, it) then
                if not UnitAddItem(b, it) then
                    call SetItemPosition(it, GetUnitX(b), GetUnitY(b))
                endif
            endif
            call MergePremiumAll(gHero[p])
        endif
    endif
    set it = null
    set b = null
endfunction

function OnItemPickup takes nothing returns nothing
    local integer p = GetPlayerId(GetOwningPlayer(GetTriggerUnit()))
    local item it = GetManipulatedItem()
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
        if KindNext(p, s) < gStatTiers and gStatItem[s * 64 + KindNext(p, s)] == id then
            call UnitAddItem(gHero[p], it)
            set it = null
            return
        endif
        set s = s + 1
    endloop
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
    loop
        exitwhen p >= 8
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
function OnHeroLevel takes nothing returns nothing
    local unit h = GetTriggerUnit()
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

// Compact scoreboard: the title carries game time + wave + castle HP; one row per player = name, level, kills,
// deaths, income (gold per minute from the Bank).
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
    call MultiboardSetTitleText(gBoard, "|cff4fc3ff" + TimeText(gGameTime) + "|r    Wave |cffffcc00" + I2S(gWave) + "|r    Castle |cffffcc00" + castle + "|r")
    set i = 0
    loop
        exitwhen i >= 8
        if gBoardRow[i] > 0 then
            if gHero[i] != null then
                call BoardSet(gBoardRow[i], 1, I2S(GetHeroLevel(gHero[i])))
            else
                call BoardSet(gBoardRow[i], 1, "-")
            endif
            call BoardSet(gBoardRow[i], 2, I2S(gKills[i]))
            call BoardSet(gBoardRow[i], 3, I2S(gDeaths[i]))
            call BoardSet(gBoardRow[i], 4, "|cffffcc00+" + I2S(gIncome[i]) + "|r")
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
    call MultiboardSetColumnCount(gBoard, 5)
    call MultiboardSetItemsStyle(gBoard, true, false)
    call BoardWidth(rows, 0, 0.075)
    call BoardWidth(rows, 1, 0.022)
    call BoardWidth(rows, 2, 0.03)
    call BoardWidth(rows, 3, 0.038)
    call BoardWidth(rows, 4, 0.038)
    call BoardSet(0, 0, "|cffffcc00Player|r")
    call BoardSet(0, 1, "|cffffcc00Lv|r")
    call BoardSet(0, 2, "|cffffcc00Kills|r")
    call BoardSet(0, 3, "|cffffcc00Deaths|r")
    call BoardSet(0, 4, "|cffffcc00Income|r")
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

// Waves come out of the lane's tower; once the tower is destroyed, out of the Nexus (or its ruins).
function SpawnWaveUnit takes integer L, integer ut returns nothing
    local integer d = LaneArm(L)
    local real x = gNexusSpawnX[L]
    local real y = gNexusSpawnY[L]
    local unit u
    if GetWidgetLife(gTower[L]) > 0.405 then
        set x = gTowerSpawnX[L]
        set y = gTowerSpawnY[L]
    endif
    set u = CreateUnit(gInvader[d], ut, x + GetRandomReal(-140.0, 140.0), y + GetRandomReal(-90.0, 90.0), gDirFace[d])
    if L >= 8 then
        // gate level: its bonus HP / damage and colour
        call UnitAddAbility(u, gGateHpAbil[L])
        if gGateDmgAbil[L] != 0 then
            call UnitAddAbility(u, gGateDmgAbil[L])
        endif
        call SetUnitVertexColor(u, gGateTintR[L], gGateTintG[L], gGateTintB[L], 255)
    endif
    call SetUnitUserData(u, L * 16 + 1)
    call SetUnitState(u, UNIT_STATE_LIFE, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    if gWave == 1 then
        call GroupAddUnit(gFirstWave, u)
        set gFirstWaveLeft[L] = gFirstWaveLeft[L] + 1
    endif
    call GroupAddUnit(gWaveUnits, u)
    call IssuePointOrder(u, "attack", gWpX[L * 8 + 1], gWpY[L * 8 + 1])
    set u = null
endfunction

// Standardized waves: the lane STAGE picks the unit types, the wave number only adds units.
// Front line (melee) = 4 + wave, back line (ranged) = wave / 2. Every 10th wave: wave/10 weakened champions.
function SpawnWave takes integer L returns nothing
    local integer d = LaneArm(L)
    local integer st = LaneStage(L)
    local integer front = gFrontBase + gWave
    local integer back = gWave / gBackDiv
    local integer i = 0
    if front > gFrontMax then
        set front = gFrontMax
    endif
    if back > gBackMax then
        set back = gBackMax
    endif
    loop
        exitwhen i >= front
        call SpawnWaveUnit(L, gStageUnit[d * 6 + st * 2])
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= back
        call SpawnWaveUnit(L, gStageUnit[d * 6 + st * 2 + 1])
        set i = i + 1
    endloop
    if ModuloInteger(gWave, gChampEvery) == 0 then
        set i = 0
        loop
            exitwhen i >= gWave / gChampEvery
            call SpawnWaveUnit(L, gWaveChamp[d])
            set i = i + 1
        endloop
    endif
endfunction

function OnWaveTimer takes nothing returns nothing
    local integer L = 0
    if gGameOver then
        return
    endif
    set gWave = gWave + 1
    if gWave == 2 then
        loop
            exitwhen L >= 8
            call GrantLevelTwo(L)
            set L = L + 1
        endloop
        set L = 0
    endif
    loop
        exitwhen L >= 8
        if gLaneActive[L] and (gLaneState[L] == 0 or gLaneState[L] == 1) then
            call SpawnWave(L)
        endif
        set L = L + 1
    endloop
    set L = 8
    loop
        exitwhen L > 11
        if gGateState[L] == 0 or gGateState[L] == 1 then
            call SpawnWave(L)
        endif
        set L = L + 1
    endloop
    call Msg("|cffff4040Wave " + I2S(gWave) + "|r is coming down the lanes!")
    if ModuloInteger(gWave, gChampEvery) == gChampEvery - 1 then
        call Msg("|cffffcc00Champions|r march with the next wave!")
    endif
    call StartSound(bj_questWarningSound)
    // the next countdown only starts once every wave monster is dead (checked in OnTick)
    set gWaitingClear = true
    if gWaveDialog != null then
        call TimerDialogDisplay(gWaveDialog, false)
    endif
    call UpdateBoard()
endfunction

// 30 s between waves, but a 1 min break after every 5th wave.
function NextWaveDelay takes nothing returns real
    if ModuloInteger(gWave, 5) == 0 then
        return gWaveBreak
    endif
    return gWaveInterval
endfunction

// Shopping break (after every 5th wave): announcement + gold pings and effects on the secret grove.
// Wave reward, paid when the wave is CLEARED: 100 gold for wave 1, +50 for every next wave (no cap).
function WaveGold takes nothing returns integer
    return 50 + 50 * gWave
endfunction

function ShoppingTime takes nothing returns nothing
    local integer i = 0
    call Msg("|cffffcc00BREAK - Time to go Shopping!|r   Secret grove (SE).   |cffffcc00+" + I2S(WaveGold()) + " gold|r  |cff80ff80+1 tree|r   Next wave in " + I2S(R2I(gWaveBreak)) + "s.")
    call StartSound(bj_questHintSound)
    loop
        exitwhen i >= gShopFxCount
        call PingMinimapEx(gShopFxX[i], gShopFxY[i], 6.0, 255, 204, 0, true)
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\Resurrect\\ResurrectTarget.mdl", gShopFxX[i], gShopFxY[i]))
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Items\\ResourceItems\\ResourceEffectTarget.mdl", gShopFxX[i], gShopFxY[i]))
        set i = i + 1
    endloop
endfunction

function OnFirstWave takes nothing returns nothing
    call OnWaveTimer()
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
        if best == null and IsUnitEnemy(t, p) and not IsUnitType(t, UNIT_TYPE_DEAD) and not IsUnitType(t, UNIT_TYPE_STRUCTURE) and GetUnitTypeId(t) != 0 then
            set best = t
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    set p = null
    return best
endfunction

function BossCast takes unit boss, string ord, integer kind, unit target returns nothing
    if kind == 0 then
        call IssueImmediateOrder(boss, ord)
    elseif kind == 1 then
        call IssueTargetOrder(boss, ord, target)
    else
        call IssuePointOrder(boss, ord, GetUnitX(target), GetUnitY(target))
    endif
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
        call UnitApplyTimedLife(u, 'BTLF', 40.0)
        call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Undead\\AnimateDead\\AnimateDeadTarget.mdl", GetUnitX(u), GetUnitY(u)))
        set i = i + 1
    endloop
    set u = null
endfunction

function BossTick takes integer L returns nothing
    local integer d = LaneArm(L)
    local unit b = gBoss[L]
    local unit t
    local real dx
    local real dy
    if b == null or GetWidgetLife(b) <= 0.405 then
        set b = null
        return
    endif
    set gBossTick[L] = gBossTick[L] + 1
    set dx = GetUnitX(b) - gNexusX[L]
    set dy = GetUnitY(b) - gNexusY[L]
    // leash: the boss never leaves the ruins of its Nexus for long
    if dx * dx + dy * dy > 1440000.0 then
        call IssuePointOrder(b, "move", gNexusX[L], gNexusY[L])
        set b = null
        return
    endif
    if GetUnitCurrentOrder(b) == OrderId("move") and dx * dx + dy * dy > 90000.0 then
        set b = null
        return
    endif
    set t = BossFindTarget(b, 700.0)
    if t != null then
        if ModuloInteger(gBossTick[L], 10) == 0 then
            call BossCast(b, gBossOrd1[d], gBossKind1[d], t)
        elseif ModuloInteger(gBossTick[L], 14) == 0 then
            call BossCast(b, gBossOrd2[d], gBossKind2[d], t)
        elseif ModuloInteger(gBossTick[L], 30) == 0 then
            call BossSummon(L)
        elseif GetUnitCurrentOrder(b) == 0 then
            call IssueTargetOrder(b, "attack", t)
        endif
    elseif GetUnitCurrentOrder(b) == 0 and dx * dx + dy * dy > 90000.0 then
        call IssuePointOrder(b, "attack", gNexusX[L], gNexusY[L])
    endif
    set b = null
    set t = null
endfunction

//---------------------------------------------------------------------------
// Periodic tick (1 s)
//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
// The Dryad's skills (v2.6). WarCraft 1.27 has no "any unit damaged" event, so every enemy unit (players 8-11) is
// registered on gDmgTrig when it enters the map; DmgRebuild starts a fresh trigger when too many dead units piled up.
//   Extra Spear (gSpearAbil): +1 spear per level at another enemy within gSpearRange of the target, full damage
//   Fire Spears (gFireSkill): +gFirePct % of every hit as extra fire damage per level
// Swift Throw adds hidden attack-speed abilities on learn (OnHeroSkill). gDmgLock stops our own damage re-triggering.
//---------------------------------------------------------------------------
function OnDamaged takes nothing returns nothing
    local unit src = GetEventDamageSource()
    local unit tgt = GetTriggerUnit()
    local real dmg = GetEventDamage()
    local integer p
    local integer n
    local integer f
    local integer o
    local real hit
    local unit u
    if gDmgLock or src == null or dmg <= 0.0 then
        set src = null
        set tgt = null
        return
    endif
    set p = GetPlayerId(GetOwningPlayer(src))
    if p >= 8 or src != gHero[p] then
        set src = null
        set tgt = null
        return
    endif
    set n = GetUnitAbilityLevel(src, gSpearAbil)
    set f = GetUnitAbilityLevel(src, gFireSkill)
    set hit = dmg * (1.0 + I2R(gFirePct * f) / 100.0)
    set gDmgLock = true
    if f > 0 then
        call UnitDamageTarget(src, tgt, hit - dmg, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
    endif
    if n > 0 then
        call GroupEnumUnitsInRange(gDmgGroup, GetUnitX(tgt), GetUnitY(tgt), gSpearRange, null)
        loop
            set u = FirstOfGroup(gDmgGroup)
            exitwhen u == null or n <= 0
            call GroupRemoveUnit(gDmgGroup, u)
            set o = GetPlayerId(GetOwningPlayer(u))
            if u != tgt and o >= 8 and o <= 11 and GetWidgetLife(u) > 0.405 then
                call UnitDamageTarget(src, u, hit, true, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
                if f > 0 then
                    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Weapons\\FireBallMissile\\FireBallMissile.mdl", u, "chest"))
                else
                    call DestroyEffect(AddSpecialEffectTarget("Abilities\\Weapons\\Dryadmissile\\Dryadmissile.mdl", u, "chest"))
                endif
                set n = n - 1
            endif
        endloop
        call GroupClear(gDmgGroup)
    endif
    set gDmgLock = false
    set src = null
    set tgt = null
    set u = null
endfunction

function DmgRebuild takes nothing returns nothing
    local group g = CreateGroup()
    local rect r = GetWorldBounds()
    local unit u
    local integer o
    if gDmgTrig != null then
        call DestroyTrigger(gDmgTrig)
    endif
    set gDmgTrig = CreateTrigger()
    call TriggerAddAction(gDmgTrig, function OnDamaged)
    set gDmgRegs = 0
    call GroupEnumUnitsInRect(g, r, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        set o = GetPlayerId(GetOwningPlayer(u))
        if o >= 8 and o <= 11 and GetWidgetLife(u) > 0.405 then
            call TriggerRegisterUnitEvent(gDmgTrig, u, EVENT_UNIT_DAMAGED)
            set gDmgRegs = gDmgRegs + 1
        endif
    endloop
    call DestroyGroup(g)
    call RemoveRect(r)
    set g = null
    set r = null
endfunction

function OnEnterMap takes nothing returns nothing
    local integer o = GetPlayerId(GetOwningPlayer(GetTriggerUnit()))
    if o >= 8 and o <= 11 and gDmgTrig != null then
        call TriggerRegisterUnitEvent(gDmgTrig, GetTriggerUnit(), EVENT_UNIT_DAMAGED)
        set gDmgRegs = gDmgRegs + 1
    endif
endfunction

function OnHeroSkill takes nothing returns nothing
    local integer L = GetLearnedSkillLevel()
    if GetLearnedSkill() == gSwiftSkill and L >= 1 and L <= 5 then
        call UnitAddAbility(GetTriggerUnit(), gSwiftAbil[L])
    elseif GetLearnedSkill() == gFireSkill and L == 1 then
        call UnitAddAbility(GetTriggerUnit(), gFireOrb)
    endif
endfunction

function OnTick takes nothing returns nothing
    local integer L = 0
    set gElapsed = gElapsed + 1
    if gDmgRegs > 3000 then
        call DmgRebuild()
    endif
    if gStarted and not gGameOver then
        set gGameTime = gGameTime + 1     // game clock: from the end of champion select, stops at the end
        if ModuloInteger(gGameTime, 60) == 0 then
            call IncomeTick()             // bank income is paid on every full minute of the game clock (1:00, 2:00, ...)
        endif
    endif
    call ForGroup(gWaveUnits, function WaveUnitTick)
    if gWaitingClear and not gGameOver and CountUnitsInGroup(gWaveUnits) == 0 then
        set gWaitingClear = false
        call TimerStart(gWaveTimer, NextWaveDelay(), false, function OnWaveTimer)
        call TimerDialogDisplay(gWaveDialog, true)
        // every cleared wave pays its gold + 1 tree (lumber) to every player
        call GiveAllGold(WaveGold())
        set L = 0
        loop
            exitwhen L >= 8
            if IsPlaying(L) then
                call SetPlayerState(Player(L), PLAYER_STATE_RESOURCE_LUMBER, GetPlayerState(Player(L), PLAYER_STATE_RESOURCE_LUMBER) + 1)
            endif
            set L = L + 1
        endloop
        set L = 0
        if ModuloInteger(gWave, 5) == 0 then
            call ShoppingTime()
        else
            call Msg("|cff40ff40All monsters dead!|r  |cffffcc00+" + I2S(WaveGold()) + " gold|r  |cff80ff80+1 tree|r   Next wave in " + I2S(R2I(gWaveInterval)) + "s.")
        endif
    endif
    loop
        exitwhen L > 11
        if (L < 8 and gLaneState[L] == 1) or (L >= 8 and gGateState[L] == 1) then
            call BossTick(L)
        endif
        set L = L + 1
    endloop
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
    set gWaitingClear = false
    call PauseTimer(gWaveTimer)
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
    call Msg("|cff40ff40VICTORY!|r  Every Nexus is rubble, every boss is dead and the castle still stands!")
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

// Any lane still sending waves? (tower/Nexus standing, or Nexus down but its boss alive, or the Dark Gate open)
function AnyNexusLeft takes nothing returns boolean
    local integer L = 0
    loop
        exitwhen L > 11
        if L >= 8 and (gGateState[L] == 0 or gGateState[L] == 1) then
            return true
        endif
        set L = L + 1
    endloop
    set L = 0
    loop
        exitwhen L >= 8
        if gLaneState[L] == 0 or gLaneState[L] == 1 then
            return true
        endif
        set L = L + 1
    endloop
    return false
endfunction

// A lane's tower fell: a Protector (the faction champion, bigger) guards the Nexus, and that lane's next wave
// comes at once - already the stronger Nexus wave. Works for the Dark Gate (lane 8) too.
function OnTowerDestroyed takes integer L returns nothing
    local integer d = LaneArm(L)
    local real x = (gTowerX[L] + gNexusX[L]) * 0.5
    local real y = (gTowerY[L] + gNexusY[L]) * 0.5
    local unit p = CreateUnit(gInvader[d], gChampion[d], x, y, gDirFace[d])
    call UnitAddAbility(p, 'AIl2')
    call UnitAddAbility(p, 'AIlf')
    call SetUnitScale(p, 1.5, 1.5, 1.5)
    call SetUnitVertexColor(p, 255, 220, 120, 255)
    if L >= 8 then
        // gate Protector: the level's bonus HP / damage and colour
        call UnitAddAbility(p, gGateHpAbil[L])
        if gGateDmgAbil[L] != 0 then
            call UnitAddAbility(p, gGateDmgAbil[L])
        endif
        call SetUnitScale(p, 1.8, 1.8, 1.8)
        call SetUnitVertexColor(p, gGateTintR[L], gGateTintG[L], gGateTintB[L], 255)
    endif
    call SetWidgetLife(p, GetUnitState(p, UNIT_STATE_MAX_LIFE))
    set gProtector[L] = p
    set gProtX[L] = x
    set gProtY[L] = y
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Undead\\AnimateDead\\AnimateDeadTarget.mdl", x, y))
    call PingMinimap(x, y, 3.0)
    if L >= 8 then
        call Msg("The " + gDirColor[d] + gTurretName[d] + "|r has fallen!  A |cffffcc00Protector|r guards the " + gBaseName[d] + " - the next wave comes NOW, stronger!")
    else
        call Msg(gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r's " + gTurretName[d] + " has fallen!  A |cffffcc00Protector|r guards the Nexus - the next wave comes NOW, stronger!")
    endif
    if not gGameOver then
        call SpawnWave(L)
    endif
    set p = null
endfunction

// Protectors stay at their Nexus (leash, from OnTick).
function ProtectorTick takes nothing returns nothing
    local integer L = 0
    local real dx
    local real dy
    loop
        exitwhen L > 11
        if gProtector[L] != null then
            if GetWidgetLife(gProtector[L]) <= 0.405 then
                set gProtector[L] = null
            else
                set dx = GetUnitX(gProtector[L]) - gProtX[L]
                set dy = GetUnitY(gProtector[L]) - gProtY[L]
                if dx * dx + dy * dy > 810000.0 then
                    call IssuePointOrder(gProtector[L], "move", gProtX[L], gProtY[L])
                endif
            endif
        endif
        set L = L + 1
    endloop
endfunction

//---------------------------------------------------------------------------
// Gate levels: LEVEL 2 = the Dark Gate (lane 8, NE) opens when the first player destroys his Nexus;
// LEVEL 3 = the Frozen Gate (lane 9, NW) opens when the Dark Citadel falls. gGateState: -1 closed, 0 open, 2 done.
//---------------------------------------------------------------------------
function OpenGateLane takes integer L returns nothing
    local integer d = LaneArm(L)
    if gGateState[L] != -1 or gGameOver then
        return
    endif
    set gGateState[L] = 0
    call SetDestructableInvulnerable(gGate[L], false)
    call ModifyGateBJ(bj_GATEOPERATION_OPEN, gGate[L])
    set gTower[L] = CreateUnit(gInvader[d], gTurretType[d], gTowerX[L], gTowerY[L], gDirFace[d])
    set gNexus[L] = CreateUnit(gInvader[d], gBaseType[d], gNexusX[L], gNexusY[L], gDirFace[d])
    call PingMinimapEx(gGateX[L], gGateY[L], 6.0, 255, 60, 60, true)
    call PingMinimapEx(gNexusX[L], gNexusY[L], 6.0, 255, 60, 60, true)
    call StartSound(bj_questWarningSound)
    call Msg(gDirColor[d] + "LEVEL " + I2S(L - 6) + ":|r " + gDirColor[d] + gFactionName[d] + "|r is open (" + gGateDir[L] + ")!  Stronger monsters, " + I2S(L - 6) + "x gold per kill!")
endfunction

// A gate's Nexus fell: its boss rises from the ruins (the level is done when the boss dies), waves keep coming
// from the ruins, and the next level opens.
function OnGateNexusDestroyed takes integer L returns nothing
    local integer d = LaneArm(L)
    set gGateState[L] = 1
    set gBossTick[L] = 0
    set gBoss[L] = CreateUnit(gInvader[d], gBossType[d * 3 + 1], gNexusX[L], gNexusY[L], gDirFace[d])
    call DestroyEffect(AddSpecialEffect("Objects\\Spawnmodels\\Other\\NeutralBuildingExplosion\\NeutralBuildingExplosion.mdl", gNexusX[L], gNexusY[L]))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\MassTeleport\\MassTeleportTarget.mdl", gNexusX[L], gNexusY[L]))
    call PingMinimap(gNexusX[L], gNexusY[L], 6.0)
    call StartSound(bj_questWarningSound)
    call Msg("|cff40ff40The " + gBaseName[d] + " is destroyed!|r  From its ruins rises " + gDirColor[d] + gBossName[d] + "|r!   |cffffcc00+" + I2S(gGateGold[L]) + " gold|r")
    call GiveAllGold(gGateGold[L])
    if L < 11 then
        call OpenGateLane(L + 1)
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
    if not AnyNexusLeft() then
        set gWaitingClear = false
        call PauseTimer(gWaveTimer)
        call TimerDialogDisplay(gWaveDialog, false)
    endif
    call UpdateBoard()
    call CheckVictory()
endfunction

// Minion kill gold (wave units only; their built-in bounty is 0): gold = wave number on the player lanes,
// x level on the gate lanes (Level 2 x2 ... Level 5 x5). Floating +N only the killer sees.
function MinionBounty takes unit u, integer kid returns nothing
    local integer g = gWave
    local texttag tt = CreateTextTag()
    if GetUnitUserData(u) / 16 >= 8 then
        set g = (GetUnitUserData(u) / 16 - 6) * gWave
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
    call OpenGateLane(8)
    set gLaneState[L] = 1
    set gBossTick[L] = 0
    set gBoss[L] = CreateUnit(gInvader[d], gBossType[d * 3 + 1], gNexusX[L], gNexusY[L], gDirFace[d])
    call DestroyEffect(AddSpecialEffect("Objects\\Spawnmodels\\Other\\NeutralBuildingExplosion\\NeutralBuildingExplosion.mdl", gNexusX[L], gNexusY[L]))
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\MassTeleport\\MassTeleportTarget.mdl", gNexusX[L], gNexusY[L]))
    call PingMinimap(gNexusX[L], gNexusY[L], 6.0)
    call StartSound(bj_questWarningSound)
    call Msg(gPlayerColorCode[L] + GetPlayerName(Player(L)) + "|r destroyed the " + gBaseName[d] + "!   From its ruins rises " + gDirColor[d] + gBossName[d] + "|r!  Kill it!   |cffffcc00+150 gold|r")
    call GiveAllGold(150)
    if not AnyNexusLeft() then
        set gWaitingClear = false
        call PauseTimer(gWaveTimer)
        call TimerDialogDisplay(gWaveDialog, false)
        call Msg("No Nexus is left - no more waves. Kill the remaining bosses!")
    endif
    call UpdateBoard()
endfunction

function OnBossSlain takes integer L returns nothing
    local integer d = LaneArm(L)
    set gLaneState[L] = 2
    set gBoss[L] = null
    call DropEpic(1, gNexusX[L], gNexusY[L])
    call GiveAllGold(250)
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
            call ReviveHero(gHero[p], gHeroX[p], gHeroY[p], true)
            call TimerDialogDisplay(gReviveDialog[p], false)
            call PanCameraToTimedForPlayer(Player(p), gHeroX[p], gHeroY[p], 0.5)
            call SelectUnitForPlayerSingle(gHero[p], Player(p))
            if gFollow[p] then
                call SetCameraTargetControllerNoZForPlayer(Player(p), gHero[p], 0.0, 0.0, false)
            endif
            call PingLane(p)
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
    if u == gCastle then
        call OnCastleDestroyed()
    elseif oid >= 8 and oid <= 11 then
        set d = oid - 8
        if kid >= 0 and kid < 8 then
            set gKills[kid] = gKills[kid] + 1
            if GetUnitUserData(u) > 0 and GetUnitUserData(u) < 192 then
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
            endif
            set L = L + 1
        endloop
    elseif oid < 8 and u == gHero[oid] then
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
    call AddQuest("Defend your lane", "Pick a champion: click a hall and click a hero. You then defend |cffffcc00your own lane|r - every player has one lane, and a lane only sends monsters when its player is in the game.\n\nThe next wave comes 10 s after all monsters of the last one are dead (2 min shopping break after every 5th wave). Keep the |cffffcc00Castle of Lordaeron|r alive - if it falls, everyone loses.", "ReplaceableTextures\\CommandButtons\\BTNCastle.blp", true)
    call AddQuest("Destroy your Nexus", "At the end of |cffffcc00your lane|r stands your own enemy Nexus, guarded by a strong tower. The Nexus sends the waves of your lane. Destroy it and your lane goes quiet - but its boss rises from the ruins.", "ReplaceableTextures\\CommandButtons\\BTNDemonGate.blp", true)
    call AddQuest("Slay the bosses", "Kill the boss of every lane to |cff40ff40win|r. Help your friends with theirs!", "ReplaceableTextures\\CommandButtons\\BTNPitLord.blp", true)
    call AddQuest("Tips", "- Killing monsters gives gold and experience; every wave also pays gold.\n- |cffffcc00Secret grove|r: the narrow passage at the south-east corner of the plaza leads to the Fountain of Power (HP + mana), the Premium Armory (1000-gold items) and the Apothecary.\n- Your champion appears and revives on the circle in your colour at your lane - click the circle to |cffffcc00buy stats|r instantly (each buy costs 10% more).\n- Type |cffffcc00-help|r for the command list.\n- |cffffcc00Space|r = jump to your champion (hold to keep him centred); |cffffcc00Esc|r or -cam = camera follows him.\n- Spells are on |cffffcc00Q W E R|r. Clearing your first wave gives level 2.\n- Staff of Teleportation lets you jump back to the castle or to a friend.\n- Type |cffffcc00-zoom 250|r to zoom out (any value, e.g. -zoom 200; -zoom 165 = normal).", "ReplaceableTextures\\CommandButtons\\BTNSnazzyScroll.blp", false)
endfunction

//---------------------------------------------------------------------------
// Self-test (only in the *_TEST build): revealed map + scripted run through
// base -> lord -> victory.
//---------------------------------------------------------------------------
function TestKillEnum takes nothing returns nothing
    call KillUnit(GetEnumUnit())
endfunction

function TestStep takes nothing returns nothing
    local integer L
    set gTestClock = gTestClock + 5
    call Msg("|cff00ffff[TEST]|r t=" + I2S(gTestClock) + "  wave=" + I2S(gWave))
    if gTestClock == 5 then
        call FogEnable(false)
        call FogMaskEnable(false)
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
    elseif gTestClock == 15 then
        if IssueImmediateOrderById(gLaneMarker[0], gStatItem[1]) then
            call Msg("[TEST] tome #2 via shop order: accepted")
        elseif IssueNeutralImmediateOrderById(Player(0), gLaneMarker[0], gStatItem[1]) then
            call Msg("[TEST] tome #2 via neutral order: accepted")
        else
            call Msg("|cffff0000[TEST] tome #2: both orders REJECTED|r")
        endif
    elseif gTestClock == 30 then
        call SetPlayerState(Player(0), PLAYER_STATE_RESOURCE_LUMBER, 5)
        call SelectUnitForPlayerSingle(gCastle, Player(0))
        if IssueNeutralImmediateOrderById(Player(0), gCastle, gStatItem[9 * 64]) then
            call Msg("[TEST] castle buy via neutral order: accepted")
        elseif IssueImmediateOrderById(gCastle, gStatItem[9 * 64]) then
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
    elseif gTestClock == 25 then
        if gTestRound == 0 then
            set gTestRound = 1
            call ExecuteFunc("CDRestart")
            return
        endif
        call KillUnit(gTower[0])
    elseif gTestClock == 35 then
        call KillUnit(gNexus[0])
    elseif gTestClock == 40 then
        call PanCameraToTimed(gGateX[8] + 800.0, gGateY[8], 0.0)
        call Msg("[TEST] gate states L2=" + I2S(gGateState[8]) + " L3=" + I2S(gGateState[9]) + "   income=" + I2S(gIncome[0]) + "   Fang Lv2 slot=" + I2S(GetInventoryIndexOfItemTypeBJ(gHero[0], gPremItem[2])) + "   reach=" + I2S(GetPlayerTechCount(Player(0), gReachTech, true)))
    elseif gTestClock == 45 then
        call KillUnit(gBoss[0])
    elseif gTestClock == 50 then
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
    elseif gTestClock >= 60 and gTestClock <= 75 then
        // one gate level per step: kill the previous level's boss, then this level's tower + Nexus (boss rises)
        set L = 8 + (gTestClock - 60) / 5
        call Msg("[TEST] gates L2=" + I2S(gGateState[8]) + " L3=" + I2S(gGateState[9]) + " L4=" + I2S(gGateState[10]) + " L5=" + I2S(gGateState[11]))
        if gBoss[L] != null then
            call KillUnit(gBoss[L])
        endif
        if L < 11 then
            call PanCameraToTimed(gNexusX[L + 1], gNexusY[L + 1], 0.0)
            call KillUnit(gTower[L + 1])
            call KillUnit(gNexus[L + 1])
        endif
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
    loop
        exitwhen i >= 8
        set gLaneActive[i] = IsPlaying(i)
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= 8
        if gLaneActive[i] then
            call SetDestructableInvulnerable(gGate[i], false)
            call ModifyGateBJ(bj_GATEOPERATION_OPEN, gGate[i])
        endif
        set i = i + 1
    endloop
    set i = 0
    loop
        exitwhen i >= 8
        if gLaneActive[i] then
            call CreateLaneBase(i)
        else
            set gLaneState[i] = -1
        endif
        set i = i + 1
    endloop
    call TimerStart(gWaveTimer, gFirstWaveDelay, false, function OnFirstWave)
    if gWaveDialog == null then
        set gWaveDialog = CreateTimerDialog(gWaveTimer)
        call TimerDialogSetTitle(gWaveDialog, "Next wave in")
    endif
    call TimerDialogDisplay(gWaveDialog, true)
    if not gTickStarted then
        set gTickStarted = true
        call TimerStart(CreateTimer(), 1.0, true, function OnTick)
        if gTestMode then
            call TimerStart(CreateTimer(), 5.0, true, function TestStep)
        endif
    endif
    call CreateBoard()
    call Msg("|cffffcc00Defend your lane!|r   |cffffcc00-help|r = commands")
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
            call SetTextTagPos(tt, gHallX - 470.0, gHallY + 620.0, 0.0)
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
    // any number of players may play the same champion (6 champions, up to 8 players)
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

function OnUnitSold takes nothing returns nothing
    local unit h = GetSoldUnit()
    local integer p = GetPlayerId(GetOwningPlayer(h))
    if gSelecting and p < 8 and IsUnitType(h, UNIT_TYPE_HERO) and gHero[p] == null then
        call AssignHero(p, h)
        if AllChosen() then
            call EndChampionSelect()
        endif
    endif
    set h = null
endfunction

// Test build: player 1 buys a hero through the real tavern sale path.
function TestBuyOrder takes nothing returns nothing
    if IssueNeutralImmediateOrderById(Player(0), gTavern[0], gHeroPool[0]) then
        call Msg("[TEST] P1 buy champion #1 from the Hall of Champions: accepted")
    else
        call Msg("|cffff0000[TEST] P1 buy champion #1 from the Hall of Champions: REJECTED|r")
    endif
endfunction

function TestBuyHero takes nothing returns nothing
    call TimerStart(CreateTimer(), 2.0, false, function TestBuyOrder)
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
            set gSoul[i] = CreateUnit(Player(i), gSoulType, gHallX, gHallY, 90.0)
            call SetPlayerState(Player(i), PLAYER_STATE_RESOURCE_HERO_TOKENS, 1)
            call SetPlayerTechMaxAllowed(Player(i), 'HERO', 1)
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
    set gWaitingClear = false
    call PauseTimer(gWaveTimer)
    call PauseTimer(gSelectTimer)
    if gWaveDialog != null then
        call TimerDialogDisplay(gWaveDialog, false)
    endif
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
        set j = 0
        loop
            exitwhen j >= gHeroPoolCount
            call SetPlayerTechMaxAllowed(Player(i), gHeroPool[j], 1)
            set j = j + 1
        endloop
        call ModifyGateBJ(bj_GATEOPERATION_CLOSE, gGate[i])
        call SetDestructableInvulnerable(gGate[i], true)
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
        call ModifyGateBJ(bj_GATEOPERATION_CLOSE, gGate[j])
        call SetDestructableInvulnerable(gGate[j], true)
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
    set gWave = 0
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
//   -break 60   shopping-break length (5-300 s)      -wave 5   seconds between waves (1-60 s)
// Without a number they show the current value. A running countdown that is longer is shortened at once.
//---------------------------------------------------------------------------
function OnConfigChat takes nothing returns nothing
    local player p = GetTriggerPlayer()
    local string m = GetEventPlayerChatString()
    local string who = gPlayerColorCode[GetPlayerId(p)] + GetPlayerName(p) + "|r"
    local integer n
    local boolean isBreak = SubString(m, 0, 6) == "-break"
    if not isBreak and SubString(m, 0, 5) != "-wave" then
        set p = null
        return
    endif
    if isBreak then
        set n = DevArg(m, 6, -1)
    else
        set n = DevArg(m, 5, -1)
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
        if n < 1 then
            set n = 1
        elseif n > 60 then
            set n = 60
        endif
        set gWaveInterval = I2R(n)
        call Msg(who + " set the wave gap to |cffffcc00" + I2S(n) + "s|r")
    endif
    // a countdown that is running now gets shortened if it is longer than the new setting
    if gStarted and not gGameOver and not gWaitingClear and gWave > 0 and TimerGetRemaining(gWaveTimer) > NextWaveDelay() then
        call TimerStart(gWaveTimer, NextWaveDelay(), false, function OnWaveTimer)
    endif
    set p = null
endfunction

function InitGame takes nothing returns nothing
    local trigger t
    local integer i = 0
    local region rg
    local rect rr
    call InitData()
    set gKingdom = Player(14)
    set gWaveUnits = CreateGroup()
    set gFirstWave = CreateGroup()
    set gWaveTimer = CreateTimer()
    set gSelectTimer = CreateTimer()
    call SetupAlliances()
    call SetupDarkness()
    call EnumDestructablesInRect(GetWorldBounds(), null, function MakeWallInvulnerable)
    call FogEnable(false)
    call FogMaskEnable(false)
    loop
        exitwhen i > 11
        set gGate[i] = CreateDestructable(gGateType[i], gGateX[i], gGateY[i], gGateFace[i], 1.0, 0)
        call SetDestructableInvulnerable(gGate[i], true)
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
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_HERO_SKILL)
    call TriggerAddAction(t, function OnHeroSkill)
    set rg = CreateRegion()
    set rr = GetWorldBounds()
    call RegionAddRect(rg, rr)
    call RemoveRect(rr)
    set t = CreateTrigger()
    call TriggerRegisterEnterRegion(t, rg, null)
    call TriggerAddAction(t, function OnEnterMap)
    call DmgRebuild()
    call CreateQuests()
    call TimerStart(CreateTimer(), 0.5, false, function SetupChampionSelect)
    set t = null
endfunction
