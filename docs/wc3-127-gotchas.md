# WarCraft III 1.27 gotchas (all hit for real on this map)

## Crashes and silent failures

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

## Shops and items

- `EVENT_PLAYER_UNIT_SELL_ITEM` does **not** fire for player-owned shops → react to PICKUP/USE item events.
- Scripted buy from an owned shop: `IssueImmediateOrderById(shop, itemId)`; neutral shop:
  `IssueNeutralImmediateOrderById(player, shop, itemId)`.
- Research/upgrades are queued with a progress bar, never instant → use power-up items + abilities.
- Items without `ubpx/ubpy` share their base item's button position, so the shop reshuffles them after
  every restock. Give every sold item an explicit slot.
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
- `war3mapUnits.doo` is ignored (units come from the script). Custom unit ids start lowercase (uppercase = hero).

## Loading screen

- Replace the MP loading screen by importing
  `UI\Glues\Loading\Multiplayer\Loading-{TopLeft,Human-TopRight,BotLeft,Human-BotRight}.blp`.
- The game stretches the 4:3 image to 16:9 and draws the player list over the left ~62 % → lay the art out on
  a 16:9 canvas, far right. Keep the background **flat**: the 4 tiles are filtered separately, so any colour
  change across a tile edge shows as a seam.

## Game install / Wine

- **Never overwrite a map file in place while WC3 runs**: the game keeps the MPQ open and reads it lazily, and
  a rewritten file crashes it with "Not enough memory — SFile.cpp line 898". `build.py` installs by copying to
  `*.tmp` and renaming over the old file (the running game keeps the old inode); the new map loads next game.
- **Never rename the launchers** (`Frozen Throne.exe` etc.): a renamed launcher fails with a fake
  "insert CD" error.
- A second `war3.exe` launch silently attaches to the running instance → `tools/run_test.sh` refuses to run
  while WC3 is up, and kills only its own `-window -loadfile` process.
- In `-loadfile` mode slot 2 becomes a computer. Clicking the test window with xdotool freezes the game.
