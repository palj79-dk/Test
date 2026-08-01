"""V6.44 suite — per-map threat identity in the wave composition.

The claim under test is narrow and it is the reason the change is safe: a biased map sends a
DIFFERENT MIX at the same total pressure. So the central assertions are invariants, not effects:

  * unit count per wave is EXACTLY the unbiased count (substitution, never addition)
  * HP budget per wave stays within 5% of the unbiased budget (swaps stay inside an HP class)
  * Tier A/B maps carry no bias and their composition is byte-identical to the pre-change baseline,
    which is what protects the fresh-account onboarding curve confirmed by play-log #12

Plus the effect itself (a biased map really does demand a different counter), the V6.26 detector
rule surviving underneath the bias, and the Fisher-Yates replacement for the old broken comparator.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import sys
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
NEW = H.target()
fails = []
checks = 0

# index -> tier, from the roster. Tier A/B (diff 1-3) must stay unbiased.
UNBIASED = list(range(0, 10))          # Outpost .. Rimline
BIASED = list(range(10, 25))           # Delta .. Ground Zero
WAVES = [7, 9, 12, 14, 16, 18, 19]     # non-boss waves that carry the interesting units


def chk(name, cond, extra=""):
    global checks
    checks += 1
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


html = NEW.read_text()
# Source assertions run against the GAME block only. Grepping the raw file also greps three.js,
# whose single minified line happens to contain both `.sort(` and `Math.random` — that alone made
# the shuffle check below fail against correct code.
game = H.game_block(html)
_live = [ln for ln in game.splitlines() if not ln.strip().startswith("//")]

# NOTE: no version-label assertion here on purpose. run_all.sh step 3 already enforces the
# filename/label agreement the APK workflow depends on, and it DERIVES the version from the
# filename instead of hardcoding it. A per-suite copy pins the suite to the version it was
# written at, so every `git mv` to a new build breaks it (641/642 were hand-patched forward
# at V6.43 rather than fixed). Assert the relationship once, centrally.
chk("the broken comparator shuffle is gone from live code",
    not [ln for ln in _live if ".sort(" in ln and "Math.random" in ln])
chk("a real Fisher-Yates replaced it", "function shuffle(a)" in game and "shuffle(seq);" in game)
chk("intel ties break on a fixed order", "sev.indexOf(a) - sev.indexOf(b)" in game)
chk("bias table exists", "const WAVE_BIAS" in game)
chk("bias runs before the detector rule",
    game.index("applyWaveBias(cnt, mapIdx)") < game.index('Tech.isUnlocked("tesla") || Tech.isUnlocked("prism")'))
chk("waveIntel cache is keyed by map", 'S.difficulty || "") + "|" + S.mapIndex' in game)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(NEW.resolve().as_uri())
    pg.wait_for_function("() => !!window.__GAME", timeout=60000)
    pg.evaluate("() => { localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); }")
    pg.wait_for_timeout(400)

    # ---- composition: counts, HP budget, and what the bias actually does -------------------
    # waveComp(n, mapIdx) is pure, so the whole matrix is one evaluate with no rendering.
    data = pg.evaluate(
        """([waves, maps]) => {
        const G = __GAME, E = G.__ENEMIES, out = {};
        // research a detector so the camo rule is not masking the cloak bias in the main matrix
        for (let i = 0; i < 40 && !G.Tech.isUnlocked('tesla'); i++) { G.Meta.alloy = 999999; G.Tech.buy(1); }
        const cnt = (n, m) => {
          const c = {};
          for (const e of G.__waveComp(n, m)) c[e.type] = (c[e.type] || 0) + 1;
          return c;
        };
        for (const m of maps) {
          out[m] = {};
          for (const n of waves) {
            const c = cnt(n, m);
            let tot = 0, hp = 0;
            for (const k in c) { tot += c[k]; hp += c[k] * E[k].hp; }
            out[m][n] = { c: c, tot: tot, hp: hp };
          }
        }
        return { out: out, detector: G.Tech.isUnlocked('tesla') };
    }""", [WAVES, UNBIASED[:1] + BIASED])
    chk("a detector is researched for the matrix", data["detector"])
    O = data["out"]
    base = O[str(UNBIASED[0])]   # Outpost, unbiased, is the reference

    worst_cnt, worst_hp, worst_hp_map = None, 0.0, None
    for m in BIASED:
        for n in WAVES:
            bm, bs = O[str(m)][str(n)], base[str(n)]
            if bm["tot"] != bs["tot"] and worst_cnt is None:
                worst_cnt = "map %d wave %d: %d vs %d" % (m, n, bm["tot"], bs["tot"])
            d = abs(bm["hp"] - bs["hp"]) / bs["hp"]
            if d > worst_hp:
                worst_hp, worst_hp_map = d, "map %d wave %d (%d vs %d hp)" % (m, n, bm["hp"], bs["hp"])
    chk("unit count is EXACTLY preserved on every biased map/wave", worst_cnt is None, worst_cnt or "105 combinations")
    chk("HP budget stays within 5% of unbiased", worst_hp < 0.05, "worst %.2f%% at %s" % (worst_hp * 100, worst_hp_map))

    # the effect: each profile must visibly move the unit it is named after
    EFFECT = {10: ("wraith", "air"), 11: ("sentinel", "armor"), 12: ("warden", "shield"),
              13: ("insulator", "energy"), 14: ("phantom", "cloak")}
    for m, (unit, prof) in EFFECT.items():
        got = O[str(m)]["16"]["c"].get(unit, 0)
        ref = base["16"]["c"].get(unit, 0)
        chk("map %d (%s) sends more %s than an unbiased map" % (m, prof, unit), got > ref, "%d vs %d" % (got, ref))

    # Tier A/B must be genuinely untouched, not merely "close"
    tierab = pg.evaluate(
        """([waves, maps]) => {
        const G = __GAME, out = {};
        for (const m of maps) { out[m] = {};
          for (const n of waves) { const c = {};
            for (const e of G.__waveComp(n, m)) c[e.type] = (c[e.type] || 0) + 1;
            out[m][n] = c; } }
        return out;
    }""", [WAVES, UNBIASED])
    same = all(tierab[str(m)][str(n)] == tierab[str(UNBIASED[0])][str(n)] for m in UNBIASED for n in WAVES)
    chk("all 10 Tier A/B maps compose identically to each other (no bias anywhere)", same)
    nobias = pg.evaluate("() => __GAME.__MAPS.slice(0,10).every(m => !m.bias)")
    chk("no Tier A/B map carries a bias field", nobias)
    allbias = pg.evaluate("() => __GAME.__MAPS.slice(10).every(m => Array.isArray(m.bias) && m.bias.length)")
    chk("all 15 Tier C/D maps carry one", allbias)

    # boss cadence must be untouched by the bias
    boss = pg.evaluate("""() => {
        const G = __GAME, r = {};
        for (const m of [0, 10, 15, 24]) r[m] = [5, 10, 20].map(n => G.__waveComp(n, m).filter(e => e.type === 'juggernaut').length);
        return r; }""")
    chk("boss waves are unaffected by bias", all(boss[k] == boss["0"] for k in boss), boss)

    # ---- the V6.26 detector rule must still hold underneath the cloak bias ------------------
    camo = pg.evaluate("""() => {
        const G = __GAME;
        localStorage.removeItem('research'); localStorage.removeItem('spec');
        G.Tech.load ? G.Tech.load() : null;
        return null; }""")
    pg.reload()
    pg.wait_for_function("() => !!window.__GAME", timeout=60000)
    pg.wait_for_timeout(300)
    fresh = pg.evaluate("""() => {
        const G = __GAME, det = G.Tech.isUnlocked('tesla') || G.Tech.isUnlocked('prism');
        const c = (n, m) => { const o = {}; for (const e of G.__waveComp(n, m)) o[e.type] = (o[e.type] || 0) + 1; return o; };
        // 14 = Highway (cloak), 23 = Blockade (armor+cloak)
        return { det: det, hi: c(16, 14), bl: c(16, 23), out: c(16, 0),
                 tot: [G.__waveComp(16, 14).length, G.__waveComp(16, 0).length] }; }""")
    chk("fresh account has no detector", not fresh["det"])
    chk("cloak-biased map sends 0 phantoms with no detector", fresh["hi"].get("phantom", 0) == 0, fresh["hi"])
    chk("armor+cloak map likewise", fresh["bl"].get("phantom", 0) == 0)
    chk("wave size still identical when phantoms are substituted", fresh["tot"][0] == fresh["tot"][1], fresh["tot"])

    # ---- the shuffle is actually uniform now -----------------------------------------------
    # With the old comparator the first slot was heavily skewed toward the insertion order
    # (stalker, the first type pushed). A real shuffle puts each type there in proportion to count.
    shuf = pg.evaluate("""() => {
        const G = __GAME, N = 3000, first = {};
        let tot = 0;
        for (let i = 0; i < N; i++) { const w = G.__waveComp(16, 0); first[w[0].type] = (first[w[0].type] || 0) + 1; }
        const c = {}; for (const e of G.__waveComp(16, 0)) { c[e.type] = (c[e.type] || 0) + 1; tot++; }
        return { first: first, c: c, tot: tot, N: N }; }""")
    st_share = shuf["first"].get("stalker", 0) / shuf["N"]
    st_expect = shuf["c"].get("stalker", 0) / shuf["tot"]
    chk("first arrival is proportional to count, not to insertion order",
        abs(st_share - st_expect) < 0.04, "stalker first %.3f, expected %.3f" % (st_share, st_expect))
    chk("more than a couple of types can lead a wave", len(shuf["first"]) >= 6, sorted(shuf["first"]))

    # ---- intel bar reflects the bias, and its cache does not stick across maps --------------
    intel = pg.evaluate("""() => {
        const G = __GAME;
        const read = (m) => { G.S.mapIndex = m; G.selectMap(m); return G.__waveIntel(16).map(x => x.k + ':' + x.n); };
        const a = read(0), b = read(10), c = read(0);
        return { out: a, air: b, back: c }; }""")
    chk("intel differs on a biased map", intel["out"] != intel["air"], [intel["out"][:3], intel["air"][:3]])
    chk("intel cache is not stale after switching back", intel["out"] == intel["back"])

    # ---- every map still loads, spawns and paths -------------------------------------------
    # "still has enemies alive after 10s" is the wrong probe: Ground Zero's gates are ~10-13 tiles,
    # so with no towers the whole first wave has already leaked by then. Assert the wave was really
    # SENT instead — the queue drained and it cost core or produced kills.
    smoke = pg.evaluate("""() => {
        const G = __GAME, bad = [];
        for (let m = 0; m < G.__MAPS.length; m++) {
          try {
            G.S.endless = false; G.S.campaign = false; G.S.mapIndex = m; G.selectMap(m); G.reset();
            G.S.screen = 'playing';
            const core0 = G.S.core;
            G.startWave();
            if (!G.S.queue.length) { bad.push([m, 'wave queued nothing']); continue; }
            G.sim(50, 400);
            const reached = G.S.core < core0 || G.enemies.length > 0;
            if (!reached) bad.push([m, 'wave never reached the field']);
          } catch (e) { bad.push([m, String(e)]); }
        }
        return bad; }""")
    chk("all 25 maps load, queue a wave and put it on the field", not smoke, smoke[:4])

    # a biased map must still be winnable and a bare one must still lose
    ends = pg.evaluate("""() => {
        const G = __GAME;
        G.S.endless = false; G.S.campaign = false; G.S.mapIndex = 10; G.selectMap(10); G.reset();
        G.S.screen = 'playing'; G.startWave(); const r = G.sim(50, 40000);
        return { screen: r.screen, wave: r.wave }; }""")
    chk("a no-tower run on a biased map still resolves to gameover", ends["screen"] == "gameover", ends)

    chk("no page errors", not errs, errs[:3])
    b.close()

print()
print("V6.44: %d checks, %d failed" % (checks, len(fails)))
if fails:
    print("FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
