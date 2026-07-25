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
