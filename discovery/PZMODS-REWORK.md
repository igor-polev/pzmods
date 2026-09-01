# pzmods rework: the Discoveries tab

Input context for a Claude Code session working on pzmods
(`C:\Users\igor\Zomboid\pzmods\`). Read `README.md` and `HANDOVER.txt`
first - they carry the design doctrine and the settled decisions. This file
adds one feature on top: surfacing the results of the periodic
**workshop-discovery** skill runs inside the pzmods web interface.

## What exists already

A Claude (Cowork) skill named `pz-workshop-discovery` periodically scans the
Steam Workshop for new Build 42 mods, filters them against the criteria in
`discovery/criteria.md`, and writes its results into this folder:

    discovery/discoveries.json   machine-readable result of the latest run
    discovery/report.txt         the same content as prose, for reading
    discovery/state.json         run bookkeeping (last run time, id cutoff)
    discovery/criteria.md        the criteria the skill follows (user-editable)

pzmods currently knows nothing about these files. The task is to make it
read `discoveries.json` and give the list a proper tab.

## discoveries.json contract (schema 1)

Top level: `schema`, `generatedAt`, `gameBuild`, `window {from,to,note}`,
`sources[]`, `stats {...}`, `classes {name: description}`, `items[]`.

Each item:

    id            workshop id, string - the natural key
    title         workshop title at scan time
    class         "companion" | "high" | "caution" | "watch"
    note          one- or two-sentence reason it is on the list
    companionOf   [] of subscribed-mod names/labels it accompanies
    overlapsWith  [] of subscribed-mod names it overlaps or conflicts with
    subs          integer or null - subscriber count when verified
    stars         1-5 or null
    ratings       integer or null
    updated       ISO date or null
    url           steam page url

`subs/stars/ratings` are null for most items (only top candidates get
verified per run). Class meanings are in the file's own `classes` map -
render from there, do not hardcode descriptions.

## The Discoveries tab - behavior

- New tab "Discoveries" next to the existing ones, built like the others
  from the same page skeleton in `ui.html`.
- Grouped by class in this order: companion, high, caution, watch. Show the
  class description under each group header. Per row: title (a link to the
  Steam page - the workshop-id-is-a-link rule from README applies), the
  note, `goes with:` / `overlaps:` lines when present, and subs/stars badge
  when present.
- Cross-link like the Issues tab does: a name in `companionOf`/`overlapsWith`
  that matches an installed mod's title should jump to the Mods tab search;
  unmatched names stay plain text (README: "an id that has no row to jump to
  is not dressed up as a link").
- An item whose workshop id is now in the subscription snapshot (the user
  subscribed since the run) gets a "subscribed" badge and drops to the
  bottom of its group - it is resolved, not interesting.
- Per-item user verdict, stored in `discovery/verdicts.json` (pzmods-owned,
  same spirit as `data/notes.json` - never touched by the skill):
  buttons `interested` / `dismissed` per row. Dismissed rows collapse into a
  "dismissed (N)" section at the bottom of the tab. Verdicts survive new
  skill runs: key by workshop id. The next skill run may read
  `verdicts.json` to avoid re-listing dismissed ids - the skill already
  tolerates the file being absent.
- Header line on the tab: when the run happened (`generatedAt`), the window,
  and the headline stats (scanned / excluded / selected). If
  `discoveries.json` is missing, the tab says so and points at the skill,
  rather than erroring.
- The tab is read-only with respect to pzmods' own model: nothing on it
  writes to tags, configs, or `pz_modlist_settings.cfg`.

## Integration rules (from the existing doctrine - do not violate)

- No new cache of derived state. `discoveries.json` is read fresh on every
  Update pass, like every other source. `verdicts.json` is user data, the
  only thing the tab writes, via its own endpoint with the same
  read-modify-write care as notes.
- Do not re-fetch anything from Steam for this tab. The skill did the
  fetching; the tab only renders its output. (The existing Update pass
  already refreshes metadata for *subscribed* items - that is unrelated.)
- Mod ids on the Mods tab stay plain text (settled decision). On the
  Discoveries tab the linked thing is the *workshop* id/title, which is
  wanted, same as the Issues tab.
- Keep it one python file + one html file, stdlib only.
- Test the way HANDOVER describes: fixture folder from `data/snapshot.json`,
  spare port, drive over the HTTP API; UI checks headless via Playwright
  (chromium is preinstalled in the cloud workspace at /opt/pw-browsers).
  Add a fixture `discoveries.json` with all four classes, a null-stats item,
  a subscribed-since-run item, and a verdict round-trip.

## Nice-to-have (only if cheap)

- Count badge on the tab header ("Discoveries (12 new)") = items not yet
  verdicted and not subscribed.
- A filter box like the Mods tab search.
- Sort within a group by subs desc, nulls last.
