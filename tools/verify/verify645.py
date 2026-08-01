"""V6.45 suite — support towers read honestly, and STRONG stops being a trap.

Two changes, both driven by measurement rather than by reading the code:

  * A support tower's headline number was its own damage, which is the worst in the game (cryo L1
    is 4) and says nothing true about it. A 1/3 cryo mix was measured to roughly halve leaks.
    The panel now shows SLOW and the tower menu shows the damage the tower has ENABLED.
  * STRONG and CLOSE were unbounded, so a tower would focus the tankiest foe in range while the
    enemy about to reach the Core walked past unshot. Measured over 6 trials: first 34.5+-15.6,
    strong 106.0+-23.2, close 42.7+-9.0. Both are now restricted to the leading part of the pack,
    and STRONG scores on maxHp so it stops re-picking as HP drops. After: strong 50.0+-12.9.

The suite asserts the mechanism, not the exact leak numbers, which are noisy by construction.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import statistics
import sys
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
NEW = H.target()
fails = []
checks = 0


def chk(name, cond, extra=""):
    global checks
    checks += 1
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


html = NEW.read_text()
game = H.game_block(html)

chk("cryo is flagged as a support tower", 'support: true' in game)
chk("lead band exists", "const LEAD_BAND" in game)
chk("STRONG scores on maxHp, not current hp", 'e.maxHp || e.hp' in game and 'e.hp + e.shield;' not in game)
chk("support towers get their own stat line", "function statLine" in game and "ASSIST" in game)
chk("assist is credited from live slow sources", "SID_TOWER" in game and "tw.assist" in game)
chk("no synergy bonus shipped", "synergyMul" not in game)   # measured unnecessary, deliberately absent

BOARD = """([mode, cap]) => {
  const G = __GAME;
  G.S.endless = false; G.S.campaign = false; G.S.difficulty = 'hard';
  G.S.mapIndex = 5; G.selectMap(5); G.reset(); G.S.screen = 'playing';
  let n = 0; const mp = G.__MAPS[5];
  for (let c = 0; c < mp.cols && n < cap; c++) for (let r = 0; r < mp.rows && n < cap; r++) {
    const ty = (n % 3 === 2) ? 'cryo' : 'turret';
    if (G.build(c, r, ty)) { const t = G.towers[G.towers.length - 1]; t.lvl = 3; t.branch = 'a'; t.mode = mode; n++; }
  }
  G.S.core = 4000; G.S.coreMax = 4000; G.S.scrap = 0; G.startWave(); G.sim(50, 200000);
  return { leaks: 4000 - G.S.core, assist: G.towers.filter(t => t.type === 'cryo').reduce((a, t) => a + (t.assist || 0), 0) };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(NEW.resolve().as_uri())
    pg.wait_for_function("() => !!window.__GAME", timeout=60000)
    pg.evaluate("() => { localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); }")
    pg.wait_for_timeout(400)

    # ---- targeting: STRONG must no longer ignore the leader -------------------------------
    res = {}
    for m in ["first", "strong", "close"]:
        runs = [pg.evaluate(BOARD, [m, 22]) for _ in range(5)]
        res[m] = statistics.mean(r["leaks"] for r in runs)
    print("      leaks: " + ", ".join("%s %.1f" % (k, v) for k, v in res.items()))
    # Before the fix STRONG was ~3x FIRST. It should not be a trap any more; FIRST staying the best
    # default is correct and expected, so the bar is "within 2x", not "equal".
    chk("STRONG is no longer a trap (was ~3x FIRST)", res["strong"] < res["first"] * 2.2,
        "strong %.1f vs first %.1f (%.2fx)" % (res["strong"], res["first"], res["strong"] / max(res["first"], 1)))
    chk("CLOSE stays usable", res["close"] < res["first"] * 2.2,
        "close %.1f vs first %.1f" % (res["close"], res["first"]))

    # the lead band must actually restrict the candidate set
    # Deterministic rather than spawn-dependent: place one tower, then put three synthetic foes in
    # range at known path progress -- a tanky one at the BACK and two weak ones ahead of it. Before
    # the fix STRONG picked the tank and let the leaders through; it must now pick inside the band.
    band = pg.evaluate("""() => {
        const G = __GAME;
        G.S.mapIndex = 5; G.selectMap(5); G.reset(); G.S.screen = 'playing';
        let t = null; const mp = G.__MAPS[5];
        for (let c = 0; c < mp.cols && !t; c++) for (let r = 0; r < mp.rows && !t; r++)
          if (G.build(c, r, 'turret')) { t = G.towers[0]; t.lvl = 3; t.branch = 'b'; }
        const T = G.__TILE, p = { x: t.c * T + T / 2, y: t.r * T + T / 2 };
        // route/spd/type are needed because the RAF loop keeps updating and rendering these
        const mk = (pi, hp, dx) => ({ alive: true, flying: false, camo: false, revealed: 0, route: 0,
          x: p.x + dx, y: p.y, pi: pi, hp: hp, maxHp: hp, shield: 0, shieldMax: 0, r: 10, spd: 0,
          type: 'raider', slowF: 1, frost: 0, flash: 0 });
        G.enemies.length = 0;
        G.enemies.push(mk(100, 50, 4));    // leader, weak
        G.enemies.push(mk(90, 50, 8));     // near-leader, weak
        G.enemies.push(mk(10, 9000, 12));  // tank, far behind
        t.mode = 'strong';
        const s = G.__findTarget(t, p);
        t.mode = 'first';
        const f = G.__findTarget(t, p);
        const out = { strongPi: s ? s.pi : null, strongHp: s ? s.maxHp : null, firstPi: f ? f.pi : null };
        G.enemies.length = 0;   // do not leave synthetic foes for the render loop to walk
        return out;
    }""")
    chk("STRONG no longer picks the tank parked behind the pack",
        band["strongPi"] is not None and band["strongPi"] >= 55, band)
    chk("FIRST still picks the leader", band["firstPi"] == 100, band)

    # ---- support legibility ---------------------------------------------------------------
    run = pg.evaluate(BOARD, ["first", 22])
    chk("cryo accumulates assist damage in a real run", run["assist"] > 0, "%.0f assist" % run["assist"])

    panel = pg.evaluate("""() => {
        const G = __GAME;
        G.S.mapIndex = 0; G.selectMap(0); G.reset(); G.S.screen = 'playing';
        return { support: !!G.__TOWERS.cryo.support, slow: G.__TOWERS.cryo.levels[0].slow,
                 role: G.__TOWERS.turret ? 1 : 0 };
    }""")
    chk("cryo carries a slow value to display", panel["support"] and panel["slow"] > 0, panel)
    chk("codex teaches the support idea", "Support towers are not weak" in game)
    chk("codex teaches what TARGET does", "TARGET</b> on a tower menu" in game)

    # ---- regression: the change must not move the default board ---------------------------
    ends = pg.evaluate("""() => {
        const G = __GAME;
        G.S.endless = false; G.S.campaign = false; G.S.mapIndex = 0; G.selectMap(0); G.reset();
        G.S.screen = 'playing'; G.startWave(); const r = G.sim(50, 40000);
        return { screen: r.screen }; }""")
    chk("a no-tower run still resolves to gameover", ends["screen"] == "gameover", ends)

    chk("no page errors", not errs, errs[:3])
    b.close()

print()
print("V6.45: %d checks, %d failed" % (checks, len(fails)))
if fails:
    print("FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
