# Fallen Grid — Play Feedback Backlog

Running list of things the user finds while playing. **Recording only — do not analyse, plan or
implement until the user explicitly asks.** Points are added over multiple sessions; each keeps the
user's own wording plus a short neutral note of relevant context found in the code (no proposed
solution — that comes later, when asked).

Status legend: `OPEN` = recorded, untouched · `PLANNED` = spec'ed, not built · `DONE` = shipped (with version).

---

## 1. No welcome / onboarding when the game starts — `DONE` (V6.29)

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

## 2. The starting guide never teaches the Hero — `DONE` (V6.29)

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
- ~~Supported by a V6.25 run finishing with `heroLvl: 0`~~ — **superseded 2026-07-25**: the newer log
  shows **`heroLvl: 5` in all four runs**, i.e. V6.26's labelled "HERO / DEPLOY · FREE" tray button
  already fixed *discovery*. The point still stands (the guide never teaches the Hero) but it is
  polish, not an urgent gap. Do not cite the heroLvl:0 run again.
- Partially improved already by V6.26: the Hero is now a labelled tray button reading
  "HERO / DEPLOY · FREE" instead of an unlabelled circle floating over the map — but that is a
  passive hint, not guidance.

## 3. The Airstrike is never introduced either — `DONE` (V6.29)

> "also introduce the strike"

**Recorded:** 2026-07-25 · against V6.27. Same root cause as #2 — likely one combined fix.

**Context:**
- Same gap: no tutorial step, no `TIPS` entry. The only signal is the V6.26 tray button
  ("STRIKE / ORBITAL · READY") and its cooldown fill.
- The Airstrike is a free, recharging ability that deals heavy explosive damage, **stuns**, and
  **reveals camo** — genuinely useful and currently easy to miss entirely.
- Both #2 and #3 are "the game never teaches its two free active abilities", so they probably want a
  single onboarding beat rather than two separate ones — and it should tie in with #1.

## 4. No landscape support — layout stays portrait when the phone is rotated — `DONE` (V6.30-V6.32)

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

## 5. Build menu still shows 7 towers on one cramped row — `DONE` (V6.28)

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

## 6. Siege Battery + Prism trivialise the mid campaign — `DONE` (V6.35)

> "det ser ud som om de to nye tårne (prism og bombard) er for kraftige i de tidlige baner.
> Overvej om de skal fjernes igen, kan låses på en eller anden måde så de først bliver mulige at
> udvikle senere i spillet. eller noget helt tredje"

> (on the chosen direction) "brug 'specialister + kampagne gate' — det er dog kun med disse tårne jeg
> har kommet igennem de sidste to baner så måske ikke nødvendigt at skære i styrken"

**Recorded + resolved:** 2026-07-26 · against V6.34 · shipped in V6.35.

**Measured from the 2026-07-26 log (12 runs):**
- V6.27, no research: `turret + cryo`, **10-21 towers** per map.
- V6.29, armory 0.5: mixed roster (turret/cryo/tesla/mortar), 7-12 towers.
- V6.32, armory 0.59+: **only prism + siege (+cryo)** — turret, mortar, pyre and tesla vanish entirely.
  Crossroads/normal cleared with **5 towers**, 20/20 core. Gauntlet **brutal** cleared with **5 towers**
  at **15/15 core**.

So the defect was **roster collapse**, not just "strong early": once unlocked, nothing else was worth a plot.

**Why the original V6.25 tuning missed it (my analysis error):** I balanced on **DPS per scrap** and
concluded ~1.6-2.1× power for 1.7-1.9× cost. But `scrapSpent` stayed high (4.7k-9k) while tower counts
fell to 5 — the binding resource on these maps is **build plots**, not scrap. On **DPS *per plot***
siege/prism win decisively, and that is the metric that mattered.

**Why we did NOT cut damage (user's counter-evidence, and it holds):** on the late brutal maps these
towers were *needed*, not dominant — The Maw cost 6 core, **Blockade cost 12 of 25**, and Ground Zero
was an outright **loss**. A flat nerf would have broken the top end.

**What shipped instead — reshape coverage, keep punch:**
- **All damage values unchanged** (Cataclysm 340, Ruination 760, Spectrum 190, Singularity 470).
- **Range cut** on both: siege 172→148 (L1) and 222→190 (t4a); prism 238→202 and 302→256.
- **Splash cut** on siege: 92→78 (L1), 152→118 (t4a).
- **Campaign gate**: both capstones now carry `reqCamp: 12` — unbuyable until 12 missions are cleared,
  regardless of Alloy. New `Tech.blockedBy()` drives it; the Armory shows "🔒 MISSION 12 REQUIRED"
  instead of a dead button, and the post-run nudge never advertises a gated node.

Net effect: they stay the late-game answer they need to be, but one of them can no longer cover a whole
map, so the rest of the roster keeps a reason to exist.

## 7. Six points from the clean-account run — `DONE` (V6.36)

**Recorded + resolved:** 2026-07-26 · against V6.35 · shipped in V6.36. All six came in one message with a
13-run play-log from a freshly reset account.

> "when building, focus must change to the newly build tower so I can upgrade it."

Shipped: `doPending` selects the tower it just pushed.

> "it seems that I have maxed Armery out after 9 rounds of campaign - except the ones locked until map 12.
> can you verfi that this is a general case or that there are an issue when I reset my player?"

**Answered from the log: general case, not a reset bug.** Alloy earned per run was
561/561/1001/1001/1000/1001/1000/1000/1351 = **8,476** by run 9, against **8,990** of reachable (un-gated)
nodes — the log's `armory: 0.91` is correct arithmetic. The defect was the *pricing*: the tree totalled
**10,670**, i.e. 2.4× under the ~25,700 the design target called for. V6.36 re-costed it to **25,380**.

> "it is a bit confusing that the hero and airstike is two different places. also the airstrike is partly
> gotten by the build menu. can you instead keep the bottom line with hero, strike and core and then have
> the build menu starting above that line or maybe as a menu sliding in from the left? the sliding menu
> will also give room for larger scans/more info. also in the build menu an exit bottom is needed."

**Root cause found:** HERO/STRIKE/CORE were a *tray state*, and selecting a plot swapped them for floating
circles at the map edge — hence "two different places". User chose **"Panel der glider ind fra venstre"**.
Shipped: permanent command strip + left-sliding build panel with big rows, per-tower info and a ✕.

> "hero has no indication of range. also the mechanisms for placing the hero is different from placing towers."

Shipped: hero deploy goes through the same pending-confirm sheet as a tower (with the range ring on the
target plot), and a deployed Commander carries a permanent range ring.

> "overclocking needs a confirmation as well as a way to se when a tower is overclocked. also evaluate if
> the time is and effect is correlating with the gain"

**Measured:** 200 scrap for +10% damage on one tower vs ~330 for a whole maxed Auto-Gun, used **3 times in
13 runs**. Shipped: 120 × 1.7ⁿ for +15% damage **and** +6% fire rate, capped at 3 stacks, behind a confirm
sheet, with a ⚡N pip on the tower in the field.

> "consider if the time between waves have to be fitted for the individual map and possible also difficulty.
> is seems that for the more advanced maps and largewqvs that they new Annie's are sent while the old wave
> is still been send into the map. or a block that said a new wave (unless sent by the player) can not be
> sent while previous wave is still being sent - but can be sent right in the tail of it."

**Confirmed and quantified:** spawn time vs the 20s `WAVE_GAP` — wave 12 = 17.1s (no overlap), wave 14 =
**20.4s** (overlap starts), wave 18 = 30.7s, wave 20 = **34.3s**. User chose **"Blød spærring: vent til
halen"**. Shipped: the gap timer freezes while >20% of the current wave is still queued and resumes in the
tail; player early-sends unaffected. This is also the per-map/per-difficulty fit that was asked about —
bigger waves spawn longer, so the block adapts on its own without a per-map constant.

## 8. Three follow-ups after testing the new build menu — `DONE` (V6.37)

**Recorded + resolved:** 2026-07-26 · against V6.36 · shipped in V6.37. Opened with "jeg har testet den
nye byggemeny. det ser rimelig godt ud" — so the V6.36 panel itself is accepted; these are refinements.

> "Tilføj at hero bygges fra byggemenyen og pulse fra menu linjen."

V6.36 fixed *where* Hero and Strike live but left the Commander with its own placement mode (arm from the
strip, then tap the map) — still a second way to place something. Shipped: the Commander is the first row
of the build panel while none is deployed, and the strip button does exactly one thing, fire the Overload
Pulse. `S.heroArm`, `drawHeroArm()` and the armed-map tap branch are deleted.

> "når der klikkes på et stykke land kommer byggemenyen frem og når samme stykke land klikkes forsvinder
> den igen. den skal også forsvinde når man klikker på et andet stykke land."

The panel closed on a second tap of the *same* plot but silently retargeted on a *different* one. Shipped:
strict toggle — any plot tap while it is open closes it; the next tap opens it on the new plot.

> "it also seems that the heroes shoot area is always shown."

Correct — V6.36's permanent ring was visual noise. Shipped: it appears when you tap the Commander (a
toggle), for 2.5s after deploy or level-up (the level-up widens the range, so the flash is the point), and
while the Pulse button is held — the same press-to-preview gesture the build and upgrade rows use.
