# Fallen Grid — Plan for feedback points 1-5

Covers `docs/FEEDBACK-backlog.md` #1-#5, recorded against V6.27.

> **STATUS: ✅ ALL SHIPPED — this document is now a record of the reasoning, not a to-do list.**
> Written as a plan against V6.27; every iteration below has landed. What shipped for each point, and
> the measurement behind it, lives in `docs/FEEDBACK-backlog.md`; the implementation detail is in the
> `HANDOFF.md` changelog under each version.
>
> | Iteration | Points | Shipped in |
> |---|---|---|
> | A — onboarding | #1 welcome, #2 hero, #3 airstrike | **V6.29** (briefing, run-end Armory nudge, hero/strike coach-marks) |
> | B — build row | #5 cramped 7-tower row | **V6.28** (two rows of four + tray expansion) |
> | C — landscape | #4 phone + tablet, both orientations | **V6.30 (C1)**, **V6.31 (C2)**, **V6.32 (C3)**, then **V6.33/V6.34** for aspect fill |
>
> **Two of these were later rebuilt on further feedback, and the newer design wins:** the build row
> became a slide-in left panel in **V6.36** (#5's layout here is superseded), and the onboarding became
> a 7-step guided tour in **V6.38** (points #2/#3 here got one coach-mark each; see backlog #9).

## Play-log evidence (2026-07-25, 4 runs on V6.27)

Four campaign runs, all on a **fresh account (`armory: 0`)**: Outpost + Serpentine on Normal, then both
again on **Hard**. All four won — 0 leaks in three of them, 1 leak in the fourth.

| Run | Map · Diff | Result | Core | Towers | byType | Alloy earned | activeMs |
|---|---|---|---|---|---|---|---|
| 1 | Outpost · Normal | victory | 20/20 | 10 | turret 8, cryo 2 | 561 | 271 s (+327 s paused) |
| 2 | Serpentine · Normal | victory | 20/20 | 17 | turret 14, cryo 3 | 561 | 195 s |
| 3 | Outpost · **Hard** | victory | 18/18 | 21 | turret 17, cryo 4 | 1010 | 267 s |
| 4 | Serpentine · **Hard** | victory | 17/18 | 21 | turret 18, cryo 3 | 1009 | 286 s |

### Finding 1 — the Armory is being ignored completely. **This is the headline.**
`armory: 0` in **all four runs**. Roughly **3,140 Alloy earned and nothing spent** — the cheapest node
costs 110. Everything V6.24-V6.26 built (the research tree, tower unlocks, the free/reversible fork) is,
in practice, **invisible to the player**. This is the strongest possible confirmation of feedback #1, and
it narrows it: the missing piece is not story, it is **"you have a second currency and a place to spend it."**

### Finding 2 — consequence: the whole campaign is being played with two tower types
Because nothing is researched, `byType` is **only turret + cryo** in every run. The gating works exactly
as designed — but nothing pulls the player toward the Armory to open it up.

### Finding 3 — and no difficulty wall forces the discovery either
Both maps are Tier A/B (`mapHp: 1`), so the V6.17 world-wall has not bitten yet. Gun + cryo clears
Serpentine on **Hard** with a single leak. Early-game balance is therefore *fine* — arguably too
comfortable to create any pull. The wall only starts at ★3+, which the player has not reached.

### Finding 4 — `activeMs` (V6.27) is validated in the field
Run 1 records **271 s active vs 327 s paused** — cleanly separated, exactly the case that produced my
earlier bad read. Runs 2 and 4 show `pausedMs: 0` with `activeMs == durationMs`. The metric can be trusted now.

### Finding 5 — correction: the Hero *is* being used
**`heroLvl: 5` in all four runs.** My earlier note citing a `heroLvl: 0` run as evidence for feedback #2
is now **stale** — that was V6.25, before V6.26 turned the Hero into a labelled "HERO / DEPLOY · FREE"
tray button. That change appears to have fixed discovery on its own. Feedback #2 still stands (the guide
does not *teach* the Hero), but it is a polish item now, not an urgent one.

### Minor observations (recorded, not acted on)
- **Economy surplus on the easiest map:** run 1 ended with 4,617 unspent scrap against 3,185 spent. Hard
  is much tighter (703-788 left), so difficulty is doing its job — but Normal/Outpost has real slack.
- `repairs: 0` everywhere and `satBlocks: 0` — the repair button and congestion cap are not being exercised
  at this level. `overclocks` fired once, in one run: the late-game scrap sink is barely used.
- `earlySends` falls away as difficulty rises (6 → 3 → 1 → 0), which is the intended risk/reward behaviour.

---

## The five points collapse into two themes

| # | Point | Theme | Effort | Risk |
|---|---|---|---|---|
| 5 | Build row: 7 towers at 45.7 px | **Layout** | XS — already prototyped | Low |
| 1 | No welcome / story / guidance | **Onboarding** | M | Low |
| — | *(from log)* Armory never used — 3,140 Alloy unspent | **Onboarding** | XS | Low |
| 2 | Hero never taught | **Onboarding** | S | Low |
| 3 | Airstrike never taught | **Onboarding** | S | Low |
| 4 | No landscape (phone + tablet) | **Layout** | L — architectural | **High** |

#1/#2/#3 are one problem stated three ways: *the game never introduces itself, its stakes, or its two
free active abilities.* #4/#5 both touch the tray.

## Sequencing — and the one real tension

#4 (landscape) rebuilds the tray layout anyway, so strictly speaking #5 should wait or it gets done
twice. **I recommend doing #5 first regardless**, because:

- It is already prototyped, measured and screenshotted — it is essentially ready to ship.
- It is hit **every single game**; landscape is a multi-iteration project. Making the cramped row wait
  weeks to save ~30-60 min of re-layout is a bad trade.
- The two-row concept and the horizontal cell design carry over into landscape; only the positioning
  maths is redone.

Order: **A (quick win) → B (onboarding, launch-critical) → C (landscape, big refactor).**

---

## Iteration A — V6.28 · Two-row build menu (XS)

Ships the build half of bottom-bar Proposal 1. The idle half already shipped as V6.26's Wave Intel bar.

- Build palette becomes **2 rows of 4**, horizontal cells (art left, name + cost right).
  Measured: **45.7 × 74 → ~81.5 × 46 px**. Crowded dimension nearly doubles; total tap area unchanged.
- Tray **temporarily grows ~22 px upward while the build menu is open** (`BUILD_EXP`), so rows get 46 px
  instead of 42 and stay clear of the gesture-nav area. 22 px borrowed from a 466 px play area, only
  while building, is imperceptible — confirmed by the earlier side-by-side renders.
- New `trayTop()` used by **both** the tray fill and the tap gate (today: `if (y >= PLAY_BOTTOM)`).

**Main risk:** the tap-gate change touches world-tap routing. Verify taps in the borrowed strip reach
the tray and not the world, and that armed Hero/Strike targeting still behaves.

**Verify:** all 7 cells present, ≥48 px in the crowded dimension, no overlap, inside 360 px; tap in the
borrowed strip hits the tray; full build→confirm→place flow; locked towers still blocked; core regression.

---

## Iteration B — V6.29 · Onboarding (M) — covers #1, #2, #3

Design principle: **no wall of text.** Mobile players skip intros. Three surfaces, **reordered by the
play-log**: the post-run nudge now leads, because it targets the one problem we can actually see happening.

### B0 — Post-run Armory nudge (NEW, from the log — XS, highest impact)
Not one of the five points, but the log makes it the most valuable single change available: the player
finished four missions with ~3,140 unspent Alloy. The victory/gameover screens *already* have an Armory
button — it is simply not compelling. Make the earned Alloy an explicit call to action:

- On the run-end screen, show **"+561 ⬡ ALLOY EARNED · 561 unspent"** prominently.
- When the wallet can afford the next node in any branch, name it:
  **"Ready to research: Mortar (⬡120)"** with a direct button into the Armory.
- Optional light badge on the menu's Armory button while affordable research is waiting.

This is XS and could ship alongside Iteration A if you want the fix sooner. It should measurably move
`armory` off 0 in the next log — that is the acceptance test.

### B1 — First-launch briefing (#1)
Shown **once** on a fresh account (Store flag), **skippable**, and re-viewable from the Codex so it is
never lost. Three short cards, one idea each:

1. **The world** — the Grid has fallen; you hold the line. (Story text already exists in the Codex
   "story" tab but is effectively unseen — reuse and tighten it.)
2. **The stakes** — machines walk the road to your Core; survive 20 waves; every leak costs Core.
3. **Your edge** — two currencies: **Scrap** builds during a mission, **Alloy** is earned per run and
   spent in the **Armory** to research permanent upgrades and unlock new towers.

Ends with **BEGIN** → straight into Mission 1. Card 3 matters most: since V6.24 a new account starts with
**only Auto-Gun + Cryo**, and nothing currently explains why or how that changes.

**Deliberately excluded:** enemy types and counters. The V6.26 Wave Intel bar already teaches those
in-mission, at the moment they matter. Do not duplicate it.

### B2 — Teach the two free abilities (#2, #3)
Use the existing **`TIPS` coach-mark system** rather than extending the blocking tutorial — it is
already non-blocking and one-time, and it currently holds only `timer`, `phantom`, `cinder`, `insulator`.

- **Hero tip** — fires early (first wave cleared / wave 2 start), anchored to the HERO tray button:
  *free to deploy, fights on its own, levels up through the run, reveals cloaked foes.*
- **Strike tip** — fires the first time the strike is ready with enemies on the field:
  *free, recharges, heavy damage + stun + reveals camo.*

These anchor cleanly onto the labelled tray buttons V6.26 introduced — that change is what makes a
coach-mark pointing at them possible.

**Evidence, updated:** the older V6.25 run that finished with `heroLvl: 0` is **superseded** — the
2026-07-25 log shows **`heroLvl: 5` in all four runs**, so V6.26's labelled tray button already fixed
Hero *discovery*. These tips are now polish (teach the ability well) rather than a fix for it being
missed entirely. Priority drops accordingly; B0 takes the urgency.

**Verify:** briefing shows once on a fresh account and never again; SKIP works and is visible; Codex
re-entry works; both tips fire on their trigger and only once; no tip fires when the ability was already
used; core regression.

---

## Iteration C — V6.30-V6.32 · Landscape + responsive layout (L) — covers #4

The genuinely hard one, and I want to be honest about why: the entire UI is positioned against a **fixed
logical space** (`W = 360, H = 640`, with `HUD_H`, `TRAY_H`, `PLAY_BOTTOM` derived). This is not a
viewport/CSS change — it touches nearly every draw and hit-test function. Proposed as three verifiable steps:

- **C1 — Make the layout dynamic, still portrait.** Convert `W/H/HUD_H/TRAY_H/PLAY_BOTTOM` from
  constants to values recomputed on resize, and route every consumer through them. Ship with portrait
  output **pixel-identical** to V6.29 — that is the acceptance test. Pure foundation, no visible change.
- **C2 — Landscape play screen.** In landscape the tray cannot stay a full-width bottom band (it would
  eat a 640×360 space). Move to **HUD across the top, tray as a right-hand side panel**; re-fit the
  camera for the new aspect; handle live orientation changes mid-run without breaking a run.
- **C3 — Menus, overlays and tablet pass.** The `show(html)` overlay screens are DOM/CSS and should adapt
  more easily, but need a real pass. Combine with a tablet sizing check in both orientations, and set the
  Android manifest orientation accordingly for the APK.

**Decision to confirm before starting C:** true landscape layout (planned above) vs. **portrait-lock +
letterbox** (far cheaper, ships in one small iteration, but does not deliver what was asked). The plan
assumes the former because that is what you asked for — but it is 3 iterations against 1, so it is worth
saying out loud before committing.

---

## Process (unchanged, per iteration)

New version file via `git mv` → build script with assert-counted replacements → `node --check` + guards
→ dedicated `verifyNNN.py` + core regression suite → screenshot check → HANDOFF entry → export the HTML
→ commit and push with **`[skip ci]`, no APK**.

## Not in this plan (deliberately)

- The Armory node **costing/balance pass** — still waiting on a play-log with the new trustworthy
  `activeMs` (V6.27) before touching numbers.
- V7 ads/monetization — previously deferred by you.
