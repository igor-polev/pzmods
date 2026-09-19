# pzmods

A local manager for a Project Zomboid mod collection: tags, load order, collection health and
sandbox options, in a browser interface served by a Python script on your own machine. Standard
library only, nothing to install.

## What it does

Project Zomboid itself offers no way to group mods. The usual answer is
[\[B42\] Mod Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3567084868) by
Duncan E., which adds to the in-game modifications menu much of what it lacks — including a
warning when you disable something other mods depend on — and keeps your mod lists in its own
config file. **pzmods assumes Mod Manager is installed and works on that same file.**

What it adds is room to work. Mod Manager runs inside the game's own interface, which is
comfortable for dozens of mods and cramped for hundreds, and each mod list behind it is a flat
line of ids. pzmods gives that file a structure and a place to edit it outside the game:

- **Tags instead of lists.** A tag is a named group of mods; a mod can wear several. A config is
  built from an ordered list of tags rather than from mods chosen one by one, so the load order
  follows from two orderings you control and duplicates cannot happen.
- **A report on the whole collection at once.** Missing dependencies, mods named in a config but
  not installed, incompatibilities declared in `mod.info`, mods outside their stated game-version
  range, load-order rules violated by the current config, and map mods whose world cells overlap —
  each with the mods, the config and the position that produced it. All of it read from the files,
  with the game shut.
- **Sandbox options.** Reads the options every installed mod declares and edits either a sandbox
  preset or a save's `map_sand.bin` in place, writing only the values you touched and leaving the
  rest of the file byte for byte as it was.
- **One update pass.** Local folders, Steam's manifest, the config file, the Workshop API and
  your subscription list are read together, and every tab is rebuilt from the same snapshot, so
  you are never looking at a half-refreshed picture.

## Requirements

- Python 3, standard library only — no packages to install
- Project Zomboid, Build 42
- [\[B42\] Mod Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3567084868) —
  pzmods reads and writes its config file, `pz_modlist_settings.cfg`
- Steam Workshop content and a `Zomboid` user folder on the same machine

## Setup

```bash
git clone https://github.com/igor-polev/pzmods.git
cd pzmods
cp settings.example.json settings.json
```

Then point `settings.json` at your installation:

| key | meaning |
|---|---|
| `workshop` | Steam workshop folder, e.g. `C:\Program Files (x86)\Steam\steamapps\workshop` |
| `zomboid` | the game's user folder, e.g. `C:\Users\<you>\Zomboid` |
| `port` | port for the local server, default `8765` |
| `gameVersion` | `"auto"` reads the build from the game's own debug log; a version here overrides it |
| `updateOnStartup` | run the update pass when the program starts |
| `fetchCommentsOnUpdate` | also read every mod's comment page during an update — slow on the first run, off by default |
| `modImageSize` | mod picture size in pixels, 16 to 96 |

## Running

```bash
python pzmods.py
```

It prints `http://127.0.0.1:8765/` and opens a browser there. Ctrl-C stops it.

## The tabs

| tab | what it is for |
|---|---|
| Mods | the collection: tagging, ordering inside a tag, per-mod page with dependencies, notes and comments |
| Tags | creating, renaming, reordering and deleting tags — the vocabulary lives here and nowhere else |
| Configs | building each config out of an ordered tag list, with a preview of the exact file to be written |
| Issues | everything wrong with the collection, grouped by kind, with every identifier clickable |
| Sandbox | editing sandbox options of a preset or a save |
| Discoveries | reader for candidate mods found by an external tool, with your verdict on each |
| Backups | restoring a previous version of Mod Manager's config file |
| Setup | paths, options, resolved game build, subscription sync |

## How it treats your files

Mod Manager's config file is the only source of truth for tags and configs: pzmods keeps no
independent copy that could drift from it. Edits live in the program until you press Save, every
write is preceded by a timestamped backup, and a change made to the file by something else — by
Mod Manager itself, for instance — while pzmods was open is detected rather than silently
overwritten.

Outside its own folder the program touches exactly two things, and only on an explicit action:
`pz_modlist_settings.cfg` when you press Save, and one sandbox preset or one save's `map_sand.bin`
when you press Write on the Sandbox tab.

Its own data — the scan snapshot, Workshop metadata, cached comments, your notes and backups —
stays under `data/`, `backups/` and `discovery/` inside the project folder.

## Subscription list

Everything except your Steam subscription list is read locally. That list needs a signed-in Steam
session, which this program deliberately does not have: it never sees your password, cookies or
tokens. Setup → "Sync from my profile" hands you a bookmarklet that your own browser runs, and
falls back to a paste box if the browser will not let it reach the local server.

Until you sync, subscription status comes from Steam's local manifest, which is accurate for
everything Steam has actually downloaded.

## Limitations

- Build 42 only. The version-folder rules and several of the `mod.info` fields it reads do not
  apply to Build 41.
- Paths and defaults assume a Windows installation.
- Close the game before editing a save on the Sandbox tab: Project Zomboid holds those values in
  memory and writes them back out, so an edit made while it runs is lost. pzmods checks and
  refuses unless you override it.
- The Discoveries tab only reads a file produced elsewhere; pzmods never searches the Workshop
  itself.

## Licence

MIT.
