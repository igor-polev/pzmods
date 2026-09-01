# pzmods — local mod collection manager for Project Zomboid

## Start it

```
cd C:\Users\igor\Zomboid\pzmods
python pzmods.py
```

It prints http://127.0.0.1:8765/ and opens your browser there. Standard library
only, nothing to install. Ctrl-C stops it.

## One button: Update

There used to be three separate refresh actions and no way to tell what each one
did. There is now one, and it reads every source in a single pass:

| | source | where |
|---|---|---|
| local | the workshop content folder | `...\steamapps\workshop\content\108600` |
| local | your own mods folder | `...\Zomboid\mods` |
| local | Steam's own manifest | `appworkshop_108600.acf` |
| local | the mod list config | `...\Zomboid\Lua\pz_modlist_settings.cfg` |
| online | the public Workshop API | titles, descriptions, tags |
| online | your subscription list | the only source that needs you signed in |

Update runs automatically when pzmods starts, and every tab — Mods, Tags,
Configs, Issues, Sandbox — is rebuilt from the same snapshot when it finishes.
There is no way to be looking at a half-refreshed picture. The one exception is
deliberate: sandbox edits you have not written yet hold their tab where it is,
because an Update is no reason to throw your work away.

The header shows the current phase and a progress bar while it runs. Metadata is
only re-fetched for items Steam says have changed since the last look, so after
the first run the online part is nearly free. "Update, re-fetching all metadata"
on the Setup tab forces a full re-read.

The only thing pzmods cannot read by itself is your subscription list, because
that needs a signed-in Steam session and this program deliberately has none — it
never sees your password, cookies or tokens. Setup → "Sync from my profile"
gives you a bookmarklet your own browser runs; it reports progress and errors on
the page and never fails silently, and if Chrome blocks it from reaching this
local server it puts the list on your clipboard for the paste box.

### Two witnesses, and they age differently

Steam rewrites `appworkshop_108600.acf` the moment you subscribe or unsubscribe.
The synced profile list is frozen at the moment you took it. So:

- the manifest decides wherever it has anything to say
- the synced list only fills the gap the manifest cannot cover — an item Steam
  is not tracking at all, which is what "subscribed but never downloaded" looks
  like
- when the manifest is newer than the sync, even that gap goes to the manifest.
  An entry Steam has since dropped entirely is an unsubscribe that happened
  after the snapshot, not a subscription waiting to download.

That last rule is why unsubscribing no longer leaves mods sitting in "Subscribed
but not on disk" claiming to be subscribed. They move to "Your synced profile
list has gone out of date", which names them and says what happened. Re-sync or
drop the list on the Setup tab and the card disappears. Any mod ids they left in
your config file show up under "Named in the config file, but not installed",
where the Forget button clears them.

The header and the Setup tab both show when the snapshot was taken and when Steam
last wrote its manifest, so you can see which one is older before it misleads you.

Until you sync at all, subscription status comes from the manifest alone, which
is accurate for everything Steam has downloaded.

## The config file is the only source of truth

pzmods keeps no independent idea of what your tags contain. Tags, configs and the
markers in between are read out of `pz_modlist_settings.cfg`, and `data/tags.json`
is only a working copy of what was last read. That matters: an earlier version
kept its own cache, the cache drifted from the file, and the drift showed up as
mods being reported missing from tags they were plainly in, and as long-deleted
mods being reported as still tagged. A cache that can disagree with the file is
worse than no cache.

Save writes the file back byte for byte, trailing semicolons and all, so a Save
that changes nothing leaves the file untouched.

## The config file is watched, not owned

Every Update fingerprints `pz_modlist_settings.cfg`. If you edited it by hand, or
ModManager rewrote it, pzmods notices and reacts:

**the file changed, you had no unsaved edits**
tags and configs are re-read from the file, and a banner says so

**the file changed AND you had unsaved edits**
nothing is clobbered. A banner offers you the choice: reload from the file
and lose your edits, or keep your edits and let the next Save overwrite the
file. Your previous `tags.json` is copied aside either way.

Restoring a backup also re-reads tags and configs out of the restored file.

## Tags, not themes

A tag is a named list of mods, and a mod may wear as many tags as make sense —
that is the normal case now, not a warning. The vocabulary is fixed: tags are
created, renamed, reordered and deleted on the Tags tab and nowhere else, so a
typo can never invent a new one.

Name a tag whatever you like. The two leading digits were only ever cosmetic and
the rule is gone. Three names are still refused, because the file format cannot
carry them: anything containing `:` or `;` (the separators), anything shaped like
a config name (`-4- Something`), and anything starting with punctuation, which is
how Mod Manager writes its own markers. pzmods remembers which lines it considers
tags, so an unusually named tag survives being written and read back.

You put tags on mods in two places:

| where | what you get |
|---|---|
| Mods tab | select any number of rows, then add tag / remove tag / clear all tags |
| a mod's page | click the tag chips to toggle them |

The order of tags on the Tags tab is the order the tag lines appear in the file.

## `-- Disabled`: the built-in tag

One tag always exists and cannot be renamed or deleted. Put a mod on it and:

- it is left out of every config pzmods writes, so the game never loads it
- it stays installed, and keeps every other tag it had
- it is greyed out on the Mods tab and shows a "disabled" badge
- its own missing dependencies stop being reported — you switched it off on
  purpose, so its problems are not problems
- anything that still requires it IS reported, under "Disabled, but an enabled
  mod requires it". That is the one thing you need to know when switching
  something off.

Take the tag off and the mod comes back at exactly the position it held in every
config. Nothing is remembered to make that work: a mod's place in a config is
worked out from its tags every time, so switching one off and on again cannot
move it down the load order.

The Mods tab has a "hide disabled" checkbox and a "disabled only" filter.

## My notes

One free text box on a mod's page, and nothing else. It used to also ask for a
stability rating and a load order, which were two more fields to fill in and
neither of them was ever read by anything — the load order is decided by tags and
configs now, and a rating you never look at is not worth a dropdown.

A mod carrying a note says so, loudly. The section on its page is framed while
there is text in it, and the row on the Mods tab gets a "note" badge that shows
the text on hover. The "has my notes" filter lists them.

### Red or green, and you draw the line

A note is a queue, not a paragraph. A line holding nothing but

```
-OK-
```

splits it: everything below that line is what you have already read and
accepted, everything above it is still waiting for you.

So the note is green only when nothing is left above the line. Any text above
it, or no such line at all, and both the section and the badge are red. Move the
line down as you work through what is written, and the mod goes quiet.

The line is matched on its own, whole line, spaces around it are fine and the
case does not matter. Only the first one counts.

The 250 notes that already existed when this was added were all written by an
AI, so each one was given an `-AI-` line above its text and starts out red. That
was a one-time edit of `data/notes.json`; the file it replaced is kept next to it
as `data/notes.<timestamp>.json`.

Empty means empty: clear the box, press Save, and the entry is deleted from
`data/notes.json` rather than left behind as a blank record. A badge can never
outlive the text that earned it.

A note outlives the mod. Unsubscribe, delete the folder, forget the id out of
every tag — the note stays, and the mod keeps a row on the Mods tab for as long
as it has one, so you can still read what you wrote. That is the point: what you
learned about a mod is worth more than the mod, and it is exactly what you want
back on the day you subscribe again. Only clearing the box deletes a note.

This is the only file in pzmods that is purely yours. Nothing an Update reads can
touch it.

## The "required by N" badge

A mod carries this badge on the Mods tab when something else installed and not
disabled names it in its own `mod.info` `require=`. Hover it for the list; the
mod's own page names them and links to each. It is what tells you, before you
touch anything, that a mod is holding others up: damnlib carries "required by 58".

Only enabled requirers count. Put a requirer on `-- Disabled` and its vote goes
away, because a mod is not being held in place by something you have switched
off. The lookup also goes through the alias list, so a requirer naming any id a
folder declares credits the mod the game actually loads.

The "required by another mod" filter shows only these.

## The game says which build it is

Two things depend on knowing your build: which version folder a `mod.info` is read
from, and whether `versionMin` / `versionMax` put a mod out of range. pzmods does
not ask you.

The game writes its own version into its debug log every time it starts:

```
LOG  : General      f:0> version=42.20.4 b0bbce05d5 demo=false.
```

so pzmods reads the newest log in `Zomboid\Logs` that names one, and the Setup tab
shows the answer and which file it came from. Only the newest few are read — a
B41-era log does not write this line, and a log from months ago is not evidence
about the build installed now.

This used to be a number in `settings.json`, and a number is right on the day it is
typed and wrong after the next patch — quietly. `gameVersion` said 42.20 while the
game was on 42.20.4, and three perfectly current mods were reported as needing a
newer game than the one running them. Now `gameVersion` is `"auto"` by default. Put
a real version there to override the log, which is what you want for testing what a
different build would read.

## Two ids in one folder

A Build 42 mod keeps a `mod.info` per version folder, and the game reads the newest
one it is able to run. Those files do not have to agree with each other, and
sometimes they do not: TwisTonFire - Exercises declares `id=TwisTonFireExercises`
in its 42.20 folder and `id=twistexercises` in common. Reading the wrong folder
means reporting an id the game never uses, and then reporting the id it does use
as not installed.

pzmods picks the highest-numbered version folder that is not above your game
build — read from the game's own log, see above — and treats every id the folder
declares anywhere as installed. A mod's page lists the other ids and says which
folder is active.

## The Sandbox tab

A mod that adds sandbox options declares them in `media/sandbox-options.txt`, with
a type, a range and a default, and gives them readable names in
`media/lua/shared/Translate/EN/Sandbox_EN.txt`. The values themselves live
somewhere else entirely, in one of two files, and the Sandbox tab edits both:

| file | what it is |
|---|---|
| `Zomboid\Sandbox Presets\*.cfg` | text, read only by a NEW game |
| `Zomboid\Saves\<mode>\<save>\map_sand.bin` | binary, what a save already runs on |

Pick one in the box at the top left. The banner says which kind it is, because the
difference matters: editing a preset changes nothing in a game already in progress,
and editing a save changes nothing about the next game you start.

Options are grouped under the mod that declares them, and the cards start shut —
three thousand rows opened at once is a page nobody can read. Search by option
name, by its readable label or by its page, and the cards that match open
themselves. "From a mod only" is on by default; turn it off and the vanilla
options come too, in one last card for everything no installed mod claims.

Each row gets the widget its declared type deserves: a true/false box, a numbered
list for an enum with the mod's own wording for each choice, a number field
carrying the declared min and max, and plain text for anything else. The default
is on the right — click it to put the value back.

Options a mod declares but the file has never held are shown too, marked "not in
this file yet", holding the default the game would fall back to. Those are usually
the interesting ones: a mod installed after the save was made has never had its
say. Edit one and it is added when you write.

Nothing is written until you press Write, and only the values you actually touched
are sent. The file is not regenerated:

- a preset keeps its own comments, blank lines, line order and CRLF endings; the
  only bytes that move are the ones after the `=` on the lines you changed
- a save keeps its header, its pair order and its trailing bytes; a write that
  changes nothing leaves the file byte for byte identical

A copy goes into `backups/sandbox/` before every write, newest 60 kept.

Close the game before editing a save. Project Zomboid holds these values in memory
and writes `map_sand.bin` back out every time the save saves, so an edit made while
it is running is an edit thrown away without a word. pzmods checks and refuses,
and you can override the refusal if you know what you are doing.

Which folder the options are read from follows the same rule as `mod.info`, above:
`common/` plus the one version folder your build actually loads. This matters. The
Antibodies mod declares its options as `lgd_antibodies_180_*` in its root `media/`
and as `lgd_antibodies_194_*` in `42.13/`, and only the second set is real — the
save file has never heard of the first.

## Configs are synthetic tags

You never list mods in a config by hand. You give a config an ordered list of
tags, and pzmods unions them in that order — first tag first, each later tag
contributing only what is not already there. That is what fixes load order and
what makes duplicates impossible.

A mod that wears several of a config's tags enters at the first of them, at the
position it holds inside that tag, and the later tags do not move it — they reach
it when it is already there. So a config line is decided by exactly two things,
and nothing else:

| what decides it | where you change it |
|---|---|
| the order of the config's tags | Configs tab, up/down arrows |
| the order of the mods in each tag | Mods tab, "reorder inside the tag" |

Nothing is remembered from the last write. The line is recomputed from those two
orders every time, which is why disabling a mod and enabling it again puts it
back where it was, and why there is no hidden state that can drift from the file.

The Configs tab shows each config's tag list with up/down arrows, how many mods
each tag contributes and how many of those are new at that point in the order.
"Preview the file that will be written" shows the exact text before you Save.

Two guarantees, both tested against your real file:

- a rebuild produces exactly the original order with duplicates removed
- writing twice in a row changes nothing the second time

Two things a config can still carry:

**extras**
mods that were in the hand-written line but wear no tag. They are kept
and appended so nothing is lost, and listed in red with a "drop them"
button. Tag them properly and the carry clears itself.

**adds**
the opposite case. If you add a mod to a tag by hand in the file, the
tag is still recognised as part of every config that uses it, and the
Issues tab tells you exactly which mods the next Save will add to
which config. Nothing changes until you press Save.

## Everything is a link

On the Issues tab every identifier is clickable:

| you click | you get |
|---|---|
| a workshop id | opens that item's Steam page in a new tab |
| a mod id | jumps to the Mods tab with the search set to it and the other filters cleared, so the mod is definitely on screen |
| a workshop title | the same, searched by name |
| a tag name | jumps to the Mods tab filtered to that tag |

An id that is neither installed nor named anywhere in your config file stays
plain text — it has no row to jump to, so it is not dressed up as a link.

The Mods tab has no Workshop column any more. The workshop id sits under the mod
name next to the mod id and links to Steam from there. The mod id itself is plain
text — you are already looking at the row, so a link back to it would go nowhere
useful.

## What the Issues tab is telling you

**In Steam's manifest, but there is no folder**
Steam's own bookkeeping, not yours. When an item is delisted or unsubscribed
Steam deletes the folder but can leave the record behind in
`appworkshop_108600.acf`, still flagged installed and subscribed. That stale
record is the only place the id survives. The game never loads it — it scans
folders. Verify Integrity of Game Files clears it, or Steam does eventually.

**Your synced profile list has gone out of date**
Items your last sync called subscribed that Steam has since dropped from its
manifest and deleted the folder for — you unsubscribed them after the
snapshot was taken. pzmods believes Steam, not the snapshot.

**Subscribed but not on disk**
Subscribed according to whichever source pzmods trusts for that item, with no
folder. Each row says which case it is: gone from the Workshop (API result
9), banned, still listed but not fetched yet, or no metadata read yet.

**Named in the config file, but not installed**
Leftovers. The mod was removed but its name stayed in the lines it had been
written into. Each row says exactly where the name still is — which tags,
which configs — so you can see why pzmods is mentioning it at all. "Forget
the N uninstalled" strikes them all out at once; nothing reaches the file
until you Save.

**Installed and in a config, but wearing no tag**
Actionable, unlike the one above: the mod is really there, it is being
carried into a config by hand, and it wants a tag.

**Declares another installed mod incompatible**
Read from `mod.info` `incompatible=`, which pzmods now parses. Both mods are
installed and neither is disabled, so any config holding both is asking for
trouble. Putting one on `-- Disabled` settles it.

**Disabled, but an enabled mod requires it**
You switched a dependency off and left something that needs it on. That
something will not load.

**Built for a different game version**
`mod.info` can state the builds a mod is for, and a mod's page now shows that
range on its id line, written as

```
versionMin - the build you run - versionMax
```

with "any" for a bound the mod does not state, and in red when your build
falls outside it. This card lists the red ones.

The build compared against is read from the game itself — see below. One mod
writes `versionMin=42.16.+`, which is not a version; a bound nobody can read is
ignored rather than guessed at.

**Loaded in the wrong order for its own rules**
The config line is the load order — the game loads the mods in the order the
line names them — so a rule about which mod comes first is a rule about that
line. Three are readable from `mod.info`:

| rule | meaning |
|---|---|
| `require=` | names a dependency, which has to be loaded already |
| `loadModAfter=` | this mod must come after the ones named |
| `loadModBefore=` | this mod must come before the ones named |

Each row names the config, both mods and their positions in that line. A rule
is only checked when both mods are in the same config; one of them missing or
disabled is a different card's problem. The fix is not on the Issues tab: move
the tag on the Configs tab, or move the mod inside its tag on the Mods tab.

`loadModAfter`, `loadModBefore` and `incompatible` are the only sorting rules
Build 42 reads from a version-numbered folder. The older names — `loadAfter`,
`loadBefore`, `loadFirst`, `loadLast`, `incompatibleMods` — are read from common
only, and appear four times in this collection, so pzmods does not chase them.

**Requires a mod that is not installed**
Read from `mod.info` `require=`. Note that most Build 42 `mod.info` files write
dependencies with a leading backslash — `require=\damnlib` — and often a
trailing comma. In this collection 241 of 323 dependency tokens are written
that way, no token has an interior separator, and no mod mixes the two
styles, so the backslash is punctuation the game ignores, not part of the id.
pzmods strips it before comparing. Taking it literally turned 11 real missing
dependencies into 245 false ones.

## Where a mod's picture comes from

`mod.info` names its own pictures, so pzmods asks it before guessing, and it asks
in this order:

| field | when it is used |
|---|---|
| `poster=` | the picture the author made to be recognised by. Used everywhere — the Mods tab row and the mod's own page |
| `icon=` | only stands in for the row when there is no usable poster |

Neither field is mandatory, which is why the guessing stayed. Across the 1262
`mod.info` files here, `poster=` is in 98.7% of them and `icon=` in 71.2%, 16 files
have neither, and 55 posters name a file that was never shipped. So a declared
value is only used when it resolves to a file that really exists inside the mod;
otherwise pzmods falls back to looking in the mod's own folder and then in each
version folder, taking the first match of:

```
poster.png  icon.png  thumbnail.png  preview.png  poster.jpg  icon.jpg
icon_*.png  poster_*.png  icon_*.jpg
```

Exact names win over the patterns, so a mod carrying both `poster.png` and a pile
of `icon_something.png` files still shows its poster. When a pattern matches
several files the first by name is taken, so the choice does not wander between
scans. Directories that happen to be named like an image are ignored.

The path in `poster=` / `icon=` is relative to the folder that `mod.info` sits in,
and a few point outside it (`../common/poster.png`), which is followed. The active
version folder is asked first, then the others newest first, so a mod with no
picture in 42.20 still shows the one in common. A mod that declares several
posters — some declare up to five — shows the first. A mod's page falls back to
the row picture when it declares no poster.

This found a picture for 29 mods that had none, and put the author's own poster
on 430 more that used to show whatever the filename scan happened to find first.
15 mods still show no picture: they declare none and ship none.

The size is `modImageSize` in `settings.json`, or the box on the Setup tab.

## How the Mods list is ordered

Reading the list top to bottom is meant to be reading your load order — but a
load order belongs to a config, not to the collection, because each config puts
the tags in its own sequence. So the Mods tab has an order box:

| order | what it means |
|---|---|
| by tag | the fallback — the tag order from the Tags tab, and inside a tag that tag's own order |
| `-3- With Stuff` | that config's line, exactly as it will be written |

With a config chosen, a mod sits where that config puts it, which is at the first
of its tags that config lists. Mods the config does not contain fall in after it,
in tag order. Either way untagged mods go last, and a workshop item takes the
position of its earliest mod so its mods stay together underneath it — which is
the one thing that can put a row out of strict load order, and only within an
item that ships several mods.

The search box has a clear button that appears once there is something to clear.

## Setting the order inside a tag

The other half of the load order. Pick a single tag in the tag filter and press
"reorder inside the tag": the list flattens to that tag alone, in the tag's own
order, numbered by real position, with drag and drop and four buttons per row —
to the top, one up, one down, to the bottom.

- tick several rows and they move as one block, keeping their order
- a search narrows what you see without losing what it hides — positions are
  the mod's place in the tag, not its place on screen, and a move over a hidden
  neighbour still lands where the numbers say
- the hint line names the tag and says how many mods it holds

Every move is an edit like any other: it goes into pzmods, the unsaved-edits
banner appears, and nothing reaches the file until you press Save.

## One workshop item, several mods

A workshop item routinely ships more than one `mod.info`, and tagging happens per
mod, not per item. The Mods tab makes that structure explicit: an item with
several mods gets a header row with its poster, title, Steam link, subscription
status and a "N mods in this item" badge, and its mods sit beneath it on a
bracket. The header checkbox selects all of them at once. An item with a single
mod stays a single row.

The "workshop item with several mods" filter shows only the packs, which is the
quickest way to find variants you never tagged.

## Options — Setup tab, stored in `settings.json`

| option | what it does |
|---|---|
| `modImageSize` | mod picture size in pixels, 16 to 96 |
| `gameVersion` | `"auto"` (the default) reads your build from the game's own debug log. A version here overrides it. Not on the Setup tab, which only shows what was resolved |
| `updateOnStartup` | run the Update pass when pzmods starts |
| `fetchCommentsOnUpdate` | also read every mod's comment page during Update. One request per mod, so minutes on the first run, then only items Steam says changed. Off by default — comments are then fetched when you open a mod. |

## Requirements, and where each one lives

1. **browser, simple** — one python file plus one html file, no dependencies
2. **local vs Steam** — Issues tab: not on disk / not subscribed / manifest gap
3. **grouping** — tags, multi-valued, edited from the Mods tab and from each
   mod's page; the vocabulary is fixed on the Tags tab
4. **maintains the cfg** — "Save config file". Every write backs up first, keeps
   the last 40 in `backups/`, restore from the Backups tab. External edits are
   detected, never silently overwritten
5. **quick link to Steam** — every workshop id anywhere in the app is the link
6. **mod info** — the drawer shows the mod's poster, its version range on the id
   line, then require / loadModAfter / incompatible from `mod.info`, what
   requires this mod, the other ids the folder declares, an Open folder button
   next to close, the Workshop description and the user comments. Your own notes
   live in `data/notes.json` and are never touched by a refresh
7. **profile access** — Steam's local manifest by default; the bookmarklet or
   the paste box for the live profile list
8. **sandbox options** — the Sandbox tab edits a preset or a save in place, with
   every option under the mod that declares it, the widget its type asks for,
   and a backup before every write

## Files it writes

| file | what it holds |
|---|---|
| `data/snapshot.json` | the last full scan of both mod folders and the manifest |
| `data/tags.json` | the working copy of what was last read from the cfg |
| `data/tags.*.json` | a copy set aside before any automatic reload |
| `data/steam.json` | the Workshop metadata snapshot |
| `data/subs.json` | the synced subscription list and when it was taken |
| `data/notes.json` | your notes — the only file that is purely yours |
| `data/comments/` | cached comment threads, one file per workshop id |
| `backups/` | timestamped copies of `pz_modlist_settings.cfg` |
| `backups/sandbox/` | the same, for every sandbox file the Sandbox tab writes |

Outside this folder it touches `pz_modlist_settings.cfg` when you press Save, and
one sandbox preset or one save's `map_sand.bin` when you press Write on the Sandbox
tab. Nothing else, and neither of them without asking you first.

## Settled — do not reopen

These were decided once, on purpose. Each one was tried the other way first.

- **The regrouping proposal was cancelled.** An earlier todo list included
  "analyse current mod grouping, propose corrections" — splitting 05 Vehicles,
  breaking up 19 QoL - Secondary UI, filing the untagged. It was cancelled
  explicitly. Do not propose it again unasked.
- **Mod ids on the Mods tab are plain text, not links.** They were made
  clickable once and that was reverted as meaningless. Ids on the Issues tab
  ARE links, and that is wanted.
- **Tag names do not need two leading digits.** That rule was removed on
  request.
- **pzmods keeps no cache of the grouping.** The config file is the only source
  of truth. An earlier version cached it, the cache drifted, and the drift
  invented mods that were not there. Do not reintroduce a cache.

## How to test a change without touching the real files

Every change to pzmods was verified this way rather than by guessing.

Build a fixture from the real data: `data/snapshot.json` holds the full scan of
every mod (ids, `require`, version folders), so a throwaway tree of `mod.info`
files can be regenerated from it, next to a copy of the real
`pz_modlist_settings.cfg` and the real `appworkshop_108600.acf`. Point a copy of
`settings.json` at that tree, run the server on a spare port, and drive it over
the HTTP API.

The guarantees worth re-checking after any change to the writer:

- preview == the file on disk, byte for byte, when nothing has changed
- writing twice in a row changes nothing the second time
- disable a mod, save, re-enable, save — it returns to the same index in every
  config it was in

The UI was checked headlessly with Playwright (chromium is preinstalled in the
cloud workspace at `/opt/pw-browsers`), taking screenshots and reading them back.
That is how the layout and sticky-header bugs were caught.

A container cannot reach `api.steampowered.com`, so the metadata and comment
fetches can only be exercised for their failure handling. Those paths run on the
real machine.

## The rest of the Zomboid work in this folder

Separate projects, all still in place, listed here so they are not lost:

| where | what it is |
|---|---|
| `Zomboid\mods\Mindset42\` | rebuild of a long-broken trait mod (workshop 3554341903) for B42.20.4. Four traits registered through the B42 CharacterTrait API |
| `Zomboid\mods\CompanionCatPurr\` | add-on making cats relieve unhappiness more than other pets, via a purr moodle hooked into `CD.DogMoodles`. Depends on CompanionCat (3791294616) |
| `Zomboid\Lua\bandits\clans.txt` | custom NPC clan scheme: six eras spread over about five in-game years, companions removed, spawn rates cut so roaming groups are rare. Only altered fields are in the file; `clans_extended.txt` is the full-value overview for reading, and `clans_gantt.py` draws the timeline. Backups of earlier schemes sit beside it |
| `Zomboid\Sandbox Presets\Custom.cfg` | tuned Bandits parameters that go with the above |
