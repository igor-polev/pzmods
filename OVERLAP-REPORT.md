# Feature overlap cross-check — run 2

563 subscribed Workshop items · game build 42.20.4 · 3 Sep 2026
Sources: `pzmods\data\steam.json`, `snapshot.json`, `tags.json` (descriptions and `mod.info`)
**plus** a file-path census read off the installed mod folders and the game's own `media\lua`.
Online lookups: none.

---

## 0. What changed since run 1

**You acted on nine findings.** These nine mods are no longer on disk — every one of them was
a "drop this" recommendation from the first report:

| gone | was |
|---|---|
| Injury Indicator | A1, duplicate of Pain Sense |
| Simple Show XP | A4, duplicate of Neat XP Drop |
| Load All Magazines | A8, the declared function collision |
| Trap Manager | A10, duplicate trapping helper |
| Vehicle Safety | A11, the rival crash system |
| TwisTonFire – Better Character Info | A12, the Character Info contest |
| TwisTonFire – Exercises | A12, the fitness-window half of it |
| Nested Health Info | B5, the health-panel ordering problem |
| Loot Goblin 2000 | B8, covered by Proximity Inventory |

⚠️ **All nine are still named in `pz_modlist_settings.cfg`**, across six tags — and
`twistbettercharacterinfo` is named twice, in `02 Firsts` and `19 QoL - Secondary UI`. pzmods
will show them on the Issues tab under *"Named in the config file, but not installed"* — press
**Forget the N uninstalled**, then Save, and the config is clean.

(Seven of the nine went after this morning's 02:53 scan, so pzmods will not know until you press
Update.)

**Four clean version swaps**, all correct:

- Antibodies (2392676812) → **Antibodies B42.20 Community** (3782193024)
- Long Term Preservation + its patch → **Long Term Preservation [42.20]** (3774789651), one mod instead of two
- Simple Belt Flashlight → **Simple Belt Flashlight+** (3778709615), same mod id, the black-screen bug named on the new page belongs to the old item
- Vanilla Vehicles Animated → **the 42.20.4 temporary fix** (3791619698), mod id preserved

**65 new items, 16 removed** (including ten maps). Net: 514 → 563.

---

## 1. Tier A — duplicates, both live

Nine of the thirteen Tier-A findings from run 1 are closed. What is left, plus what arrived with
the 65 new mods.

### A-new-1. Towbars and Harry's Tow Truck declare each other incompatible
`Towbars` (3661430479, 06 Vehicles - Mechs) · `Harry's Tow Truck - Zombie Buddy Ed.` (3776518013, 05 Vehicles - Items)

Towbars' own page: *"New feature supporting KI5 Tow Trucks / Wreckers towing without a java mod!
**Incompatible with Harrys Tow Truck!**"* Both are subscribed and enabled. The incompatibility is
not declared in `mod.info`, so nothing in pzmods can catch it — it is only in the prose.
**This is the clearest single action in the report.**

### A-new-2. Z-UET and Zed's Better FPS patch the same Java methods
`Zomboid Unified Engine Tweaks` (3793911582, 01 Utils, last in the tag) ·
`Zed's Better FPS - B42.20.2 Fix` (3782613536, 01 Utils) · `SmartZOptimizer[Legacy]` (3707376688)

Z-UET's page: *"Do not use with other mods that patch `MovingObjectUpdateScheduler` /
`IsoCell.getGridSquare` at the same time (**e.g. ZBBetterFPS's optimizeIsoMovingObject**)."*
It names your mod. Both are enabled, plus a third ZombieBuddy optimiser whose own title says
Legacy. Three Java-level patches reaching into the same scheduler is where hard-to-trace
stutter and crashes come from.

### A-new-3. Two mods declare a trait called Second Wind
`Even More Traits [42.20]` (3777663603) — lists *Second Wind* among its 30+
`Survivor Quirks` (3759277273) — *"Second Wind: Once per day, recovers a burst of endurance"*

Traits are registered by id. Two registrations of the same name is a collision, not an addition.
The same page also gives Survivor Quirks a **Sixth Sense** trait — and you run the
`SixthSense` mod (2863908612), whose whole content is a trait of that name.

This takes your trait-mod count from four to **six**: SOTO, Somewhat Traits, Sandbox Traits,
Challenge Traits, Even More Traits, Survivor Quirks — plus trait-bearing skill mods (Toughness,
Combat Mastering, Efficiency, SixthSense, Break Into Tears, B42 Driving). SOTO and Somewhat
Traits both rewrite *vanilla* traits on top of that.

### A-new-4. CH Status HUD takes the key Inspect Weapon uses
`CH Status HUD` (3776182375, 18 QoL - Core UI) · `Inspect Weapon` (2948824747, 19 QoL - Secondary UI)

CH Status HUD: *"Press **;** (semicolon) to show or hide the panel."*
Inspect Weapon: *"Pressing **;** button to inspect current weapon."*
One key, two mods. Rebind one under Options → Key Bindings.

Separately, CH Status HUD is your **third** live status panel (with Mini Health Plus and the
Restingmod HUD, StatZ having no Lua of its own), and its *"Hide vanilla moodles"* option
switches off the icons that `Moodles in lua` and `Simple Moodle Indicators` exist to restyle.

### A-new-5. Layered Placement and Place Anywhere
`Layered Placement` (3775423228) · `Place Anywhere` (3613917826)

Place Anywhere *"removes all tile placement restrictions and allows you to place tiles anywhere
regardless of what tiles are already in the square."* Layered Placement does the same thing with
rules and per-feature sandbox switches. The blunt one makes the careful one's rules moot.

### A-new-6. JB's Work Orders duplicates four mods at once
`JB's Work Orders` (3775310237) automates gathering, area clearing, **farming**, moving corpses
and **auto-resting**. Against: `Batch Floor Action` (area clearing), `Batch Farming` (area
farming), `TwisTonFire - Restingmod` (rest + game-speed control), `Drag Bodies Faster`.
Its auto-rest and Restingmod's rest handling are the pair most likely to fight.

### A-new-7. Neat Lockpicking and Common Sense both pry with a crowbar
`Neat Lockpicking` (3783535220) — *"Crowbar — skill-check on doors, garages, windows, and car doors"*, and it **replaces vanilla hotwire**
`Common Sense` (3750253491) — feature 1, *"Pry open Doors, Windows and Vehicles with Crowbars"*

Two crowbar systems on the same objects. `dustinguished bolt cutters` is a third route through
the same locked doors, though by a different tool.

### A-new-8. Two ammo-crafting economies
`Hot Brass — Ammo Craft` (3637364024) · `Ammo Maker` (2788256295, 59 calibres, gunpowder from nitre)

### A-new-9. Two KI5 fix packs with overlapping scope
`KI5 General Fixes` (3789366983) · `KI5 Mini-fixes` (3740300378)

Both patch KI5 vehicles; both name the same cars. General Fixes claims *"Stutter as a vehicle
loads in… Affects every KI5 vehicle"*, Mini-fixes lists per-vehicle repairs. The census below
shows Mini-fixes also writes a file into damnlib's own folder — see §4.

### A-new-10. Three ledgers of which skill books you have
`Skill Book Library` (3787062830) — 120 vanilla skill books, 24 skills × 5 volumes, missing ones shown as gaps
`Unwanted Items Collection` (3725196303) — *"a matrix of 24 skills × Vol.1–5"*
`Easy Literature` (2914650723) — found / not-found literature tracker

The first two are the same feature written twice.

### A-new-11. Two grenade/explosive packs
`US Military Grenades` (3745718141, craftable Mk2/M26/M67, mines, flares) ·
`ExtraBombs 2` (3652008781, remote triggers, four tiers)

### Still open from run 1

- **A2 — the resting mod, twice.** `twistrestingmodonly` (20 QoL - Actions) and `twistresting`
  from the QoL Modpack (02 Firsts, index 6 of 12) are both live. The modpack page asks you not
  to. The census confirms they are separate code: 156 files vs 45, no shared paths.
- **A3 — two wardrobes.** NeatUI Equipment (85 files) and Quick Fits (23 files), adjacent in
  18 QoL - Core UI. NeatUI Equipment is the superset.
- **A5 — two structure-health readouts.** Show Wall Health (33 files) and Door, Fence &
  Furniture Health Display (24 files). Same information, one on demand, one always on.
- **A6 — bag-bottom slots.** Unchanged, and now documented: both mods carry a note stating
  Better Backpack Bottoms loads first (which is the current order, 23 then 24 in 08 Gears).
- **A7 — belt flashlight**, now three-way rather than four: Simple Belt Flashlight+,
  ExpandedAttachements, Common Sense, Pack Mule.
- **A9 — two bulk-packing economies.** More Packing (−90%, any item) still makes Hoarder's
  Delight's crafted cartons redundant.
- **A13 — two Humvees**, KI5 and Papa_Chad.
- **A12 — the Character Info screen** is now settled in Neat Rocco's UI's favour, because both
  challengers are gone. Note Rocco's still replaces the **Learning window**, where Unwanted
  Items Collection and Skill Book Library both want to live.

---

## 2. Tier B — same system, different opinion

### B-new-1. Under the Hood lands on four existing vehicle mods
`Under the Hood [B42] [BETA]` (3780938346) is a full vehicle-maintenance overhaul — engine oil
and viscosity, filters, coolant, radiator hoses, head gaskets, brakes, ignition — and it is the
largest new mod by code volume in this pass (**114 Lua files**). It arrives on top of:

- `Restore Engine Quality` (3543612325, also new) — restores the vanilla engine-quality stat
- `Car Parts Repair` (3281301960) — repair without resources
- `Better Auto Mechanics` (3635856965) — one-click training
- `Immersive Cars: Decay` (3495105059) — simulated condition decay
- `More Car Features` (3520758551, 44 files) — vehicle quality rebalance

Six mods now write to vehicle condition. Under the Hood is BETA and the most opinionated; it is
the one to decide about first.

### B-new-2. Bandits: Adaptive Threats overrides your own clan scheme
`Bandits: Adaptive Threats` (3791560174, mod id `HumanRemains`) — *"Five-stage NPC progression…
Balanced encounters, camps, bases, and roadblocks."*

Your `Lua\bandits\clans.txt` is a hand-tuned six-era scheme spread over about five in-game years,
with companions removed and spawn rates cut so roaming groups stay rare. A mod whose stated job
is to supply progression and encounter balance for Bandits V2 is competing with exactly that
file. Also live: `Bandits Fix Plus` (3777752751, includes a companions fix) and
`Bandits Melee Armor Patch` (3745699559, load after Bandits — it is, in 21 Patches).

### B-new-3. Hydrocraft Reinvented lands on the whole crafting stack
`Hydrocraft Reinvented` (3778201332) — **5,196 items, 3,620 recipes, 121 fixing schemes.**
Its stated philosophy is *"complement, don't duplicate"* and it deliberately steps aside on
smithing, pottery, masonry, glassmaking and butchering. It does not step aside on food, drink,
chemistry, mining, beekeeping or weaving — where you already run Long Term Preservation, the six
`[B42.2*]` jar/dry mods, Craftable Vanilla Food Items, Boiling Eggs, Herbalist and Break Big Rocks.

Five thousand new items also land on `Zed's Item Tiers` (rarity rolls on almost any item),
`Better Sorting` (categorises them) and `Total Weight Rebalance` (1600 hand-tuned weights).

### B-new-4. Cye's Push Doors joins the knockdown cluster — and meets EasyDoors
`Cye's Push Doors` (3780683663) makes opening a door damage, stagger or knock down whatever is
behind it. Alongside `BackOff!`, `Risky Unarmed`, `Do not push! PLEASE!!` that is a fourth mod on
zombie knockdown. More concretely: `EasyDoors` (3621001191) opens doors **automatically** when
you run into them — which now means running through a doorway can swing a weaponised door.

### B-new-5. Clothing and Shoe Sizes meets 400+ added garments
`Clothing and Shoe Sizes` (3783807916) assigns you a size and blocks anything two sizes off, with
a movement penalty for near-misses. You run Vanilla Clothing Expansion (240+ variants), Vanilla
Outfits Expanded, Spongie's Clothing, KATTAJ1 Military, ALICE Gear and more — every one of those
items now needs a size. `Working Run Modifier` is a second movement penalty from clothing.

### B-new-6. Real Flashlights vs the other light mods
`Real Flashlights` (3787125307) multiplies **all vanilla light sources** by 0.6 and is tuned
against `[B42MP] Lantern Fix` (which it names). It is not tuned against
`Nepenthe's High Beams` (3438126404), which exists to make headlights reach much further.

### B-new-7. Fuel gets a second type and a second status display
`Diesel Fuel` (3784993266) splits vehicles into petrol and diesel and adds diesel to pumps.
`Gas Pump Indicator` (3755993986) paints pump state onto the LED slit.
Both sit on top of `More Car Features`, which already reworks *"refueling vehicles from pumps at
gas stations… fuel station status"*. Also in that system: Vehicle Fluid Logistics, Water Trailer,
the KI5 tanker add-on and Car to Car Siphon.

### B-new-8. Fifth-Wheel RV vs RV Interior Expansion
`Fifth-Wheel RV Trailer` (3775310562) ships its own built-in interior and declares itself fine
alongside `[B42]Project RV Interior`. It says nothing about `RV Interior Expansion` (3618427553),
whose page says *"Not compatible with other custom interior mods."*

### Still open from run 1

B1 reading speed (M-13's vs Immersive Reading) · B2 ballistic vests (Armored Vests vs No Holes —
and the census confirms No Holes ships **no Lua at all**, so it is pure item-script replacement,
which is exactly why the Armored Vests buff will not follow) · B3 the clothing texture overwrite
chain · B4 the trait economy, now six mods · B6 infection (the Antibodies fork's mod id changed
from `lgd_antibodies` to `AntibodiesB4220Community`, so any mod checking for the old id — Wounds
Overhaul names Antibodies as supported — will no longer see it, and your existing sandbox values
for the old option keys are orphaned) · B7 evolved-recipe menus · B9–B28 as before.

---

## 3. Tier C — stacking

Unchanged in kind, larger in degree. Skill XP faucets now include `Skill Book Library`;
mood relief gains `Playable Arcade`; encumbrance relief is unchanged; the trait stack is at six
mods. `Spoiling Liquids` and `Worm Digging` are additive and conflict with nothing.

Map ground overlap is still pzmods' own job — but you added twelve maps and removed ten this
week, so the Issues tab's cell check is worth a look before your next new save.

---

## 4. The file-path census

This is the pass descriptions cannot do. Method: for every mod in the 16 script-bearing tags,
list every file under the version folders the game actually loads, and compare against the
game's own `media\lua` tree read from the install.

| | |
|---|---|
| mods examined | 401 |
| of those, shipping Lua | 382 |
| distinct mod Lua files seen | 8,310 |
| vanilla Lua paths on disk | 2,707 |
| **mods that replace a vanilla Lua file** | **9** |
| **distinct vanilla files replaced** | **47** |
| **paths shipped by two or more mods** | **7** |
| of those, a vanilla file | **1** |

**The headline is reassuring.** 373 of 382 mods stay entirely inside their own namespace — they
hook and patch at runtime rather than shipping copies of the game's files. The risk is
concentrated in nine mods, and only one vanilla file is contested.

### 4.1 The one contested vanilla file

```
client/ISUI/ISInventoryPaneContextMenu.lua
    CleanUI            [02 Firsts, index 10 of 12]
    twistbetterpause   [02 Firsts, index 1 of 12]
```

Both ship a complete replacement of the same vanilla file. Only one can load: **the later one
wins, and CleanUI is later.** TwisTonFire – Better Pause's copy of that file never runs.

This is worth sitting with, because it inverts the mod's own instruction. Better Pause's page
says **"FIRST IN MOD LOAD ORDER"** — and being first is precisely what makes it lose a
whole-file replacement. The author knows, and ships a `twistbetterpause_cleanui_compat` module
*"loaded after Clean UI"*, with the recommended order

```
1. TwisTonFire - Better Pause
2. Clean UI
3. Better Pause Clean UI Compatibility
```

**Your setup already satisfies this**, though not obviously: Better Pause is first in
`02 Firsts`, CleanUI is tenth in the same tag, and the compat module is tagged into
`19 QoL - Secondary UI` — a later tag, so it loads third. Nothing to change. Recorded because
the census made it look broken until the compat module turned up two tags later, and because it
is the exact pattern to check for whenever a mod says "load me first" and then ships a whole
vanilla file.

### 4.2 The nine mods that replace vanilla files

| mod | tag | vanilla files replaced |
|---|---|---|
| **CleanUI** | 02 Firsts | **33** |
| **TwisTonFire – Better Pause** | 02 Firsts | 6 |
| TwisTonFire – QoL Modpack (`twistresting`) | 02 Firsts | 3 |
| Faster Hood Opening | 16 Balance | 1 |
| Consolidate All Fix | 20 QoL - Actions | 1 |
| Better Vanilla Trapping | 19 QoL - Secondary | 1 |
| Fox's Butchering Fix | 16 Balance | 1 |
| Rebalanced Prop Moving | 16 Balance | 1 |
| Simon MD's Tiles | 03 Frameworks | 1 |

**CleanUI is the centre of gravity of your whole setup.** It replaces the inventory pane, the
inventory page, the context menu, the loot window controls and 28 of the small
`LootWindow/Handlers/*.lua` files — plus two that have nothing to do with inventory:
`shared/TimedActions/ISFixAction.lua` and `ISFixVehiclePartAction.lua`, the vanilla repair
actions. Anything that patches vehicle-part repair is patching CleanUI's copy, not the game's.

Two more things its folder shows: it ships `ISInventoryPane.luabkp` and
`ISInventoryPaneContextMenu_VanillaB42.16.1.luabkp` — the vanilla originals it forked, labelled
**42.16.1**, while you run 42.20.4. That is normal practice for this kind of mod, but it means
any vanilla context-menu change between 42.16.1 and 42.20.4 is absent from your game.

**Better Pause's other five** are worth knowing because each is a whole vanilla screen:
`ISWorldObjectContextMenu.lua`, `ISMenuContextWorld.lua`, `ISHotbar.lua`,
`ISVehicleMechanics.lua`, `ISHealthPanel.lua`. So Better Pause — not Mini Health Plus, not
Wounds Overhaul — owns the base copy of the vanilla health panel; and it owns the vehicle
mechanics panel that Neat Rocco's UI, Better Auto Mechanics and Under the Hood all reach into.

**Simon MD's Tiles replaces `client/Foraging/ISZoneDisplay.lua`** — a tile pack quietly owning a
vanilla foraging file. It sits in 03 Frameworks, so it loads early and anything later wins; worth
knowing it is there at all.

### 4.3 The six mod-file collisions

```
client/Hooks/DAMN_SemiAttachmentHelper.lua
    damnlib        [03 Frameworks]     the framework's own file
    KI5minifixes   [21 Patches]        overwrites it
```
Deliberate, and the order is right (patches load after frameworks) — but it means KI5 Mini-fixes
is silently replacing a file inside damnlib, the library **58 other mods depend on**. If a KI5
vehicle misbehaves in a way General Fixes claims to fix, this is the first place to look.

```
client/ISUI/ISUI_EasyLaundry.lua
    EasyLaundry             [20 QoL - Actions]   ← installed but untagged, never loads
    EasyLaundryB4220Fixed   [21 Patches]
```
Confirms the earlier read: the "Fixed" version is a whole-file replacement, not an additive
patch. Because the original wears no tag, nothing collides today — but enabling both would be a
straight conflict. Unsubscribing the original is safe.

```
client/TheyKnew_InfectionMeds.lua
server/Items/TheyKnew_OnDeathDistribution.Lua
shared/NPCs/TheyKnew_BodyLocations.lua
shared/NPCs/TheyKnew_ZombieDefinition.lua
    TheyKnewB42        [12 Mechs - Core, index 3]
    TheyKnewB42Patch   [12 Mechs - Core, index 4]
```
Four files replaced by the patch — which is how the patch works, and your order is correct
(base at 3, patch at 4). No action; recorded because it is the pattern to recognise elsewhere.

### 4.4 What the census settled about earlier findings

- **A6 stands.** Both bag-bottom mods live in `08 Gears`, outside this census's tag scope, but
  neither ships a vanilla file — they collide in the attachment tables at runtime, which is what
  the note now records.
- **A8 is closed by removal**, but the census shows why it mattered: CleanUI owns the whole
  `ISInventoryPaneContextMenu.lua` file. Common Sense's 90 files are all in its own namespace
  (`BB_CS_*`, `VB_CS_*`), so it patches CleanUI's copy at runtime. Anything else touching the
  magazine menu is a third layer on the same object.
- **B2 sharpened.** `No Holes For Ballistic Armor` ships **no Lua at all** — it is item scripts
  only, i.e. new item definitions copied from the vanilla vests. Armored Vests' Lua-side buff
  cannot reach copies made that way. This is now confirmed rather than suspected.
- **A5 confirmed independent.** Show Wall Health (33 files) and Door/Fence Health (24 files)
  share no paths — two complete implementations running side by side.
- **False alarm retracted.** Pain Sense ships a file called `client/InjuryIndicator.lua`, which
  looked like a collision with the Injury Indicator mod. It is not a vanilla path and Injury
  Indicator is gone; the name is a coincidence of naming, not a conflict.

### 4.5 Translation files — noise, not signal

299 paths are shared by two or more mods, and 293 of them are translation files:
`shared/Translate/EN/Sandbox.json` is shipped by **109** mods, `UI.json` by 94, `IG_UI.json` by 81.
The game merges translation tables rather than replacing them, so this is normal and expected.
It is listed only so the number does not alarm you if you run the census yourself.

### 4.6 What the census still cannot see

Two of the three blind spots from run 1 remain, because both need file **contents**, not names:

- **Item-script collisions** — two mods defining the same `Base.Item`. This is where
  Hydrocraft's 5,196 items, Zed's Item Tiers, Total Weight Rebalance and the clothing packs
  would show up.
- **Sandbox option key collisions.** I tried to read these directly and could not: staging is
  all-or-nothing over the bridge, and a batch containing one non-existent path fails whole.

Both are covered by **`census.py`**, now sitting in your pzmods folder. It does everything above
plus those two, on the full 563 items rather than the 401 I could reach, in one pass:

```
cd C:\Users\igor\Zomboid\pzmods
python census.py
```

Standard library only, reads only, writes `census\census.json` and `census\census.txt`. It reads
your build from the game's log the same way pzmods does, and picks the same active version folder.
Worth re-running after any big Workshop update — this class of conflict appears silently.

---

## 5. Housekeeping

| item | state |
|---|---|
| Nine unsubscribed mods still named in the config | Issues tab → **Forget the N uninstalled** → Save |
| `TwisTonFire - Outside Freezer` (3566244478) | **Still delisted, still installed, still tagged** into 15 Mechs - Environment. Newest version folder 42.13; you run 42.20.4 |
| `[B42] Medicine Moodles` (3778856579) | **Still inverted** — the base `MedicineMoodlesB42` is on `-- Disabled`, only the `…SkillRequirements…` add-on is enabled |
| `Easy Laundry` (2925034918) | Still untagged, never loads; census confirms the Fixed version fully replaces it. Safe to unsubscribe |
| `Mod Comparer` (3019672735) | **Resolved** — now tagged into 01 Utils |
| Better Pause CleanUI compat module | Enabled and correctly ordered (in 19 QoL - Secondary UI, so it lands after CleanUI). No action — see §4.1 |
| `Vanilla Clothing Expansion` | Still 7th of 26 in 08 Gears, still asking to be last; see B3 |
| Notes added | `BBB` and `BagBottomWeaponAttach` now carry the load-order note, marked `-AI-` so they show red until you clear them |

---

## 6. How deep could a Lua-level review go?

You asked me to assess this rather than do it. Here is the honest shape of it.

### What it would actually buy you

The census answers *"do two mods ship the same file"*. It cannot answer the question that
matters more in Build 42, because almost every modern PZ mod works by **monkey-patching at
runtime**: it keeps a reference to a vanilla function and replaces it with its own.

```lua
local old_doMagazineMenu = ISInventoryPaneContextMenu.doMagazineMenu
function ISInventoryPaneContextMenu.doMagazineMenu(player, context, items)
    old_doMagazineMenu(player, context, items)   -- polite: chains
    ...                                          -- rude: doesn't
end
```

A Lua review would extract, for every mod, the set of **global functions it overwrites** — and
then two mods overwriting the same function is a real finding, whether or not they share a file.
That is the thing your collection has a lot of and I currently cannot see. Concretely, it would
have found the Common Sense × Load All Magazines collision from the code rather than from a
sentence in a description — and it would find every one of that class that nobody wrote down.

It would also catch:
- **Chain-breaking**: a mod that replaces a function without calling the previous version. Two
  polite mods coexist; one rude mod silently kills everything loaded before it. This is the single
  highest-value thing a code pass produces, and it is invisible from every other angle.
- Event-handler pile-ups on `OnPlayerUpdate` / `OnTick` — a performance map, not just a conflict map.
- Keybind registrations, which would have found the `;` collision automatically.
- Sandbox keys and item ids, though `census.py` gets those far more cheaply.

### What it would cost

The corpus is roughly **8,300 Lua files** across 382 mods in scope, and closer to 12,000 across
all 563 items. Very rough sizing from what I saw: 30–60 MB of source, tens of millions of tokens
if read naively. That is not the way to do it.

The tractable shape is **two stages, and only the second one needs a language model**:

**Stage 1 — a parser, not a reader.** Perhaps 300 lines of Python on top of `census.py`. Regex
and bracket-matching over each file for:
- `function <Global>.<name>(` and `<Global>.<name> = function` — declarations
- `local old = <Global>.<name>` followed by reassignment — the monkey-patch signature
- whether the saved reference is called inside the new body — the chain test
- `Events.<Name>.Add(` — event registrations
- `getCore():addKeyBinding` / `ISModOptions` — keybinds and options

Output: a table of *(mod, global function, patches-or-declares, chains-or-not)*. Then the same
group-by that produced §4. This runs in seconds on your machine, costs nothing per run, and
produces the 80% finding: **every function two or more mods overwrite, flagged red where one of
them does not chain.** I would estimate a few hours of my work to write and test it, and it
would be re-runnable forever.

**Stage 2 — reading the actual code**, and only for what stage 1 flags. If stage 1 finds, say,
40 contested functions, reading both sides of each is maybe 80 files — a few hundred KB, entirely
affordable, and that is where you learn *which* mod should win and whether the loser is merely
shadowed or actively broken.

### My honest opinion

**Stage 1 is clearly worth doing and I would recommend it.** It is a bounded piece of
engineering with a permanent payoff, it needs no AI at runtime, and it targets the exact failure
mode your collection is most exposed to — 373 mods all monkey-patching the same vanilla surface.
It is the natural next tool after `census.py`, and it is the same kind of tool.

**Stage 2 is worth doing only on stage 1's output**, never as a sweep. A blind read of 8,000 Lua
files would be expensive, slow, and would mostly rediscover that mods are written normally.

And a caveat I would rather say than have you discover: even a perfect static pass has a ceiling.
Load order is decided by your config, some patches are applied conditionally at runtime, and the
game itself reloads Lua in ways a static reader cannot model. It will tell you where to look with
high precision. It will not tell you the game works — only playing does that.

The cheapest thing on this whole list, by a wide margin, remains what you already have: run
`census.py`, act on the nine tagged-but-uninstalled entries, enable the Better Pause compat
module, and pick one of Towbars / Harry's Tow Truck.
