# Plan for the open findings after V6.40

**Status:** ✅ **Part A complete.** A.0/A.5/A.1 shipped as V6.41; A.2/A.3 shipped as V6.42 along with
a user-reported occlusion bug on blocked tiles. A.4 was dropped after the re-audit showed the towers
are already good. Part B is planned in `PLAN-commander.md`, not started.
Written 2026-07-31 against `fallengrid-v6.40.html`.

Two things are outstanding. They are unrelated and should not share an iteration.

- **A. Graphics.** The user's ask was *"analysér om du kan forbedre grafikken af både maps, tårne,
  fjender samt om lyden kan forbedres"*. V6.40 delivered the audio half. The graphics half is
  untouched.
- **B. The Command branch.** Backlog #11. Structurally dominated; the user has bought 0/8 of it after
  8 missions while the other three branches sit at 7/8. **Decided 2026-07-31: direction 2, make the
  Commander load-bearing.** The measurement in §B.2 has been run and confirms the finding by a wide
  margin. Part B is now specified in full in **`PLAN-commander.md`**; §B.2-B.4 below are kept as the
  record of how the decision was reached.

---

# Part A — Graphics (V6.41 and V6.42)

## A.0 First: re-audit, because some of my earlier findings are stale

I wrote an art audit against V6.39 from screenshots. Checking it against the code today, **it is
partly wrong**, and I would rather say so than build on it:

| earlier claim | status today | evidence |
|---|---|---|
| ground tiles identically per 64-unit tile | **confirmed, and worse than stated** | `:8380` — every ground tile is one flat vertex colour picked from two biome ashes by a per-tile hash; the grunge texture is planar-projected at `1/96` (`:8473`), so it also repeats every 1.5 tiles |
| checkerboard tinting | **confirmed in the live path** | same line. The reassuring comment *"no hard checkerboard"* at `:5638` is in **dead 2D code** (see A.5) |
| props scattered like confetti | **confirmed, and the cause is exact** | `buildDecor` `:4557` runs an independent per-tile hash with fixed thresholds, one prop per tile, uniform across the map. No clustering, no density falloff, no relationship to roads or terrain |
| map floats in a void | **needs re-checking in 3D** | the void backdrop I found (`:5564`) is in the dead 2D bake. The 3D scene uses `Fog(sky, 800, 2600)` and an extruded land mesh; whether it reads as floating has to be judged from a fresh screenshot |
| normal strength too high | **unverified — and my reasoning was nearly wrong** | I was about to claim Lambert ignores `normalMap` in r147. **I tested it: it does not.** `THREE.ShaderLib.lambert.fragmentShader` includes `normalmap_pars_fragment` in r147, so the ground normal map is live and `normalScale 0.8` is real. Any claim about strength must come from a screenshot comparison, not from reading the number |
| Juggernaut is a grey box | **overstated** | `:8695` builds hull, turret, barrel, muzzle brake, two track skirts with eight road wheels, an antenna and an eye. It is not a box. What is true is that its palette (`#4a4e56`/`#26292e`) is the same neutral grey as everything else and its only accent is a 3.4px eye, so at play zoom it reads as a grey mass |

**Step A.0 is therefore mandatory and comes first:** re-run `scratchpad/artaudit.py` against V6.40,
produce the close-ups again, and **write down per finding whether it survives**. Anything that does
not survive gets struck from this plan rather than built.

Cost: ~30 min. Output: a findings table with a screenshot per row.

## A.1 Ground: kill the tile grid (highest value, lowest risk)

**The problem, stated precisely.** Three separate things all repeat on a grid:

1. one flat colour per 64-unit tile (`:8380`)
2. a coarse 2×2-tile `patch` multiplier of 0.9 on the same line
3. a 128 px texture planar-projected at `1/96`, i.e. repeating every 1.5 tiles (`:8473`, `:8321`)

Nothing varies *within* a tile, so the eye locks onto the 64-unit lattice at every zoom level.

**What to do**

- **Per-vertex, not per-tile colour.** `boxM` already writes per-vertex colours into the merged
  buffer. Drive the top face's four corners from a **corner-indexed** hash (`hash2(c, r)`,
  `hash2(c+1, r)`, …) so adjacent tiles *share* corner values. The hard edge disappears without a
  single extra triangle or draw call.
- **Two-octave macro variation.** Add a low-frequency term (period ~6-8 tiles) on top of the
  per-corner jitter, so the ground has large soft regions instead of uniform noise.
- **Break the texture repeat.** Raise the grunge canvas to 256 px, drop `uvScale` to ~`1/220`, and
  add a second UV set (or a second sampler via `onBeforeCompile`) at a different scale and rotation.
  The cheap version — just changing the scale — is worth doing even alone.
- **Delete the `patch` term** once macro variation exists; it is a worse version of the same idea.

**Acceptance (measurable, not "looks better").** Render a top-down 512×512 crop of flat ground.
Compute the 2D autocorrelation. The peak at a 64 px lag must drop by **≥60%** versus V6.40. Add this
as a check in the suite so the grid cannot come back.

**Risk:** low. Vertex colours are already in the buffer; no new materials, no new draw calls.

## A.2 Props: cluster them instead of sprinkling them

**The problem.** `buildDecor` (`:4557`) gives every non-road tile an independent draw from the same
distribution, so props are spatially uniform — which is exactly what reads as confetti. Real ruined
ground has dense pockets and empty stretches.

**What to do**

- Generate **3-6 seeded cluster centres per map**, each with a type bias (a wreck field, a rubble
  drift, a stand of dead trees) and a radius.
- Prop probability becomes `base × clusterFalloff(distance)`, with `base` low enough that
  outside-cluster ground is genuinely empty.
- **Keep total prop count within ±15% of today's**, so build-space feel and draw cost do not move.
- Bias density *away* from tiles adjacent to roads — those are the tiles the player looks at most and
  builds on.
- Authored `mp.props` set-pieces keep priority exactly as they do now.

**Acceptance.** Mean nearest-neighbour distance between props drops ≥25%, its variance rises ≥2×
(that is the signature of clustering), and total count stays within ±15%. Assert on 5 maps.

**Risk:** low-medium. Prop tiles are decorative, not buildable — but confirm that `computeObstacles`
and `buildable()` are genuinely independent of `DECOR` before touching it, or build space changes and
the balance work of V6.9 silently regresses.

## A.3 Silhouette and accent pass on enemies

**The problem.** Every enemy uses a desaturated body/dark pair. At play zoom the reliable
discriminator is silhouette, and the roster does not lean on it hard enough — the Juggernaut being
the clearest case: a genuinely detailed model that still reads as grey.

**What to do**

- Give each enemy **one emissive accent** sized to its threat: a rim strip, a glowing vent, a lit
  cockpit. The Juggernaut gets the loudest (it is the boss and it is already pink-eyed at
  `#e0479a`).
- Nudge the **relative scale spread** so heavy units read heavier at distance.
- Re-shoot the twelve close-ups; judge the roster as a contact sheet, not one at a time.

**Acceptance.** Render all twelve at identical camera distance, downsample to 24×24, and compute
pairwise perceptual distance. No pair may fall below a floor that the current worst pair
(Brute/Sentinel, to be measured in A.0) already sits at. This is a "no two enemies are confusable at
thumbnail size" test.

**Risk:** medium. Emissive accents interact with the bloom pass; too much and the screen blows out
during a big wave. Cap emissive intensity and check a 60-enemy frame.

## A.4 Towers: make the branch choice visible — **DROPPED (A.0, V6.41)**

The re-audit close-ups show detailed models with distinct silhouettes and strong branch accent rings.
There is nothing here worth spending an iteration on. Section kept for the record.

### original text

**To check in A.0, not assumed:** whether an `a`-branch and `b`-branch tower of the same type are
distinguishable at play zoom. The audit shots exist (`art_tower_*_a.png` / `_b.png`) — compare them
before planning work. If they are already distinct, **this section is dropped.**

If they are not: the fix is a branch-coloured accent element (barrel shroud, coil, vent) rather than
a whole new model, so it costs one extra part per tower type.

## A.5 Delete the dead 2D terrain bake

`buildTerrain()` (`:5564`), `groundTile()` (`:5638`) and `roadTile()` (`:5662`) have **no callers** —
`loadMap` builds the 3D world and nothing else references them. This is roughly 130 lines of
plausible-looking, actively misleading code: it is where I read the "no hard checkerboard" comment
that contradicts the live renderer.

Delete it, and confirm with a grep for every symbol it touches. Do this **in its own commit**, before
the visual work, so the diff of the actual graphics change stays readable.

## A.6 Sequencing

| iter | contents | why together |
|---|---|---|
| ~~**V6.41**~~ | ✅ **shipped** — A.0 re-audit · A.5 dead-code deletion · A.1 ground · plus the `discM` winding bug the work uncovered | done |
| ~~**V6.42**~~ | ✅ **shipped** — A.2 props · A.3 enemies · plus blocked tiles moved from the 2D overlay into 3D geometry (user-reported: the marker drew over enemies on the road) | done. The enemy harness now works (`tools/enemysheet.py`); the fix that mattered was reading `worldToScreen` *after* the RAF loop applies `clampCam()`. |

Both follow the standing loop: `git mv` to a new version, `gamecheck.sh`, both wave guards, a new
`verifyNNN.py`, **all fourteen** existing suites, a HANDOFF entry, commit + push with `[skip ci]`,
and the HTML exported to the user.

**Performance is a hard gate, not a nice-to-have.** Every step above must leave frame time on a
60-enemy wave unchanged within 10% on the SwiftShader harness, and the merged-buffer/draw-call
structure must not change. Terrain work stays out of the per-frame path (HANDOFF 2.7 §3).

## A.7 What I cannot promise

The same limitation as the audio work, in a different sense. I can measure autocorrelation, nearest-
neighbour spread and thumbnail distance — those are real and they will improve. **Whether the result
looks good is your call**, and I will send screenshots at each step rather than declaring it done.

---

# Part B — The Command branch (V6.43)

## B.1 The finding, and why it needs you

Measured from the V6.38 device screenshot: Ordnance 7/8, Arc 7/8, Logistics 7/8, **Command 0/8**.

Reading the tree (`:4240`), the reason is structural, not taste:

- **5 of 8 nodes** buff the Commander or the Airstrike (`c_hero`, `c_strike`, `c_hrate`, `c_pulse`,
  `c_cap`)
- **2 of 8** add starting Core (`c_core1`, `c_core2`)
- the fork is Aggression (more hero/strike) *or* Resilience (more Core/scrap)

Core only matters if you leak. The user clears Hard with almost no leaks, so Core is worth zero to
them, and the hero and strike are marginal because towers do the damage. **Command only pays off when
you are losing.** The other three branches are unconditional multipliers on damage, rate, range and
economy — always correct purchases.

It is also the **second most expensive branch** at 6410 Alloy (Ordnance 6195, Arc 6770, Logistics
6005), so it charges a premium for the weakest effect.

## B.2 The measurement to run first, regardless of direction — **DONE, see `PLAN-commander.md` §1**

Result: the Commander is **2.9%** of army damage; the entire 6 410-Alloy branch takes it to **4.2%**.
Ordnance buys **25× more damage per Alloy**. Confirmed, and worse than "dominated" implied.
The win-rate half of the measurement was not usable — the auto-player is bimodal — which is itself
carried forward as a blocker in `PLAN-commander.md` §5.5.

Before changing anything, quantify how much the Commander actually contributes. Use the existing
headless `sim()` harness across 5 maps × 3 difficulties:

1. hero damage as a share of total damage dealt
2. the same with the full Command branch bought vs none
3. win-rate delta from Command alone, at a fixed Alloy budget, versus spending the same Alloy in
   Ordnance

If Command's win-rate delta at equal cost is within noise of the others, the branch is confirmed
dominated and the numbers go in the HANDOFF entry. If it is not, the finding was wrong and this part
is dropped. Cost: ~1 hour, mostly compute.

## B.3 The three directions — **decided: option 2**

Kept for the record. The user chose **option 2** on 2026-07-31.

**1. Make Command unconditional.** Replace 2-3 hero/strike nodes with effects that always apply — an
extra build plot, a second Airstrike charge, a global economy or utility node. *Result:* Command
becomes a normal competitive branch. *Cost:* the branch loses its identity and becomes "more of the
same"; 2-3 nodes need new effect plumbing in `BONUS_KEYS`.

**2. Make the Commander load-bearing.** Leave the branch alone and raise the Commander's baseline so
its multipliers matter — more base damage, a real ability, or a role towers cannot fill (mobile
responder to leaks and camo). *Result:* the most interesting outcome; the hero becomes a genuine
third pillar next to towers and the strike. *Cost:* the largest change, and it touches live balance
that V6.4/V6.5/V6.13 tuned. Highest regression risk.

**3. Accept it as insurance and stop pretending 32/32 is the goal.** Re-price Command down to match
its conditional value, label it in the Armory as the branch for players who are struggling, and drop
the implicit "buy everything" framing. *Result:* honest, cheap, no balance risk. *Cost:* a completionist
player still sees a branch they will never buy.

**Chosen: 2.** (This was also my recommendation.) The user plays on Hard with almost no leaks, which
is exactly the profile that finds a defensive branch worthless — but it is also the profile that would
enjoy a Commander worth actively using. Option 2 turns dead weight into a mechanic. If B.2 shows the
Commander is too deeply wired into balance to raise safely, fall back to 1.

## B.4 Shape of the work once a direction is chosen

Sizing depends entirely on the answer, so this is deliberately coarse:

- **Direction 3:** a re-costing plus copy. ~1 iteration, low risk, mostly the same shape as the V6.36
  Armory re-cost.
- **Direction 1:** new effect keys, Armory UI for them, balance re-measure. ~1-2 iterations.
- **Direction 2:** hero stat/ability rework, then a full balance re-measure across the campaign, then
  a difficulty re-check. ~2-3 iterations, and it must not regress the wave-progression guarantee
  (HANDOFF 1.10).

---

## Order I would work in

1. **A.0** — re-audit, ~30 min, strikes the stale findings before any effort is spent
2. **A.5 + A.1** → V6.41 (dead code out, ground grid gone)
3. **A.2 + A.3 (+A.4)** → V6.42
4. ~~**B.2** — the Command measurement~~ — **done**, see `PLAN-commander.md` §1
5. ~~**B.3** — your decision~~ — **done**, option 2
6. **V6.43 / V6.44** per `PLAN-commander.md`

Neither part is blocked. Part B now carries its own blocker — the balance harness has to be rebuilt
before any Commander stat change can be verified (`PLAN-commander.md` §5.5).
