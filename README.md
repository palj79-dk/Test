# Fallen Grid

A single-file HTML5 tower defense — post-apocalyptic sci-fi, portrait mobile-first, built to sideload
on Android through a Capacitor WebView wrapper. Everything is procedural: no assets, no CDN, no build
step, no network. three.js r147 is embedded inline, so the game is one `.html` file you can open
locally and play offline.

**Current build: [`fallengrid-v6.38.html`](fallengrid-v6.38.html)** (~1.1 MB). Open it in a browser.

## What it is

Defend a reactor Core through 20 waves per sector. Build and upgrade towers on fixed plots beside a
serpentine path, read what the next wave is bringing, and never let a machine reach the Core.

| | |
|---|---|
| Sectors | 25, across four geometry tiers, each with its own biome |
| Towers | 7, each with two level-3 specialisations and a level-4 tier |
| Enemies | 13, with tactical traits — armor, shields, flying, camo, freeze-immune, energy-resist, healing, splitting |
| Modes | Campaign · Free Play · Daily Op (seeded, with rule-changing modifiers) · Challenge Lab · Endless |
| Meta | Alloy earned per run, spent in a 4-branch, 32-node research tree (25,380 Alloy end to end) |
| Extras | Commander hero, orbital Airstrike, achievements, Codex, mastery medals, per-run telemetry |

Damage types form a counter triangle — kinetic is weak against armor, explosive is strong against it,
energy strips shields — and only direct-fire towers reach flyers, so no single tower covers a map.

## Repository layout

```
fallengrid-v6.38.html      the game — the deliverable
fallengrid-v3.html         frozen: V3.6, the first real-3D build
fallengrid-v2.5.html       frozen: V2.5, the last 2D build
fallengrid.html            frozen: V2.4

HANDOFF.md                 source of truth: spec, architecture, and the full changelog
docs/TECHTREE-spec.md      design of record for the Armory research tree
docs/FEEDBACK-backlog.md   play-test feedback, each point with what shipped for it
docs/PLAN-feedback.md      the plan those points were built from (all shipped)
docs/ANALYSIS-prerelease.md   critical pre-release review + release checklist
docs/monetization/         deferred V7 monetization plan and spec

app/                       Capacitor wrapper that turns the newest build into an APK
.github/workflows/android.yml   CI that builds and signs that APK
```

Older builds are kept because the changelog references them; only the newest is live. **The filename
version must match the version label inside the file** — the APK workflow picks the newest by version
sort and fails the build if the two disagree.

## Working on it

Each iteration is a new version-numbered copy (`git mv fallengrid-v6.38.html fallengrid-v6.39.html`),
so every shipped build stays reproducible. Before anything is committed:

1. **Syntax check** the game's own `<script>` block — the file contains four, and the largest is
   three.js, so a naive "check the biggest block" check silently validates the wrong code.
2. **Playwright regression suites** run the real game in headless Chromium with a `pageerror`
   listener, covering combat, economy, campaign flow, layout in both orientations, onboarding, and a
   full 20-wave headless victory.
3. **Two wave-progression guards** must stay intact — one `id: "nextwave"` button and one
   `S.countdown -= raw` decrement. Duplicating either has broken wave pacing before.
4. **A changelog entry in `HANDOFF.md`** stating what changed, what was measured, and what was verified.

Balance decisions come from real play-logs (exported from the in-game Settings screen), not from
intuition — `docs/FEEDBACK-backlog.md` records the measurement behind each one.

## Building the APK

Push to a branch and the GitHub Action bundles the newest build, generates the Android project with
Capacitor, signs it with the committed debug keystore, and uploads the APK as an artifact. Full
instructions, including a local build, are in [`app/README.md`](app/README.md).

Commits marked `[skip ci]` deliberately skip the APK build — most iterations ship as an HTML test
build only.
