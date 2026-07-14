# Fallen Grid — Specification & Handoff (v3)

Single-file HTML5 canvas tower defense, post-apocalyptic sci-fi theme, portrait mobile-first, intended to ship on Google Play via a Capacitor WebView wrapper. This document is the source of truth for continuing the work. Part 0 is the operating contract. Part 1 is the technical spec (updated to current code). Part 2 is the continuation brief: quality assessment, backlog, changelog. Part 3 is the **Visual & Map Direction V2** — the re-evaluation of graphics ("how do we get a 3D-rendered look?") and map layout, with a phased implementation plan.

The deliverable file is `fallengrid-v3.html` (real-3D build — see Part 4; the older 2D builds are kept frozen alongside). Everything lives in one file inside a single IIFE. No build step, no CDN: three.js r147 is embedded inline. WebGL via three.js for the world + Canvas2D for UI + WebAudio.

**Current state (v3).** All original backlog items are closed: graphics pass 1, strategic depth, audio, onboarding, meta-progression, endless + 5-map roster with biomes, balance pass, and the Hero/Commander. The game is mechanically a genre-standard TD with retention. The open front is **presentation ceiling and map composition** — the subject of Part 3.

---

# Part 0 — Operating Contract (read first)

Operate as a senior game-dev collaborator, not a generic assistant. Rules:

Lead with the answer or the working code, then reasoning if needed. Skip preambles, filler affirmations, and needless caveats. Prose over bullets unless the content is naturally list-shaped. No em dashes. No hedging unless uncertainty is genuine. Avoid passive voice.

If a request is ambiguous, make a reasonable assumption, state it in one line, and proceed. Do not stack clarifying questions. If a request has a better framing, say so once, then execute the better version.

All code, config, and data must be copy-paste ready with no placeholders or TODO stubs unless a template was explicitly requested. Flag genuine technical flaws, regressions, or Play-compliance risks directly rather than softening them.

Definition of done is fixed in 2.7 and is non-negotiable: syntax check, hex scan, headless logic/render check, and the two wave-progression guards in 1.10 intact.

---

# Part 1 — Technical Specification

## 1.1 Product intent

Twenty-wave tower defense. The player defends a reactor (Core) against waves of raiders and war-machines by building and upgrading towers on a fixed serpentine path. Run currency is Scrap. A persistent meta-currency, Alloy, is earned each run and spent on permanent talents. The game runs at 60fps on mid-range phones, responds to touch (tap to build/select, pinch to zoom, drag to pan), and never soft-locks between waves.

## 1.2 Coordinate systems (critical concept)

The engine separates two spaces. Get this wrong and everything else breaks.

**Screen space** is a fixed 360x640 logical canvas. The HUD (top) and tray (bottom) are drawn here and never move. The canvas is letterboxed to the device via a uniform scale in `resize()`, with `devicePixelRatio` applied through `ctx.setTransform`.

**World space** is the map, independent of the screen. World origin `(0,0)` is the map's top-left corner. The map spans `WORLD_W x WORLD_H` = `704 x 1024`. All gameplay entities live in world coordinates.

A camera projects world into the on-screen play viewport, the screen rectangle from `y = PLAY_TOP (56)` to `y = PLAY_BOTTOM (522)`, full width.

```
cam = { x, y, zoom }   // x,y = world coord at viewport top-left; zoom = screen px per world unit
screenToWorld(sx, sy) = { x: sx/zoom + cam.x,  y: (sy - PLAY_TOP)/zoom + cam.y }
worldToScreen(wx, wy) = { x: (wx - cam.x)*zoom, y: (wy - cam.y)*zoom + PLAY_TOP }
```

World rendering each frame: clip to the viewport rect, `translate(0, PLAY_TOP)`, `scale(zoom, zoom)`, `translate(-cam.x, -cam.y)`, draw world, then `restore()`. HUD, tray, ability button, zoom buttons, and tutorial marks draw afterward in raw screen space.

Zoom limits: `MINZOOM = min(W/WORLD_W, PLAY_H/WORLD_H) * 0.98`, `MAXZOOM = 1.9`. `fitCamera()`, `clampCam()`, `zoomAt(sx, sy, factor)` as before.

## 1.3 Layout constants

```
W = 360, H = 640
HUD_H = 56          PLAY_TOP = 56
TRAY_H = 118        PLAY_BOTTOM = 522    PLAY_H = 466
TILE = 64  COLS = 11  ROWS = 16   WORLD_W = 704  WORLD_H = 1024
```

## 1.4 Terrain (pre-rendered, baked once)

`buildTerrain()` renders the entire static wasteland once into an offscreen canvas at `WORLD_W*TS x WORLD_H*TS` (`TS = 1.5`). Each frame the world layer blits this single image. Ground is now organically hash-mottled (no hard checkerboard), roads have curbs, and a baked directional light (warm upper-left → cool lower-right) plus a grime vignette give a consistent light source. Per-tile cracks, speckle, road markings, wrecks, rubble, craters, barrels, and pool bases are baked. **Do not move any per-tile terrain drawing into the frame loop.**

Dynamic map elements drawn live over the terrain: toxic pool glow (`drawPoolGlow`), spawn breach + base reactor (`drawSpawnAndBase`), ground scorch decals (`drawScorches`), and ambient dust/embers (`drawAtmosphere`, ~34 deterministic motes).

## 1.5 Maps, grid size, and routes

Maps vary in **grid size** and can have **multiple entrances**. `COLS/ROWS/WORLD_W/WORLD_H/MINZOOM` are `let`, set per map by `loadMap(i)` from `MAPS[i].cols/rows`; the baked terrain canvas sizes to the map. Large maps exceed the viewport at readable zoom and are panned (the camera already supports this; `fitCamera` fits width, top-anchored).

Each map defines `routes: [[...corners], ...]` — one or more routes, each a `[col,row]` corner list (consecutive corners share a row/column). **All routes end at the shared base** (the last point); their starts are the entrances. `loadMap` builds `ROUTES` (array of world-point polylines) and `PATH_SET` = the union of all route tiles, so where two routes overlap the roads simply **cross** (baked as an intersection). Enemies carry a `route` index assigned round-robin at spawn (`spawnIdx`, reset each wave); they move along `ROUTES[e.route]` and leak at its end. `drawSpawnAndBase` draws a breach at every route start and one base. `buildable` = any in-bounds tile not in `PATH_SET`. **`buildTerrain()` must never run in the frame loop** — only on map load; `selectMap(i)` re-bakes only on change.

Roster (rising difficulty, **10 maps** in v2.5 / 7 in the v2.4 file): `Outpost` 9×12 ★ 1-route intro · `Serpentine` 11×16 ★★ · `Spiral` 11×14 ★★ single route spiraling inward, base at the center (v2.5) · `Crossroads` 11×16 ★★★ 2-gate crossing · `Gauntlet` 9×18 ★★★ tall single-route switchback ladder (panned) · `Delta` 13×18 ★★★★ **3 entrances** whose routes T-merge (parallel overlap = merge, no bridge) into one final approach · `Sprawl` 13×22 ★★★★ long single route (panned) · `Fracture` 12×16 ★★★★ 2 gates with one perpendicular bridge crossing then a T-merge final (v2.5) · `Twin Gates` 13×20 ★★★★★ 2-gate crossing (panned) · `Terminus` 15×22 ★★★★★ finale: 3 entrances, two bridge crossings + merges, largest board (v2.5). `S.mapIndex` (persisted `map`) selects. In v2.5 the menu map picker is a styled native `<select>` dropdown (`id "mapsel"`, class `.mapsel`, options show name/★/size/gates) — free play only; the v2.4 file keeps the button grid.

**Campaign mode**: the maps double as a mission sequence. Menu button `⚔ Campaign · Mission N/${MAPS.length}` (`id "cp"`) starts at `Store("camp")` (clamped); `S.campaign = true`. On victory the screen becomes "Mission N Secured", persists `camp = mapIndex+1` (clamped to last), and offers `⚔ Next Mission · <name>` (`id "nm"` → next map, fresh run) — or a `⚔ CAMPAIGN COMPLETE` banner on the last map. Free-play Deploy and Endless set `S.campaign = false`; map picker stays independent for free play.

## 1.6 Economy and progression

```
START_SCRAP = 150   START_CORE = 20   TOTAL_WAVES = 20   NEXT_WAVE_COUNTDOWN = 6s
SELL_REFUND = 0.7 (of cumulative cost through current level incl. branch)
Wave clear bonus = round((20 + wave*3) * waveBonusMul())
Difficulty (three tiers in `DIFFS`, chosen on the menu, persisted): Normal hp1.0/spd1.0/core20/alloy1.0 · Hard hp1.7/spd1.1/core18/count1.25/reward0.92/alloy1.5 · Brutal hp2.6/spd1.2/core15/count1.6/reward0.85/alloy2.0. `count` pads each wave's spawn list; `reward` scales scrap per kill. Leaks cost 1 core (brute/sentinel/warden 2, juggernaut 6).
```

Meta (persistent, via `Store`): **Alloy** earned per run = `round((kills + wave*4 + (victory?120:0)) * (hard?1.4:1))`, awarded once (`awardAlloy`, guarded by `S.alloyAwarded`). Spent in the **Armory** on six talents (see 1.15).

## 1.7 Towers

Four archetypes in `TOWERS`, order `[turret, cryo, mortar, tesla]`. Each has a `kind` (firing model), a `dmgType`, two shared levels (L1, L2), then an L2→L3 **branch** choice into one of two specializations. `t.lvl` is 0/1/2; at `lvl 2` stats come from `t.branch` (`"a"`/`"b"`). `tStats(t)` returns the branch spec at L3, else `levels[t.lvl]`.

| id | name | kind | dmgType | L1 cost/dmg/range/rate | branch a | branch b |
|----|------|------|---------|------------------------|----------|----------|
| turret | Auto-Gun | hit (hitscan+tracer) | kinetic | 50/9/152/500 | Gatling: 75, dmg16, rate175 | Breacher: 85, dmg44, rate500, **pierce** |
| cryo | Cryo Emitter | orb (AoE slow) | energy | 65/4/136/720, splash60 slow0.45 | Glacier: 80, splash96, slow0.84 | Shatter: 95, dmg26, **+90% vs slowed** |
| mortar | Mortar | lob (arced splash) | explosive | 85/26/150/1150, splash78 | Carpet: 105, dmg56, splash126 | Buster: 135, dmg158, **pierce** |
| tesla | Rail-Tesla | beam (hitscan bolt) | energy | 95/40/215/1250 | Arc-Coil: 115, dmg58, range250, **chain 3** | Railgun: 155, dmg205, range320 |

Firing models in `fire(t, p, st)` compute `dmg = st.dmg * dmgMul()` (talent) then: `hit` instant + tracer; `beam` instant + jagged bolt (+ chain if `st.chain`, which also hits flyers); `orb` homing projectile → AoE damage + slow (+shatter bonus vs slowed/frost); `lob` arced shell → AoE explosive (skips flyers). `st.pierce` bypasses armor.

Targeting: per-tower `mode` in `[first, strong, close]`. `findTarget` skips flyers for towers whose kind is not direct-fire (`canHitAir(kind)` = `hit || beam`).

## 1.8 Enemies

Ten types in `ENEMIES`. `statsFor(type, wave)` applies HP mul `1 + 0.14*w + 0.013*w²` (quadratic so late waves outpace maxed towers), speed mul `1 + min(0.25, 0.011*w)`, reward mul `1 + 0.035*w`, shield mul `1 + 0.12*w`, and copies trait flags. Non-boss wave counts grow faster (`rd = 3 + 0.7n` capped 22, etc.) and are padded by the difficulty `count` multiplier.

| id | label | base hp | speed | reward | r | shape | trait |
|----|-------|--------:|------:|-------:|--:|-------|-------|
| stalker | Stalker | 16 | 148 | 4 | 15 | stalker | fast runner |
| raider | Raider | 34 | 90 | 5 | 18 | raider | medium |
| brute | Brute | 105 | 54 | 10 | 24 | brute | tank |
| sentinel | Sentinel | 92 | 60 | 13 | 23 | brute | **armor** |
| wraith | Wraith | 38 | 122 | 8 | 16 | wraith | **flying** |
| warden | Warden | 66 | 72 | 12 | 20 | raider | **shield 60** |
| juggernaut | Juggernaut | 1150 | 42 | 130 | 34 | juggernaut | boss, **shield 420** |
| mender | Mender | 55 | 72 | 14 | 19 | mender | **heals** allies in r95 by 7% maxHp every 1.3s (`heal:1`) |
| splitter | Splitter | 110 | 60 | 16 | 23 | splitter | **splits** into 3 spawnlings on death (`split:3`) |
| spawnling | Spawnling | 14 | 138 | 2 | 11 | stalker | fast fragment (spawned only, never in `waveComp`) |

**Behavior traits**: `statsFor` copies `heal`/`split`. Mender pulse lives in `updEnemies` (timer `healT`, fx flag `healFx` drives a green cross-glow + expanding ring; only fires if it actually healed someone) — counterplay is STRONGEST targeting to focus it. Splitter death lives in `hurt()` (after the scorch decal): spawns `e.split` spawnlings via `statsFor("spawnling", S.wave)` with the difficulty hp/speed multipliers applied, on the parent's route/`pi` with position offsets — leaks do NOT split (no `hurt` call), so letting one through costs 1 core, killing it late costs 3 fast runners near your base.

**Counterplay triangle** (in `hurt(e, dmg, type, pierce)`):
- **armor** (unless `pierce`): kinetic `*0.4`, explosive `*1.2`, energy `*1.0`.
- **shield**: absorbs the whole hit (no bleed-through that hit); energy strips `*1.6`, kinetic `*0.7`, explosive `*1.0`. Regenerates `shieldMax*0.22`/s after 3s with no damage (`shieldCd`). Boss shield shown on the boss bar; others as a bubble + thin bar.
- **flying**: only direct-fire towers (turret, tesla) can target; ground splash (mortar, cryo) cannot; splash loops skip flyers. Airstrike hits everything.

`waveComp(n)`: every 5th wave is a boss wave (2 juggernauts every 20th wave, else 1). Non-boss waves add stalkers/raiders/brutes plus `wraith` (n≥3), `sentinel` (n≥6), `warden` (n≥8), `mender` (n≥9), `splitter` (n≥11). Counts are capped (rd≤20, br≤12, wr≤10, se≤10, wd≤8, md≤6, sl≤7, boss-wave extra≤16) so deep **endless** waves stay performant; `statsFor` keeps scaling HP unbounded. Campaign values (n≤20) are below the caps, so the campaign is unchanged. Leaks cost 1 Core (5 for a juggernaut).

**Endless mode** (`S.endless`): reachable from the menu (`∞ Endless`) or by continuing after a campaign victory. Waves never trigger `victory`; `startWave`, the auto-advance countdown, and the HUD deploy control all drop the `TOTAL_WAVES` cap when `S.endless`. Best endless wave persists as `highEndless`. A long endless run is the main Alloy farm (Alloy scales with `S.wave`).

## 1.9 Active ability — Airstrike

`STRIKE_CD = 30 - Meta.val("strike")` effective (`strikeMax()`), `STRIKE_R = 92`. Bottom-left circular FAB with a cooldown sweep. Tap to arm (`S.strikeArm`), then a tap in the play viewport calls `doStrike(wx, wy)`: layered explosions + `explosive`, `pierce` AoE that hits air and ground, brief `stunT`, shake + flash. Armed state shows a red reticle overlay ("TAP A TARGET ZONE") and the FAB reads CANCEL.

## 1.10 The wave-progression guarantee (do not regress)

Two independent guards make a freeze impossible; both must remain:
1. The Deploy/Start control lives in the persistent top HUD (`drawHUD`), always rendered (`hudBtns` id `"nextwave"`) and checked **first** in the tap handler, so it is always tappable even with a selection panel showing.
2. `NEXT_WAVE_COUNTDOWN` auto-starts the next wave with zero input after a wave resolves (`frame` loop, `S.countdown -= raw`).

**UX note (changed on request):** selection is **no longer** force-cleared when a wave *resolves* — the player's build/upgrade focus stays on the build menu through the between-wave countdown (a wave ending no longer yanks the menu away). This is safe because guards 1–2 alone prevent any softlock (selection panels never gate input in v3; the Deploy button and the countdown both work regardless). Selection is still cleared on `startWave` (a fresh wave begins) and on `reset`, and whenever an ability is armed. Onboarding, airstrike arming, and the Armory remain **non-blocking**. Enemies a mismatched defense cannot kill simply leak and the wave still resolves.

## 1.11 Game loop

`frame(now)` caps dt at 50ms; when `screen === "playing"` runs `updSpawns, updTowers, updEnemies, updProjs, updParts`, shake decay, airstrike cooldown, and the auto-advance countdown. Speed multiplier (1/2/3) scales the sim step, not the render. Render order: world layer under camera (terrain blit → pool glow → scorches → spawn/base → sel range → towers → enemies → gibs → beams → projs → booms → smoke → parts → atmosphere), then screen FX (flash, low-core vignette, strike-arm overlay, boss bar, banner), zoom buttons, ability FAB, HUD, tray, tutorial.

## 1.12 Input model

Pointer events with a `ptrs` Map for multitouch. Tap vs pan by `DRAG_THRESH = 8px`; two-finger pinch zoom + pan. `tap(x, y)` priority order: tutorial skip → HUD buttons → zoom buttons → ability FAB → armed-airstrike placement → tray buttons → world tile. Build flow is plot-first. A document-level `pointerdown` calls `Sound.resume()` to satisfy mobile audio autoplay policy.

## 1.13 Persistence and audio

`Store` wraps `localStorage` with an in-memory fallback. Persists `sfx`, `music`, `haptics`, `eco`, `speed`, `map`, `camp`, `difficulty`, `high`, `highEndless`, `tutDone`, `alloy`, `talents`. `Sound` is a procedural WebAudio synth: a master gain → `DynamicsCompressor` chain, oscillator layers plus filtered noise bursts for gun/tesla/cryo/boom/hit/place/up/sell/err/leak/shield/strike/wave/win/lose (all gated by the persisted **SFX** flag), and an ambient music bed (detuned drone + LFO-swept lowpass + filtered wind) gated by the **independent, persisted Music flag**, started on entering play and faded out otherwise. Haptics (`vibrate()`) are gated by the persisted `haptics` flag. All guarded in try/catch.

## 1.14 Onboarding

First-play coach-marks (`S.tut`, persisted `tutDone`). Three non-blocking steps that advance by observed state: spotlight a build plot → the placed tower (upgrade) → the Deploy button, each with a pulsing ring/arrow + banner and a SKIP button. Deploying completes it. `drawTutorial()` uses `worldToScreen` for world targets.

## 1.15 Meta-progression (Armory)

`Meta` module (persisted `alloy`, `talents:{id:level}`). Six talents in `TALENTS`, three levels each, escalating cost:

| id | name | effect (L1/L2/L3) | applied in |
|----|------|-------------------|------------|
| scrap | Reserves | +25/50/75 start scrap | `reset()` |
| core | Reinforced Core | +5/10/15 start core | `reset()` |
| dmg | Munitions | +5/10/15% tower dmg (`dmgMul`) | `fire()` |
| reward | Salvage Rigs | +8/16/25% scrap/kill (`rewardMul`) | `hurt()` |
| strike | Rapid Response | −3/6/9s airstrike cd (`strikeMax`) | `doStrike`, FAB |
| waveb | War Economy | +25/50/75% wave bonus (`waveBonusMul`) | `updSpawns` |

Armory is an HTML overlay (screen `"armory"`) reachable from the main menu and both end screens; rows show current→next effect, level pips, and hex-cost buy buttons. `Meta.buy(id)` deducts Alloy and persists.

## 1.16 Debug hook

```js
window.__GAME = { S, cam, Meta, screenToWorld, startWave, tap, fitCamera, render,
                  build(c,r,type), get enemies(){...}, get towers(){...} }
```
Used by the headless/Playwright harnesses. `build(c,r,type)` places a tower for combat tests; `Meta` lets tests grant/inspect Alloy and talents; `sim(stepMs, maxIters)` fast-forwards the simulation with no rendering (returns `{wave, screen, core, kills, iters}`) for auto-battle balancing. The frame update block is factored into `stepSim(stepMs)`, shared by the render loop and `sim`.

---

# Part 2 — Continuation Handoff

## 2.0 Changelog since v1

1. **Graphics overhaul** — procedural but consistent: distance-driven enemy walk cycles + directional facing, shaded per-type bodies (stalker/raider/brute/wraith/juggernaut), death gibs + scorch decals + frost/shield overlays; detailed per-level tower art with emissive trim and muzzle flash; de-checkered organic terrain with a baked light direction; layered explosions, comet-trail orbs, branching bolts, ambient motes.
2. **Strategic depth** — damage-type counterplay triangle; three counterplay enemy traits (armor, shield, flying) + boss shield; L2→L3 branching upgrades per tower; the Airstrike active ability.
3. **Audio** — procedural synth (noise + filters + compressor) replacing the beeps, plus an ambient music bed.
4. **Onboarding** — non-blocking first-play coach-marks.
5. **Meta-progression** — persistent Alloy currency + six-talent Armory.
6. **Content — endless + second map (Plan A)** — `MAPS[]` + `loadMap`/`selectMap` with a menu picker; a second `Switchback` layout; uncapped Endless mode with capped wave counts, `highEndless` best, and a post-victory "continue into endless".
7. **Balance pass (Plan C)** — added a headless auto-battle harness (`__GAME.sim`; the frame update block is now `stepSim`). Equal-count and equal-budget sims showed Tesla was the dominant per-scrap option (solo-cleared at L1) while the other three sat in their intended niches (Mortar/Cryo are air-blind by design, so their low *solo* numbers are the flyer counterplay, not weakness — confirmed by mortar+turret clearing wave 20). Fix was a targeted Tesla nerf (range/dmg/rate down across L1–L3); Tesla is now on par per budget and remains the anti-air/anti-shield specialist. No dead branches; mixed play stays challenging (normal ~clears, hard ~wave 20).
8. **Map variety** — generalized to per-map grid sizes and multi-route maps (see 1.5). Five maps from small to large-and-panned, single- to dual-entrance with crossing roads, rising ★1–★5. Enemies split across a map's entrances (two defensive fronts). Verified: all routes traverse to base, terrain re-bakes once per load, 60fps on the largest (13×22) map.
9. **Per-map biomes** — `BIOMES` table (rust/toxic/ash/ember) tints baked terrain, pools, directional light, and dust motes so maps read as distinct places. `BM = C + biome overrides`, set in `loadMap`.
10. **Hero / Commander (Plan B)** — one deployable, in-run-leveling unit (`hero`): energy auto-fire that hits air, XP from kills near it (5 levels), and an Overload Pulse ability (energy AoE + stun) on a 16s cooldown. Deployed via a second FAB (arm → tap a plot). `HERO` config; the `Command Core` Armory talent (`heroDmgMul`) boosts its damage. The frame update block is `stepSim` (also used by `__GAME.sim`), now including `updHero`.
11. **Graphics uplift (3 commits)** — (a) maps: baked path-edge ambient occlusion, denser+varied decor, new landmark set-pieces (ruined buildings, crashed dropships, sandbag walls, dead trees), richer barrels/rubble/craters/wrecks, road tire tracks; (b) towers: two-layer grounding shadow, glossy specular sheen, brighter emissive trim; (c) enemies: higher-contrast `bodyFill` + a screen-aligned overhead sheen and underside shadow for consistent form lighting. `_hx()` now parses `rgb()` strings so tint chaining is safe. All baked/per-frame-cheap; 60fps held.
12. **V2.1 + V2.2 SHIPPED (game is now branded V2.0)** — the Part 3 projection/composition phases:
    - **Island board**: terrain bakes with a `TMARGIN` ring — void backdrop with distant silhouettes, jagged island rim, extruded cliff faces (2 depth layers + strata + lit rim). Frame blits terrain at `(-TMARGIN,-TMARGIN)` over a `VOID_COL` fill.
    - **Curved roads**: corner tiles render as quarter-annulus asphalt (curb, trench shading, curved tire tracks, arc dashes) via a neighbor-pattern branch in `roadTile`; waypoint pathing unchanged.
    - **Trench walls**: straight/junction road edges get NW shadow gradients + lit SE inner walls, so paths read as sunken channels under the global light.
    - **Bridges**: `loadMap` classifies route overlaps — perpendicular = crossing (`CROSS_MAP`/`BRIDGES`), parallel = merge. Crossings render as live steel decks (`drawBridges`) with correct layering: under-route enemies → deck → over-route enemies (`bridgeUnder` predicate splits `drawEnemies`).
    - **Structures**: breach = ruined tunnel mouth (rock collar, teeth, dark throat, molten glow); base = walled fortress (wall ring, corner bastions with beacons, court) around the bunker.
    - **Authored set-pieces**: optional `MAPS[i].props` hand-place landmarks (reserved before hash decor); Outpost + Twin Gates composed.
    Verified: all 5 maps route-sim to gameover (gameplay untouched), no errors, 60fps in heavy combat on Twin Gates, guards intact. **V2.3 sprite baking SHIPPED**: `bakeSprites()` renders static tower bases (`towerBaseArt`) and enemy bodies (`enemyStatic`, per type incl. armor plating) once at 3x into offscreen canvases (`SPRITES`, `bakeSprite`/`drawSprite`; `ctx` is `let` and retargeted during baking so all shared helpers bake). Frame keeps only animated parts vector: legs/boots/arms/treads/rotor blades, rotating heads/cannon, and glows. Per-enemy sheen/underside overlays are baked generic sprites (`fx_sheen`/`fx_under`) blitted scaled by r — the frame loop constructs no per-entity gradients. Baked sprites carry an extra wear+rim pass (`wearPass`). Verified: no errors, walk anim intact, 57-59fps at max stress on software rendering. **V2.4 bloom/post pass SHIPPED**: a half-res glow buffer (`glowCv`/`renderGlow`) collects pure-glow emitters as cheap sprite blits (pool glows, breach/base/tower/hero/orb glows via baked `gl_*` sprites, beam impacts, boom flashes) under the same camera transform, then composites additively (`compositeGlow`, `lighter`) — bilinear upscale doubles as the blur. Plus drifting cloud shadows (`fx_cloud` sprite, multiply) and a per-biome screen-space color grade (`drawGrade`) that covers entities. **Adaptive quality** (`FX`/`fxTick`): bloom and clouds default on and auto-degrade (bloom first, then clouds) when the rolling 90-frame average exceeds 19ms, so weak devices settle at full frame rate (measured: 58.8fps settled on software rendering; capable GPUs keep everything). Do not re-run shadowBlur-heavy passes inside the glow layer — blits only. **Remaining: V2.5 optional tilt (only if still needed).**
13. **Difficulty rebalance + Brutal tier** — a greedy-player sim (builds/upgrades/branches with real scrap, uses hero + airstrike) showed every scenario cleared wave 20 with near-perfect core, even old-Hard without hero/strike. Fixes: quadratic HP curve, +25% speed creep, denser waves, heavier leak costs (tanks 2, boss 6), and the three-tier `DIFFS` table (Normal/Hard/Brutal) with count/reward/core/alloy knobs. Measured after tuning (same near-optimal AI): Normal full-kit comfortable, Hard full-kit 18 core (humans will bleed), Brutal full-kit 9 core and 8-tower builds DIE — Brutal is the maxed-talents tier. Re-run `scratch`-style sims via `__GAME.sim` after any future data change.
14. **Behavior enemies + 2 maps + Campaign mode** — (a) `mender` (radius heal pulse with cross-glow/ring fx + `gl_heal` bloom hint, wave 9+) and `splitter` (bursts into 3 `spawnling` fragments on kill, wave 11+); trait flags flow through `statsFor`, heal logic in `updEnemies`, split in `hurt()` so leaks don't split. Baked statics + animated bodies for both (mender pods/cross plates, splitter sac with squirming inner blobs + stubby legs). (b) `Gauntlet` 9×18 ash switchback ladder and `Delta` 13×18 toxic **3-entrance** map whose routes T-merge — roster is now 7, all in the menu picker. (c) **Campaign**: `⚔ Campaign · Mission N/7` menu button resumes from persisted `camp`; victory becomes "Mission N Secured" with a Next Mission button (or CAMPAIGN COMPLETE on map 7); Deploy/Endless clear `S.campaign`. Verified: both new maps route-sim to gameover, Delta uses all 3 routes, heal + split observed in a wave-12 sim, campaign start→victory→next→resume→complete flow, 60fps in combat on both maps, zero pageerrors, guards intact.
15. **V2.5 in a new file (`fallengrid-v25.html`; `fallengrid.html` frozen at V2.4)** — (a) the oblique tilt experiment — **since reverted to full 2D after user playtest; see Part 3 V2.5 for the verdict** (`TILT = 1` now; scaffolding inert); (b) **3 more maps → 10**: `Spiral` ★★ ember (single route spiraling to a center base), `Fracture` ★★★★ rust (2 gates, one bridge crossing + T-merge final), `Terminus` ★★★★★ ash finale (15×22, 3 entrances, two bridge crossings + merges); campaign is Mission N/10; (c) the free-play map picker is now a **styled `<select>` dropdown** (`#mapsel`) replacing the button grid — campaign is unaffected (it always resumes from `camp`). Verified: 154-probe screen↔world round-trip exact under tilt, tap selects the intended tile, all 10 maps no-tower route-sim to gameover, Terminus spawns on all 3 routes, campaign flow to CAMPAIGN COMPLETE on map 10, 56–60fps in heavy combat, zero pageerrors, guards intact.
16. **V3.0 REAL 3D — `fallengrid-v3.html`** — the documented WebGL exit, taken on user request. three.js r147 (UMD, 607KB) is embedded inline so the game stays a single offline file; the world is a true 3D scene (perspective camera at ~55°, extruded terrain, procedural low-poly meshes, one shadow-casting sun, per-biome sky/fog) while **all game logic, UI panels, HUD, audio, and the sim harness are unchanged** from V2.5. Full architecture in **Part 4**. Verified: 100-tile raycast round-trip exact, taps select the intended tile, all 10 maps route-sim to gameover, campaign flow, distinct biomes, zero pageerrors, ~40fps on SwiftShader *software* GL after adaptive quality (real GPUs run full quality).
17. **V3.1 polish pass on the 3D build** — ACES filmic tone mapping (exposure 1.05) + PCFSoft shadows with a stronger sun/ambient ratio for punchier shading; per-biome **gradient sky** background; additive **glow sprites** on every emitter (reactor core with pulse, breach lava, toxic pools, tesla orbs, cryo dome emissive pulse, tower accent + level studs, muzzle flashes, explosion flashes as camera-facing billboards, orb halos); terrain got **broken-slab height jitter** (0/1.1/2.2 steps — towers/hero/tile-highlight sit on `tileH`), **curb lip strips** where ground meets sunken roads, and stronger color mottling with patch tints; enemies got **swinging legs** driven by `e.walk`, spawn pop-in, spinning wraith ring; gatling barrels spin while targeting; 50 drifting dust motes; screen-space vignette on the UI canvas; pulsing selection ring. Verified: tap accuracy still exact (100/100 + real tap), route sims, campaign, zero pageerrors; software-GL fps unchanged after the adaptive ladder (real GPUs run full quality).
18. **V3.2 material/grounding polish (close-up quality)** — evaluation at max zoom showed towers reading as flat-shaded primitives on plastic slabs with nothing grounding them. Fixes: a **procedural PMREM environment map** (sky-gradient equirect canvas → `PMREMGenerator`) set as `scene.environment`, so **PBR `MeshStandardMaterial` metal** on towers (`std(col, rough, metal)`, roughness ~0.4 / metalness ~0.7) and the hero catch real specular/reflection; tower bases rebuilt as **beveled octagonal machined mounts** (dark foot + bevel + plinth, `rotation.y = π/8`) replacing the flat 50×50 pad; **contact-AO discs** (soft radial-black ground decals, `aoDisc`) under every tower, the hero, and all ground enemies (disc counter-offsets the spawn pop so it stays flat on the ground); a tiling **grunge texture** on the terrain via world-planar UVs (`toMesh(..., uvScale)`, `1/96`) multiplied over the vertex colors to kill the flat-plastic ground; exposure 1.05→1.12, hemi 0.72→0.55, sun 1.35→1.5 for more directional contrast now that the env map fills shadows. Verified: 100/100 tap round-trip + real tap, all 10 route sims, campaign, zero pageerrors, guards intact; software-GL fps ~23 on the largest map (PBR costs more per pixel in software rasterization — adaptive ladder already degrades there; real GPUs run PBR at full rate).
19. **V3.3 real post-processing + normal maps (the "high-quality 3D" pass)** — user note that the 3D still read "old and simple" vs the 2D build. Root cause: the 3D meshes had no per-surface detail and no post pipeline, whereas the 2D build's richness came from baked pixel detail + a bloom/grade pass. Fixes on the SURFACE + FINISH axes (both proven feasible before building): (a) a real `EffectComposer` stack — **SSAO + UnrealBloom + SMAA** — inlined from r147 `examples/js/` legacy modules (global-namespace, no bundling; ~124KB), giving true light-bleed, crevice shading, and clean edges; (b) **procedural tangent-space normal maps** (Sobel of a baked heightfield) on all metal (panel seams + rivets) and terrain (grit + cracks) so surfaces show relief under the sun; (c) a faster degrade-only adaptive ladder (SSAO→composer→shadows→downscale) that keeps normal maps/PBR at every level since they're near-free on real GPUs. See **Part 4.7–4.9**. Verified: 100/100 tap round-trip + real tap, all 10 route sims, campaign, zero pageerrors, guards intact; software-GL full stack ~14fps → ladder floor ~22fps (GPU-cheap post, CPU-rasterization-expensive; real phones run the full stack at cap). The honest remaining gap is FORM (procedural primitive meshes vs sculpted models) — an art-production task, not engineering (2.6).
20. **V3.4 code-authored art assets, pass 1 — towers + hero.** User: take it further / create real art assets. Interpretation stated up front: not purchased/Blender-sculpted GLTF (genuinely outside my ability), but **detailed models authored in code with real craft** — the approach many stylized games ship. Added a **modeling toolkit** (`Model()`/`xf()`) that accumulates primitives (box/cyl/sph/cone/torus) and **merges them per-material via `BufferGeometryUtils.mergeBufferGeometries`** (inlined, global-namespace) so a detailed multi-part unit is still ~2-4 draw calls. Redesigned all four towers as real machines on a shared beveled hex base with a glowing accent groove: **Auto-Gun** armored housing + mantlet + cheek plates + ammo drums + barrel (branches: spinning gatling cluster / long breacher); **Cryo** finned coolant base + emitter prongs + faceted glowing core dome; **Mortar** trunnion mount + recoil pistons + banded tilted tube + breech (branches: triple carpet / massive buster siege tube); **Rail-Tesla** insulator column + stacked coil toroids + top emitter cone + energy orb (branch: railgun rails). Redesigned the **hero** as a command unit: hex dais, armored torso with pauldrons + backpack + antenna, visored head, rotating energy-cannon arm. `emis()` PBR-emissive material zones bloom through the V3.3 pipeline. Tuned bloom (0.34/0.5/0.88) + emissive intensities so glows stay colored, and **fixed the tesla-orb scale** in `syncTowers` (the old `(4.5+lvl)×` multiplier ballooned the new real-radius orb). Verified: all 12 tower level/branch model paths build without error, 100/100 tap round-trip, all 10 route sims, campaign, zero pageerrors, guards intact; ~347 draw calls / 30k tris (trivial for real mobile GPUs). **Enemies (10 types) are pass 2** — same pipeline, next.
21. **V3.5 code-authored art assets, pass 2 — the 10 enemies.** Rebuilt every enemy with the `Model()` toolkit as a detailed, merged creature/machine with a strong silhouette and material zones, preserving the exact `syncEnemies` interface (per-instance tintable `MeshStandardMaterial` body/dark in `mats` for frost-lerp + hit-flash, shared non-tinted `emis()` eyes/emblems merged in, separate animated legs / wraith ring / shield bubble / heal ring / AO disc). Designs: **stalker** sleek capsule hunter-drone (nose cone, swept fins, 4 thin legs); **raider** trooper-bot (torso, chest plate, capsule head, shoulders, arms) — **warden** adds a front shield slab + back emitter; **brute** hulking mech (chest, shoulder yoke, capsule arms + box fists) — **sentinel** adds side armor plates; **wraith** floating icosahedral crystal core + spinning energy torus, no legs; **mender** rounded medbot with side dispenser pods + emissive green cross; **splitter** bulbous subdivided-ico sac with 3 visible inner blobs + stubby legs; **juggernaut** siege tank (hull, turret, cannon, track guards, road wheels, antenna). Toolkit hardened: added `cap`(capsule)/`ico`(icosahedron) primitives and made the merge index-safe (`toNonIndexed` — icosahedra are non-indexed). Verified: all 10 types instantiate through wave 19 with zero errors, 100/100 tap round-trip, all 10 route sims, campaign, guards intact; ~246 draw calls (per-instance PBR enemy materials are heavier on software GL but trivial for real mobile GPUs).
22. **V3.6 code-authored art assets, pass 3 — the maps.** (a) **Focal structures rebuilt with the toolkit**: `buildBreach` (ring of angled rock chunks + teeth + throat rim over the animated molten floor/glow) and `buildBase` (fortress — 4 perimeter walls, 4 corner bastion turrets with emissive beacons, a reactor housing with an emissive trim torus around the glowing core) — added to `world` as merged PBR models, a few draw calls each. (b) **Metallic props buffer**: a third merged buffer (`metal`, `MeshStandardMaterial` + `metalNormal`, roughness .5/metalness .62) so barrels (now with lid rim + mid band), wrecks, the dropship (fuselage + tail + stub wings + nose), building rooftop units/antennae, and bridge decks read as **shiny metal** instead of sharing the matte ground material. (c) **Scattered rocks/debris** on ~15% of buildable tiles (into the free merged land buffer). (d) Buildings gained a two-row lit-window pattern + rooftop greebles. All still baked at map load (never per-frame). Verified: all 10 maps build + route-sim to gameover, taps exact, campaign, zero pageerrors, guards intact; ~257 draw calls.
23. **QoL / settings pass** — (a) **Haptics on/off** (`Haptics` module, persisted `haptics`; `vibrate()` now early-returns when off — gates every buzz in the game; menu toggle paired with Audio in a `.row`, a short buzz confirms when re-enabled). (b) **Reset Campaign** — a menu ghost button (`id "rc"`, shown only when `Store("camp") > 0`) that `confirm()`s then sets `camp = 0`; Alloy/Armory untouched. (c) **Battery Saver** (`id "eco"`, persisted `eco`) — `G3D.setEco(on)` pins a lean fixed quality level (no post-processing, no shadows, full res, PBR+normals kept) and locks the adaptive ladder (`q.locked`); seeded at init from `Store`, a real win for battery/heat on the Android target. (d) **Speed persistence** — the 1x/2x/3x HUD toggle now saves to `Store("speed")` and seeds `S.speed` at init. (e) **Abandon confirm** — the pause-screen Abandon now `confirm()`s so a run isn't lost by a mis-tap. Verified: haptics gating (0 buzzes off / 45 on across a leak-heavy sim), speed + eco persist across reload, eco forces shadows off and releasing restores them, campaign reset clears to Mission 1, abandon returns to menu; route sims + campaign + guards intact.
24. **Audio split + range preview** — (a) **Music vs SFX** are now independent, persisted toggles (`Sound` module holds `sfx = Store("sfx")` gating `osc`/`nz`, and `musc = Store("music")` gating `startMusic`; API `toggleSfx`/`sfxOn`/`toggleMusic`/`musicOn` replace the old single `toggle`/`isOn`). Menu settings are two 2-button rows: Music | SFX and Haptics | Battery. Toggling SFX on plays a confirming blip; music start/stop still keys off `S.screen`. (b) **Tower range preview** — pressing (finger-down) a build tray button shows an **amber range ring** (`preRing`/`preFill` in `G3D.syncSel`) at the selected plot for that tower's L1 range, and pressing an Upgrade/branch button on a selected tower previews the resulting range; `S.rangePreview` is set by `previewFromPoint(x,y)` on pointerdown + updated on drag across the tray, and cleared on release (the release tap then performs the actual build/upgrade). No change to the one-tap build flow. Verified: Music/SFX toggle independently + persist, all four towers preview their correct L1 range (152/136/150/215) and clear on release, real tap-build still works, route sims + campaign + guards intact.

---

# Part 5 — V4 line (retention / liveops), `fallengrid-v4.html`

Copied from `fallengrid-v3.html` (V3.6 art baseline) as **V4.0**; each solution bumps the version +0.1. Sequenced by retention ROI from the competitive analysis (presentation is done; the gap vs successful Android games is retention systems, content cadence, platform integration). Same single-file / verify-before-ship discipline.

**V4.1 — Daily Op (date-seeded challenge + streak).** A once-a-day run with a deterministic map + difficulty + modifier picked from the calendar date (`dayKey` YYYYMMDD → `dhash` → `dailyConfig`), plus a persisted streak. **Modifier system** (reusable foundation): `activeMod` holds a bundle of multipliers folded into the existing balance via `modv(k)` — `diffMul` (hp), enemy `speed`, `modCount()` (wave counts), `reset` scrap/core, `awardAlloy` alloy, and a `ban` field that takes a tower offline in the build menu (`afford=false` + "⊘ OFFLINE" label). 8 modifiers (Swarm, Titan Rush, Blitz, Austerity, Fragile Core, Bounty, No Artillery, Grid Down). `Daily` persists `dstreak`/`dlast`/`ddone`; `complete()` on victory bumps the streak if yesterday was the last clear, resets to 1 on a gap, idempotent same-day; `activeStreak()` shows the live streak. Menu button `◈ Daily Op · <map> · <mod>` with ✓/🔥N; victory screen reads "Daily Op Cleared · 🔥 streak N"; +80 base Alloy bonus on a daily clear. `activeMod`/`S.isDaily` cleared on every non-daily start (Deploy/Campaign/Endless/Play-Again). Verified: config deterministic, modifiers apply (Fragile Core → 4 core), completion + streak increment/reset/idempotent, menu ✓/🔥, **no modifier leak into normal play** (Deploy still 20 core / 150 scrap), all 10 route sims + campaign + taps + guards intact.

**V4.2 — Achievements (24).** `ACH` array of `{id, name, desc, test(ctx)}`; `Ach` persists unlocks (`Store("ach")`) + cumulative stats (`Store("astat")`: kills, wins, alloy, maps-beaten set). Run flags added to `reset` and set in the sim: `S.leaked` (any core loss), `S.usedStrike` (doStrike), `S.builtTypes` (per tray/debug build), plus run-end reads of hero level and max-tier towers. `runAchCheck(won)` runs once per run (guarded by `S.achChecked`) on the gameover/victory render, updates cumulative stats, builds a ctx (won/diff/noLeak/endlessBest/heroLvl/usedStrike/builtCount/maxTower/kills/alloy/wins/mapsBeat/talentsMaxed/campaignDone/dailyStreak), and unlocks any passing achievement; newly-unlocked names show as a gold 🏆 line on the results panel. Armory purchases also call `evalAch(achCumulative())` so talent achievements unlock immediately. Menu button `🏆 Achievements · N/24` opens a scrollable list screen (`S.screen === "ach"`) with 🏆/🔒 per entry. Categories: wins/difficulty/flawless, endless milestones, cumulative kills, maps beaten, campaign, daily streak, tower mastery, hero, airstrike, alloy, talents. Verified: menu screen lists 24, a scripted win unlocked win1/noleak/l3/hero/arsenal/strike, unlocks persist across reload, `runAchCheck` idempotent (stats not double-counted on re-render), route sims + campaign + guards intact.

**V4.3 — Codex.** The old "Field Manual" (`S.screen === "howto"`) is now a **tabbed Codex** (`S.codexTab`: guide / tw / en; menu button renamed "📖 Codex"). **Guide** = the how-to-play bullets (updated for Daily Op). **Towers** = data-driven from `TOWERS`/`TOWER_ORDER`: each archetype with its accent-colored name, ◆ damage type, L1 DMG/RNG/rate, a role line, and both branch specializations with costs — topped by the damage-triangle summary. **Threats** = data-driven from `ENEMIES`: all 10 types in threat order with HP/SPD/reward and a one-line trait + counter hint (`THREAT` map: armor→explosive/pierce, flying→Auto-Gun/Tesla, shield→energy, mender→focus, splitter→kill-early-or-leak, boss→strip-then-sustain). Purely presentational/onboarding; no gameplay change. Verified: menu opens the Codex, all three tabs render their data (tower names/branches/dmgtypes, enemy names/traits/counters present), Back returns, route sim + guards intact.

**V4.4 — Expanded Armory (7 → 14 talents).** Added, each with `vals[3]`/`costs[3]`/`fmt` and a mul folded at one clean site: **Fire Control** `rate` (`rateMul = 1 − val` on `t.cd = st.rate`), **Targeting Optics** `range` (`rangeMul = 1 + val` on the findTarget gate + the 3D range ring + the range-preview + the 2D ring), **Warheads** `splash` (`splashMul` on `st.splash` at the two fire sites), **Salvage Refit** `sell` (`sellRefund = SELL_REFUND + val` on both sell display + sell action), **Contracts** `alloyf` (`alloyFindMul` in `awardAlloy`), **Battle Drills** `hrate` (`heroRateMul` on the hero fire cooldown), **Overcharge** `pulse` (`heroAbilCd = HERO.abilityCd − val` on the pulse cooldown). `TALENT_ORDER` regrouped (offense / economy / abilities / hero). The Armory list scrolls with 14 rows. Verified: 14 talents render, all buy, **base balance unchanged with talents at 0** (all 10 route sims still gameover), and the effects are exact — Overcharge L3 → pulse cd 16→10, Targeting Optics L3 → Tesla range 215→258 (preview reflects it), Salvage Refit L3 → 85-scrap mortar refunds 72 (85%). Guards intact.

**V4.5 — 5th archetype (Pyre) + deeper L4 upgrade tiers.** Two content additions folded into the existing tower pipeline.
- **Deeper tiers (L4):** every branch (`branches.a/.b` on all 5 towers) gained an optional `t4` stat block. The upgrade path is now L1 (build) → L2 (`+cost`) → L3 (branch choice) → **L4** (`t4`). `tStats(t)` returns `br.t4` when `t.lvl >= 3 && br.t4` (branch stats otherwise, `levels[t.lvl]` when unbranched). Wired at one site each: `towerSpent` adds the t4 cost; the tower-menu upgrade button is `canUp = t.lvl < 1 || (t.lvl === 2 && branch && t4)` with the right `upCost`; the upgrade action picks `levels[1].cost` vs `branches[br].t4.cost`; `branched` title flag is `t.lvl >= 2`; 2D `drawTowerArt` `brSpec` and 3D `buildTower` branch geometry both trigger on `lvl/L >= 2` so L4 keeps the branch's silhouette (just bigger stats). L4 values are ~1.5–1.7× the branch (e.g. Railgun→Annihilator 205→340 dmg / 320→352 rng; Buster→Devastator 158→270 dmg).
- **Pyre (5th tower, `kind: "burn"`, explosive, ground-only):** a cheap flame projector that hits **every ground foe in a forward cone** (range + |Δangle| < 0.85) for a small direct hit and stamps a **burn DoT** (`e.burn = {dps, t, pierce, dtype}`) ticked in `updEnemies` (after the `healFx` decay, inside the enemy loop, with an `if (!e.alive) continue` guard). Branches: **Inferno** (wider/hotter) and **Plasma** (`pierce`, ignores armor), each with a `t4`. New 2D art (`drawTowerArt` `else` after splitting tesla into its own `else if (kind==="beam")`): squat body + fuel tanks + flared nozzle + animated pilot flame. New 3D model in `buildTower` (`t.type === "pyre"`): pump body, side fuel tanks, flared nozzle tube + muzzle, plasma rails on the b-branch, and a pulsing emissive flame sphere reusing the `orb` handle so `syncTowers` animates it. `canHitAir("burn")` = false. Added to `TOWER_ORDER` (now 5), the Codex `ROLE` map, and the tray layouts (`drawTrayIdle`/`drawBuildMenu` now compute `bw` from `N = TOWER_ORDER.length` so 5 cells fit the width). **Full Arsenal** achievement → `builtCount >= 5`.
- Verified (Playwright/Chromium, `verify45.py`): V4.5 label; build menu renders 5 towers; all 5 types × both branches at **L4 build in 3D with no page errors**; Pyre places, **applies burn DoT** (`e.burn` observed) and kills (19 kills in a scripted wave); Full Arsenal reaches 5 built types; base balance intact (maps 0/3/7/9 route-sim to gameover with no towers, fresh scrap still 150); campaign next-mission flow intact; **0 page errors**. Guards intact (`nextwave`=1, `countdown -= raw`=1), `node -c` on the 608 KB game script passes.

**V4.6 — Android essentials (Capacitor-ready platform pass).** No gameplay change; makes the single HTML behave as a proper Android app when wrapped in Capacitor, with clean browser fallbacks so it still runs standalone.
- **Hardware/gesture back button:** new `onBack()` state machine — a live run pauses (or first cancels an armed airstrike/hero deploy), the pause screen resumes, sub-screens (howto/armory/ach/gameover/victory/stats) step back to the menu, and only the main menu returns `false` so the OS exits. Wired to `Capacitor.Plugins.App` `backButton` (→ `exitApp()` when unhandled) when present, else a browser/PWA fallback that traps the back gesture with a sentinel `history.pushState` + `popstate` re-push.
- **Lifecycle pause:** `visibilitychange`/`blur`/`pagehide` call `backgroundPause()` → `Sound.suspend()` (stops music + parks the `AudioContext`) and pauses a live run, so a backgrounded game never keeps simulating (and losing) or draining battery. New `Sound.suspend()` on the audio API.
- **Capacitor Haptics bridge:** `vibrate()` now prefers `Capacitor.Plugins.Haptics` when available — arrays/≥40 ms → `vibrate({duration})`, short taps → `impact({style: Medium|Light})` — falling back to `navigator.vibrate`. Still gated by the existing user-toggleable `Haptics.isOn()`.
- **Portrait lock** via `screen.orientation.lock("portrait")` (best-effort, try/catch). **Safe-area insets:** `#overlay` padding switched to `max(20px, env(safe-area-inset-*))` for notches/gesture bars (the in-canvas HUD is already inset by the 360×640 letterbox fit, so it clears notches on tall phones without touching HUD math).
- Verified (Playwright, `verify46.py`/`verify46b.py`): back state machine (playing→paused→playing, armed-strike cancel, all sub-screens→menu, menu→unhandled), a real browser back gesture pauses a running game, `visibilitychange` hidden pauses it, the **Capacitor Haptics path is actually taken** (`deployHero` → `impact("Medium")` observed on a stubbed plugin), safe-area CSS rule present, V4.6 label, and regression intact (route sim → gameover, campaign start). 0 page errors, guards intact, `node -c` passes.

**V4.8 — Camo/detection enemy + 4 new maps + Daily round-robin.** (V4.7 "second hero" skipped by user request — jumped straight to 4.8.)
- **Camo/detection mechanic — new enemy "Phantom" (`camo: true`, ground, hp 46 / spd 116 / ⬡9).** A cloaked infiltrator that towers **cannot target until it is revealed**. New `updDetection(dt)` (runs in `stepSim` *before* `updTowers`): camo foes fade their `e.revealed` timer down each tick, and any **Rail-Tesla tower** (range-based) or the **Hero** (150px) re-reveals every camo enemy in range to `revealed = 0.9` — so once detected, *all* towers can engage it. `findTarget` skips `e.camo && !(e.revealed > 0)`. An **airstrike** also reveals (`revealed = 1.4`) whatever it blankets. `statsFor` carries `camo`, spawn inits `revealed: 0`. Injected into waves from n≥7 (`ph = min(floor((n-4)/3), 8)`). 3D render: camo materials flagged `transparent` in `buildEnemy`; `syncEnemies` drives `opacity = revealed > 0 ? 1 : 0.2` (glowing eyes stay visible as a faint tell since the emissive eye material isn't in `mats`). Codex Threats tab + `ENEMY_LABEL` + Tesla ROLE ("reveals camo") updated.
- **4 new maps → roster 10→14:** Switchback (ember, 10×16), Crucible (toxic, 13×18, 2 routes), Meltline (ash, 12×20), The Maw (rust, 15×22, 3 routes). Free-play picker and campaign pick them up automatically. "Conqueror" achievement retargeted to `mapsBeat >= MAPS.length` ("Beat every map").
- **Daily Op now round-robins through every map.** Replaced the hash-mod map pick with a deterministic day-ordinal rotation: `dayNum(d)` = UTC midnights since epoch, `map = ((dayNum % MAPS.length) + MAPS.length) % MAPS.length`. Guarantees a different map each day, visiting all 14 in turn with no repeat inside a cycle (difficulty + modifier stay hash-driven).
- Verified (Playwright, `verify48.py`): 14 maps in the picker; Daily config over 28 consecutive days = `[0..13,0..13]` (covers all 14, changes daily, periodic, no consecutive repeat); camo unit test — a crafted cloaked Phantom is **not** targeted by a turret with no detector, a placed Tesla sets `revealed=0.9` and the turret then targets it; Phantom actually spawns in waves 7–14; all 4 new maps load (3D world builds) and route-sim to a resolved end; base map0 still route-sims to gameover. 0 page errors, guards intact, `node -c` passes.

**V4.9 — Build/upgrade confirmation with stat preview + early-call wave bounty.** Player-help & wave-flow pass from direct user feedback.
- **Confirm step with stats (build / upgrade / branch).** Tapping a tower in the build tray, or UPGRADE/a branch in the tower menu, no longer commits instantly — it arms `S.pending = {kind, tower, branch}` and the tray renders a **confirm panel**: tower art + name, ◆ damage type, a stat line, cost, and **✓ CONFIRM ⚙cost / ✗** buttons, with the range ring shown persistently on the target plot. Builds show plain stats (`DMG · RNG · rate · ~DPS`); upgrades/branches show **before→after deltas** (`DMG 9→15  RNG 152→168  0.5→0.4s  DPS 18→34`) plus special tags (PIERCE/CHAIN/SPLASH/SLOW/BURN/SHATTER). The mutation moved into a new `doPending()` (re-checks affordability); the old instant-build/upgrade/branch paths in `trayAction` now just set `S.pending`. `✓` disabled (dim) when unaffordable; a world tap, ability-arm, wave start, or `reset()` cancels the pending confirm. `previewFromPoint` early-returns while pending so the hold-preview doesn't fight the persistent ring. Fixes the "it builds the instant I release" problem and surfaces stats before spending.
- **Early-call wave bounty + longer prep window.** `NEXT_WAVE_COUNTDOWN` 6→12 s. Deploying the next wave before the countdown expires pays `earlyCallBonus() = round(countdown × (2 + min(wave,15)×0.5))` bonus scrap (more time forfeited → bigger reward), with a floating `+N EARLY` at the reactor. The DEPLOY button advertises the live bonus (`▶ DEPLOY 8s  +32`). Rewards aggressive pacing while the longer default gives builders more room; base wave-clear bonus unchanged.
- Verified (Playwright, `verify49.py`, driving real taps via exposed `trayBtns`/`hudBtns`): first build tap arms pending + shows the ring but **does not build**; cancel builds nothing; confirm builds and deducts 50; upgrade routes through confirm (no lvl change until confirm, then +1); early-call pays exactly +32 at wave 4 / 8 s left and starts the wave; a no-time call pays 0; countdown lengthened (~11.9 s after a clear); base map0 still route-sims to gameover; campaign start intact. 0 page errors, guards intact, `node -c` passes.

**V4.10 — Continuous wave cadence + send-during-wave bounty.** Reworked the wave loop so the next wave is on a visible, always-running timer (old model only started the countdown *after* the field was fully cleared, and blocked sending a new wave while one was active).
- **Continuous timer / auto-launch:** new `WAVE_GAP = 20 s`. `S.countdown` now runs continuously while more waves remain (frame + headless sim ticks lost their `!S.waveActive` guard); at 0 it auto-launches the next wave. `startWave()` no longer guards on `waveActive` — it **appends** the new wave's spawns to the live queue (`{...e, t, w}`, `w` = wave# so overlapping spawns keep their own `statsFor` tier) and re-arms `WAVE_GAP`, so waves overlap under pressure. `updSpawns` always drains the queue and **derives** `S.waveActive = wave>0 && (queue||enemies)`; victory fires when every wave is launched and the field is clear. Per-wave "survival salvage" (`20 + (wave-1)*3`) now paid on each launch (wave ≥ 2) instead of on clear.
- **Send next wave mid-combat for a bonus:** the HUD button is now always shown while waves remain (not just between waves). Label shows the live countdown + bonus (`▶ NEXT 15s  +36`); left of it shows `☠ N` hostiles while fighting or the incoming-wave dot preview otherwise. Tapping it launches the next wave immediately (even with the current one alive) and pays `earlyCallBonus() = round(countdown × (2 + min(wave,15)×0.5))` — launching wave 1 pays nothing (no prior wave survived).
- Verified (Playwright, `verify410.py`): countdown runs from run start (~20 s, button present) and ticks down; with core pinned high, waves **auto-launch on the timer and overlap** (reached wave 3 with 5 enemies still alive, `waveActive`); mid-wave send pays exactly early+salvage and increments the wave; wave-1 early launch pays 0; a maxed build reaches **victory** (wave 20) and a no-tower run still **gameover**s; campaign start intact. 0 page errors, guards intact, `node -c` passes. **Next: V4.7 second hero (open) or V5.0 map hazards.**

## 2.1 Where things are

```
fallengrid-v3.html   the current build — REAL 3D (three.js r147 embedded), 10 maps, campaign, dropdown — ship this
fallengrid-v25.html  the V2.5 build (full-2D Canvas2D, 10 maps, dropdown picker) — kept as the 2D fallback
fallengrid.html      the V2.4 build (7 maps, button-grid picker) — frozen, kept per user request
HANDOFF.md           this document (source of truth)
README.md            repo readme
```
New work goes into `fallengrid-v3.html` (see Part 4 for its renderer architecture); the older files are frozen.
Git: work on branch `claude/tower-defense-graphics-l7p9mn`. No build artifacts committed; verification scripts are ephemeral (see 2.7).

## 2.2 Edit and verify loop

Edit `fallengrid.html` directly (the JS is the largest `<script>` block). After any change run the checks in 2.7 before declaring done.

## 2.3 Environment constraints

No Android SDK/emulator; `dl.google.com`/Google Maven not allowlisted. Cannot compile/sign an AAB here. Produce the web build + Capacitor project; the user builds and signs locally. Chromium is pre-installed at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (Playwright, `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`).

## 2.4 Conventions

Single IIFE, `"use strict"`. Terse helpers (`clamp`, `lerp`, `rr`, `hash2`, `mix/lighten/darken/rgba`). Colors centralized in `C`; tuning is data-driven in `TOWERS`/`ENEMIES`/`TALENTS` — prefer editing those tables over logic. World drawing goes inside the camera block; screen UI after `restore()`. Color helpers return `rgb()/rgba()` strings so the hex scan stays clean; keep literal hex colors valid.

## 2.5 Quality assessment vs genre leaders (Kingdom Rush, Bloons TD 6, Arknights)

Mechanically the game is at genre standard: depth (counterplay triangle, branches, hero, airstrike), retention (Alloy/Armory, endless, campaign), content (10 maps, 4 biomes), feedback, audio, onboarding, and a verified balance curve. The remaining distance to the flagships:
- **Presentation** is now the #1 gap — see Part 3 for the full root-cause analysis and plan. Short version: the game is drawn in true top-down with no verticality, so nothing has fronts/sides; leaders render in a tilted 3D-ish view where everything is a volume.
- **Enemy design**: 5 traits deep (armor/shield/flying/heal/split) — now comparable to mid-tier leaders; teleport/burrow-style movement tricks remain unexplored.
- Content keeps scaling value (more maps/enemies) but is no longer structurally behind.
- No liveops/social/monetization (not a craft gap).

## 2.6 Backlog, prioritized (remaining)

1. **Art assets, pass 2 — the 10 enemies** (towers + hero done in V3.4). Rebuild each enemy with the V3.4 `Model()` toolkit as a detailed, merged, characterful creature/machine (strong silhouette + material zones + emissive), replacing the current primitive bodies in `buildEnemy`. Keep the animated parts (legs, wraith ring) separate from the merged body. Same pipeline as the towers. **Ceiling note:** code-authored detailed models (the V3.4 approach) get us to a strong, cohesive stylized look; the absolute top tier (Bloons-TD-6 hand-sculpted characters) still needs **hand-authored GLTF from a 3D artist / licensed packs** dropped in at the `buildTower`/`buildEnemy` sites — an art-production task an LLM can't author at that quality. Flagged honestly.
2. **Camera feel & accessibility** — pan inertia, zoom easing, colorblind-safe enemy/HP palette, larger-touch-target option.
3. **Android port** — Capacitor scaffold, icons/splash, signed AAB (done by the user locally).

Done and verified: endless + map roster (Plan A), balance pass + sim harness (Plan C), Hero/Commander (Plan B), biomes, graphics uplift pass 1, Visual Direction V2.1–V2.5 (V2.5 in `fallengrid-v25.html`), difficulty tiers, behavior enemies + campaign (14–15), REAL 3D V3.0–V3.3 (three.js, PBR, env map, normal maps, EffectComposer post — in `fallengrid-v3.html`).

---

# Part 3 — Visual & Map Direction V2

The re-evaluation asked two questions: **how do we make the game read like a 3D-rendered title**, and **how do we make map layouts feel composed rather than simple**. This part is the answer and the plan. Plans A/B/C from the previous handoff revision are complete and archived in the changelog (2.0).

## 3.1 Re-evaluation: why the game still reads "flat 2D"

Judged against Kingdom Rush (painted 3D-ish perspective) and Bloons TD 6 (real 3D renders), the current build's gap is not detail — pass 1 added plenty — it is **projection and volume**. Root causes, in order of impact:

1. **True top-down projection.** Everything is drawn from directly overhead, so no object can show a front or a side. The leaders render from a tilted ~50–65° camera: every tower, tree, and wall shows a **top AND a front face**. Verticality is the single strongest "3D" cue and we have none of it.
2. **No extrusion.** Objects are silhouettes filled with gradients. There are no side walls on the sunken roads, no plinths under towers, no wall faces on buildings' lower halves. Volume = top face + side face + cast shadow; we only have tops.
3. **No directional cast shadows.** We have contact blobs under entities, but a real scene has one global light with **elongated shadows falling one consistent direction** from everything — that is what visually welds objects to the ground plane.
4. **Per-frame vector redraw caps the detail budget.** Every tower/enemy is rebuilt from primitives 60×/s, so each can only afford a handful of gradient layers. The leaders' sprites are *renders* — hundreds of lighting passes baked offline. We can get most of that headroom by **baking our procedural art into sprites at load** and blitting.
5. **The board is a wall-to-wall rectangle.** Leaders float an irregular "island" board over a backdrop with visible cliff edges — the world reads as a diorama on a table. Ours runs edge-to-edge with hard clipping, killing the diorama depth cue.
6. **Map composition is uniform.** Decor is hash-scattered, corners are hard 90° squares, spawn/base are small glows rather than structures, and there is no elevation. Nothing anchors the eye; layouts feel generated, not designed.

**Projection decision.** Four options were weighed:

| Option | Look | Cost | Risk | Verdict |
|---|---|---|---|---|
| A. Stay top-down, more detail | incremental | low | low | insufficient — detail was pass 1; projection is the gap |
| B. **Faux-3D extrusion** (keep top-down math, draw every object with height: top + front face + directional shadow) | "tilted board" illusion, à la many premium 2D TDs | medium | low — gameplay/input math untouched | **chosen core** |
| C. World y-foreshortening (scale world y ~0.85 in the camera, full oblique view) | strongest tilt illusion | medium | medium — `screenToWorld`/tap must be updated symmetrically | optional layer on top of B, behind a flag |
| D. WebGL/three.js real 3D | true 3D | very high (renderer rewrite, breaks single-file/no-framework constraint) | high | rejected for now; documented exit if the game outgrows Canvas2D |

## 3.2 The plan — phases V2.1 → V2.5

Each phase is a separate verified commit. All must keep the 1.10 guards, the "terrain bakes once per load" rule, and 60fps on the largest map (13×22, 2× DPR).

### V2.1 — Extrusion & global light (the projection change)

**Design.** Introduce a global light constant (`LIGHT = upper-left`, matching the baked gradient) and a world-standard **elevation rendering idiom**: any object with height `h` draws (bottom→top) directional cast shadow (offset SE, length ∝ h, soft) → front/side face (darkened body color, height `h`) → top face (existing art, offset up by `h`). Apply it to the **baked terrain first** — the highest coverage per effort:
- Sunken roads: visible **inner north wall** (light catches it) and shadowed south lip, so paths become real trenches.
- Buildable ground gets subtle raised-pad edges every few tiles (broken slabs), giving the plane texture without noise.
- Props re-rendered with the idiom: buildings get full front faces with doors/windows; sandbags, barrels, rubble, wrecks get fronts + directional shadows; dead trees get long ground shadows.
- Spawn/base become **structures**: breach = ruined tunnel arch with dark interior; base = walled fortress compound around the reactor.
**Touch-points.** `buildTerrain`, `roadTile`, all `draw*` decor functions, `drawSpawnAndBase`. All baked; zero frame cost.
**Risk.** Low (visual-only, baked). **Estimate.** ~1 session.
**DoD.** Roads read as trenches with lit/shadow walls; every prop casts a consistent SE shadow; spawn/base are structures; screenshots on 3 biomes; 60fps.

### V2.2 — Map Layout 2.0 (composition)

**Design.**
- **Island board.** Bake an irregular edge mask: the outermost ring of tiles crumbles into cliff edges with visible dark rock faces (extrusion idiom) over a deep backdrop (biome-tinted void + faint distant silhouettes). The map becomes a floating diorama. Board edge never cuts a route.
- **Curved corners.** Road corner tiles render as quarter-arc asphalt (with curb + tracks following the curve) instead of squared blocks. Pure `roadTile` change keyed on the neighbor pattern; enemy waypoints unchanged (the visual arc covers the same tile).
- **Bridges at crossings.** Where two routes' tiles overlap (Crossroads, Twin Gates), render route 2's crossing tile as a **bridge deck** (planks/steel + railings + shadow cast onto the road below). Data already knows the overlap; flyers/ground logic unchanged — it is a pure render upgrade that makes crossings a landmark.
- **Authored set-pieces.** Add optional `props: [{c,r,type}]` to `MAPS[i]` for hand-placed landmarks (e.g., the dropship crash framing Outpost's first corner) so each map has a composed focal point; hash decor fills around them.
- **Elevation tier (stretch).** A per-map `plateau` region: tiles one tier up with cliff-wall faces; purely visual first (towers on it just look elevated), optional +range gameplay later.
**Touch-points.** `MAPS` data, `buildDecor`, `buildTerrain`, `roadTile`, new `drawCliffEdge`/`drawBridge` bakes.
**Risk.** Low-medium (baked; bridge draw order needs care at crossings). **Estimate.** ~1 session.
**DoD.** Every map reads as a floating island; corners curve; both crossing maps show bridges; at least 2 maps have authored set-pieces; routes/gameplay unchanged (no-tower sim still reaches gameover on all maps); 60fps.

### V2.3 — Procedural sprite baking (the detail unlock)

**Design.** A `bakeSprites()` step at load (and on map/biome change if tinted): render each **tower base** (per type × level × branch) and each **enemy body** (per type) once into offscreen canvases at 2–3× resolution with a far richer pass stack than the frame budget allows — base coat, noise/wear texture, AO pass, bevel highlights, rim light, decals. Frame loop blits sprites (`drawImage`) and keeps only the dynamic parts vector: rotating heads/cannons, legs/treads (animated), glows, muzzle flashes, shields. This is the original handoff's sprite-pipeline item, self-sourced: same architecture as dropping in a Kenney atlas later (the blit sites become the atlas API).
**Touch-points.** New `bakeSprites()`; `drawTowerArt` split into `bakeTowerBase` + dynamic head; `enemyBody` split into baked body + dynamic limbs; cache keyed by type/level/branch.
**Risk.** Medium — draw-order and rotation seams; memory for sprite canvases (bounded: ~20 towers + 7 enemies × small sizes). **Estimate.** ~1–1.5 sessions.
**DoD.** Frame loop contains no per-frame gradient construction for bodies/bases; visual quality strictly better in side-by-side screenshots; 60fps with 30 towers + 40 enemies; walk/turret animation intact.

### V2.4 — Lighting & post pass (the "render" feel)

**Design.**
- **Bloom compositing:** all emissives (accents, cores, beams, pools, breach) draw to a half-res offscreen glow layer each frame, blurred once, composited additively — real bloom instead of per-shape `shadowBlur` (also a perf win: removes many shadowBlur calls).
- **Cloud shadows:** two huge soft dark blobs drifting slowly over the terrain (screen-space multiply), selling the sun.
- **Biome color grade:** a final translucent gradient overlay per biome (already partial via baked light; extend to entities by applying it after the world layer).
- Muzzle light: firing towers briefly tint nearby ground (radial gradient, cheap, capped count).
**Touch-points.** Frame compositor (one offscreen canvas), `drawBeams`/`drawBooms`/glow call sites, `drawAtmosphere`.
**Risk.** Medium — the only phase touching per-frame architecture; must profile on 2× DPR. **Estimate.** ~1 session.
**DoD.** Bloom visibly unifies emissives; fps ≥ 58 on the largest map with heavy combat; toggling the glow layer off is a one-line fallback.

### V2.5 — Optional tilt (projection C) — TRIED AND REVERTED (decision final)

**Outcome.** Implemented in `fallengrid-v25.html` (`TILT = 0.85` ground foreshortening in both camera transforms, all screen↔world conversions symmetric, `uprightAt(y)` counter-scaling entities/floats/base upright) and verified mechanically sound (154-tile round-trip exact, taps accurate, 56–60fps). **User playtest verdict: rejected.** Squashing top-down-authored terrain does not create perspective — the map still reads flat 2D while ground-plane ellipses (tower range rings) imply a perspective that isn't there; the cues contradict. Reverted to `TILT = 1` (exact full-2D math; the scaffolding remains inert in the file with a comment recording the verdict).
**Lesson recorded.** An affine y-squash cannot tilt art that was authored top-down; the projection must be baked into the art itself. A genuinely 3D view is the documented **WebGL exit** (Part 3 "Out of scope") — a renderer rewrite behind the same game state — not a camera transform. Do not re-attempt tilt-by-scale.
**Presentation direction.** The game commits to the polished top-down look (V2.1–V2.4 extrusion/light/bake/bloom), where circles are circles and all cues agree.

### Sequencing & constraints

**V2.1 → V2.2 → V2.3 → V2.4 → (V2.5 if needed).** The first two are baked-only (zero frame cost, low risk) and deliver the biggest projection change; sprite baking then raises the entity ceiling; the post pass unifies it. Constraints throughout: single file, no frameworks, no external assets, `buildTerrain` never in the frame loop, 1.10 guards intact, verify per 2.7 (syntax, hex, headless run incl. a no-tower route sim per map, screenshots per biome, fps sample).

**Out of scope / exits.** Real 3D (WebGL) remains the documented exit if the game outgrows Canvas2D — it would be a renderer rewrite behind the same game state, and nothing in V2.1–V2.4 is wasted (the baked art becomes texture sources). External art packs remain compatible: V2.3's blit sites are exactly where a downloaded atlas would plug in.

## 2.7 Definition of done for any change

1. **Syntax + hex.** Extract the largest `<script>` to `_ex.js`, `node -c _ex.js`, and scan for malformed hex:
   ```bash
   python3 - <<'EOF'
   import re; html=open("fallengrid.html").read()
   open("_ex.js","w").write(max(re.findall(r'<script>(.*?)</script>', html, re.S), key=len))
   EOF
   node -c _ex.js && grep -oE '#[0-9a-fA-F]{3,8}' _ex.js | sort -u | awk '{n=length($0)-1; if(n!=3&&n!=6&&n!=8) print "BAD HEX:",$0}'
   ```
2. **Headless logic/render.** Playwright + Chromium (`/opt/pw-browsers/...`) driving `__GAME`: assert waves resolve, auto-advance fires, wave 2 auto-starts with no input, no NaN in `S`/enemies across several waves (incl. a boss shield wave), and capture at least one screenshot confirming the change renders. Watch `pageerror`/console for zero errors.
3. **Performance.** Sample frame times; hold ~60fps. Never move baked terrain work into the per-frame path.
4. **Guards.** The two wave-progression guards in 1.10 remain intact.
5. State any balance or UX assumption made.

## 2.8 Android port path

1. Capacitor app, `webDir` = `www`, copy `fallengrid.html` → `www/index.html`.
2. `npm install`, `npx cap add android`.
3. Icons/splash via `@capacitor/assets`.
4. `npx cap sync`, `npx cap open android`.
5. In Android Studio set applicationId, build a signed release AAB, upload to Play Console (content rating, privacy policy, store assets are not code). No known technical rejection cause.

---

# Part 4 — V3.0 Real-3D Renderer (`fallengrid-v3.html`)

The WebGL exit documented in Part 3 was taken on user request. V3.0 replaces the world renderer with a true 3D scene; **everything else — game state, simulation, waves, economy, UI panels, HUD/tray drawing, audio, the `__GAME` sim harness — is byte-identical logic carried over from V2.5.** The 3D module only *reads* game state.

## 4.1 Architecture

- **Single file, still offline.** three.js r147 (UMD build, 607KB, global `THREE`) is embedded inline as the first `<script>`; the game IIFE follows. No CDN, no build step. r147 is pinned deliberately: it is the last release line with a UMD single-file build.
- **Two stacked canvases.** `#gl` (WebGL, z-index 1) renders the world; `#game` (Canvas2D, z-index 2, transparent) renders ALL screen-space UI exactly as before: HUD, tray, banners, FABs, boss bar, tutorial, plus the projected overlay (enemy health bars, damage floats). `frame()` clears the 2D canvas, calls `G3D.frame(shake, dt, dtMs)` then `G3D.overlay()`, then the unchanged screen-layer draw calls.
- **The `G3D` module** (IIFE inside the game IIFE, also on `window.G3D`) exposes: `buildMap()` (called by `loadMap` — replaces the 2D terrain bake), `frame(so, raw, dtMs)`, `overlay()`, `pick(sx, sy)`, `project(wx, wy, h)`, `resize(sc, dpr)`, `applyCam()`, plus `scene/camera/renderer` for debugging.

## 4.2 Camera & input (the critical contract)

`cam { x, y, zoom }` keeps its exact V2 semantics — a virtual top-down window (world coords of the viewport top-left, pixels-per-world-unit) — so **all pan/pinch/clamp/fit code is unchanged**. `applyCam()` derives the real camera each frame: view center `(cx, cz)` from the window, distance `dist = (W/zoom/2) / (tan(fov/2) * aspect)`, position at elevation `ELEV = 0.96 rad (~55°)` south of the target, `lookAt` the center (with a small aim offset so the play viewport, not the full canvas, centers the world). World mapping: 2D `(wx, wy)` → 3D `(x=wx, y=up, z=wy)`.

- `screenToWorld` = `G3D.pick`: raycast through the pixel onto the ground plane `y=0`. Exact by construction — verified 100/100 tile round-trips.
- `worldToScreen` = `G3D.project(wx, wy, 0)`: project + NDC→pixels. Used by coach marks and the overlay.
- `zoomAt` re-anchors by raycasting the same pixel after the zoom change and shifting `cam` by the world delta (perspective-safe).

## 4.3 World build (per map, `buildMap`)

Heights: buildable tile tops `y=0`, road channels sunken to `ROAD_Y=-10`, bridge decks `DECK_Y=+6`, island bottom `-46`, flyers at `+26`. The whole island — tile columns with conditional side walls (lit SE / shadowed NW faces, cliff color at the perimeter), craters, sandbags, rubble, wrecks, dead trees, buildings with emissive windows, dropships, breach tunnels, fortress base walls — is pushed into **one merged vertex-colored BufferGeometry** (Lambert) plus one emissive merged geometry (road dashes, windows, barrel tops) = 2 draw calls for all static world. Pools and breach lava are small separate meshes with pulsing opacity; the reactor core is a pulsing emissive sphere. Per-biome: sky/fog color, hemisphere tint, sun color (warm on ember). One directional sun casts real shadow maps (1024px ortho frustum sized to the world).

## 4.4 Entities & effects

- **Towers**: procedural low-poly groups per type×level×branch (rebuilt when the key changes) — plinth + rotating head (`rotation.y = -t.angle`), barrels/domes/tubes/coils per type, emissive accent tips, muzzle-flash sphere on `t.flash`, recoil offset. Cached shared unit geometries (`GEO.*`) scaled per part.
- **Enemies**: per-shape builders (stalker/raider/brute/wraith/mender/splitter/juggernaut) pooled per type; per-instance cloned body materials so **frost tints** (lerp to ice blue), **hit flashes** (emissive pulse), shield bubbles (transparent sphere, opacity from shield fraction), and the mender's expanding heal ring all animate independently. Position = sim state; ground height lerps between road/deck (smooth bridge ramps); walk wobble from `e.walk`, flyers hover with bank roll.
- **Effects, all pooled, zero allocation per frame**: beams = additive-blended stretched cylinders; explosion rings = ground rings, flashes = additive spheres; orbs/mortar shells = pooled meshes (shells fly a real arc); scorches = dark ground decals; smoke = billboarded sprites (canvas radial texture); sparks + gibs share one 500-point additive `THREE.Points` cloud with per-point color fade.
- **Selection**: range ring (thin additive ring, radius = range — a true ground-plane circle, consistent under perspective), pulsing tile highlight quad, tutorial plot spotlight.

## 4.5 Performance & quality ladder

Adaptive controller (90-frame rolling average): >30ms → shadows off + pixelRatio 1; >45ms → shadow maps disabled + 0.8× render scale. SwiftShader *software* GL settles ~40fps at 360×640 with heavy combat; real GPUs never degrade. Never rebuild geometry in the frame loop — `buildMap` runs only on map change; entity meshes rebuild only on upgrade/branch.

## 4.6 Verification additions (on top of 2.7)

Headless WebGL needs Chromium flags: `--no-sandbox --enable-unsafe-swiftshader`. Verify per change: `THREE.REVISION` loads, `G3D.renderer.getContext()` truthy, 100-tile `project→pick` round-trip exact, `tap` selects the intended tile, all-map no-tower route sims, campaign flow, biome screenshots, settled fps, zero pageerrors, and the 1.10 guards (unchanged, they live in sim/HUD code).

## 4.7 Post-processing pipeline (V3.3)

Real `EffectComposer` stack, inlined from three.js r147 `examples/js/` (legacy global-namespace variants — no ES-module bundling; ~124KB as a second `<script>` after the core): `RenderPass → SSAOPass → UnrealBloomPass → SMAAPass`. Built in `buildComposer(w,h)`, driven each frame via `composer.render()` when `post.on`. This is what recovers (and exceeds) the 2D build's bloom/grade: **UnrealBloom** gives true light-bleed on every emissive, **SSAO** adds crevice/contact shading over the whole scene, **SMAA** removes the low-poly jaggies. `SSAOPass` needs the `SimplexNoise` math addon (also inlined).

**Adaptive ladder (`quality`/`setLevel`)** is degrade-only with a 40-frame window after a 40-frame warmup: L0 full → L1 drop SSAO → L2 drop the whole composer → L3 shadows off → L4 downscale 0.8×; it jumps multiple levels when far over budget. **Normal maps + PBR + shadows stay on at every level** — they're near-free on real GPUs (measured: the no-composer floor equals V3.2). A real 60fps phone (16.7ms) never trips L0; weak devices shed post fast and land on the solid PBR floor. `G3D.setPost(on, ssao)` forces state for screenshots/debug. **Perf note:** on this container's SwiftShader *software* GL the full stack runs ~14fps and the ladder settles to the ~22fps floor; post-processing is GPU-cheap but CPU-rasterization-expensive, so those numbers do not represent real mobile GPUs (which run the full stack at vsync cap).

## 4.8 Surface materials (V3.2–V3.3)

Procedural PMREM **environment map** (`scene.environment`) so PBR metal reflects; tower/hero metal is `MeshStandardMaterial` (`std()`). **Procedural normal maps** (`normalFromHeight` bakes a heightfield canvas then Sobels it into a tangent-space normal map, tangents derived in-shader from derivatives — no explicit tangent attribute): `metalNormal()` (panel seams + rivets) on all metal, `groundNormal()` (grit + hairline cracks) on the terrain, so surfaces show real relief under the sun. Terrain also carries a `grungeTex()` albedo detail map via world-planar UVs (`toMesh(..., uvScale)`), contact-AO discs (`aoDisc`) ground every tower/hero/walker, and tower bases are beveled octagonal mounts.

## 4.9 Known deltas vs the 2D build (accepted)

Cloud-shadow and color-grade overlays are replaced by real lighting + fog + the grade the bloom/tone-map path gives; walk-cycle is bob/wobble + swinging legs rather than fully articulated; the boss juggernaut uses the top boss banner instead of a floating bar. The 2D sprite bake still runs at load purely for HUD tray icons. **The remaining ceiling is FORM, not finish:** enemies/towers are procedural primitive assemblies, so up close they read as clean stylized shapes, not sculpted models. Closing that last gap needs hand-authored GLTF art (a 3D artist / licensed asset packs), which is an art-production task, not an engineering one — see 2.6.

# Part 6 — Active roadmap: V5 "Balance & Challenge" line (`fallengrid-v4.html`)

Approved plan from player playtest feedback (mono Tesla-wall + Glacier-slow trivialises the game; difficulty ceiling too low for skilled play; daily wants to be a real ruleset variation, not a random standard map). Shipped in +0.1 increments. **PROCESS RULE: export the full HTML to the user after every iteration for download + on-device testing before continuing.** Each iteration: Playwright verify + balance harness where relevant + Codex update for new content + commit/push + export.

**Balance harness (tool, built in Iter 1, reused after):** headless auto-player that plays *named strategies* — "mono-Tesla+Glacier wall" (the dominant exploit) vs "diverse overlapping build" — and reports win-rate / core-loss / wave reached per difficulty+map. Tune until mono-strategy is no longer strictly best and diverse builds are rewarded. (The earlier one-off probe under-built and was not representative — the player beats Brutal easily.)

- **Iter 1 — V4.11 Anti-slow & anti-mono balance.** Global **slow floor** (an enemy can't be slowed below a min-speed %, so stacking Glacier past 1–2 is wasted → over-investing in slow becomes a disadvantage). New enemy resistances: `slowResist` (0–1); ≥1 **freeze-immune** fast unit (ignores slow → needs raw DPS/coverage); ≥1 **energy-insulated** unit (resists Tesla/energy → forces kinetic/explosive). Cost/strength retune of cryo & tesla + others so overlapping mixed coverage beats single-type spam. Also **cap wave-overlap congestion** (the 146-hostile pile-up) — ties to the health-bar artifact below. Validate mono-vs-diverse with the harness.
- **Iter 2 — V4.12 Custom difficulty (sliders).** New **Custom** difficulty: start-scrap, **enemy-HP ×0.5–2.0**, **enemy-speed ×0.5–2.0**, **tower-DMG ×0.5–2.0**, earnings ×, core count. Folded through `diffMul`/`modv`/economy; persisted. This same custom-difficulty is **also selectable for the Daily and in the Challenge Lab** (player controls difficulty everywhere, per feedback).
- **Iter 3 — V4.13 Challenge Modes engine + real Daily.** Expand the `MODIFIERS`/`activeMod` system into distinct **rule-changing modes** (e.g. Sudden Death = short wave gap; Fortress = high start-scrap, little/no income; Specialist = only 1–2 tower types; Glass Cannon = high dmg, low core; Deep Freeze / No Freeze tie into the balance theme), each combinable with **any map**. **Daily always applies a meaningful mode + shows a briefing/intro screen** describing exactly what the modifier changes *before* the run starts, and the **player picks the difficulty** for it (no more forced hard/brutal). A daily is never just a random map played standard.
- **Iter 4 — V4.14 Challenge Lab (test menu).** New menu entry where the **player chooses mode + map + difficulty** freely and plays/tests it. Each mode carries a short description (shared with the daily briefing).
- **Iter 5 — V4.15 Wave pacing + onboarding.** Shorter/scaling auto-gap; **wave 1 waits for manual deploy**; refreshed coach-marks teaching early-send bonus, build-confirm, camo→Tesla/Hero, and the new freeze-immune enemies.
- **Iter 6 — V4.16 Late-game scrap sink + polish.** Core-repair / in-run overclock sink (surplus scrap problem); run-summary screen; colour-blind-friendly damage-type cues; more SFX variety.

**Tracked bug (fix in Iter 1):** the "green meter that fills upward" in the boss screenshot is **not** an inverted bar — it is a single-file column of freshly-spawned, full-health enemies (each drawing a full green HP bar) piling up at a spawn gate because V4.10 wave-overlap + heavy slow floods the field (146 hostiles). Reproduce that state, then fix by capping overlap/congestion and/or de-cluttering stacked full-HP bars; confirm the per-enemy bar in `overlay()` (`w * ratio`, `ratio = hp/maxHp`) still depletes correctly.

**Open questions to the user before Iter 1:** (a) brand-new enemy types vs "affix" variants of existing ones; (b) whether to do Custom-difficulty (Iter 2) *first* so they can self-tune immediately; (c) keep V4.11… numbering or relabel the line V5.0.
