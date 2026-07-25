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

## 4. No landscape support — layout stays portrait when the phone is rotated — `OPEN`

> "when I turn the phone the layout is still portrait. consider to make both portrait and landscape a
> possibility (and for phone and tablet)"

**Recorded:** 2026-07-25 · against V6.27. Scope explicitly covers **phone *and* tablet**, both orientations.

**Context:**
- The whole UI is built on a **fixed logical space of `W = 360, H = 640`** (portrait), with
  `HUD_H = 56`, `TRAY_H = 118`, and `PLAY_BOTTOM = H - TRAY_H` derived from it. Everything —
  HUD, tray, menus, hit-testing — is positioned against those constants.
- So this is not a CSS/viewport tweak: a real landscape mode means the layout constants become
  orientation-dependent, and the tray/HUD need a side-by-side arrangement rather than stacked.
- V6.18 did tablet **scaling** (the portrait canvas scales up on bigger screens) — that is not the
  same as a landscape **layout**, which is what is being asked for here.
- Worth deciding at planning time: true landscape layout vs. letterboxed portrait-locked. The
  ask is for the former.

## 5. Build menu still shows 7 towers on one cramped row — `OPEN`

> "når jeg bygger er der stadig 7 tårne på linje. de er meget små. syntes du havde ordnet det"

**Recorded:** 2026-07-25 · against V6.27.

**Status clarification (my miscommunication, recorded so it is not lost):** the two-row build menu was
only ever **prototyped**, never shipped. The sequence was: bottom-bar proposals → the user asked to see
proposal 1 rendered → I built a throwaway prototype in scratchpad and sent screenshots, stating V6.25
was untouched → the user then asked for the **Wave Intel bar + camo fix**, which became V6.26. Wave Intel
was the *idle* half of proposal 1; the **build half was never requested and never built**. The user
reasonably expected both.

**Context / what a fix needs:**
- Current build palette: one row of `TOWER_ORDER.length` (7) cells at **45.7 × 74 px** — measured. The
  45.7 px width is below the 48 px Android / 44 pt iOS minimum, with six adjacent neighbours.
- Prototype that was already built and validated: **two rows of four**, horizontal cell layout
  (art left, name + cost right) → **81.5 × 42 px** cells; total tap area essentially unchanged (+1%),
  but the crowded dimension roughly doubles. Screenshots exist from that run.
- Known refinement, agreed but not built: let the tray **temporarily grow ~22 px upward while the build
  menu is open**, so rows get ~46 px instead of 42 and do not crowd the bottom edge / gesture-nav area.
  This needs `trayTop()` used by the tray fill *and* by the tap gate (`if (y >= PLAY_BOTTOM)` today).
- Interacts with **#4**: if landscape lands first, the tray layout changes anyway — worth sequencing
  these two together rather than solving the row twice.
