# WarCraft III 1.27 gotchas (all hit for real on this map)

## Crashes and silent failures

- **A data block silently vanished from `InitData`** (a big search-and-replace in `build.py` swallowed it): the map
  compiled and ran, but Bank buys and premium upgrades did nothing because their ids were 0. `check_script_data`
  now fails the build when a required block is missing — add new data blocks to `REQUIRED_SCRIPT_DATA`.

- **A custom object must be based on a real object of the same kind.** An item based on an ability id
  (`AIlf`) built fine and crashed the game (ACCESS_VIOLATION) right after the loading screen.
  `build.py:check_object_bases` now fails the build instead.
- `Crash.txt` in `BlizzardError` only says ACCESS_VIOLATION. Bisect by building variants.
- `UnitAddAbility` with an id the unit already has does nothing. Item-bonus abilities stack only with
  **distinct ids** → one ability id per price step (`XhNN`…), and castle steps are global.
- Heroes can take over wave monsters (Dark Ranger Charm, Banshee Possession): the unit changes owner but keeps
  its group/userdata. Everything that tracks wave units must check the owner (`ReleaseWaveUnit`), or the wave
  never counts as cleared and the unit keeps getting lane orders.
- JASS: a function must be defined before use; don't reuse native names (`RestartGame` is a native).
- **A scaled-down dummy shoots scaled-down missiles** when its base unit has "Art - Scale Projectiles" (`uscb`,
  UnitUI `scaleBull`) = 1 — the Archer (`earc`) and most ranged units do. The 0.01-scale spear dummy hit fine (damage
  events, self-test PASS) but its spear was 1 % size = invisible ("the extra spear has no animation", v3.5). Fix:
  full scale, `uscb` 0, and `SetUnitVertexColor(d, 255, 255, 255, 0)` right after `CreateUnit` (same thread → never
  drawn).
- **`CreateUnit` puts a unit on the nearest FREE pathable spot, ignoring walls.** A wave too big for its spawn spot
  spills onto any floor nearby, even a separate walled room: monsters showed up in the Hall of Champions, 512 from the
  Frozen Gate tower spawn (most likely this; v3.8 moved the hall 2300+ away from every spawn). Keep separate rooms
  well away from spawn points.
- **All stuns players can apply use one buff:** Storm Bolt, War Stomp, Bash (also the item) = `BPSE` in AbilityData
  (Inferno `BNin`). Removing it with `UnitRemoveAbility` on a fast timer = stun immunity.
- **Max HP / damage / armor can't be set in 1.27:** item-bonus abilities with distinct ids stack, so binary "bit" abilities
  add any amount (`FinalBits`); keep the HP % yourself, removing a bit clamps the life.
- **Never kill an attack dummy — remove it.** A transparent dying Archer still plays its death scream and blood: those
  are model events, `usnd` "" doesn't stop them. The old spear dummies were removed with `RemoveUnit` (both gone since v4.3: the Dryad throws with the native ability).
- **A dummy whose target dies before its damage point re-acquires** anything within its acquisition range (the
  cancelled attack doesn't start the cooldown) — the 2000-range spear dummy shot far towers. Keep dummy ranges short,
  give it damage point 0, remember its assigned target and stop it in `EVENT_PLAYER_UNIT_ATTACKED` if it attacks
  anything else (that event fires when the attack starts, before the missile).
- **`EVENT_PLAYER_UNIT_ATTACKED` fires at the START of an attack**, before the damage point, and again on every
  restart (stop-spam, cancelled swings). Anything that must happen with the real release (extra missiles) waits for
  `damage point / attack speed` (2 % per agility, item and skill bonuses, capped at +400 %) and is cancelled by a new
  point / immediate order.

## Shops and items

- `EVENT_PLAYER_UNIT_SELL_ITEM` does **not** fire for player-owned shops → react to PICKUP/USE item events.
- Scripted buy from an owned shop: `IssueImmediateOrderById(shop, itemId)`; neutral shop:
  `IssueNeutralImmediateOrderById(player, shop, itemId)`.
- Research/upgrades are queued with a progress bar, never instant → use power-up items + abilities.
- Items without `ubpx/ubpy` share their base item's button position, so the shop reshuffles them after
  every restock. Give every sold item an explicit slot.
- Buying a **permanent** item from a neutral shop fires **no** "picked up" event (power-ups fire "used", which is why
  tomes and castle upgrades worked) — premium-item merges never ran. A **remote** purchase from a neutral shop (buyer
  far away, large `Aneu` radius) even leaves the item on the ground at the shop. `EVENT_PLAYER_UNIT_SELL_ITEM` does fire
  for neutral shops, but ⚠️ **never `UnitAddItem` the sold item inside it** (verified in-game, v3.3): when the buyer is in
  range the game delivers the item right AFTER the event, so adding it too puts the **same item handle into two
  inventory slots** (1 potion order = 2 slots; a merge sweep then deleted it; 1 premium buy counted as 2 levels).
  `OnItemSold` only queues the item; `PendingTick` (0.2 s) hands over what is still on the ground and not owned
  (`IsItemOwned`). Merges (`MergePremium`, `MergePotions`) run in the 0.2 s `GrabTick` sweep and skip `ib == ia`.
- A neutral shop **refuses a normal item when the buyer's inventory is full** (6 items), even one that would stack;
  a **power-up** is still sold (verified in-game, v3.4) → potions are sold as power-up tokens (`GivePotion`).
- A neutral shop sells to the player's **closest unit with an inventory** — in the self-test, extra heroes of the
  same player took the purchases (so test champions belong to an empty slot, player 2). With the champion dead and no
  other inventory unit the order is refused (nothing paid). Right after `ReviveHero` shop orders are refused for ~1 s.
- The Preload file writer (`PreloadGenEnd("TestResults\\x.txt")`) writes under
  `<game>/CustomMapData/` (`CustomMapData/TestResults/cd_test.txt`), not the game root.
- **Who counts as a shop's buyer, measured (v4.5):** with no living inventory unit in range every button of a neutral shop is grey and its tooltip says "Requires: Nearby Patron". A non-hero with `AInv` in range lifts that, also with its sight at 0 and the fog on. **Hidden (`ShowUnit` false) or with Locust (`Aloc`) it does not count**, the order is refused. A buyer standing near the shop gets a normal item straight into its bag and is refused when that bag is full; a power-up is used at once. Runs `20261102-231632-a-d514`, `20261102-231939-a-8959`, `20261102-232903-a-2ae1`.
- A player buys from an allied player's shop through `Aall` (Shop Sharing); its `Neu1`/`aran` set the radius.
- Tavern heroes: `usst` = 0 or they unlock only after 120–135 s; `ureq` = "" or the Altar (`TALT`) requirement
  greys out the neutral tavern; a scripted tavern buy needs ~2 s after the buyer unit is placed.

## Script and UI

- `|n` is a line break only in object-data text (tooltips). In script strings (messages, quests) it prints
  literally → use `\n`, or one `DisplayTimedTextToPlayer` per line.
- 1.27 scripts can't detect Space; only arrow keys and Esc (`EVENT_PLAYER_END_CINEMATIC`).
  Space jumps to the "quick position" → keep it on the hero with `SetCameraQuickPosition` (local, 0.1 s).
- Text tags are anchored at their left edge (centre by shifting x by half the text width).
- An open dialog pauses a single-player game (tests!).

## Lobby and map info

- All slots on one team → "You must have an opponent". The invaders are fixed computer players (w3i type 2)
  in a second force with the fixed-player-settings flag 0x20, so the host can't remove or edit them.
- HM3W header "max players" = **human** slots only (8). Writing 12 made the computers open, editable slots.
- w3i version 25; force flags 0x01 allied, 0x02 allied victory, 0x08 shared vision.
  Camera bounds = playable area ± margins (L/R 512, B/T 256).

## File formats (checked against the official 1.27 maps)

- w3e v11; boundary = bit 0x4000 of the water-level word; tile variation follows WE's distribution.
- doo v8 / subversion 11, 50 bytes per entry. **Doodad pathing exists only in the wpm** → walls are abyss
  cells in the wpm with wall destructables on top as visuals.
- w3u/w3t v2: original-table entries `id + 0000`, end token 0. w3a/w3q use the level format
  (id, type, level, data pointer, value, 0).
- Minimap (`war3mapMap.blp`) and `war3map.mmp` cover the **playable** area.
- Paletted BLP1 = 156-byte header + 256 BGRA palette (alpha byte 0) + per mip [indices][alpha]. The first mip
  offset is exactly 1180. A writer that said 1184 still "worked" for the minimap/loading screen (4-pixel shift),
  but command-button icons with a mip chain became **solid green** (the last mip pointed past the end of the file).
- An Orb of Fire copy (`AIfb`) gives the attack **splash** even with 0 bonus damage and area 0 (the Dryad's v2.6–v3.1
  fire orb) — don't use orbs just for the missile look.
- An icon path that does not exist also shows as a **solid green** square (Shadow Crown → `BTNCrownOfKings`, which
  1.27 does not have; Crown of Kings uses `BTNHelmutPurple`). `build.py:check_icons` now fails the build.
- `war3mapUnits.doo` is ignored (units come from the script). Custom unit ids start lowercase (uppercase = hero).

## Loading screen

- Replace the MP loading screen by importing
  `UI\Glues\Loading\Multiplayer\Loading-{TopLeft,Human-TopRight,BotLeft,Human-BotRight}.blp`.
- The game stretches the 4:3 image to 16:9 and draws the player list over the left ~62 % → lay the art out on
  a 16:9 canvas, far right. Keep the background **flat**: the 4 tiles are filtered separately, so any colour
  change across a tile edge shows as a seam.

## Playing on several monitors

- **A fullscreen game can open on the wrong monitor and stay there.** GNOME on Wayland, Wine, no `-window`: no title bar, the game holds the mouse, so it can't be dragged. Seen 2026-11-01 on pc1, on the left monitor although the middle one is primary; why it picked left is not proven. `xdotool windowmove <id> 1920 0` moved the running game, fullscreen and with focus, and it stayed there. On pc1, `~/.local/bin/war3` (not in this repo) starts the game and does this. Moving the running game is verified, a fresh start through `war3` is not.

## Measuring

- **The Preload writer cuts a line at 259 characters.** Long log lines lost their last fields without any error: one record = several short lines.
- `CountUnitsInGroup(gWaveUnits)` counts the dead too, until the next 1 s tick, which also starts the next wave. To see the moment a wave is cleared, count the living.
- A unit of a model with two attacks: `uaen = 1` leaves attack 1 only, and attack 1 may be useless (`nbal` hits air only, `nhyc` no structures). Set `ua1g` too.

## Game install / Wine

- **A single-player game pauses when its window loses focus** (most likely cause: the clock froze at 0:11 for a whole
  self-test run while the owner used the PC, with no crash and no results). `tools/test_env.py` therefore runs the game
  in a Wine virtual desktop on its own Xvfb, where nothing takes the focus away.

- **Never overwrite a map file in place while WC3 runs**: the game keeps the MPQ open and reads it lazily, and
  a rewritten file crashes it with "Not enough memory — SFile.cpp line 898". `build.py` installs by copying to
  `*.tmp` and renaming over the old file (the running game keeps the old inode); the new map loads next game.
- **Never rename the launchers** (`Frozen Throne.exe` etc.): a renamed launcher fails with a fake
  "insert CD" error.
- A second `war3.exe` launch in the same Wine prefix silently attaches to the running instance, and "Warcraft III is already
  running" is a text of `Warcraft III.exe`. A second prefix has its own wineserver and named objects, so both run → [test-env.md](test-env.md).
- **The game goes through DXVK (`d3d8.dll`, `d3d9.dll` in its folder), and wined3d crawled at 2.5 FPS.** On Xvfb it runs on software Vulkan: `VK_DRIVER_FILES` = lavapipe
  (the whole self-test in about 3 min at 800x600). DXVK is a Windows DLL: a Unix `DXVK_LOG_PATH` does not work, its log goes to stderr.
- Wine keeps a server's socket in `/run/user/<uid>/wine/server-<dev>-<inode of the prefix>`, ignoring `XDG_RUNTIME_DIR`: the prefix's inode is what separates two servers.
- `/bin/sleep` is a Rust coreutils multi-call binary, so a copy under another name dies at once. A stand-in for the game must be a script.
- A fresh prefix links `Documents`, `Desktop` etc. to `$HOME`, and `z:` to `/`. With a private `HOME` they are real folders; `z:` must be deleted. It stays deleted. A prefix is still not a filesystem sandbox.
- In `-loadfile` mode slot 2 becomes a computer. Clicking the test window with xdotool freezes the game.

## Native abilities and the engine (v4.3, all measured in hidden runs)

- **An ability text that is too long crashes the game while the map loads** (CustomObject, "Not enough memory"): `aub1` at 973 and 986 bytes started, at 1059, 1074 and 1338 it crashed, colour codes counted. The exact limit is not proven: `check_tooltips` in `build.py` stops the build above 900 bytes and names the text.
- **A Learn text has one version for all ranks:** `aret` and `arut` have repeat 0 in the metadata. Native `%d` in `aret` shows the offered rank. So a Learn card can list the ranks and name the offered one in its title, and no more. The normal `atp1`, `aub1`, `aut1`, `auu1` are per rank, so the current rank can be marked without any per-player state.
- **An item stops a hero learning a NATIVE ability with the same code, for good:** with the Stormhammer (`AIbx`, code `AHbh`) in his bag the Mountain King could not learn `AHbh`, with the Axe (`AIcs`, code `AOcr`) the Blademaster not `AOcr`: `SelectHeroSkill` does nothing, the points stay. Learned first, then bought: both work. A custom copy of the same ability has no such problem (the Dryad's `A000`, `A028`), so these learnables have ids of their own (`LEARN_REMAP`): `Xhbh`, `Xhcr`, `Xhev`, all ranks tested with real purchases in both orders.
- **A bash's bonus damage is its own damage event**, after the armor, next to the hit: a test that looks for one big hit finds none.
- **A boss's spell levels need a cooldown written:** a copied level without `acdn` or with 1 s lets the engine's own use of a creep spell fire two Frost Novas 1.8 s apart, off any schedule of ours.
- **The Learn button pushes the card around:** with a skill point left, an ability placed where the Learn button sits moves to a free slot and can push others. A picture of a card with points left does not show the card a player has without them.
- **`RemoveUnit` in the sale event is not done yet in that instant:** the sold hero still counts in `GroupEnumUnitsOfPlayer` right after the order and is gone a moment later. Check later.
- **A hidden pointer works:** `xdotool mousemove` on the slot's private display shows the game's tooltips, no click needed (a click freezes the game). `ForceUIKey("O")` opens the Learn card. **A shop's button cannot be pressed there:** `ForceUIKey("Q")` and `xdotool key q` bought nothing with a castle selected, also with the champion alive and the button in colour (`20261102-231939-a-8959`). Whether a key buys in a real game was not looked into. Test a shop with the tooltip picture and `IssueNeutralImmediateOrderById`. See the tour in docs/test-env.md.
- **Barrage (`Aroc`) goes with the unit's attack:** one volley per attack, so faster attacks make more volleys, and it does the damage of the unit's **weapon**: its Damage Per Target and Maximum Total Damage fields do nothing. Measured with 12 enemies around: 4 / 6 / 8 / up to 10 enemies hit per attack at levels 1 to 4, her own hit included. On one lone enemy one hit. Stop orders add nothing and holding position with nobody in reach gives none. So a test that filters hits by the field's number sees nothing.
- **The hero limits count who was ever hired:** `SetPlayerTechMaxAllowed(p, 'HERO', 1)` and the same for a hero type refuse the next hire for good. The hidden count rose by 1 per native hero sold, and `RemoveUnit`, giving him to Neutral first or killing him do not lower it, while `GetPlayerTechCount` reads 0 (the lowest `HERO` limit that sold climbed 1, 2, 3 ... 9, `20261101-212039-a-9395`). More tokens do not help. The custom Dryad did not count for `HERO`, but the limit on her own type stopped her too. Real effect: **Play again** refused the player's pick from the round after a native hero on and he got a random champion, in every version with these limits. Tests had always bought the custom Dryad, then one native hero, so they never saw it. The map now sets neither limit and `OnUnitSold` enforces one champion.
- **Tavern heroes have tiers:** a standard hero needs `Requirescount` / `Requires1` / `Requires2` (Keep, Castle) for any purchase after the first of a game, also after he was removed. `ureq ""` is not enough, `urqc` 0, `urq1` "", `urq2` "" are. It looked like a broken tavern in the second round.
- **A new ability level has nothing:** copy an ability to 10 levels and levels 2 to 10 have no range, targets or buffs unless they are written. The base's data only covers its own levels.
- **`MaxUnitSpeed` is 400** in MiscGame: a unit's speed field stops there, `GetUnitMoveSpeed` reads 400 and it walks about 390. An item speed bonus did not get past it either. 522 needs the constant.
- **`CreateUnit` moves a unit that touches another:** units with collision 48 placed 96 apart swapped ranks. At 128 they stay. Read the positions back after placing.
- **An opened gate keeps its posts:** Gate1PathDeath blocks 2 cells at each end, so two pieces side by side leave a post in the middle. No army may be placed there.
- **Removing Impale's buff at once takes away its damage**, which lands when the unit comes down after a second. Removing a stun buff is safe for an instant spell, not for this one.
- **Roar (`ACr1`) takes no invulnerable target**, the Tauren's own copy does. Frost Armor and Frost Frenzy likewise: test them on a normal friend.
- **Order names lie in the func files:** `ACbf` says `breathoffire` there, the order is `breathoffrost` (UI\\TriggerData.txt has the true ones: also `coldarrowstarg`, `carrionscarabsinstant`).
- **A dying monster is no corpse yet:** Carrion Beetles want a corpse, and a skeleton's death takes 5 s. Monsters with death type 0 never leave one: wave units now all have `udea` 3.
- **Skill points disappear when nothing is left to learn:** at hero level 25 with every skill maxed `GetHeroSkillPoints` reads 0, and the Learn button is gone, which frees its slot.
- **A second level of Doom refuses the creep race:** the game's row `ANdo` has one level, Max Creep Level `DataD1` 5 and `DataD2` "-". A map's level 2 then takes no monster of the creep race, also ours (`q00m`), only others like the Footman: measured on the copied ability in our map, not in a run of the whole reference map. No object field reaches that cell (`Ndo4` is not in the metadata), so the map carries the game's whole `Units\AbilityData.slk` with that one cell at 5: `ability_slk_doom_fix` in `build.py`, generated at build from the game's own file, checked for exactly one changed cell, never committed. It costs 111 KiB of map, because an MPQ compresses in 4 KiB sectors. A/B on the same script and objects: `20261101-213507-a-4dc1` level 2 refuses Skeleton Warrior, Felguard, `q00m`, Ogre Mauler, takes the Footman; `20261101-213711-a-93da` takes all of them, 3000 damage in 3 s, 2 Doom Guards at the death; the level 6 Elder Jungle Stalker stays refused and level 1 is unchanged in both. A paused target takes no Doom damage.
