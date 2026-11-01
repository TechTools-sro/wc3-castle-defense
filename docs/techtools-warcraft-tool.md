# The WarCraft III tool on techtools.cz

Context for anyone working on this map: the website around it. State as of **2026-11-01**, read from the sources listed at the end.
This repo holds only the map generator. The tool's code lives elsewhere, and nothing here deploys it.

## Two repositories

| | This repo | The web tool |
|---|---|---|
| Repo | `TechTools-sro/wc3-castle-defense` (public) | `TechTools-sro/techtools-4` (private) |
| What | Generator of one map, TechTools Castle Defence | `tools/warcraft3/` plus the `/warcraft3-api` API |
| Output | A `.w3x` file, published through the catalogue API (by a person or an agent) | https://techtools.cz/tools/warcraft3/ |
| Runs on | A developer's machine, tests in Wine | The TechTools main server |

The map does not call the website, and the website does not build the map. The only link between them is an upload to the catalogue.

## Architecture

- **Frontend:** vanilla HTML, CSS and JS in `tools/warcraft3/`, with no framework and no build step. Pages: LAN, Voice rooms, Maps, Messages, Help.
- **Backend:** the `warcraft3_api` namespace in the shared Rails API `techtools-api`, behind nginx and Puma. Public API docs: `GET /warcraft3-api/docs`.
- **The website is not a game server.** The game engine runs on the players' own machines. This repository contains no WarCraft III engine or game files.

## LAN play

WarCraft III finds LAN games by a UDP broadcast on port 6112. A routed VPN would not carry that, so the tool uses **OpenVPN Community in TAP mode**, not WireGuard.

- Each signed-in account claims its own VPN slot and downloads a Windows installer or a Linux script built for that account. These files are personal: never commit one.
- Players then open **Local Area Network** in the game. Everyone needs the same patch (TFT 1.27b) and the same map file.
- Slots are claimed and revoked without restarting the VPN server. A slot whose config was downloaded is burned when released, so one certificate never reaches a second person.
- Public connection facts: `GET /warcraft3-api/vpn/info`.

**Not verified here:** a full run of the Windows installer on a physical Windows PC, or a complete multiplayer game through the VPN. This document does not claim either.

## Accounts and permissions

One shared TechTools account for every tool, identified by the session cookie.

| Action | Who |
|---|---|
| List maps, map details, download, read comments, map docs | anyone |
| Upload, rate, comment, VPN slot, voice rooms | signed-in account |
| Messages | signed-in account, no chat nickname needed; see [Voice rooms and messages](#voice-rooms-and-messages) for who can start a conversation |
| See a voice room's call link | members of that room |
| Delete a voice room | its owner |
| Add a version to a map | that map's uploaders and admins |
| Write a map's documentation | its uploader or an admin |
| Delete a map file | admin only, not even the uploader |

## Map catalogue

- **Versions:** every uploaded file has its own id and SHA-256. Files with the same title (minus the trailing version) form one family, shown as one map with its newest upload on the card and all versions on the detail page. Rating and comments belong to the family.
- **Nobody takes over a family:** someone else's upload with the same title gets a family of its own.
- **Player docs:** one Markdown file per version at `/warcraft3-api/maps/:id/doc.md`, written part at most 100 KB. Catalogue index: `/warcraft3-api/maps.md`, which links the newest version of each map.
- **This map:** the current version and every catalogue id are in [`CLAUDE.md`](../CLAUDE.md) § Published. The player guide is [`map-catalog.md`](./map-catalog.md), uploaded with each version.

Checked live on 2026-11-01: `/warcraft3-api/maps/78` answers v4.1, the latest of 29 versions, SHA-256 `354e5f1fed52bfb06e94c9f53ab101585ec783ff9c425db56dfe5fadf56eeeb1`.

⚠️ **Open:** the upload limit is described differently in two places. The server code at `techtools-4` commit `9b1d3cc` limits new map families per day, and new versions of your own map are not limited. The public API docs and the tool's own notes still say a limit on uploads. Check the code before relying on a number.

## Voice rooms and messages

- **Voice rooms** (the API says `teams`) embed a TechCall call in an iframe. TechCall is a separate tool: WebRTC mesh in the browser, signalling through `/techcall-api`, TURN when needed.
- **Messages** have their own API, `Warcraft3Api::MessagesController`, on the shared Public Chat models, so conversations and blocks are the same ones. The tool stores no messages of its own, and no nickname is created.
  - Endpoints: `GET /warcraft3-api/messages/conversations`, `GET|POST /warcraft3-api/messages/dm/:address/messages`, `POST|DELETE /warcraft3-api/messages/dm/:address/block`. Attachments stay at `/public-chat-api/dm/files/:id`.
  - `:address` is a chat profile's public id, or a signed address of a VPN slot or a conversation.
  - **A new conversation:** the recipient must hold an active VPN slot. The sender must either hold an active slot too, or both accounts must have a chat name. Neither player needs to be connected.
  - **An existing conversation** survives a released or deleted slot. A third account gets a 404. A block stops messages both ways, and only the blocker can lift it.
  - Public Chat itself still requires a nickname.
- **Online means different things:** VPN online (the LAN page) and chat presence (a heartbeat of the chat profile) are separate signals. In messages, a player with a chat profile is online by either one, and a player without a profile by VPN only.

State on 2026-11-01: `techtools-4` commit `1497fd1` is live, deployed at 14:44 with an API-only restart and no VPN change. As reported by the coordinators of that release (not run from this repo), 32 live checks passed: send, read, reply and attachment to an offline player with no chat name, isolation of a third account, and blocks in both directions. Availability of online players was checked read-only, with no test messages to real people. Those checks did not cover delivery while the recipient is actually connected to the VPN. Release notes: `techtools-4` commit `fcd2838`.

## What is where

| Thing | Where | Managed by |
|---|---|---|
| Map source, tests, player guide | this repo | commit here |
| Built map in the local game | `Maps/CustomMaps/` of the local install | `python3 build.py` |
| Web page | `tools/warcraft3/` in `techtools-4` | web deploy |
| API, models, VPN service, installer templates | `app/` in `techtools-4` | web deploy |
| VPN server setup | `deploy/war3lan/` in `techtools-4` | its runbook |
| Uploaded map files, ratings, comments | the server's storage and database | through the API |
| Company context | TechTools Brain: `projects/games/`, `company/decisions/` | Brain commit |

For agents with access, read these for detail: `tools/warcraft3/CLAUDE.md`, `tools/techcall/CLAUDE.md` and `DEPLOY.md` in `techtools-4`; `projects/games/CLAUDE.md` and `projects/techtools-4/CLAUDE.md` in the Brain.

## Working on it

| Task | How |
|---|---|
| Map change | Generator here, then `python3 build.py`, then `tools/test_env.py run` ([test-env.md](./test-env.md)) |
| Map release | New version in `build.py`, build, commit, upload, check the download's SHA-256: [`CLAUDE.md`](../CLAUDE.md) § Versions and § Published |
| Web change | In `techtools-4`. Verify with `test/controllers/warcraft3_api/warcraft3_api_test.rb` (two accounts), `test/models/war3_map_family_test.rb`, `test/services/warcraft3_map_info_test.rb` and a browser pass of the changed page; a messages change also needs `test/controllers/warcraft3_api/messages_test.rb`, a voice change the tests of TechCall. Release with `bin/deploy` as `DEPLOY.md` describes, never from this repo |

A map release and a web release are independent: an upload needs no deploy, and a deploy changes no map.

## Sources

Read on 2026-11-01: `techtools-4` at `9b1d3cc` (`tools/techcall/CLAUDE.md`, `deploy/war3lan/README.md`, `DEPLOY.md`, `app/models/war3_map.rb`, `app/models/public_chat_profile.rb`, `app/controllers/warcraft3_api/`) and, for messages, at `1497fd1` (`app/controllers/warcraft3_api/messages_controller.rb`, `app/controllers/concerns/direct_message_thread.rb`, `test/controllers/warcraft3_api/messages_test.rb`, `tools/warcraft3/CLAUDE.md`); Brain `company/decisions/2026-10-29-war3-lan-vpn-na-main.md` and `projects/techtools-4/CLAUDE.md`; live `GET /warcraft3-api/docs`, `/vpn/info`, `/maps/77` (HTTP 200). The map file itself was not downloaded again for this document.
