# Fallen Grid — Specification & Handoff (v2)

Single-file HTML5 canvas tower defense, post-apocalyptic sci-fi theme, portrait mobile-first, intended to ship on Google Play via a Capacitor WebView wrapper. This document is the source of truth for continuing the work. Part 0 is the operating contract. Part 1 is the technical spec (updated to current code). Part 2 is the continuation brief: quality assessment, backlog, and a concrete implementation plan for the remaining work.

The deliverable file is `fallengrid.html`. Everything (HTML, CSS, JS) lives in that one file inside a single IIFE. There is no build step and no framework. Vanilla Canvas2D + WebAudio.

**Current state (v2).** The five highest-priority gaps from the original handoff have been closed: graphics fidelity, strategic depth, feedback/audio, onboarding, and meta-progression. What remains is scope (content volume, a hero unit) and tuning, not craft. See the changelog in Part 2.0 and the plan in Part 2.6.

---

# Part 0 — Operating Contract (read first)

Operate as a senior game-dev collaborator, not a generic assistant. Rules:

Lead with the answer or the working code, then reasoning if needed. Skip preambles, filler affirmations, and needless caveats. Prose over bullets unless the content is naturally list-shaped. No em dashes. No hedging unless uncertainty is genuine. Avoid passive voice.

If a request is ambiguous, make a reasonable assumption, state it in one line, and proceed. Do not stack clarifying questions. If a request has a better framing, say so once, then execute the better version.

All code, config, and data must be copy-paste ready with no placeholders or TODO stubs unless a template was explicitly requested. Flag genuine technical flaws, regressions, or Play-compliance risks directly rather than softening them.

Definition of done is fixed in 2.7 and is non-negotiable: syntax check, hex scan, headless logic/render check, and the three wave-progression guards in 1.10 intact.

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

## 1.5 Maps and path

`MAPS[]` holds map definitions `{ name, seed, wp }`. Per-map state (`WAYPOINTS, PATH_TILES, PATH_SET, PATH_PTS, DECOR, POOLS`) is `let` and rebuilt by `loadMap(i)` (path from `wp`, decor/pools from `seed`, then a one-time `buildTerrain()` re-bake). `selectMap(i)` re-bakes only when the map changes. `buildable`, `center`, `drawSpawnAndBase`, and terrain all read these by name, so reassignment is safe. **`buildTerrain()` must never run inside the frame loop** — only on map load.

Two maps ship: `Serpentine` (`[0,1] [9,1] [9,4] [1,4] [1,7] [9,7] [9,10] [1,10] [1,13] [9,13] [9,15] [5,15]`) and `Switchback` (`[1,0] [1,2] [9,2] [9,5] [1,5] [1,8] [9,8] [9,11] [1,11] [1,14] [6,14] [6,15]`). Corners share a row/column; spawn is the first point (an edge), base the last. `S.mapIndex` (persisted `map`) selects; the menu has a map picker.

## 1.6 Economy and progression

```
START_SCRAP = 150   START_CORE = 20   TOTAL_WAVES = 20   NEXT_WAVE_COUNTDOWN = 6s
SELL_REFUND = 0.7 (of cumulative cost through current level incl. branch)
Wave clear bonus = round((20 + wave*3) * waveBonusMul())
Difficulty: normal = 1.0, hard = 1.35 enemy-HP multiplier (diffMul)
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

Seven types in `ENEMIES`. `statsFor(type, wave)` applies HP mul `1 + 0.13*(wave-1)`, reward mul `1 + 0.045*(wave-1)`, shield mul `1 + 0.1*(wave-1)`, and copies trait flags.

| id | label | base hp | speed | reward | r | shape | trait |
|----|-------|--------:|------:|-------:|--:|-------|-------|
| stalker | Stalker | 16 | 148 | 4 | 15 | stalker | fast runner |
| raider | Raider | 34 | 90 | 5 | 18 | raider | medium |
| brute | Brute | 105 | 54 | 10 | 24 | brute | tank |
| sentinel | Sentinel | 92 | 60 | 13 | 23 | brute | **armor** |
| wraith | Wraith | 38 | 122 | 8 | 16 | wraith | **flying** |
| warden | Warden | 66 | 72 | 12 | 20 | raider | **shield 60** |
| juggernaut | Juggernaut | 1150 | 42 | 130 | 34 | juggernaut | boss, **shield 420** |

**Counterplay triangle** (in `hurt(e, dmg, type, pierce)`):
- **armor** (unless `pierce`): kinetic `*0.4`, explosive `*1.2`, energy `*1.0`.
- **shield**: absorbs the whole hit (no bleed-through that hit); energy strips `*1.6`, kinetic `*0.7`, explosive `*1.0`. Regenerates `shieldMax*0.22`/s after 3s with no damage (`shieldCd`). Boss shield shown on the boss bar; others as a bubble + thin bar.
- **flying**: only direct-fire towers (turret, tesla) can target; ground splash (mortar, cryo) cannot; splash loops skip flyers. Airstrike hits everything.

`waveComp(n)`: every 5th wave is a boss wave (2 juggernauts every 20th wave, else 1). Non-boss waves add stalkers/raiders/brutes plus `wraith` (n≥3), `sentinel` (n≥6), `warden` (n≥8). Counts are capped (rd≤20, br≤12, wr≤10, se≤10, wd≤8, boss-wave extra≤16) so deep **endless** waves stay performant; `statsFor` keeps scaling HP unbounded. Campaign values (n≤20) are below the caps, so the campaign is unchanged. Leaks cost 1 Core (5 for a juggernaut).

**Endless mode** (`S.endless`): reachable from the menu (`∞ Endless`) or by continuing after a campaign victory. Waves never trigger `victory`; `startWave`, the auto-advance countdown, and the HUD deploy control all drop the `TOTAL_WAVES` cap when `S.endless`. Best endless wave persists as `highEndless`. A long endless run is the main Alloy farm (Alloy scales with `S.wave`).

## 1.9 Active ability — Airstrike

`STRIKE_CD = 30 - Meta.val("strike")` effective (`strikeMax()`), `STRIKE_R = 92`. Bottom-left circular FAB with a cooldown sweep. Tap to arm (`S.strikeArm`), then a tap in the play viewport calls `doStrike(wx, wy)`: layered explosions + `explosive`, `pierce` AoE that hits air and ground, brief `stunT`, shake + flash. Armed state shows a red reticle overlay ("TAP A TARGET ZONE") and the FAB reads CANCEL.

## 1.10 The wave-progression guarantee (do not regress)

Three independent guards make a freeze impossible; all three must remain:
1. The Deploy/Start control lives in the persistent top HUD (`drawHUD`), always rendered (`hudBtns` id `"nextwave"`).
2. `NEXT_WAVE_COUNTDOWN` auto-starts the next wave with zero input after a wave resolves (`frame` loop, `S.countdown -= raw`).
3. Selection is force-cleared (`selTile = selTower = null`) the instant a wave resolves (`updSpawns`) and on `startWave`.

Onboarding, airstrike arming, and the Armory are all **non-blocking** — they never gate input, so they cannot introduce a soft-lock. Enemies a mismatched defense cannot kill simply leak and the wave still resolves.

## 1.11 Game loop

`frame(now)` caps dt at 50ms; when `screen === "playing"` runs `updSpawns, updTowers, updEnemies, updProjs, updParts`, shake decay, airstrike cooldown, and the auto-advance countdown. Speed multiplier (1/2/3) scales the sim step, not the render. Render order: world layer under camera (terrain blit → pool glow → scorches → spawn/base → sel range → towers → enemies → gibs → beams → projs → booms → smoke → parts → atmosphere), then screen FX (flash, low-core vignette, strike-arm overlay, boss bar, banner), zoom buttons, ability FAB, HUD, tray, tutorial.

## 1.12 Input model

Pointer events with a `ptrs` Map for multitouch. Tap vs pan by `DRAG_THRESH = 8px`; two-finger pinch zoom + pan. `tap(x, y)` priority order: tutorial skip → HUD buttons → zoom buttons → ability FAB → armed-airstrike placement → tray buttons → world tile. Build flow is plot-first. A document-level `pointerdown` calls `Sound.resume()` to satisfy mobile audio autoplay policy.

## 1.13 Persistence and audio

`Store` wraps `localStorage` with an in-memory fallback. Persists `sfx`, `difficulty`, `high`, `tutDone`, `alloy`, `talents`. `Sound` is a procedural WebAudio synth: a master gain → `DynamicsCompressor` chain, oscillator layers plus filtered noise bursts for gun/tesla/cryo/boom/hit/place/up/sell/err/leak/shield/strike/wave/win/lose, and an ambient music bed (detuned drone + LFO-swept lowpass + filtered wind) gated behind the audio toggle, started on entering play and faded out otherwise. All guarded in try/catch.

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

## 2.1 Where things are

```
fallengrid.html   the game (single file, ship this)
HANDOFF.md        this document (source of truth)
README.md         repo readme
```
Git: work on branch `claude/tower-defense-graphics-l7p9mn`. No build artifacts committed; verification scripts are ephemeral (see 2.7).

## 2.2 Edit and verify loop

Edit `fallengrid.html` directly (the JS is the largest `<script>` block). After any change run the checks in 2.7 before declaring done.

## 2.3 Environment constraints

No Android SDK/emulator; `dl.google.com`/Google Maven not allowlisted. Cannot compile/sign an AAB here. Produce the web build + Capacitor project; the user builds and signs locally. Chromium is pre-installed at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (Playwright, `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`).

## 2.4 Conventions

Single IIFE, `"use strict"`. Terse helpers (`clamp`, `lerp`, `rr`, `hash2`, `mix/lighten/darken/rgba`). Colors centralized in `C`; tuning is data-driven in `TOWERS`/`ENEMIES`/`TALENTS` — prefer editing those tables over logic. World drawing goes inside the camera block; screen UI after `restore()`. Color helpers return `rgb()/rgba()` strings so the hex scan stays clean; keep literal hex colors valid.

## 2.5 Quality assessment vs genre leaders (Kingdom Rush, Bloons TD 6, Arknights)

The four craft gaps from v1 (graphics, depth, feedback/audio, retention) are closed; moment-to-moment play and one strategic loop are at genre standard. Remaining distance is **scope, not craft**:
- **Content volume** is the biggest gap: one map, 20 waves, exhausted in a sitting. Leaders ship dozens of maps + endless/challenge modes.
- **No hero/commander** — the last big *mechanical* gap; leaders anchor on a leveling unit with its own kit.
- **Enemy design** is 3 traits deep vs healing/splitting/spawning/teleporting in leaders.
- **Presentation** competes with early-2010s TDs, not 2020s flagships (procedural Canvas2D vs authored sprite/3D art).
- No liveops/social/monetization (not a craft gap).

## 2.6 Backlog, prioritized (remaining)

1. ~~**Content volume — endless + second map**~~ — DONE (Plan A). Further content (more maps, more enemy variants) still adds value.
2. **Hero / Commander** — one deployable, leveling unit with an active kit. Biggest remaining mechanical gap with the leaders. Now the top priority (Plan B).
3. ~~**Playtest tuning pass**~~ — DONE (Plan C): Tesla dominance fixed via `__GAME.sim` auto-battles; branches/economy verified. Re-run the harness after any future data change.
4. **More enemy behaviors** — healing, splitting, or shielded-aura for real puzzles.
5. **Camera feel & accessibility** — pan inertia, zoom easing, colorblind-safe enemy/HP palette, larger-touch-target option.
6. **Android port** — Capacitor scaffold, icons/splash, signed AAB (done by the user locally).

---

## Implementation plan (next work)

Ordered to maximize play-time and retention per unit of risk. Each item lists goal, design, code touch-points, data, risk, and its own definition of done. All items must keep the 1.10 guards intact and pass 2.7.

### Plan A — Endless mode + second map (backlog 1)

**Goal.** Give the deep loop somewhere to go: an uncapped survival mode with a leaderboard-style best, plus a second serpentine layout for variety.

**Design.**
- **Endless**: a run mode where waves continue past `TOTAL_WAVES` with `waveComp` extrapolated (scale HP/counts by a smooth curve, boss every 5, mix trait enemies). Track `S.endless` and a persisted `Store.get("highEndless")`. Alloy scales with waves survived, so endless is the primary Alloy farm. Victory screen becomes "continue into endless?" instead of a hard end.
- **Second map**: promote map data into a `MAPS[]` array — each entry is `{ name, waypoints, seed }`. `WAYPOINTS`, terrain decor placement (`hash2` seeded), and `POOLS` all derive from the selected map. A map picker on the menu (or unlocked via Alloy). Camera/path/terrain already read from these, so the change is mostly parameterizing globals that are currently module constants.

**Code touch-points.** `waveComp` (extrapolation branch), `startWave`/`updSpawns` (endless never sets victory; awards per-wave Alloy), `MAPS` + a `loadMap(i)` that rebuilds `PATH_*`, `DECOR`, `POOLS`, and re-runs `buildTerrain()`, menu render (mode + map select), `reset(mapIndex, mode)`.

**Data.** `MAPS` array (2 entries to start); endless scaling constants.

**Risk.** Medium. Terrain and path are currently top-level `const`s computed once; making them per-map means converting them to `let` and rebuilding on map load. Must re-bake terrain off the frame path (keep the perf rule). Endless must not overflow numbers at very high waves (cap multipliers).

**DoD.** Endless runs past wave 20 without NaN/soft-lock, boss cadence holds, Alloy accrues; map 2 loads, renders, and is playable; switching maps rebuilds terrain once (not per frame); 60fps; a Playwright run to wave 25+ in endless and a full clear on map 2.

**Estimate.** ~1 focused session.

### Plan B — Hero / Commander unit (backlog 2)

**Goal.** A single player-controlled unit that adds agency and identity, the leaders' core hook.

**Design.**
- One deployable "Commander" placed on any buildable plot (or free-move on a leash). It auto-attacks in range with a signature shot, has a manual **active ability** on cooldown (e.g., a shield pulse that grants nearby enemies-in-range a slow, or a focus-fire beam), and **levels within a run** from kills, gaining damage/range/ability potency. Optionally revive on a cooldown instead of permanent death.
- Persisted meta: unlock/level the Commander via Alloy in the Armory (new talent group), tying it into the existing meta loop.

**Code touch-points.** New entity + `updHero`/`drawHero`; a second ability button next to the airstrike FAB; targeting reuse of `findTarget`; XP/level state on `S.hero`; Armory rows for hero unlock/level; `reset` init.

**Data.** `HERO` config (base stats, per-level curve, ability spec).

**Risk.** Medium-high — new entity type, movement/placement input, a second active ability, and balance. Keep it one unit with one ability to bound scope.

**DoD.** Hero deploys, attacks, levels, and its ability fires on cooldown without errors; interacts correctly with traits (respects armor/shield/flying rules via `hurt`); 60fps; screenshots of deploy + ability; guards intact.

**Estimate.** ~1–1.5 sessions.

### Plan C — Balance & tuning pass (backlog 3)

**Goal.** Make the now-deep loop worth repeating; ensure no dominant/dead option.

**Design.** Data-only sweeps of `TOWERS` (branch parity), `ENEMIES` (HP/speed/shield curves), `waveComp` (introduction pacing), economy (`START_SCRAP`, wave bonus, Alloy rate), and `TALENTS` (cost vs power). Add a lightweight in-code balance harness: run headless auto-battles with scripted builds and log waves survived / scrap curves to spot outliers.

**Code touch-points.** Tables only; optional a `__GAME.simWave()` helper for headless balancing.

**Risk.** Low. Numbers only, no logic.

**DoD.** Each tower branch clears a comparable wave range in headless sims; no talent is strictly dominant; difficulty curve is monotonic; economy never stalls or trivializes. Document the chosen values.

**Estimate.** ~half a session.

### Sequencing

Do **A (content)** first — it multiplies the value of everything already built and feeds the Alloy economy. Then **C (tuning)** because A changes the curve. Then **B (hero)** as the next depth lever. D/E/F (more enemy behaviors, camera/accessibility, Android port) follow.

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
4. **Guards.** The three wave-progression guards in 1.10 remain intact.
5. State any balance or UX assumption made.

## 2.8 Android port path

1. Capacitor app, `webDir` = `www`, copy `fallengrid.html` → `www/index.html`.
2. `npm install`, `npx cap add android`.
3. Icons/splash via `@capacitor/assets`.
4. `npx cap sync`, `npx cap open android`.
5. In Android Studio set applicationId, build a signed release AAB, upload to Play Console (content rating, privacy policy, store assets are not code). No known technical rejection cause.
