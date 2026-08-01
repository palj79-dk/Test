# Make the Commander load-bearing

**Status:** planned, not started. Written 2026-07-31 against `fallengrid-v6.40.html`.

> **Renumbered 2026-08-01.** This plan was written as "V6.43/V6.44", but both numbers were spent
> elsewhere: V6.43 shipped the terrain relief pass and V6.44 shipped per-map threat identity. The
> two iterations below are therefore **V6.45 (what the Commander is) and V6.46 (how strong it is)**.
> The plan is otherwise unchanged and still unstarted. Its blocker in §5.5 also still stands, and
> V6.44's `tools/biasmeasure.py` ran into the same wall from a different direction: a saturated
> board leaks the same amount whatever you change, so any balance probe has to be checked for
> saturation before its numbers mean anything.
Direction chosen by the user from `PLAN-open-findings.md` §B.3: **option 2 — make the Commander
load-bearing**, rather than re-costing the branch or replacing its nodes.

---

## 1. The measurement (B.2), done

### 1.1 What I could not measure, and why

The plan called for a win-rate A/B across four conditions. **I ran it and I do not trust the outcome
half of it.** The auto-player is bimodal: it either fails to establish and dies around wave 6 with 3
towers, or it establishes and snowballs to a wave-20 victory with 24+. Ten samples per condition is
nowhere near enough to see a Commander-sized effect through that variance, and the raw table showed
exactly the tell — `map0/hard/none` died at wave 8 while `map0/hard/hero` won outright, a swing far
too large to be caused by one hero.

So the outcome numbers are not evidence and are not used below.

### 1.2 What I do trust

One number from that run is robust because it does not depend on whether the auto-player wins — only
on the **ratio of a fully-levelled Commander to a fully-built tower line**, both of which the sim
measured directly in the five runs that reached wave 20:

| | DPS | share of army damage |
|---|---|---|
| tower line at wave 20 (24-28 towers, Armory applied) | **7 914** | — |
| Commander L5, no Command nodes | 233 | **2.9%** |
| Commander L5, **entire Command branch bought** (6 410 Alloy) | 344 | **4.2%** |

**Buying all eight Command nodes — 6 410 Alloy, a quarter of the whole tree — moves the Commander
from 2.9% to 4.2% of the army's damage. A net gain of 1.3 percentage points.**

Per Alloy spent:

| branch | added DPS | cost | DPS per Alloy |
|---|---|---|---|
| ORDNANCE | 2 683 | 6 195 | **0.433** |
| ARC | 1 583 | 6 770 | **0.234** |
| COMMAND | 110 | 6 410 | **0.017** |

**Ordnance buys 25× more damage per Alloy than Command.** The backlog finding is confirmed, and by a
wider margin than "dominated" suggested. The user's 0/8 is not a preference; it is correct play.

*(Command also buys Core and airstrike cooldown, which this table does not price. That is the point of
the whole exercise — those are the conditional effects, and they are worth ~0 to a player who does not
leak.)*

---

## 2. The diagnosis: the Commander is a worse tower

Reading the implementation, the Commander does nothing a tower does not do:

| | Commander | tower |
|---|---|---|
| occupies a build plot | **yes** — tapping its tile selects it instead of opening the build menu (`:7989`) | yes |
| moves | **never** — `updHero` (`:5311`) never writes `hero.x`/`hero.y` | no |
| targeting | **nearest** enemy (`:5311`) | selectable mode (first/strongest/…) |
| upgradeable in-run | no — a fixed 5-level XP curve | yes, with a branch choice |
| gains XP | only from kills within `range × 1.25` (`:5301`) | n/a |
| abilities | one AoE pulse, fixed 16 s (`:5302`) | none |

So it is a static, un-upgradeable, auto-targeting turret that **costs you a build plot** and gives one
button. Three consequences fall straight out:

1. **Every Command node is a multiplier on ~3% of the army.** No amount of re-costing fixes that; the
   base is too small. This is why direction 2 is the right call and direction 1 would have been
   papering over it.
2. **A badly placed Commander never levels.** XP requires kills near it, so the punishment for a poor
   plot compounds — and the player cannot correct it, because it cannot move.
3. **Its one differentiator is negative.** The plot it eats would hold a tower worth more DPS than the
   Commander contributes.

---

## 3. The thesis

**Towers cannot move. That is the only thing the Commander can own.**

Making it load-bearing is not primarily a numbers change — it is giving it a verb the rest of the game
does not have. A Commander you *reposition* in response to pressure turns every Command node from a
multiplier on 3% into a multiplier on a decision the player actually makes. The stat work follows from
that; it does not lead.

---

## 4. What ships

Ordered so each step is independently verifiable and independently revertible.

### 4.1 The Commander moves (the change everything else depends on)

- Tap the Commander to select (already exists — `S.heroSel`, `:7989`), then tap a destination to
  **walk** there. It paths across buildable ground, not through blocked tiles or off-map.
- Movement speed around 110-130 world units/s — slower than a Stalker (148), faster than a Raider
  (90), so repositioning is a real commitment mid-wave.
- **Fires at reduced rate while walking** (~50%), so moving has a cost and parking still matters.
- The existing range ring follows it; the destination gets a marker while in transit.
- **UI conflict to resolve:** with the Commander selected, a tap on a buildable plot must mean *move
  here*, not *open the build menu*. Deselect on a second tap or on Back — the V6.38 pattern for
  `strikeArm` (`:5143`) is the precedent to copy.

### 4.2 It stops eating a build plot

The Commander should sit *on* the field, not *in* a build slot. Once mobile, the tile it happens to
occupy must remain buildable — otherwise the player is penalised for parking it usefully.

Decide with the harness in §5 whether this needs a compensating nerf; it is a real power gain.

### 4.3 Targeting and XP stop punishing the player

- **Target the enemy closest to the Core** within range, not the nearest to the Commander. That is the
  choice a player would make, and it is what makes a mobile responder feel responsive.
- **XP from any kill the Commander contributed damage to**, regardless of distance — or simply scale
  XP with damage dealt. The current radius rule (`:5301`) means a repositioning Commander loses
  progression for moving, which directly fights §4.1.

### 4.4 The numbers, last

Only after the above lands, raise the baseline so Command nodes have something to multiply.
**Target: a well-used Commander is 8-12% of army damage**, up from 2.9%, with the full branch taking
it toward ~15%. That makes Command's DPS-per-Alloy land within ~2× of Ordnance rather than 25× behind
— not equal, because Command also buys Core and airstrike utility, but close enough to be a real
choice.

Levers, in order of preference: the L3-L5 damage curve (currently 41/55/74), then the fire rate
(390/365/340 ms), then the pulse. **Do not** simply inflate `HERO.levels` L1 — the early game is
tuned and a strong wave-1 Commander would break the opening.

### 4.5 Consequences elsewhere

- **The V6.38 guided tour** teaches Commander *placement* (step 4). It must teach *repositioning*.
- **The Codex** entry for the Commander describes a static unit.
- **Achievements** `hero` / `herofull` (`:5086`) still work, but "level the Hero to max" gets easier
  once XP is fixed — check it is still a meaningful ask.
- `heroXp`, `heroStats`, `heroDmgMul`, `heroRateMul`, `heroAbilCd` are all module-private. The suite
  will need `__GAME` hooks for hero DPS, mirroring what `heromeasure.py` had to reconstruct by hand.

---

## 5. Guards — this is the risky part

Direction 2 touches live balance that V6.4, V6.5, V6.10-V6.13 and V6.36 all tuned. **Nothing ships
without these.**

1. **The wave-progression guarantee (HANDOFF 1.10) stays intact** — both greps, every iteration.
2. **Threat level must not move.** Run the maxed-meta harness before and after; the V6.0 threat figure
   on Hard and Brutal must land within ±5%.
3. **The Commander must not become mandatory.** Run the full campaign sim *with no Commander deployed*
   and confirm win rates are unchanged — a load-bearing hero must be an option, not a tax on players
   who ignore it.
4. **The Commander must not trivialise maps.** Maps like Rimline are designed around static coverage
   with a dead centre (`:4429`); a mobile Commander partially defeats that by construction. Measure
   per-map, not just in aggregate, and be willing to cap movement or add a reposition cooldown if one
   map collapses.
5. **Fix the measurement harness first.** §1.1 is a real blocker: I cannot verify any balance claim in
   §4.4 with an auto-player that dies at wave 6 two times in three. Before the balance step, the
   harness needs a build order that reliably reaches wave 20 on Hard, and enough samples per condition
   that a 10% win-rate change is distinguishable from noise. **Budget this as real work, not setup.**

---

## 6. Iterations

| iter | contents | risk |
|---|---|---|
| **V6.45** | §5.5 harness rebuild, then §4.1 movement + §4.2 plot + §4.3 targeting/XP. **No stat changes.** | medium — new verb, UI conflict, pathing |
| **V6.46** | §4.4 the numbers, §4.5 tour/Codex, Command node re-tune | high — live balance |

Splitting matters: V6.45 changes *what the Commander is* and can be judged on feel alone; V6.44
changes *how strong it is* and needs the harness. If V6.45 feels wrong, V6.46 never happens and
nothing about balance has been disturbed.

Standing loop applies to both: `git mv` to a new version, `gamecheck.sh`, both wave guards, a new
`verifyNNN.py`, **every** existing suite, a HANDOFF entry, commit + push with `[skip ci]`,
HTML exported.

---

## 7. Open question I will need answered during V6.45

Whether repositioning should be **free** (tap anywhere, walk there, only travel time is the cost) or
**limited** (a cooldown, or only between waves). Free is more fun and more readable; limited is far
safer for maps built around static coverage. I will build free first, measure guard §5.4, and come
back with the per-map numbers if any map collapses — rather than choosing pre-emptively and guessing.
