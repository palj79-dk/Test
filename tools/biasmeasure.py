"""Does a map's V6.44 threat profile actually change the answer the board has to give?

The A/B that matters is the SAME map with the SAME board, bias off vs bias on — anything else
confounds the profile with the map's geometry. `__GAME.__MAPS[i].bias` is mutable at runtime, so
the two conditions differ in exactly one field.

The design intent is narrow and this is what it asserts: a profile must cost a board that IGNORES
the counter it names, and must NOT meaningfully cost a diverse board. A profile that hurts everyone
equally is just a difficulty bump wearing a costume.

THE TOWER COUNT IS PART OF THE INSTRUMENT, NOT A DETAIL. A board that is already drowning leaks
the same amount whatever the composition is, so the metric goes flat and reads as "no effect". At
10 towers the `energy` profile measured +1.0% / -0.3% against noise of +-5% and looked dead; at 22
towers on the same map it measured +105% (12 -> 24 leaks) with the diverse control flat at +8%.
Nothing about the game changed between those two runs. Always check the absolute leak count first:
if it is in the hundreds, the board is saturated and the run is measuring nothing.

Usage: python3 tools/biasmeasure.py [trials] [towers]   (default 5 trials, 10 towers)
       FG_CASES=energy python3 tools/biasmeasure.py 8 22
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent / "verify"))
import _harness as H

import statistics
import sys
from playwright.sync_api import sync_playwright

TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
CAP_ARG = int(sys.argv[2]) if len(sys.argv) > 2 else 10

# map, profile, the board that ignores it, and a diverse control
CASES = [
    (13, "energy", "mono-Railgun (energy)", ["tesla"], "b"),
    (22, "energy", "mono-Railgun (energy)", ["tesla"], "b"),
    (10, "air",    "mono-Mortar (ground-only)", ["mortar"], "a"),
    (24, "air+shield", "mono-Mortar (ground-only)", ["mortar"], "a"),
]
if __import__("os").environ.get("FG_CASES") == "energy":
    CASES = [c for c in CASES if c[1] == "energy"]
DIVERSE = ["tesla", "mortar", "turret", "cryo", "pyre"]

# Core is pinned high on purpose. A normal 18-core run CLIPS: a board that answers the wave loses 0
# and a board that cannot loses all 18, whichever way the composition moves, so the metric carries no
# information in either tail. Measuring total leak pressure to wave 20 instead gives a continuous
# number, and capping the tower count keeps the board off the "fills every plot and trivially wins"
# ceiling. This is the same bimodality PLAN-commander.md §5.5 flags in the auto-player.
RUN = """
([mapIdx, types, branch, biasOn, savedBias, cap]) => {
  const G = __GAME;
  G.__MAPS[mapIdx].bias = biasOn ? savedBias : undefined;
  G.S.endless = false; G.S.campaign = false; G.S.isDaily = false; G.S.isLab = false;
  G.S.difficulty = 'hard';
  G.S.mapIndex = mapIdx; G.selectMap(mapIdx); G.reset();
  G.S.screen = 'playing';
  let n = 0;
  const mp = G.__MAPS[mapIdx];
  for (let c = 0; c < mp.cols && n < cap; c++) for (let r = 0; r < mp.rows && n < cap; r++) {
    if (G.build(c, r, types[n % types.length])) {
      const t = G.towers[G.towers.length - 1];
      t.lvl = 3; t.branch = types.length === 1 ? branch : ((n % 2) ? 'a' : 'b');
      n++;
    }
  }
  G.S.core = 4000; G.S.coreMax = 4000;   // no clipping: measure leak pressure, not win/lose
  const core0 = G.S.core;
  G.S.scrap = 0;
  G.startWave();
  const r = G.sim(50, 200000);
  return { towers: n, lost: core0 - G.S.core, wave: r.wave, screen: r.screen };
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=H.chrome(), args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(H.target().resolve().as_uri())
    pg.wait_for_function("() => !!window.__GAME", timeout=60000)
    pg.evaluate("() => { localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); }")
    pg.wait_for_timeout(300)

    saved = pg.evaluate("() => __GAME.__MAPS.map(m => m.bias || null)")
    names = pg.evaluate("() => __GAME.__MAPS.map(m => m.name)")

    print("%d trials per condition, Hard, 10 maxed towers, core pinned high; numbers are TOTAL LEAKS to wave 20\n" % TRIALS)
    print("%-13s %-11s %-24s %11s %11s %8s" % ("map", "profile", "board", "off", "on", "delta"))
    print("-" * 82)

    CAP = CAP_ARG   # enough to hold a line, not enough to trivialise the map

    def run(mi, types, branch, on):
        out = []
        for _ in range(TRIALS):
            out.append(pg.evaluate(RUN, [mi, types, branch, on, saved[mi], CAP]))
        return out

    for mi, prof, label, types, branch in CASES:
        off = run(mi, types, branch, False)
        on = run(mi, types, branch, True)
        lo, ln = statistics.mean(x["lost"] for x in off), statistics.mean(x["lost"] for x in on)
        so, sn = statistics.stdev(x["lost"] for x in off), statistics.stdev(x["lost"] for x in on)
        print("%-13s %-11s %-24s %6.0f+-%-4.0f %6.0f+-%-4.0f %+7.1f%%" % (
            names[mi], prof, label, lo, so, ln, sn, (ln - lo) / max(lo, 1) * 100))

        doff = run(mi, DIVERSE, "a", False)
        don = run(mi, DIVERSE, "a", True)
        do, dn = statistics.mean(x["lost"] for x in doff), statistics.mean(x["lost"] for x in don)
        sd, sdn = statistics.stdev(x["lost"] for x in doff), statistics.stdev(x["lost"] for x in don)
        print("%-13s %-11s %-24s %6.0f+-%-4.0f %6.0f+-%-4.0f %+7.1f%%" % (
            "", "", "diverse control", do, sd, dn, sdn, (dn - do) / max(do, 1) * 100))
        print()

    print("page errors:", errs[:3] if errs else "none")
    b.close()
