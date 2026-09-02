# Feature overlap cross-check — 514 subscribed Workshop items

Generated 2026-09-01 · game build 42.20.4 · source: `pzmods\data\steam.json` (Workshop
descriptions), `snapshot.json` (`mod.info`), `tags.json` (what is on `-- Disabled`).
Online lookups: none needed.

## How to read this

Every item was placed in a feature domain and compared against everything else in that
domain. A finding only appears here if **both sides are currently enabled** — mods you
have already switched off with `-- Disabled` are in §4, as confirmation, not as work.

| tier | meaning |
|---|---|
| **A — duplicate** | two mods do the same job. One is redundant, and in a few cases they fight |
| **B — rivals** | same system, different opinion. Works, but one is deciding the outcome and it may not be the one you meant |
| **C — stacking** | nothing conflicts, the effects just add up. Listed so the total is visible |

Note on your setup: only **1** of 514 items is fully disabled (ZBLuaPerfMon). The
`-- Disabled` tag is doing variant-selection work almost everywhere else — 42 items have
some sub-mods off and one on. That is why several mods you may think of as "off" are
counted as live below.

---

## 1. Tier A — duplicates, both live

### A1. Two injury pop-ups over the character's head
`Injury Indicator [B42]` (3565698092) · `Pain Sense` (3599368309) — both in **18 QoL - Core UI**

Identical concept: text above the head naming the hurt body part, plus a heal
notification. PainSense loads later (index 24 vs 10), so you see both fire.
PainSense is the superset — it also announces when a bandage can come off and when
stitches can be pulled.
**Keep PainSense, drop Injury Indicator.**

### A2. The resting mod, installed twice, by the same author
`TwisTonFire - Restingmod` → `twistrestingmodonly` (3480790670, in 20 QoL - Actions)
`Quality of Life Modpack` → `twistresting` (3480305875, in 02 Firsts)

Both are live. The modpack page says it plainly: *"Please do not use other mods that
overlap with features already included here. Most error reports I receive are caused by
duplicate or overlapping mods being used alongside this pack."* Both carry the resting
status feedback, the post-rest game-speed reset and a status HUD.
**Pick one.** The standalone has the newer configurable HUD; the modpack version loads
first and carries the rest of the pack's tweaks.

### A3. Two wardrobe / outfit-set systems
`Quick Fits` (3684691347) · `NeatUI Equipment` (3790656296) — adjacent in 18 QoL - Core UI

Both: save an outfit, wear it back later, pull the missing pieces out of nearby
containers, strip everything in one press. NeatUI Equipment also gives you the 3D doll
panel and matches the rest of your NeatUI stack.
**NeatUI Equipment covers Quick Fits entirely.**

### A4. Two on-screen XP gain readouts
`Neat XP Drop (Fixed)` (3775242298) · `[B42MP] Simple Show XP` (2891170430) — indices 20 and 21

Same job, two widgets on screen at once. Neat XP Drop matches your NeatUI theme; Simple
Show XP sums all perks into one line.

### A5. Two structure-health readouts
`[B41&B42] Show Wall Health` (3002666175, in 10 Craft) · `Door, Fence & Furniture Health
Display` (3788067801, in 19 QoL - Secondary UI)

Same information, different delivery: Kamer's is a right-click "Check Status" menu, the
other is live bars over damaged structures within a radius. The newer one covers doors,
gates, barricades, fences and furniture — a superset of what "anything you built"
reaches.

### A6. Two mods rewriting the same bag-bottom slots — order decides the winner
`Better Backpack Bottoms` (3789055972) · `Bag Bottom Weapon Attach` (3688814370)

Both patch the attachments provided by `BedrollBottom`, `BedrollBottomBig` and
`BedrollBottomALICE`. BBB puts toolboxes, first-aid kits, gas cans and bottles there;
BagBottomWeaponAttach puts rifles and big blades there. In **08 Gears** your order is
`… BBB, BagBottomWeaponAttach` — the weapon one is last, so where they both touch the
same bag it is the one that lands. If you have noticed BBB's containers refusing to
attach on some packs, this is why.
**Try swapping their order inside the tag before dropping either.**

### A7. Flashlight-on-belt, from four directions
`[B42] Simple Belt Flashlight` (3625933422, 16 Balance) · `ExpandedAttachements`
(3774158741, 08 Gears — "Hand Torch", "Large Flashlight for belts only") ·
`Common Sense` (3750253491, feature 4: *"Attach hand Flashlights to the toolbelt"*) ·
`[B42] Pack Mule` (3540903327, "Attach: Lantern", "Attach: Welding Torch")

Four mods offering the same belt slot. ExpandedAttachements and Pack Mule also overlap
on the propane/welding torch. Simple Belt Flashlight is the narrowest of the four and is
a self-described "reupload of a reupload" — it is the obvious one to test without.

### A8. Reload-all-magazines, declared incompatible
`[B41 / B42] Load All Magazines` (2920899878) · `Common Sense` (3750253491, feature 3:
*"(new) Reload all selected magazines at once"*)

Load All Magazines states: *"Modifies `ISInventoryPaneContextMenu.doMagazineMenu`, so
will be incompatible with any other mods that change this function."* Common Sense added
exactly this feature in its revival. **This is the highest-risk pair in the collection** —
it is a named function collision, not a taste question. Common Sense also asks to be put
at the end of the load order, which would put it after Load All Magazines.

### A9. Two bulk-packing economies
`Hoarder's Delight` (3626823538, 300+ crafted boxes, −1/6 encumbrance) ·
`More Packing` (3478922403 / `vac_mod_b42_6`, generic parcels, −90% weight, up to 300 kg)

More Packing works on any item from any mod at a far better ratio and needs no recipes,
which makes Hoarder's Delight's crafted cartons pointless in practice. Running both also
means two parallel weight-reduction paths on the same items.

### A10. Two trapping helper windows
`Trap Manager` (3566766862) · `TwisTonFire - Better Vanilla Trapping`
(3573232324 → `twisttrappingvanilla`, the variant you left enabled)

Both are read-only helpers over vanilla trapping: which animal, which bait, which zone,
what odds. Trap Manager adds the sortable trap table and catch-chance simulator; Better
Vanilla Trapping adds the in-game wiki plus small QoL. Neither changes mechanics, so
this is pure duplication of screen and menu space.

### A11. Two vehicle crash-injury systems
`Vehicle Safety - Seatbelt, Crash & Ejection` (3685035630) ·
`Proper Vehicle Injuries for MP` (3007922923) — both in 06 Vehicles - Mechs

Vehicle Safety says: *"Set 'Player Damage From Crash' to FALSE in sandbox options — this
mod fully replaces the vanilla crash system."* PVI's whole design is to make the vanilla
crash damage consistent and configurable, and it carries its own seatbelt integration.
Turning vanilla crash damage off to satisfy Vehicle Safety takes PVI's foundation away;
leaving it on means two crash systems firing on the same impact.
**These two cannot both be right. Choose.**

### A12. Three mods over the Character Info screen
`Neat Rocco's UI` (3723726293) replaces the *character info window (stats, health, skills,
clothing)* **and** the *fitness training window*
`TwisTonFire - Better Character Info` (3488600400, in 02 Firsts) overhauls the Character
Info screen
`TwisTonFire - Exercises` (3790614739) reworks the vanilla Exercise window

Better Character Info loads in 02 Firsts, Neat Rocco's in 18 QoL - Core UI — so Rocco's
replacement lands last and is very likely painting over the avatar system you installed
Better Character Info for. Same story for Exercises vs Rocco's fitness window.
Rocco's has a per-mod toggle (Options → Mod Options → Neat Rocco's UI → *Use Neat
Rocco's UI*) — but it is all-or-nothing, so the fix is deciding which of the three owns
the screen.

*While you are there:* Rocco's also replaces the **Learning window (books, recipes,
media)** — which is exactly where `Unwanted Items Collection` (3725196303) adds its four
tabs — and the **Animal info / livestock zone panels**, where `Better Animal Care`
(3582024827) adds its context menu. Worth a look in-game.

### A13. Two Humvees spawning side by side
`'92 AM General M998 + M101A3 Cargo trailer` (KI5, 2642541073) ·
`U.S. M998 Humvee by Papa_Chad` (3554424111)

Same real vehicle, two independent models, two spawn entries, two parts trees. Not a
bug — but with `Vehicle Military Zones` and both `Specific Loot` mods live, military
spawns are rolling from two Humvee pools.

---

## 2. Tier B — same system, different opinion

### B1. Reading speed, pulled both ways
`M-13's Reading Tweaks` (2776874515) makes reading faster and possible while walking.
`Immersive Reading` (3606009875) makes reading *slower* and spreads the mood payoff
across the duration. Both in 16 Balance, Immersive Reading first. Whichever hooks the
timer last sets the speed; the other's sandbox sliders will read as having no effect.

### B2. Ballistic vests: buffed, then replaced
`Armored Vests` (1962761540) raises bite/scratch protection on the three bulletproof
vests (plus a VGE patch for the modded ones).
`No Holes For Ballistic Armor` (3683430283) *"replaces the vanilla bullet-proof armor
items with nearly identical copies"* that cannot get holes.
A copy made from the vanilla item does not inherit Armored Vests' edits. Expect the
no-holes vests to be the plain vanilla stat line.

### B3. Vanilla clothing textures — an overwrite chain the author documented
`Vanilla Outfits Expanded` (3783094058) says on its own page:
*"Vanilla Clothing Expansion: compatible, but will overwrite this mod's texture
variants"* and *"Spongie's Open Jackets: currently not supported on new textures/items,
will overwrite vanilla variants from this mod when rolling/opening."*
All three are live: VOE (08 Gears, index 20), `Vanilla Clothing Expansion` (3421271152,
index 6), `Spongie's Open Jackets` (2812326159, indices 12–13).
VCE asks to be *"at the VERY bottom of the load order"* to fix icon mismatches — but VCE
currently loads **before** VOE, i.e. VOE's variants win. If you moved VCE to the bottom
as its page asks, VOE's new textures would start losing. Decide which mod you want to be
the last word and order 08 Gears accordingly.

### B4. Four trait mods, one point economy
`SOTO` (2840805724 — 40+ traits, 26 occupations, *"making vanilla occupations and traits
viable"*) · `Somewhat Traits` (3498347699 — 16 positive, 16 negative, **expands 14 vanilla
traits**) · `Sandbox Traits` (3777244656 — 9 positive, 3 negative) ·
`Challenge Traits` (3634630898 — 15 starting-injury traits)

SOTO and Somewhat Traits both rewrite *vanilla* traits — that is a head-on collision, not
an addition. On top of those, traits also arrive from `Toughness Skill`, `Combat
Mastering Skill`, `Efficiency Skill Mod 2`, `SixthSense`, `Break Into Tears` and `B42
Driving Skill` (which retunes the Cab Driver occupation). `SixthSense`'s own page carries
a "BROKEN (balance trait mod…)" note. You do have `JeevesPatches_SOTO` enabled, which is
the right instinct.

### B5. Five things drawing on the health panel
`Wounds Overhaul` (3775026731) — replaces the Health tab outright and states
*"Not with other health or blood overhauls"*; declares Antibodies compatible
`Nested Health Info` (3779405481) — *"Load this mod before any other mod that adds
something to the health panel"*
`Mini Health Plus` (3710913197) · `StatZContinued` (3637486686) · Restingmod's status HUD
The two hard ones are Wounds Overhaul × Nested Health Info (both rewrite what the panel
shows under a bandage — Wounds Overhaul already has "a bandage hides the wound" as a
designed behaviour, which is what Nested Health Info exists to undo) and Wounds Overhaul
× Mini Health Plus. Nested Health Info is currently in 19, i.e. **after** Wounds Overhaul
in 13 — the opposite of what its page asks for.
The three HUDs (Mini Health Plus / StatZ / Restingmod HUD) are not conflicts, just three
overlapping panels of the same numbers.

### B6. Three answers to "am I infected"
`Antibodies` (2392676812, recovery curve) · `They Knew` (3387110070, Zomboxivir cure and
Zomboxycycline prophylaxis) · `Knox Detection Kit` (3688879406, blood test) ·
`Wounds Overhaul` (Knox stage readout, transfusions carry Knox).
Wounds Overhaul names Antibodies as supported. Nothing declares anything about They Knew,
and its pills reset or purge infection outright — which short-circuits the antibodies
curve Antibodies exists to make you play.

### B7. Three mods reshaping the evolved-recipe list
`Project Cook` (3490188370) replaces the cooking interface for evolved recipes ·
`Neat Ingredients List` (3490768151) groups duplicate ingredients in that list ·
`Don't Open New One` (3696528833) changes which container the evolved recipe menu picks.
Project Cook is a full replacement, so the other two may be patching a list that is no
longer on screen.

### B8. Four overlapping ways to reach nearby loot
`Proximity Inventory` (2847184718 — every nearby container on one page) ·
`Loot Goblin 2000` (3694894350 — search nearby containers for one item) ·
`Auto Loot` (3392699932 — auto-loot plus "Store All" spreading) ·
`Picking Meister` (3422220305 — grab contents, unpack, retrieve ammo)
Loot Goblin's core question ("which box has the screwdriver") is already answered by
Proximity Inventory's single page. Auto Loot and Picking Meister are distinct enough.

### B9. Vehicle condition, decided twice
`Immersive Cars: Decay` (3495105059) simulates decay on world vehicles ·
`More Car Features` (3520758551) rebalances vehicle qualities and controls the chance to
spawn burnt or damaged. Both write to the condition of the same spawned cars.
`TEH Big Car Trunks` (3502122415) is also live and rebalances capacity that More Car
Features touches; TEH asks to be sorted to the very bottom.

### B10. Vehicle part repair, twice
`Car Parts Repair` (3281301960 — repair without resources, poorly) ·
`Better Auto Mechanics` (3635856965 — one-click mechanic training). Different aims, same
part-repair path, and both interact with `Neat Rocco's UI` replacing the vehicle
mechanics panel.

### B11. Dashboard condition — possibly already vanilla
`Condition On Dash` (3306168142). Common Sense lists *"Highlight vehicle's engine, battery
and fuel condition in the dashboard"* under **"Features already in vanilla"** as of
42.20. Worth checking whether this mod is still adding anything.

### B12. Two ways to refill a torch
`Tanks Have Propane` (3676347667 — refill tanks and blowtorches at Fossoil/Gas2Go storage
tanks, plus optional gas pumps and small tanks) · `Refill Welding Torch with Propane
Bottle` (3429836096 — 4 uses from a propane bottle). The second is a small subset of the
first's remit.

### B13. Two orchard systems
`Farming Expansion B42` (3444499190 — apple and grape, perennial, survive winter) ·
`Infoteo's Fruit Trees` (3783566179 — apple, banana, cherry, lemon, orange, peach,
pineapple). Both add a plantable apple tree with its own growth cycle and seed source.

### B14. Water plumbing, two designs
`PlumbingFixed` (3626008449) makes a plumbed sink draw from *all* barrels ·
`Water Pipes` (3739612285) lays a real pipe network that moves water between floors.
Both reroute where a plumbed fixture gets its water. Around them: `Functional Gutters`
(3439305933) and `My Own Well` (3549290115) as sources, `Water Goes Bad` (2849467715)
spoiling the stored side, and `Vehicle Fluid Logistics Library` (3791686284) +
`Water Trailer` (3776875714) + `Water Bidon` (3628782804) + `Useful Barrels` (3436499337)
as portable storage. The pair worth testing is PlumbingFixed × Water Pipes.

### B15. Weather and night colour, three hands
`[KYR] Real Weather Mod` (3051276857 — a full weather overhaul) ·
`Here Goes the Sun` (3618557184 — sunrise/sunset palettes by season and weather) ·
`Blue Moon` (3616381828 — blue night tint).
Here Goes the Sun explicitly declares Blue Moon compatible and warns about *"climate
mods that change night colours"* — which is exactly what a full weather overhaul does.
KYR is the undeclared one in this trio.

### B16. Three window-traversal mods
`Auto Smash, Clear & Jump through windows` (3495788089 — one-click smash, clear, climb) ·
`Sprint Through Windows` (3791228868 — dive through while sprinting) ·
`[B42] Hand Bag Window Climb` (3389093252 — keep held bags when climbing).
Different triggers, one animation path. Note the Auto Smash page itself advertises a
successor to Better Sorting — which you also run (`Better Sorting`, 2313387159).

### B17. Three mods on the shove
`[B42] BackOff!` (3647810515 — shoves knock down multiple zombies even without multi-hit) ·
`Risky Unarmed` (3434796669 — shoving and stomping can be counterattacked) ·
`Do not push! PLEASE!!` (3511400502 — pushed zombies tumble others down stairs).
Individually reasonable; together the shove is being modified by three mods that do not
know about each other, and two of them move in opposite directions on how safe it is.

### B18. Buildables, from two catalogues
`Jeeve's Build` (3705530591) generates ~5000 buildable entries from your five tile packs —
including **functional wall light switches** and garage doors.
`Custom Light Switch` (3779343349) adds a buildable functional wall light switch.
`Neat Building` (3536052310, full variant) adds its own extra buildables and reorganises
the menu they all appear in.
Two light-switch implementations is the concrete duplicate here.
⚠️ Separately: Jeeve's Build is **not safe to remove** once garage doors are placed, and it
hard-requires all five tile packs. Treat it as a one-way door on any save.

### B19. Two spawn-point pickers
`Spawn Selector` (3772052709 — full world map, pick any tile) ·
`[LM] Wilderness Spawn Locations` (3513206060 → `LMWildSpawnMaps`, adds wilderness entries
to the starting-location menu). Spawn Selector supersedes the second entirely.

### B20. Ground clearing, four ways
`Batch Floor Action` (3654929003 — area select: fell trees, clear weeds, remove shrubs,
pick stones) · `Lawn Care: Scythe & Rake` (3475536311 — mow grass, sow grass) ·
`Clean Ashes` (2816646537 — manual ash sweeping) · `Rain Cleans Blood` (2956146279 —
removes ash, blood and dung automatically when it rains).
Rain Cleans Blood makes Clean Ashes largely idle; Batch Floor Action and Lawn Care both
answer "get rid of this grass".

### B21. Five mods tracking what you've read and learned
`Easy Literature` (2914650723 — found/not-found literature tracker) ·
`Unwanted Items Collection` (3725196303 — skill-book matrix, magazines, recorded media
tabs) · `What Did I Just Learn?` (3777737368 — recipe discovery history) ·
`Named skill VHS tapes` (2732294885 — renames tapes to show the skill) ·
`Show VHS skills in tooltip` (3716522633 — shows the skill in the tooltip).
The last two answer the identical question in two places. The first two both maintain a
book/media ledger.

### B22. Map symbols, twice over
`Map Symbols Plus (Hand-drawn)` (3399645148) adds symbols and recommends pairing with a
"Map Symbol Size Slider".
`TwisTonFire - Map Improvements` (3627539752) already ships a symbol size slider, a
reworked symbol interface, extra colours and drawing.
`Map Legend UI` (2710167561) adds the legend — that one is genuinely separate.

### B23. Bathing and drying
`[B42:SP/MP] Take A Bath And Shower` (3592172476, in 02 Firsts) ·
`Bath Towels Overhaul` (3416208765, changes towels and rewrites "Dry Self").
Both own the get-clean/get-dry loop and both touch the towel item.

### B24. Three layers of error handling
`errorMagnifier` (2896041179) surfaces errors · `[B42.20] Console Fixes` (3778165486)
suppresses known false-positive error families via ZombieBuddy ·
`Zed's Universal Mod Unbork` (3677147974) shims renamed game APIs so old mods keep
working. Not a conflict, but Console Fixes can quiet the very message that would tell you
Unbork has stopped covering something.

### B25. Three performance mods
`Multi-Cpu Enhance` (3459875383, JVM args) · `SmartZOptimizer[Legacy]` (3707376688 —
the author's own title says Legacy) · `Zed's Better FPS B42.20.2 Fix` (3782613536).
The last two are both ZombieBuddy Java patches touching zombie/render load. SmartZ being
self-labelled Legacy makes it the candidate to retire.

### B26. Author-abandoned companion
`[Abandoned] Specific Loot (Papa_Chad)` (3459111044) — the title is the author's.
Its sibling `Specific Loot (KI5)` (3457132019) is maintained. Keep the pair only as long
as you keep the Papa_Chad vehicles.

### B27. Three re-equip layers
`Tidy Up Meister` (2769706949 — V2 watches the whole timed-action queue and restores
equipment after *any* action) · `Reequip Secondary` (2821614305 — restores your bag or
flashlight after a two-handed swap) · `Wesch's Better Wringing` (3408740647 — re-equips
clothing after wringing).
Tidy Up Meister V2's queue-observer design already covers the other two by construction,
and its page warns that mods with unusual queue behaviour are where it misfires.

### B28. Overlapping trailer and hauling fleets
`Autotsar Trailers` (3402493701) + `Hauler` (3412003257) · `Trailers!` (KI5, 3330403100) ·
`Containers!` (2625625421) + its mass patch. Four trailer catalogues, no conflict, just a
lot of the same role in the spawn tables.

---

## 3. Tier C — stacking, not conflicting

Nothing here is broken. It is listed because the *sum* is easy to lose sight of.

**Skill XP faucets, on top of vanilla books:** `Skill Book Expansion` (3557111695) ·
`Working Knowledge` (3717099183 — 372 lootable documents) · `Listen & Learn` (3785054147 —
audiobooks and skill CDs, 35 skills, multitask learning) · `Dynamic Emergency TV Channel`
(3409272479) · the `[WYD] VHS Skill Tapes` series (**18 separate items**) · plus
`Reward Night Combat`, `Nimble XP Rebalance`, `Dynamic Fitness Boost`, `Efficiency`,
`Combat Mastering`, `Toughness`, `B42 Driving`. Six independent ways to gain a level
without doing the activity.

**Zed's Item Tiers (3707251461) is a multiplier over everything else in 16 Balance.**
It re-rolls weight, durability and protection on almost any item as it spawns — sitting on
top of `Total Weight Rebalance` (1600+ hand-tuned weights), `Durable Tools`,
`Armored Vests`, `No Holes`, and `Working Run Modifier`. Each of those was balanced
against vanilla, not against a rarity roll.

**Mood relief:** `Sleep On It`, `Wilderness Calm`, `Break Into Tears`, the Walkman
ecosystem (music reduces boredom and sadness), `Lifestyle: Hobbies`, plus your own
`CompanionCatPurr`. Six sources of unhappiness reduction.

**Encumbrance relief:** `More Packing` (−90%), `Hoarder's Delight` (−1/6),
`Dynamic Backpack Upgrades`, `Pack Mule` vest capacity, `Remove Inventory Limits ZB`,
`Total Weight Rebalance`, `Wheelbarrow`, `SaucedCarts`, `Zed's Item Tiers` (lighter bags).

**Map ground overlap** is deliberately not covered here — pzmods already computes it from
the `.lotpack` cells on the Issues tab, which is more reliable than any description.

---

## 4. Already resolved — your `-- Disabled` picks, confirmed correct

Worth recording, because these are the traps you have already walked around:

- `twistonfireinventory` off, `ProximityInventory` on — the two declare each other
  incompatible in `mod.info`. Correct call; the Blacklist half stays on and is unique.
- `SPNCCFaces` off while Tomb's Body textures run — declared incompatible pair, resolved.
- `MarzGuns` (folder `GunsOfMarzPreviousVersion`, "Guns of Marz (Old Version)") off,
  `GunsOfMarz` on. Your GoM patches point at a live base.
- `twisttrapping` off / `twisttrappingvanilla` on — you chose vanilla bait tables.
- Single variants selected on: Drag Bodies Faster (50%), More Variety Loot (25%),
  Every Texture Optimized (`ETO_B`), Harry's Ammo Icons (42.14), Vanilla MRE (42),
  Neat Building (full), EasyDoors, Functional Gutters, Alice's Weapon Sling,
  Hot Brass, LM Wilderness (Maps), and all the Ogrim `-LEGACY` variants.
- `Jeeve's Patches`: only DAMN, SOTO and Tanker enabled — sensible, since the rest target
  a server modpack you do not run.

---

## 5. Housekeeping found along the way

| item | what |
|---|---|
| `TwisTonFire - Outside Freezer` (3566244478) | **Gone from the Workshop** (API result 9) — no title, no description returned. Still installed, still tagged into 15 Mechs - Environment, and its newest version folder is **42.13** while you run 42.20.4. It will keep loading until you untag it. |
| `[B42] Medicine Moodles` (3778856579) | Looks **inverted**: the base `MedicineMoodlesB42` (which is what requires MoodleFramework) is on `-- Disabled`, and only the `MedicineMoodlesSkillRequirementsB42` add-on is enabled. An add-on with nothing to modify. |
| `Easy Laundry` (2925034918) | Wears no tag, so never loads — correct, since `Easy Laundry [B42.20 Fixed]` (3782237215) is a standalone folder with its own 42.20 build, not a patch. Candidate to unsubscribe. |
| `Mod Comparer` (3019672735) | Also untagged, so not in any config. It used to be in `01 Utils` per `groups.json`. Intentional? |
| `Nested Health Info` (3779405481) | Its page asks to load **before** anything else that adds to the health panel. It is currently in 19, after Wounds Overhaul in 13. |
| `Vanilla Clothing Expansion` (3421271152) | Its page asks to be at the **very bottom** of the load order. It is at index 6 of 25 in 08 Gears. |
| `TwisTonFire - Better Pause` (3696291148) | Its page says "FIRST IN MOD LOAD ORDER". It is first inside `02 Firsts`, but every config puts `01 Utils` ahead of `02 Firsts`, so 17 mods load before it. |

---

## 6. What this pass could not see

The base dataset was Workshop descriptions plus `mod.info`. That catches feature intent
and every declared rule, and it caught the two named-function collisions above (A8, A6),
but it cannot see:

- **Which vanilla Lua files each mod actually overwrites.** Two mods shipping the same
  `media/lua/client/ISUI/…` path is a hard, silent conflict that no description mentions.
  A file-path census across the 1262 `mod.info` folders would turn most of the "rivals"
  section from suspicion into fact — that is the natural next step, and it runs entirely
  off files you already have on disk.
- **Sandbox option key collisions** between mods declaring the same option names.
- **Item script overrides** — two mods redefining the same `Base.Item`.

Descriptions also lie by omission: a mod that quietly added a feature in an update
usually does not rewrite its page. Common Sense (A8) is the example — the "(new)" markers
in its list are the only reason that collision was visible at all.
