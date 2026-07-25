# Fallen Grid — Plan for feedback points 1-5

Covers `docs/FEEDBACK-backlog.md` #1-#5, recorded against V6.27. **Plan only — nothing built yet.**

## The five points collapse into two themes

| # | Point | Theme | Effort | Risk |
|---|---|---|---|---|
| 5 | Build row: 7 towers at 45.7 px | **Layout** | XS — already prototyped | Low |
| 1 | No welcome / story / guidance | **Onboarding** | M | Low |
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

Design principle: **no wall of text.** Mobile players skip intros. Two complementary surfaces:

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

**Evidence this is needed:** a full 20-wave V6.25 run in the play-log finished with **`heroLvl: 0`** —
the Hero was never deployed once.

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
