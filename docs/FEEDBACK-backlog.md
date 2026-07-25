# Fallen Grid — Play Feedback Backlog

Running list of things the user finds while playing. **Recording only — do not analyse, plan or
implement until the user explicitly asks.** Points are added over multiple sessions; each keeps the
user's own wording plus a short neutral note of relevant context found in the code (no proposed
solution — that comes later, when asked).

Status legend: `OPEN` = recorded, untouched · `PLANNED` = spec'ed, not built · `DONE` = shipped (with version).

---

## 1. No welcome / onboarding when the game starts — `OPEN`

> "when starting the game there is no welcome to help onboard the player. it could be history and a
> bit of guidance (you decide what will work best)"

**Recorded:** 2026-07-25 · against V6.27 · user grants latitude on the form it takes.

**Context (existing pieces, for whoever implements this):**
- There is **no first-launch welcome or intro** of any kind — a new account lands straight on the main menu.
- Story text **does exist** but is buried in the Codex "story" tab, so a new player is unlikely to ever see it.
- An in-mission tutorial exists (`S.tut`) covering the *first build* and *first upgrade* only — it locks
  the first build to the Auto-Gun and has a SKIP button (V6.20). It teaches placement, nothing else.
- Nothing currently introduces: the Core/leak loss condition, the damage-type counter triangle,
  Alloy vs Scrap (two currencies), or the Armory research tree — which is now the main progression gate.
- Related recent work that changes what a newcomer needs told: the research tree (V6.24) means a new
  account starts with **only Auto-Gun + Cryo**, and the V6.26 Wave Intel bar already teaches threats
  in-mission — so a welcome flow should not duplicate what the intel bar now covers.

---

## 2. The starting guide never teaches the Hero — `OPEN`

> "at start the guide does not help to use the hero. As the hero can clear the first waves single
> tower this could be improved."

**Recorded:** 2026-07-25 · against V6.27.

**Context:**
- The in-mission tutorial (`S.tut`) has exactly two steps — *place a tower*, *upgrade it* — and then ends.
  The Hero is never mentioned.
- The coach-mark system (`TIPS`) currently holds only four entries: `timer`, `phantom`, `cinder`,
  `insulator`. **There is no hero tip and no strike tip.**
- The Hero is **free to deploy**, levels up in-run (5 levels), hits air, reveals camo within 150 px,
  and has an Overload Pulse ability — i.e. it is strong and costs nothing, but nothing tells a new
  player it exists as a *tactic*.
- User's observation is supported by the play-log: one V6.25 run finished with **`heroLvl: 0`** —
  the Hero was never deployed for a whole 20-wave mission.
- Partially improved already by V6.26: the Hero is now a labelled tray button reading
  "HERO / DEPLOY · FREE" instead of an unlabelled circle floating over the map — but that is a
  passive hint, not guidance.

## 3. The Airstrike is never introduced either — `OPEN`

> "also introduce the strike"

**Recorded:** 2026-07-25 · against V6.27. Same root cause as #2 — likely one combined fix.

**Context:**
- Same gap: no tutorial step, no `TIPS` entry. The only signal is the V6.26 tray button
  ("STRIKE / ORBITAL · READY") and its cooldown fill.
- The Airstrike is a free, recharging ability that deals heavy explosive damage, **stuns**, and
  **reveals camo** — genuinely useful and currently easy to miss entirely.
- Both #2 and #3 are "the game never teaches its two free active abilities", so they probably want a
  single onboarding beat rather than two separate ones — and it should tie in with #1.
