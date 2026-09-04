# Performance mods — source-level investigation

Project Zomboid 42.20.4 · ZombieBuddy 2.3.2 · 3 Sep 2026

| mod | id | what it really is |
|---|---|---|
| Zomboid Unified Engine Tweaks | 3793911582 · `ZUET` | 22 Java patches: async tick, world-state caches, input decoupling |
| Zed's Better FPS — B42.20.2 Fix | 3782613536 · `ZBBetterFPSB4220Fix` | 13 Java patches, **renderer only** |
| Smart Z Optimizer | 3707376688 · `SmartZOptimizer` | 4 Java patches: zombie LOD, weather, crafting-scan fix |
| Multi-CPU Enhance | 3459875383 · `Multi-CPU` | **no code at all** — one `ProjectZomboid64.json` |

Two of the four ship full Java source (Z-UET, SmartZ); ZBBetterFPS was disassembled from its jar;
Multi-CPU is a config file read directly. Patch targets below are extracted from `@Patch`
annotations in source and from the constant pool of `ZBBetterFPS.jar` — not from descriptions.

---

## 0. The headline

**The mod doing the damage is the one with no code in it.**

Vanilla Project Zomboid B42 ships this, in `ProjectZomboid64.json.original`:

```
"windows": { "10.0.17134": { "vmArgs": ["-XX:+UseZGC"] } }
```

Your live file, which is Multi-CPU's, replaces that with:

```
"-XX:+UseParallelGC", "-XX:ParallelGCThreads=4"        (base)
"-XX:+UseParallelGC", "-XX:ConcGCThreads=2"            (windows 10.0.17134)
```

ZGC is a **concurrent** collector: sub-millisecond pauses, designed for latency.
ParallelGC is a **fully stop-the-world throughput** collector: every young collection freezes
every application thread until it finishes. On an 8 GB heap that is tens to hundreds of
milliseconds, at irregular intervals.

That is a description of frame stutter. The mod's own page promises "less lag spikes even if
the main thread remains single-core" — and the change it makes is the one most likely to
*cause* them. ParallelGC maximises total work per unit of CPU, which is the right goal for a
batch job and the wrong goal for anything drawing 60 frames a second.

**Restoring ZGC is the single highest-value change available here, and it costs nothing.**

---

## 1. Multi-CPU Enhance — flag by flag

The mod ships exactly one file: `42/ProjectZomboid64.json`. No Lua, no jar, no options.
Your live file is a *hand merge* of it — it additionally carries two lines the mod's copy
does not:

```
--enable-native-access=ALL-UNNAMED
--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED
```

⚠️ **Those two lines are ZombieBuddy's.** If you ever re-copy the mod's JSON verbatim, as its
page instructs, you delete them and every Java mod stops loading. Whoever merged this the
first time did it correctly; the instruction on the Workshop page would undo it.

| flag | verdict |
|---|---|
| `-XX:+UseParallelGC` ×3 | **Replaces ZGC with a stop-the-world collector.** The core problem. |
| `-XX:ParallelGCThreads=4` | Caps GC parallelism. Only meaningful because ParallelGC was selected. |
| `-XX:+UseStringDeduplication` | **Inert.** G1/Shenandoah/ZGC only. Under ParallelGC the JVM warns and ignores it. |
| `-XX:ConcGCThreads=2` (win 10 block) | **Inert.** There is no concurrent phase in ParallelGC. |
| `-XX:+UseNUMA` | No benefit on a single-socket desktop; adds allocation-path work. |
| `-XX:+UseCompressedOops` | Redundant — the default below a 32 GB heap. |
| `-XX:+AlwaysPreTouch` with `-Xms4096m` | Commits *and touches* 4 GB at launch. Slower start, 4 GB resident immediately. Defensible, not free. |
| `-XX:+ParallelRefProcEnabled` | Harmless, marginal. |
| `-XX:+OptimizeStringConcat` | Obsolete — no effect on a modern JDK. |
| `-Xms4096m -Xmx8192m` | **The one genuinely good change**, up from vanilla's `-Xmx3072m`. Keep it. |
| win 6.1 block: `G1NewSizePercent`, `G1ReservePercent` | **Landmine.** Experimental G1 flags, with G1 not selected and `+UnlockExperimentalVMOptions` absent from that block — the JVM would refuse to start. Only applies to Windows 7, so latent for you. |

There is also a nice irony: **Z-UET's own README recommends the opposite JVM configuration** —
ZGC, `ConcGCThreads=8`, `Xmx16g`. You cannot follow both mods' advice, and the live file
follows Multi-CPU's. (Z-UET's recommendation is not wholly right either: `-XX:CompileThreshold`
is ignored whenever tiered compilation is on, which is the default.)

### Proposed replacement

`ProjectZomboid64.proposed.json`, next to this file. It keeps the heap increase and the
ZombieBuddy lines, restores the stock collectors, and drops everything inert:

- **removed** — `+UseParallelGC` (×3), `ParallelGCThreads=4`, `ConcGCThreads=2`, `+UseNUMA`,
  `+UseStringDeduplication`, `+UseCompressedOops`, `+AlwaysPreTouch`, `+OptimizeStringConcat`,
  `+ParallelRefProcEnabled`, and the whole broken G1-flags-under-ParallelGC Windows 7 block
- **kept** — `-Xms4096m -Xmx8192m`, `+DisableExplicitGC`, both ZombieBuddy lines, all vanilla `-D` args
- **restored** — `+UseZGC` (Win 10+), `+UseG1GC` (Win 7)

Apply by hand, after backing up:

```
copy "…\ProjectZomboid\ProjectZomboid64.json" "…\ProjectZomboid\ProjectZomboid64.json.bak"
```

Then **unsubscribe Multi-CPU**. Its only artifact is a JSON that is already applied; leaving it
subscribed just means a future "verify files" or a re-copy silently reverts you.

### How to prove it rather than believe it

Add this temporarily and play twenty minutes with a horde on screen, once per collector:

```
"-Xlog:gc:file=gc.log:time,uptime:filecount=5,filesize=10M"
```

Then compare pause durations in `gc.log`. That turns this whole section from my reasoning into
your measurement, which is what should decide it.

---

## 2. Zed's Better FPS — a renderer mod, and the Workshop warning is wrong

### Patch targets, from the jar's own bytecode

| target | technique |
|---|---|
| `zombie.IndieGL.glAlphaFunc` / `glDepthFunc` / `glDepthMask` | redundant GL state-change elimination (`skipOn` — skips the driver call when state is unchanged) |
| `zombie.core.SpriteRenderer$RingBuffer.create` / `isStateChanged` | larger batch pools, fewer draw calls |
| `zombie.core.DefaultShader.setChunkDepth` | chunk shader state caching |
| `zombie.core.skinnedmodel.model.VertexBufferObject.setModelViewProjection` | model MVP caching |
| `zombie.core.textures.MultiTextureFBO2.update` | framebuffer update |
| `zombie.iso.IsoChunkMap.CalcChunkWidth` | render distance |
| `zombie.GameWindow.mainThreadStep`, `zombie.core.opengl.RenderThread.renderStep`, `zombie.iso.LightingThread.runInner` | CPU yielding ("Lower CPU Use") |
| **`zombie.iso.IsoMovingObject.separate`** | collision/separation rewrite ("Streamlined Physics") |

### The warning that started this

Z-UET's page says:

> "Do not use with other mods that patch `MovingObjectUpdateScheduler` / `IsoCell.getGridSquare`
> at the same time (e.g. ZBBetterFPS's `optimizeIsoMovingObject`)."

**ZBBetterFPS patches neither of those methods.** Its only entity-side patch is
`IsoMovingObject.separate`. I reported this warning at face value in the last report; the
bytecode says otherwise, and I was wrong to pass it on unchecked.

There *is* a real interaction, but a narrower one: `separate` is called from inside
`IsoMovingObject.update()`, which Z-UET runs on worker threads **when its async path is
enabled**. That path is off by default. With it off, the two mods touch disjoint methods and
have no relationship at all.

### Notable: it already knows about your Bandits setup

```lua
-- Bandits spawn at 55–65 tiles; need ChunkGridWidth*5 >= 65 => ChunkGridWidth >= 13
local MIN_CHUNK_GRID_FOR_BANDITS = 13
```

It detects `Bandits2` and refuses to lower render distance below 13. You run Bandits — so the
one setting here that could have broken your NPC spawns is already guarded.

### Settings — all default OFF

`renderDistance` 0 (game default) · `uncappedFPS` default · `optimizeIndieGL` false ·
`optimizeSpriteBatching` false · `optimizeRingBuffer` false · `optimizeDefaultShader` false ·
`optimize3DModels` false · `optimizeIsoMovingObject` false · `instantZoom` false ·
`lowerCPUMode` = "paused or background"

Nothing in this mod is doing anything for you right now.

---

## 3. Smart Z Optimizer — the best-engineered of the four

### Patch targets

| target | technique |
|---|---|
| `zombie.characters.IsoZombie.updateInternal` | **Zombie LOD** — skip the update |
| `zombie.iso.IsoWorld.update` | per-frame driver + OpenCL dispatch |
| `zombie.iso.weather.fx.IsoWeatherFX.render` | **particle LOD** — scale `particlesToRender` |
| `zombie.entity.components.crafting.BaseCraftingLogic.setContainers` | **drop corpse containers** |

### Zombie LOD, and why it is careful

A zombie is skipped only if it is *provably* idle — no target, not alerted, no sound attraction,
not running, no lunge timer, and not in `PathFindState` or `WalkTowardState`. Those pass, and it
updates 1 frame in 5 (`SKIP_INTERVAL = 5`). State singletons are cached at class-load so the
check is a reference comparison, and the counters are plain `int` because the author documented
that only the main thread touches them.

The detail that shows real care:

```java
if (skip) {
    float timer = z.getStateEventDelayTimer();
    if (timer > 0f) z.setStateEventDelayTimer(timer - GameTime.getInstance().getThirtyFPSMultiplier());
}
```

Skipping `updateInternal` would otherwise stretch the idle→wander timer 4×, because that timer
is decremented inside the method being skipped. The author found that and compensated for it.
Compare with §4(f).

### Corpse containers — the biggest practical win in this set, for your collection specifically

`BaseCraftingLogic.setContainers` receives every nearby container when the crafting or building
menu opens; the patch strips `IsoDeadBody` containers before the game stores them, and the Lua
side does the same for `ISInventoryPaneContextMenu.getContainers` and the right-click craft menu.

You run **Hydrocraft Reinvented** (3,620 recipes), **Neat Crafting**, **Project Cook** and
**Proximity Inventory**. Every recipe availability check walks every container. A cleared street
of forty corpses is forty extra containers on every crafting menu open, times thousands of
recipes. This is a genuine hotspot and this is a correct fix for it.

Toggle key `L` flips it in-game without restarting.

### Weather and OpenCL

Particle LOD scales rain/snow/fog/cloud particle counts to 50–100%. **Currently at 100 = off.**
The OpenCL path precomputes `WeatherPeriod` Simplex noise on the GPU via LWJGL, on a
single-thread executor, off by default, and deliberately skips `OpenCLOn12` for stability.
It is an unusual and legitimate idea — CPU work moved to an idle GPU.

### Settings

`Enable` **true** · `ParticlePct` **100** (LOD off) · `EnableOpenCL` false · `EnableMetrics` false ·
`ExcludeCorpse` **true** · toggle key `L`

The author labelled the *Workshop item* "[Legacy]" but the mod itself is current — `versionMin=42.16`,
README verified against 42.20.3.

---

## 4. Z-UET — ambitious, and it costs you whether or not you use it

22 patch classes. The three headline subsystems are ParallelTicksZ (async tick), PzAlloy
(caches) and PZ-SmoothInput (Windows input decoupling).

### (a) The headline feature is off, and cannot be reached by accident

```java
boolean asyncSchedulerEnabled = cfg.allowConcurrentWorldTicks;
if (!asyncSchedulerEnabled) return false;
```

`allowConcurrentWorldTicks` defaults to **false**. Out of the box, Z-UET parallelizes nothing.
Everything below is what it does *anyway*.

### (b) It replaces the pathfinding point pool — unconditionally

```java
@Patch(className = "zombie.pathfind.PointPool", methodName = "alloc", warmUp = true)
@Patch.OnEnter(skipOn = true)
public static Object onEnter(@Patch.This Object self) {
    ArrayDeque<Object> q = TL_POOL.get();
    if (q.isEmpty()) {
        Class<?> pc = Class.forName("zombie.pathfind.Point");
        Constructor<?> ctor = pc.getDeclaredConstructor();
        ctor.setAccessible(true);
        return ctor.newInstance();          // reflective allocation, on the pathfinding hot path
    }
    return q.pop();
}
```

`release` likewise always returns `true`, so the game's own pool never runs again. There is no
config gate on either. On a pool miss this does `Class.forName` + `getDeclaredConstructor` +
`setAccessible` + `newInstance` — reflective object construction inside pathfinding. And if any
of that throws, it **returns `null`** to a caller that expects a `Point`.

`PointPoolSyncLock` — a `ReentrantLock` the class name says this was meant to use — is defined
and referenced nowhere.

### (c) It synchronizes a hot setter, for a benefit that only exists in a mode you are not in

```java
@Patch(className = "zombie.characters.IsoGameCharacter", methodName = "setForwardDirection")
public static void onEnter(@This IsoGameCharacter self, @Argument(0) Vector2 dir) {
    synchronized (self) { ... }
}
```

A monitor acquire on every character, every frame, to guard against a zero-length vector that
can only arise under concurrent updates. Biased locking was removed in JDK 15, so this is a real
CAS every call.

Worse: **two patch classes target the same method** — `HookForwardDirection` binds argument 0 as
`Vector2`, `HookForwardDirectionXY` binds it as `float`. ZombieBuddy keys patches by
`(className, methodName)` **with no descriptor**, so both advices are applied to both overloads.

### (d) Three patches that do nothing at all

```java
@Patch(className = "zombie.ai.states.ZombieIdleState",   methodName = "execute")        { }
@Patch(className = "zombie.pathfind.PolygonalMap2",      methodName = "lineClearCollide") { }
@Patch(className = "zombie.characters.IsoZombie",        methodName = "update")          { }
```

Empty bodies on three of the hottest methods in the engine. `lineClearCollide` runs constantly
during pathfinding. `HookPathFindState` and `HookPathFindBehavior2` are the same story.
`HookCellTick.onExit` contains `long t0 = nanoTime(); long dt = nanoTime() - t0;` — measuring
nothing.

### (e) Per-zombie instrumentation that cannot be switched off

`HookZombieTick.onEnter` fires on **every** `IsoZombie.update` and calls:

```java
threadHitCounter.computeIfAbsent(Thread.currentThread().getName(), k -> new LongAdder()).increment();
```

A string fetch plus a `ConcurrentHashMap` lookup per zombie per tick. The `EnableMetrics` option
that should gate it calls `ptz.setEnableMetrics(...)` — **a method that does not exist on
`PtzBootstrap`.** The Lua wraps it in `pcall`, so the toggle silently does nothing.

### (f) If the async path is ever enabled, two real behaviour bugs

**Entities in slow buckets move at a fraction of speed.** Vanilla updates distant objects 1 frame
in N and multiplies their movement by `perObjectMultiplier` to compensate. Z-UET forces
`perObjectMultiplier = 1.0f` for every entity, and the bucket's `mod` value is collected —

```java
else { asyncEntities.add(m); asyncMods.add(mod); }
```

— and then **never read again**. Compare §3, where the same class of problem was found and fixed.

**A reflection failure silently freezes the world.** The catch block around the whole bucket scan
ends with `return true` — "skip the vanilla update" — logged only on the 1st–3rd occurrence and
every 500th. After a game update renames `buckets` or `frameMod`, every moving object stops
updating, near-silently.

### (g) Documentation that does not match the code

| README | code |
|---|---|
| "player-near 20 tiles sync" | `dx*dx + dy*dy < 25.0f` → **5 tiles**, with a comment calling it a verification value |
| "`ZonePartitioner` 16×16 cells" | `GRID_SHIFT = 5` → 32 |
| "`TickWeightModel` cost model" | dead code — the live path balances by entity *count* |
| "`ZonePartitioner.partition`" | dead code on the live path |

### (h) The one file I could not read is the one that decides whether PzAlloy is safe

`PzCellMixin` / `PzChunkMixin` cache `IsoGridSquare` objects by `(cell, x, y, z)`;
`PzSquareMixin` caches `isBlockedTo` per square-pair. Blocked-ness changes when a door opens, a
window breaks, a wall is built or sledged; squares are created and destroyed as chunks stream.
Whether that is safe lives entirely in `SquareFlagsCache.java` — **8 folders deep, past the file
-transfer limit.** The README describes an "8192-entry cap with periodic clear", which is a bound
on size, not invalidation on change.

If you want that gap closed, copy the file somewhere shallow and I will read it:

```powershell
copy "C:\Program Files (x86)\Steam\steamapps\workshop\content\108600\3793911582\mods\Z-UET\java\src\zomboid\alloy\cache\SquareFlagsCache.java" "C:\Users\igor\Zomboid\pzmods\"
```

### (i) It has probably never run

There is no `ParallelTicksZ.json` in the game root, and `PtzSettings.load()` always writes one.
`ModOptions.ini` was last written 30 Aug and contains **no entry for ZUET, SmartZOptimizer or
ZBBetterFPS** — so all three are running on defaults, and you have not launched the game since
subscribing Z-UET. Good timing: this advice lands before its first run rather than after.

---

## 5. Co-existence — the actual answer

### Does ZombieBuddy allow two mods to patch one method?

**Yes, by design.** `PatchEngine` groups patches into a `Map<PatchTarget, List<…>>` keyed by the
record `PatchTarget(className, methodName)` and applies them as a chain. Two mods on
`IsoWorld.update` is supported, not a conflict.

Two caveats fall out of that same code: the key carries **no method descriptor**, so overloads
cannot be distinguished (§4c); and where several patches use `skipOn`, whichever runs first
short-circuits, so *skipping* patches on one method are load-order dependent.

### Overlap matrix

| method | Z-UET | SmartZ | ZBBetterFPS |
|---|---|---|---|
| `MovingObjectUpdateScheduler.update` | skip · **off by default** | | |
| `IsoWorld.update` | no-skip | no-skip | |
| `IsoCell.update` | no-skip (no-op) | | |
| `IsoZombie.update` | ×2, both empty | | |
| `IsoZombie.updateInternal` | | skip · **on** | |
| `PointPool.alloc` / `release` | **replace · always on** | | |
| `IsoGameCharacter.setForwardDirection` | ×2, synchronized · **always on** | | |
| `IsoCell`/`IsoChunk.getGridSquare`, `IsoGridSquare.isBlockedTo` | cache · **on** | | |
| `PolygonalMap2.lineClearCollide`, `ZombieIdleState.execute`, `PathFindState.execute`, `PathFindBehavior2.update` | empty · **always on** | | |
| `IsoMovingObject.separate` | | | off by default |
| GL / shader / buffer / threads (9 methods) | | | off by default |
| `IsoWeatherFX.render` | | on (pct=100 ⇒ inert) | |
| `BaseCraftingLogic.setContainers` | | **on** | |

**Nothing here conflicts today.** The three genuine hazards are all conditional:

1. **Z-UET async ON + ZBBetterFPS Streamlined Physics ON** — `separate` would execute on worker
   threads. The only interaction the two mods actually have, and only in that combination.
2. **Z-UET async ON + SmartZ Zombie LOD ON** — `ZombieLODManager` uses plain `int` counters and a
   static `frameCounter`, documented as main-thread-only. Off-thread that is a data race; harmless
   for statistics, but outside the author's design.
3. **Z-UET async ON, on its own** — §4(f).

All three reduce to: *do not enable `AllowConcurrentWorldTicks`.*

---

## 6. What I would actually do

### Now, in order

1. **Restore ZGC.** Back up `ProjectZomboid64.json`, apply `ProjectZomboid64.proposed.json`,
   launch, confirm the game starts and ZombieBuddy still loads its jars.
2. **Unsubscribe Multi-CPU Enhance.** Its only artifact is a config that is already applied and
   now wrong; keeping it invites a silent revert.
3. **Keep Smart Z Optimizer as-is.** `Enable` on, `ExcludeCorpse` on. These are the two settings
   already doing real work for you.
4. **Remove Z-UET** — or, if you want to keep it for the smooth-input feature, understand that
   §4(b)–(e) are the price and they apply with every other feature switched off. My reading is
   that its always-on costs land squarely on pathfinding allocation and character movement, which
   is where a large zombie count already hurts most.

### Then, one at a time, measuring between each

5. `SmartZ → Weather Particle Render %` → **75**. Cheapest remaining win; rain is a real cost in B42.
6. `ZBBetterFPS → Optimize IndieGL State` → on. Redundant-GL-call elimination is low-risk.
7. `ZBBetterFPS → Optimize Sprite Batching` → on.
8. `ZBBetterFPS → Optimize RingBuffer` → on. More VRAM; **needs a full restart**.
9. `ZBBetterFPS → Optimize Chunk Shaders`, then `Optimize 3D Models`. Stop at the first artefact —
   you run Tomb's Body Overhaul, Spongie's, and a pile of retextures.
10. `SmartZ → Enable OpenCL Weather Acceleration` → on, and read the chat line it prints ~3 s after
    load. If it names your GPU, keep it; if it says unavailable, turn it back off.

Leave alone: `renderDistance` (Bandits needs ≥13 and the mod already clamps it, but there is no
reason to go near it), `uncappedFPS`, `Streamlined Physics`, and `AllowConcurrentWorldTicks`.

### Measuring, so this is not a matter of opinion

- `-Xlog:gc:file=gc.log:...` for one session per collector — settles §0 with numbers.
- `SmartZ → Enable Performance Metrics` prints `LOD frame=… lod0=… lod1=…` every 300 frames;
  `lod1` is how many zombie updates were actually skipped. If `lod1` is near zero, the LOD is
  not helping and something is keeping zombies active.
- Test the same thing every time: a saved position with a large horde in view, in rain, standing
  still for sixty seconds. Frame-time variance matters more than average FPS — stutter is what
  you are chasing, not throughput.

### Further directions, in order of expected value

- **Zombie count is the real dial.** All the zombie-side work here scales with population.
  Sandbox population and respawn settings will outperform every patch in this report.
- **`PolygonalMap2` and pathfinding** are where B42 spends its time under load, which is why three
  separate mods reach for it. Nobody in this set actually optimises it — Z-UET only wraps it in
  empty patches. That is the open problem worth watching for.
- **The GPU is idle.** SmartZ's OpenCL weather noise is the only mod here that noticed. Lighting
  and fog are the obvious next candidates for the same treatment.
- **The corpse-container fix generalises.** Any large container list walked per menu-open is a
  hotspot; with Hydrocraft's 5,196 items you have made that list expensive. Worth watching whether
  crafting-menu latency tracks corpse count on your saves.
- **Instrument before optimising further.** You already have `ZBLuaPerfMon` subscribed and
  disabled. Turning it on for one session would tell you whether your remaining cost is Lua (your
  380-odd script mods) or engine — and those two answers point at completely different fixes.

---

## Appendix — evidence

- Java source read directly: Z-UET (45 files), Smart Z Optimizer (13 files + OpenCL kernel).
- `ZBBetterFPS.jar` disassembled with `javap`; patch targets read from the constant pool.
- `ZombieBuddy.jar` 2.3.2 disassembled to confirm `PatchEngine`'s multi-patch behaviour.
- Config read live from your machine: `ProjectZomboid64.json`, `.json.original`, `Lua/ModOptions.ini`.
- Not read: `SquareFlagsCache.java` and the 8 `dev/pzboost/**` smooth-input internals — past the
  file-transfer depth limit. §4(h) says how to close the one that matters.
