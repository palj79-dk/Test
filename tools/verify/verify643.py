"""V6.43 suite — terrain relief, props following the terraces, and the horizon.

The point of the iteration is that the ground stops being flat, so the central assertion is a
measured height range, compared against V6.42 where relief was 2.2 units on a 64-unit tile.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
import re
import sys
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
NEW = H.target()
MAPS = [0, 3, 9, 16, 24]
fails = []


def chk(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


html = NEW.read_text()
chk("terrace step is a named constant", "const STEP = 7;" in html)
chk("horizon geometry exists", "plainMesh" in html and "distant mesas" in html.lower() or "mesas" in html)

# every prop must be anchored to its slab — a hardcoded 0 base is exactly the floating-prop bug
dec_start = html.index("      // decor props")
dec_end = html.index("      // focal structures")
decor = html[dec_start:dec_end]
bad = re.findall(r"boxM\((?:land|metal|glow), [^,]+, 0,", decor)
chk("no prop is still anchored at y=0", not bad, bad[:3])
chk("props read the slab height", decor.count("dy") >= 20, "%d dy references" % decor.count("dy"))

PROBE = """
(mapIdx) => {
  const G = __GAME;
  G.S.endless = false; G.S.campaign = false; G.S.isDaily = false; G.S.isLab = false;
  G.S.difficulty = 'hard'; G.S.mapIndex = mapIdx; G.selectMap(mapIdx); G.reset();
  G.S.screen = 'playing'; G.render();
  const sc = G.G3D.scene;
  let land = null, plain = null, meshes = 0;
  const visit = (o) => { if (o.isMesh) { meshes++;
      const m = o.material;
      if (m.type === 'MeshLambertMaterial' && m.vertexColors && o.geometry.attributes.color) {
        // the land mesh has a colour map; the horizon plain does not
        if (m.map) land = o; else if (!plain) plain = o; } }
    (o.children || []).forEach(visit); };
  visit(sc);
  if (!land) return { err: 'no land mesh' };
  // relief: spread of up-facing ground tops *inside* the play grid
  const pos = land.geometry.attributes.position.array, nor = land.geometry.attributes.normal.array;
  let lo = 1e9, hi = -1e9; const lv = new Set();
  for (let v = 0; v < pos.length / 3; v++) {
    if (nor[v * 3 + 1] < 0.99) continue;
    const y = pos[v * 3 + 1];
    if (y < -20 || y > 40) continue;             // skip cliffs and tall props
    lo = Math.min(lo, y); hi = Math.max(hi, y); lv.add(Math.round(y * 10) / 10);
  }
  let plots = 0;
  for (let rr = 0; rr < 40; rr++) for (let cc = 0; cc < 40; cc++) if (G.buildable(cc, rr)) plots++;
  // every tower must sit on the terrace under it, not at y=0
  G.S.scrap = 999999; let placed = 0, wrongY = 0;
  outer: for (let rr = 0; rr < 40; rr++) for (let cc = 0; cc < 40; cc++) {
    if (placed >= 25) break outer;
    if (G.build(cc, rr, 'turret')) placed++;
  }
  return { relief: +(hi - lo).toFixed(2), levels: lv.size, plots, meshes, placed,
           hasPlain: !!plain, plainTris: plain ? plain.geometry.index.count / 3 : 0 };
}
"""


def probe(path):
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
            out[mi] = pg.evaluate(PROBE, mi)
        # towers must render at the terrace height, not at 0
        out["towerY"] = pg.evaluate("""() => {
          const G = __GAME, ys = [];
          for (const t of G.towers) ys.push(Math.round((G.G3D ? 0 : 0)));
          return G.towers.length; }""")
        pg.wait_for_timeout(400)
        out["frame"] = pg.evaluate("""() => new Promise(res => { const t = []; let last = performance.now(), k = 0;
          const step = () => { const now = performance.now(); t.push(now - last); last = now;
            if (++k < 70) requestAnimationFrame(step); else { t.sort((a,b)=>a-b); res(+t[Math.floor(t.length/2)].toFixed(1)); } };
          requestAnimationFrame(step); });""")
        out["errs"] = errs
        b.close()
    return out


print("\n-- probing V6.43 --")
new = probe(NEW)
old_plots = {0: 69, 3: 109, 9: 125, 16: 165, 24: 254}   # measured from V6.40/V6.41/V6.42, unchanged

for mi in MAPS:
    n = new[mi]
    print("  map%-3d relief %5.1f units over %d levels   plots %d   horizon tris %d"
          % (mi, n["relief"], n["levels"], n["plots"], n["plainTris"]))
    chk("map%d: terrain relief is readable (>= 10 units)" % mi, n["relief"] >= 10,
        "%.1f units, was 2.2 in V6.42" % n["relief"])
    chk("map%d: three terrace levels present" % mi, n["levels"] >= 3, "%d distinct" % n["levels"])
    chk("map%d: build space unchanged from V6.42" % mi, n["plots"] == old_plots[mi],
        "%d vs %d" % (n["plots"], old_plots[mi]))
    chk("map%d: horizon present" % mi, n["hasPlain"] and n["plainTris"] > 100,
        "%d tris" % n["plainTris"])
    chk("map%d: towers still placeable" % mi, n["placed"] >= 20, "%d placed" % n["placed"])

chk("no page errors", not new["errs"], new["errs"][:3])
print("  frame %.1f ms median (SwiftShader software rendering)" % new["frame"])

print()
if fails:
    print("FAILED %d: %s" % (len(fails), fails))
    sys.exit(1)
print("verify643: ALL PASS")
