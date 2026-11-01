# TechTools Castle Defence (WarCraft III TFT 1.27)

An 8-player co-op hero lane-defense map. Pick a champion, hold your own lane, push your own tower and Nexus, kill
its boss, break the four gate levels, then beat the final boss that grows stronger every minute — and keep the
shared castle alive. The whole map is generated from code: terrain, walls, objects, script and art. Nothing is made
in the World Editor.

**Play it:** download the current version from the [TechTools WarCraft III catalogue](https://techtools.cz/tools/warcraft3/maps)
into `Maps/` of a WarCraft III 1.27 install. `python3 build.py` installs a fresh build as
`Maps/CustomMaps/TechToolsCastleDefence_v<version>.w3x` (about 300 KiB).

## Docs

| Doc | Content |
|---|---|
| [docs/gameplay.md](docs/gameplay.md) | The spec: round flow, waves, shops, castle, items, commands, UI — with exact numbers |
| [docs/architecture.md](docs/architecture.md) | Build pipeline, file map, JASS function map, shop data model, object-ID registry |
| [docs/wc3-127-gotchas.md](docs/wc3-127-gotchas.md) | Engine and file-format traps that were hit for real |
| [docs/test-env.md](docs/test-env.md) | The hidden test environment: run the map's self-test in the real game beside a running client |
| [CLAUDE.md](CLAUDE.md) | Entry point for AI agents: rules, workflow, the owner's design rules |

## Build

```bash
python3 build.py              # -> dist/TechToolsCastleDefence.w3x, pjass + base-id check, installs into the game
python3 build.py --test       # -> dist/TechToolsCastleDefence_TEST.w3x: 8 s select, revealed map, scripted self-test (PASS/FAIL file)
python3 build.py --no-install
tools/test_env.py run         # full self-test in the real game, hidden, in its own Wine prefix; exit 0 = clean
python3 tools/verify_map.py dist/TechToolsCastleDefence_v<version>.w3x preview.png  # re-parse + top-down render
```

Needs `libstorm` (StormLib, `apt install libstorm-dev`), Pillow, and a WarCraft III 1.27 game directory (`WC3_DIR`).
The game's own files are not in this repo. pjass is built from source in `tools/pjass-src`
(`git clone https://github.com/lep/pjass && make`, needs flex and bison). `ref/` is extracted from the game's
own MPQs with `tools/extract_ref.py` (and `tools/dump_map.py` for the official maps): common.j, Blizzard.j,
the SLK tables and the official maps the formats were checked against.
