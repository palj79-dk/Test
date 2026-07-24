# Fallen Grid — Armory → Research Tree (Tech Tree) Spec

**Status:** SPEC — design locked, ready to plan Phase 1. **No code written yet.** Nothing in the game is changed by this document.
**Author context:** requested 2026-07-24 — "turn the Armory into a tech tree with branches, tower upgrades, and more advanced towers; later steps hidden, the step you research and the branch type known; investigate how others have done it."

### Locked decisions (2026-07-24)

| # | Decision | Choice |
|---|---|---|
| D1 | Starting towers | **Auto-Gun + Cryo** unlocked; everything else researched (§3.3) |
| D2 | Branch shape | **Linear ladder + one fork**, and the fork is a **free, reversible** specialization toggle (§3.8) |
| D3 | Capstones | **Two new towers** — Siege Battery (Ordnance) + Prism (Arc); Logistics/Command get effect capstones (§3.2) |
| D4 | Number of branches | **4** — Ordnance / Arc / Logistics / Command (§3.2) |
| D5 | UI | **Overview-first accordion**, future folded into one Classified strip (§4.6) |
| D6 | Depth | More **distinct** fogged nodes, ~8/branch, extendable Tier-II tail — never repeat-buy levels (§3.6) |
| D7 | Onboarding | Tower **role cards** + "next milestone" breadcrumb, sourced from the Codex (§3.5) |
| D8 | Migration | **Default: Alloy-refund** old talents → re-spend (§4.5). Not yet explicitly confirmed — flag before Phase 1. |

---

## 1. What exists today (baseline)

Two *separate* upgrade layers already ship in the game. Keep this distinction crystal-clear — the new tree only touches the first one.

| Layer | Where | Persistence | Structure today |
|---|---|---|---|
| **Armory (meta)** | Between missions | Permanent (localStorage `talents`) | **Flat shop.** 14 talents (`TALENTS`), each 3 levels, bought in any order with Alloy. |
| **Tower upgrades (in-run)** | During a mission | Resets each mission | **Already a branch tree.** Every tower shares L1/L2, then L2→L3 forks into two specializations (a/b) each with a t4 tier. |

Key facts that constrain the redesign:

- **All 5 towers are available from wave 1** today: `turret` (Auto-Gun), `cryo`, `mortar`, `tesla`, `pyre`. There is *no* tower gating.
- Meta effects are read individually: `dmgMul()`, `rateMul()`, `rangeMul()`, `splashMul()`, `rewardMul()`, `waveBonusMul()`, `strikeMax()`, `sellRefund()`, `alloyFindMul()`, `heroDmgMul()`, `heroRateMul()`, `heroAbilCd()`, plus `Meta.val("scrap")` / `Meta.val("core")` at run start. Each calls `Meta.val(id)`.
- `armoryLevel()` = `sum(levels) / (14 × 3)`, clamped to 1 — used only for telemetry + achievements now (Threat retired in V6.17).
- The **difficulty wall lives in the world** (`MAP_HP_BY_DIFF` per ★ tier). Higher-★ sectors genuinely need a built-up Armory. **This is the hook the tree plugs into**: gating towers behind research makes "the Armory is your lever for hard maps" literally true.
- `setDevArmory(0/0.5/1)` fakes Armory fill for testing; the "Reset All" dev button wipes the account.

---

## 2. How other games do meta tech trees (prior art)

I looked at the designs closest to what you're describing — a persistent, branching research tree that unlocks units and upgrades, with future nodes hidden.

### 2a. Branching meta trees that gate units/upgrades

- **Infinitode 2** (TD, the closest reference). A large **research tree**: spend a research currency to unlock new towers, new tower abilities, and stat upgrades. Branches by domain. You can see the *immediate* unlockable nodes; deeper structure is there but you commit currency step-by-step. → Confirms the core loop: *earn currency in missions → unlock towers + upgrades in a persistent tree → tackle harder maps.*
- **Mindustry** (tech tree model for the *fog*). Nodes are laid out as a branching tree; the **next researchable node is visible, nodes past a locked prerequisite are silhouetted/dimmed** until you reach them. → This is almost exactly your "you know the step you can research; you don't know later steps" rule.
- **Bloons TD 6 — Monkey Knowledge.** Perks grouped into **named categories/branches** (Primary / Military / Magic / Support / Powers / Heroes). Sequential unlocks within a branch with prerequisites. Everything is *visible*, though — no fog. → Good model for *branch theming*, not for hidden reveal.
- **Kingdom Rush** (and Fallen Grid's own in-run design). Towers reach a tier then **fork into two specializations** — a genuine either/or choice. → Fallen Grid already uses this pattern in-run; we can echo it at the meta level so the two layers feel like one language.

### 2b. The "hidden future" pattern specifically

- **Progressive-disclosure / breadcrumb trees** (Mindustry, many mobile RPG "research labs"): reveal one step ahead. Drives curiosity without full randomness — the player always has a concrete *next* goal but keeps a sense of discovery.
- **Roguelike blind rewards** (Slay the Spire, Vampire Survivors evolutions): the reward is *fully* unknown until taken. → You explicitly **don't** want this ("the step to research you will know"), so we stop short of full randomness. Fallen Grid's fog reveals the node you're about to buy in full; only the ones *beyond* it are masked.

### 2c. Takeaways applied to Fallen Grid

1. **Branch by theme, name the branch** (BTD6 / current in-run forks).
2. **Reveal one node ahead; silhouette the rest** (Mindustry). Keep the branch's *theme* and each hidden node's *category tag* visible so choices are informed, not blind.
3. **Gate towers as nodes inside branches** (Infinitode 2) — the new-player wall + the "place to earn/pay" you asked for.
4. **Capstones = new advanced towers** — aspirational end-of-branch payoffs (the "more advanced towers than the gun" ask) and future monetization targets.
5. Keep the **in-run a/b tower forks unchanged** — they're a different layer and they're good.

---

## 3. Proposed design

### 3.1 One-paragraph pitch

Replace the flat 14-talent Armory with a **Research Tree of 4 themed branches**. Each branch is a ladder of nodes bought with Alloy. A branch's **theme is always shown**. Within a branch, purchased nodes show ✓, the **single next node is fully revealed** (name, effect, cost — "RESEARCH NOW"), and **all deeper nodes are masked** — shown as a silhouette with only their **category tag** (⬢ UNLOCK / ⚔ WEAPON / ⬡ SYSTEM / ✦ CAPSTONE) visible. New players **start with the Auto-Gun only**; every other tower — and two brand-new advanced towers — is unlocked by researching down a branch.

### 3.2 The four branches

Themes chosen so all 14 existing effects survive (redistributed) and tower unlocks + two new capstone towers slot in naturally. Node order is illustrative; costs in §5.

**⚔ ORDNANCE** — *raw firepower & heavy weapons* (amber/red)
1. `UNLOCK` **Mortar** — splash tower
2. `WEAPON` Munitions I — +5% tower damage
3. `WEAPON` Fire Control I — +6% fire rate
4. `WEAPON` Warheads — +splash radius
5. `WEAPON` Munitions II — +10% tower damage
6. `WEAPON` Fire Control II — +12% fire rate
7. `✦ CAPSTONE` **Siege Battery** — *new advanced tower* (heavy anti-armor artillery) **or** Munitions III + universal armor-shred (design pick in §8)

**✦ ARC** — *energy, crowd-control, shields* (cyan/magenta)
1. `UNLOCK` **Tesla** — long-range energy, hits air, strips shields
2. `WEAPON` Targeting Optics I — +6% range
3. `UNLOCK` **Pyre** — burn/cluster control
4. `WEAPON` Coolant — energy towers +rate
5. `WEAPON` Targeting Optics II — +12% range
6. `WEAPON` Overcharged Coils — energy towers +damage
7. `✦ CAPSTONE` **Prism** — *new advanced tower* (chaining beam / focus-lens)

**⬡ LOGISTICS** — *scrap, alloy, sustain* (green/gold)
1. `SYSTEM` Reserves I — +25 starting scrap
2. `SYSTEM` Salvage Rigs I — +8% scrap per kill
3. `SYSTEM` War Economy — +wave-clear bonus
4. `SYSTEM` Salvage Refit — +sell refund
5. `SYSTEM` Contracts — +alloy earned
6. `SYSTEM` Reserves II — +50 starting scrap
7. `✦ CAPSTONE` Field Requisition — start each mission with a free pre-placed tower **or** Salvage Rigs III

**★ COMMAND** — *Commander, Core, strikes* (blue)
1. `SYSTEM` Reinforced Core I — +5 starting core
2. `SYSTEM` Command Core — +Commander damage
3. `SYSTEM` Rapid Response — −airstrike cooldown
4. `SYSTEM` Battle Drills — +Commander fire rate
5. `SYSTEM` Overcharge — −pulse cooldown
6. `SYSTEM` Reinforced Core II — +10 starting core
7. `✦ CAPSTONE` Second Strike — airstrike gains a second charge **or** Commander gains a passive

> Every one of the 14 current talents is preserved (some folded into I/II steps). Net new content: **4 tower-unlock nodes** (Mortar/Tesla/Pyre + the Auto-Gun which is free/pre-owned), **2 brand-new towers** (capstones), and **4 capstone effects**.

### 3.3 Starting state (critical for balance)

- **Unlocked at account creation:** `turret` (Auto-Gun) **+ `cryo` (Cryo Emitter)**.
  Rationale: slows are near-mandatory to clear even Tier A cleanly; shipping the account with gun+cryo keeps the earliest maps fair while still gating the *offensive* escalation (Mortar/Tesla/Pyre) and the two new towers behind research. (Alternative — gun only — is possible but requires re-checking that Tier A is winnable with a single damage type; see §8 open question O1.)
- **Locked initially:** Mortar, Tesla, Pyre, Siege Battery, Prism.
- Tutorial already locks the first build to the Auto-Gun — unchanged and consistent.

### 3.4 Fog reveal rules (the core mechanic)

For each branch, let `n` = number of nodes already purchased. Node at index `i`:

| Condition | State | Shown to player |
|---|---|---|
| `i < n` | **Owned** | Full: ✓ name + effect. |
| `i === n` | **Researchable** | Full: name, effect text, **cost**, "RESEARCH" button (enabled if Alloy ≥ cost). |
| `i > n` | **Fogged** | Silhouette: branch color + **category tag only** (⬢/⚔/⬡/✦) + "???". No name, no effect, no cost. Capstone always shows the ✦ glyph so players know a big payoff caps the branch. |

- **Presentation folds the future.** These are the *data* states; on screen the fogged nodes are not drawn as a stack of silhouettes but collapsed into a single "Classified · N ahead" strip (§4.6) — the rule is unchanged, the clutter is gone.
- **Branch theme is always visible** (name + icon + one-line promise), satisfying "the type of each branch is known."
- **Strictly linear** per branch (buy node `i` before `i+1`). This is what makes "reveal one ahead" meaningful and keeps the UI mobile-friendly. (A light 1-fork-per-branch variant is possible later; linear first — see O2.)
- Optional flavor: fogged nodes can show a scrambled/redacted codename ("PROJECT ▮▮▮▮") for tone. Cosmetic only.

### 3.5 Progressive info / onboarding layer (added per feedback)

The tree isn't just a spend screen — it's the best onboarding surface in the game, because it introduces each tower *at the moment the player chooses to invest in it*. Three additions, none of which break the fog:

1. **Tower role cards.** Any node that unlocks or upgrades a tower (UNLOCK + ✦ CAPSTONE towers) shows a compact role card: **damage-type chip** (Kinetic / Explosive / Energy), a one-line **role**, and **Strong vs / Weak vs** rows. This teaches the counter-triangle (kinetic weak vs armor, explosive strong vs armor, energy strips shields) exactly when it's relevant. Pull the text straight from the existing **Codex** so there's one source of truth.
   - On an **owned** node: the card documents what you have.
   - On the **researchable** node: the same card is framed **"You'll gain ▾"** — so a new player sees a tower's pros/cons *before* spending, turning every unlock into a teaching moment instead of a gamble.
   - On a **fogged** node: no card (that's the point) — only the category tag.
2. **Branch "next milestone" breadcrumb.** Each branch header shows how far the next *tower* (UNLOCK or ✦ CAPSTONE) is — e.g. *"Next milestone: ⬢ new tower · 2 nodes away."* Category + distance are known; the tower's identity stays fogged. This answers "what will I reach" without spoiling "what exactly."
3. **Unlock moment → Codex hook.** When a tower is first researched, surface a short "New tower unlocked — see Codex" beat (and the role card inline). Contextual teaching beats a wall of tutorial text.

Net effect: the research tree doubles as the tower school. A brand-new player learns *reliable-gun vs armor-mortar vs shield-stripping-tesla* by progressing, not by reading a manual.

### 3.6 Depth — does it make sense to add more levels?

**Yes, add depth — but as more *distinct* nodes, not repeat-buy levels.**

- The old Armory bought "Munitions I/II/III" as one node re-purchased three times. **Don't reinstate that** — the fog reveal only lands on first sight, so re-buying a revealed node is grind, not discovery.
- Instead, express depth as **separate, individually-named, individually-fogged nodes** (Munitions I early, Munitions II fogged deeper). Each step stays a fresh "what's next" beat.
- **Target ~8 nodes per branch** (up from 7) with a readable rhythm: `unlock → 2 upgrades → unlock/upgrade → 2 upgrades → capstone`. 4 × 8 = **32 nodes**.
- **Design the ladder to be extendable:** reserve a **"Tier II" tail after the capstone** that can be appended in a later content update (endless-ish long tail for retention, and the natural home for the deferred Alloy monetization) *without* redesigning the front of the tree.
- **Constraint unchanged:** front-load cheap unlocks so new players aren't walled; back-load expensive capstones. Total Alloy sink stays near the current re-paced curve (§5).

### 3.7 Sub-branches under each main branch? — recommendation: **no true sub-trees; at most one fork**

Asked whether each main branch should split into several sub-branches. Verdict:

- **Avoid a full 2D sub-tree** (a branch that forks into multiple parallel lanes). On a portrait phone it needs pan/zoom, it multiplies the number of simultaneously-visible "unknowns", and it directly re-creates the *"wall of unknowns / no overview"* problem (see §4.6). Games that do 2D meta-trees (PoE, Civ, Infinitode 2's research) are hardcore/desktop-first; this is a casual mobile TD.
- **Keep each branch a single linear ladder** for launch — it's what makes "reveal one ahead" legible and keeps the whole tree scannable as four cards.
- **Optional, later: exactly one binary fork per branch, at the capstone** — pick *one* of two capstones (e.g. Ordnance → Siege Battery **or** a universal armor-shred). One either/or is exciting and readable; it also echoes the in-run a/b tower forks the game already has. This is the *only* branching I'd consider, and not before the linear framework ships.
- Net: depth comes from **longer linear ladders (§3.6)**, not from width. Width is where overview dies.

### 3.8 The one fork per branch = a **free, reversible specialization** (locked 2026-07-24)

Decision: each branch is a linear ladder **plus exactly one fork**, and — critically — **switching the fork costs nothing and can be redone any time**, so players can try different combinations across the four branches without paying twice.

- **Where:** one **Specialization** node partway down each branch (recommended just before the capstone). The capstone (the new tower / effect) sits *after* it as a normal terminal node, so "linear + one fork" holds and the capstone reward is never gated behind the coin-flip.
- **How it pays:** Alloy is spent only to **reach/unlock** the specialization stage (a normal researched node). The **A-vs-B pick itself is not a purchase** — it's a toggle you flip freely from the Armory, like a loadout. Re-picking never costs Alloy and never rolls back your progress.
- **Not fogged:** because you actively choose between the two sides, **both options are shown** the moment you reach the fork (you always know the step you're on — consistent with the fog rule; only nodes *deeper than your frontier* stay classified).
- **Proposed specializations** (each a meaningful either/or, freely swappable):
  - **Ordnance** — *Precision* (weapon bonuses favor single-target damage) ↔ *Saturation* (favor splash/AoE).
  - **Arc** — *Overload* (energy towers hit harder) ↔ *Disruption* (energy towers slow / strip shields more).
  - **Logistics** — *Boomtown* (more scrap income) ↔ *Frugal* (cheaper builds & upgrades).
  - **Command** — *Aggression* (Commander + strike damage) ↔ *Resilience* (core integrity + repair economy).
- **Why free-respec is the right call here:** it converts the fork from a punishing permanent commitment into an experimentation surface — exactly what was asked. It also mirrors modern player-friendly respec design and pairs naturally with the in-run a/b tower forks (which remain the *committed* per-mission choice). The meta fork is your *strategy dial*; the in-run fork is your *tactical* one.
- **Data:** stored as `research.<branch>.spec = "a" | "b"` (default `"a"`), settable any time with no Alloy check. Effect aggregation (§4.2) reads it when summing that branch's bonuses.

---

## 4. What has to change in code (investigation)

Ordered by blast radius. This is the *why nothing was changed yet* section — it's a real refactor, not a tweak.

### 4.1 Data model
- **New:** `TECH` = ordered array of branches: `{ id, name, theme, icon, color, nodes: [ { id, type, name, desc, cost, effect } ] }` where `type ∈ {unlock, weapon, system, capstone}` and `effect` is either `{tower:"tesla"}` (unlock) or a stat delta `{dmg:0.05}` / `{scrap:25}` / etc., or a flag for capstones.
- **Replace:** `TALENTS` (flat) + `TALENT_ORDER`. Keep a thin compatibility shim only if migration needs it (§4.5).

### 4.2 Persistence + `Meta`
- Save format changes from `talents: {id: level}` to **`research: {branchId: nodesBought}`** (a count per branch — compact, ordered, enough because branches are linear).
- Rewrite `Meta.lvl/val/maxed/nextCost/buy` around branch counts and node effects.
- **Effect aggregation:** compute a `Tech.bonus` object once on load and after every purchase — `{dmg, rate, range, splash, scrap, core, reward, waveb, sell, alloyf, hero, hrate, strike, pulse}` — by summing the `effect` of every owned node. This is the join point to the existing multipliers.

### 4.3 The multiplier getters (mechanical but many)
Repoint each to the aggregated bonus instead of `Meta.val(id)`:
`dmgMul, rateMul, rangeMul, splashMul, rewardMul, waveBonusMul, strikeMax, sellRefund, alloyFindMul, heroDmgMul, heroRateMul, heroAbilCd`, plus the two run-start reads `Meta.val("scrap")` / `Meta.val("core")`. ~14 call sites, all one-line swaps to `Tech.bonus.X`.

### 4.4 Tower gating (new behavior)
- **New:** `unlockedTowers` set, seeded `{turret, cryo}`; unlock nodes add to it.
- **Tray build palette** (`drawTray`, ~line 6482/6497): render locked towers as a locked/❓ slot (or hide) instead of buildable. Fold `!unlocked` into the existing `banned` logic alongside `tutLock`/`modBan`.
- **Guards:** `build()` / `tap()` must reject a locked tower (defense in depth beyond the tray).
- The two **new towers** (Siege Battery, Prism) need full definitions in `TOWERS` (levels + a/b in-run branches + art in `towerBaseArt`/`bakeSprite` + a `Sound` cue + a `DMG_SYM`/glow color). This is the largest *content* cost — two new towers is real art/balance work, not just a data row.

### 4.5 Migration for existing saves
Pre-release, but there are test accounts. Recommended: on first load of the new version, if the old `talents` key exists, **refund** — sum the Alloy spent on owned talents, credit it back as spendable Alloy, delete `talents`, and let the player re-spend in the tree. Clean, no fragile id-mapping, forgiving. (Testers also have "Reset All".)

### 4.6 UI — the Armory screen (full rewrite): **overview-first accordion**

The naïve "render every node as a cell" layout fails on a phone — 4 columns × 8 nodes is a **wall of "???"** with no overview (confirmed by testing the first pitch). The launch UI must lead with an overview and fold the future away. Structure:

- **Level 1 — overview (default view).** A vertical stack of **4 branch cards**, one per theme. Each card is a single glanceable unit: icon, name, one-line theme, a **progress bar + `n/total`**, and a **"next milestone" line** ("Next: ⬢ new tower · 2 away"). Below the header, a **compact next-action row** — the one researchable node's name + cost + a RESEARCH button — so the common case ("buy my next thing") needs **zero taps to expand**. Four cards = instant overview, one clear action each, no fog wall.
- **Level 2 — expanded branch (accordion, one open at a time).** Tapping a card expands it into three zones, top to bottom:
  1. **Owned** → a compact wrap of ✓ chips (the past never clutters).
  2. **Researchable** → the *one* prominent card: category tag, name, effect, the **tower role card** (§3.5) framed "You'll gain", cost, RESEARCH.
  3. **Classified** → the entire future folded into **one dashed strip**: 1–2 category tags + "+N more classified". Never a stack of silhouettes.
- Portrait-first; reuse `show(html)` + existing `.btn/.wallet/.sub` styles. Researching auto-keeps that branch expanded and advances its frontier.
- `setDevArmory` remap: "50%/100%" buys the first X% of nodes across all branches (respecting linear order) so on-device balance testing still works.

> The interactive pitch implements exactly this layout — it's the reference for the in-game screen.

### 4.7 Peripheral references
- Achievements: `talent1`/`talentall` tests use `Meta.maxed` + `TALENT_ORDER`; retarget to "research a branch capstone" / "complete every branch."
- `armoryLevel()` = owned nodes / total nodes (telemetry + achievements keep working).
- Codex/how-to text mentions "upgrade your Armory" — update copy to "research".
- `__GAME` debug exports (`Meta`, `setDevArmory`, `armoryLevel`) — keep, adapt.
- Verify scripts + guards reference the Armory; the per-version regression suite needs new selectors for the tree.

---

## 5. Balancing

- **Total Alloy sink** should stay in the ballpark of today's re-paced curve (V6.17 set ~25,700 Alloy total ≈ 45+ Normal wins). 4 branches × ~8 nodes = **~32 nodes** (see §3.6); distribute the ~25k so early unlocks are cheap (first Mortar/Tesla reachable in the first few wins) and capstones are long-tail (the aspirational + future-monetizable targets).
- **Unlock pacing must respect the world wall.** Tier A/Normal must stay winnable with the **starting gun+cryo** at 0 research (matches the confirmed onboarding curve in the latest play-log). Tesla/Pyre/Mortar unlocking over the first several wins should line up with Tier B (★3, mapHp 1.15) starting to bite.
- **Two new towers** need their own kinetic/energy/explosive identity and a/b forks tuned like the existing five. Budget this as its own iteration.

---

## 6. Why this satisfies the brief

| Your requirement | How the design meets it |
|---|---|
| Armory → tech tree with branches | 4 themed branches (§3.2). |
| Upgrades for towers | WEAPON nodes (damage/rate/range/splash/energy buffs). |
| More advanced towers than the gun | Mortar/Tesla/Pyre gated as UNLOCK nodes + **2 new capstone towers** (Siege Battery, Prism). |
| Don't know what later steps give | Fog: only the researchable node is revealed; deeper nodes silhouetted (§3.4). |
| The step you research is known | Node at `i === n` shows full name/effect/cost. |
| The type of each branch is known | Branch theme always visible; fogged nodes still show a category tag. |
| A place that gates new players & to earn/pay | Gun-only start; unlocks earned with Alloy; capstones are long-tail IAP targets (ties into deferred V7 monetization). |

---

## 7. Suggested phasing (when you say go — not now)

- **Phase 1 — Framework, no new towers.** Build `TECH`, migration, aggregation, gating, and the fogged Armory UI using **only the existing 5 towers + 14 effects** (drop the two capstone towers to placeholder SYSTEM nodes). Fully shippable and testable. This is the big refactor; do it first, verify balance holds.
- **Phase 2 — Capstone tower #1** (e.g., Siege Battery: art, `TOWERS` entry, a/b forks, sound, balance).
- **Phase 3 — Capstone tower #2** (Prism) + capstone effects polish.
- Each phase = its own version file + HANDOFF entry + APK, per standing process.

---

## 8. Decisions — resolved

All the structural calls are now locked (see the table up top). Recap:

- **O1 — Starting towers:** ✅ **Gun + Cryo.**
- **O2 — Branch shape:** ✅ **Linear + one fork**, fork is a **free, reversible** specialization (§3.8).
- **O3 — Capstones:** ✅ **Two new towers** (Siege Battery + Prism); Logistics/Command get effect capstones.
- **O4 — Number of branches:** ✅ **4.**
- **O5 — Migration:** ▶ **Default Alloy-refund** (§4.5) — the only item not explicitly confirmed; I'll surface it once more before writing Phase 1, but pre-release it's low-risk.

### Remaining before Phase 1 (implementation-planning, not design)
1. Lock the exact node list + Alloy costs per branch (~8 nodes each, §3.6/§5) — a costing pass.
2. Confirm the four specialization effects (§3.8) are worth building vs. simplifying to a stat A/B.
3. Design the two new towers' full stat lines + in-run a/b forks + art/sound (their own phases, §7).
4. Migration confirm (O5).
