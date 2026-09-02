# Workshop discovery - selection criteria

This file is read by the `pz-workshop-discovery` skill at the start of every
run. Edit it freely - plain language is fine; the skill follows what is
written here, not a hardcoded copy. Keep one rule per bullet.

## Hard rules (set by Igor, 2026-09-01)

- Process only items published OR UPDATED since the last run (see
  `state.json`). Listing sources: Workshop browse `browsesort=lastupdated`
  (orders by last update time, but lists ONLY mods that have at least one
  update - verified 1 Sep 2026) UNION `browsesort=mostrecent` for the same window (covers never-updated new mods). On the very first run, the window started at the Build 42.20.0 stable release (29 Jul 2026).
- The currently subscribed mods are the taste reference - what "relevant"
  looks like. Read them from pzmods `data/subs.json` + `data/steam.json`.
- Exclude mods already subscribed.
- Prioritize mods with a high rating or a high subscriber count.
- Exclude multiplayer-focused mods (MP-only fixes, sync mods, PvP, factions, safehouse-raid rules and similar). SP/MP mods that work fine in SP stay in.
- Exclude mods targeted at specific PZ servers (server packs, "our server" mods, admin tools, whitelists, announcers).
- Exclude localization/translation mods.
- Exclude music-content mods (New Music, mixtapes, albums, radio-station
  song packs). Radio/TV broadcast content mods are not music mods.
- Exclude scenarios targeted mods (like Day One).
- Mods that accompany already subscribed mods (fixes, patches, add-ons,
  successors, direct alternatives, same-author series) are relevant - even with few subscribers.
- Exclude mods clearly incompatible with the installed game build (read the build from pzmods, currently auto-detected from the game log).
- Mods with clear signs of incompatibility with installed mods are less
  wanted - keep them, but file them under "caution" with the conflict named.

## Judgment guidance (editable)

- Taste profile: singleplayer sandbox, Bandits NPC ecosystem, KI5 /
  Papa_Chad / Tsar vehicles, deep crafting-farming-preservation chains,
  QoL and UI (Neat series), traits and skills, maps, medical realism,
  VHS skill tapes. Lore-breaking joke/anime/hypercar content is out.
- Test/WIP/personal uploads ("test", "my pack", single letters) are out.
- Brand-new mods with few subscribers: include only when they fit the taste profile strongly or accompany a subscribed mod; otherwise leave them for a later run - the trend ranking will resurface them if they gain traction.
- Classes used in the output: `companion`, `high`, `caution`, `watch`
  (see discoveries.json "classes" for definitions). Do not invent new
  classes without updating the pzmods Discoveries tab spec.

## Output contract (do not change casually - pzmods reads this)

- Write `discovery/discoveries.json` (schema described in
  `discovery/PZMODS-REWORK.md`) and a human-readable `discovery/report.txt`.
- Update `discovery/state.json` with the run timestamp and the newest
  workshop id seen, so the next run starts where this one ended.
- Never modify pzmods' own data files (`data/*.json`) or the game config.
