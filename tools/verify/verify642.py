"""V6.42 suite — 3D obstacles, clustered props, enemy accents.

Everything is a before/after against the V6.40 baseline copy in the scratchpad.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import math
import pathlib
import re
import statistics
import sys
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
NEW = H.target()
OLD = H.baseline("6.40")
MAPS = [0, 3, 9, 16, 24]
fails = []


def chk(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


html = NEW.read_text()
chk("the 2D obstacle overlay is gone", not re.search(r"\bdrawObstacles\(\)", html.replace("drawObstacles()\n", "", 0)) or html.count("drawObstacles") == 1,
    "%d mentions (1 = the explanatory comment only)" % html.count("drawObstacles"))
chk("obstacles are pooled 3D geometry", "const obsPool = makePool(" in html and "function setObstacles(" in html)
chk("props are placed from a normalised density field", "DECOR_RATE" in html and "DECOR_THEMES" in html)
chk("enemies carry a threat-scaled accent", "ENEMY_THREAT" in html)


def nn(d):
    if len(d) < 2:
        return 0, 0
    out = []
    for i, (c, r) in enumerate(d):
        best = 1e9
        for j, (c2, r2) in enumerate(d):
            if i != j:
                best = min(best, math.hypot(c - c2, r - r2))
        out.append(best)
    return statistics.mean(out), statistics.pvariance(out)


def probe(path, label):
    errs, out = [], {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": 360, "height": 720})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(path.as_uri())
        pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
        pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24')")
        pg.reload()
        pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
        pg.wait_for_timeout(800)
        for mi in MAPS:
            r = pg.evaluate("""(mi) => {
              const G = __GAME;
              G.S.endless = false; G.S.campaign = false; G.S.isDaily = false; G.S.isLab = false;
              G.S.difficulty = 'hard'; G.S.mapIndex = mi; G.selectMap(mi); G.reset();
              G.S.screen = 'playing'; G.render();
              let vis = 0, meshes = 0, visMeshes = 0;
              const visit = (o, shown) => { const on = shown && o.visible;
                if (o.isMesh) { meshes++; if (on) visMeshes++; }
                if (o.isGroup && on && o.children.length === 6 && o.parent === G.G3D.scene) vis++;
                (o.children || []).forEach(c => visit(c, on)); };
              visit(G.G3D.scene, true);
              // count buildable plots — props must not have changed build space
              let plots = 0;
              for (let rr = 0; rr < 40; rr++) for (let cc = 0; cc < 40; cc++) if (G.buildable(cc, rr)) plots++;
              return { decor: G.__decor.map(d => [d.c, d.r]), blocked: G.blocked.size,
                       obsGroups: vis, meshes, visMeshes, plots };
            }""", mi)
            out[mi] = r
        pg.evaluate("""() => { const G = __GAME; G.S.scrap = 999999;
          let n = 0; outer: for (let r = 0; r < 30; r++) for (let c = 0; c < 30; c++) {
            if (n >= 40) break outer; if (G.build(c, r, 'tesla')) n++; } }""")
        pg.wait_for_timeout(600)
        out["frame"] = pg.evaluate("""() => new Promise(res => { const t = []; let last = performance.now(), k = 0;
          const step = () => { const now = performance.now(); t.push(now - last); last = now;
            if (++k < 70) requestAnimationFrame(step); else { t.sort((a,b)=>a-b); res(+t[Math.floor(t.length/2)].toFixed(1)); } };
          requestAnimationFrame(step); });""")
        out["errs"] = errs
        b.close()
    return out


print("\n-- probing V6.40 baseline --")
old = probe(OLD, "V6.40")
print("-- probing V6.42 --")
new = probe(NEW, "V6.42")

tot_o = tot_n = 0
better = 0
for mi in MAPS:
    o, n = old[mi], new[mi]
    mo, vo = nn(o["decor"])
    mn, vn = nn(n["decor"])
    tot_o += len(o["decor"]); tot_n += len(n["decor"])
    if vn >= vo * 2:
        better += 1
    print("  map%-3d props %3d -> %3d   nn-var %.3f -> %.3f (x%.2f)   plots %d -> %d   blocked %d -> %d"
          % (mi, len(o["decor"]), len(n["decor"]), vo, vn, (vn / vo) if vo else 0,
             o["plots"], n["plots"], o["blocked"], n["blocked"]))
    print("         visible meshes %d -> %d (+%d, = %d obstacle parts)"
          % (o["visMeshes"], n["visMeshes"], n["visMeshes"] - o["visMeshes"], n["blocked"] * 6))
    chk("map%d: build space unchanged" % mi, n["plots"] == o["plots"], "%d vs %d" % (o["plots"], n["plots"]))
    chk("map%d: obstacle count unchanged" % mi, n["blocked"] == o["blocked"], "%d vs %d" % (o["blocked"], n["blocked"]))
    chk("map%d: one 3D obstacle group per blocked tile" % mi, n["obsGroups"] == n["blocked"],
        "%d groups for %d blocked tiles" % (n["obsGroups"], n["blocked"]))
    # Visible geometry grows by the obstacle rubble that replaced the 2D overlay (blocked x 6),
    # plus or minus a handful: pool props each carry their own mesh, and clustering moves how many
    # pools a map ends up with in both directions.
    chk("map%d: visible mesh growth stays at the obstacle budget" % mi,
        0 < n["visMeshes"] - o["visMeshes"] <= n["blocked"] * 6 + 10,
        "+%d, obstacle budget %d" % (n["visMeshes"] - o["visMeshes"], n["blocked"] * 6))

chk("props cluster on at least 4 of 5 maps (nn-variance >= 2x)", better >= 4, "%d/5" % better)
chk("prop count within 35%% of baseline", abs(tot_n - tot_o) / tot_o < 0.35,
    "%d -> %d (%+.0f%%)" % (tot_o, tot_n, 100 * (tot_n - tot_o) / tot_o))
chk("frame cost not regressed >15%% (SwiftShader, relative only)",
    new["frame"] <= old["frame"] * 1.15 + 0.5,
    "V6.40 %.1fms -> V6.42 %.1fms median software-rendered" % (old["frame"], new["frame"]))
chk("no page errors", not new["errs"], new["errs"][:3])

print()
if fails:
    print("FAILED %d: %s" % (len(fails), fails))
    sys.exit(1)
print("verify642: ALL PASS")
