# TechTools Castle Defence (WarCraft III TFT 1.27)

An 8-player co-op hero lane-defense map. Pick a champion, hold your own lane, push your own tower and Nexus,
kill its boss — and keep the shared castle alive. The whole map is generated from code: terrain, walls,
objects, script and art. Nothing is made in the World Editor.

Installed as `Maps/CustomMaps/TechToolsCastleDefence.w3x` (about 200 KiB).

## Docs

| Doc | Content |
|---|---|
| [docs/gameplay.md](docs/gameplay.md) | The spec: round flow, waves, shops, castle, items, commands, UI — with exact numbers |
| [docs/architecture.md](docs/architecture.md) | Build pipeline, file map, JASS function map, shop data model, object-ID registry |
| [docs/wc3-127-gotchas.md](docs/wc3-127-gotchas.md) | Engine and file-format traps that were hit for real |
| [CLAUDE.md](CLAUDE.md) | Entry point for AI agents: rules, workflow, the owner's design rules |

## Build

```bash
python3 build.py              # -> dist/TechToolsCastleDefence.w3x, pjass + base-id check, installs into the game
python3 build.py --test       # -> dist/TechToolsCastleDefence_TEST.w3x: 8 s select, revealed map, scripted run
python3 build.py --no-install
tools/run_test.sh 'Maps\Test\TechToolsCastleDefence_TEST.w3x' /tmp/out 40   # Wine test run + screenshots
python3 tools/verify_map.py dist/TechToolsCastleDefence.w3x preview.png     # re-parse + top-down render
```

Needs `libstorm` (StormLib, `apt install libstorm-dev`), Pillow, and the game directory (`WC3_DIR`,
default `/home/novakj/games/warcraft3`). pjass is built from source in `tools/pjass-src`
(`git clone https://github.com/lep/pjass && make`, needs flex and bison). `ref/` is extracted from the game's
own MPQs with `tools/extract_ref.py` (and `tools/dump_map.py` for the official maps): common.j, Blizzard.j,
the SLK tables and the official maps the formats were checked against.
