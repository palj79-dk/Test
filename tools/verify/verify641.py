"""V6.41 suite — ground grid removal, dead-code deletion, decal winding.

Measures the ground geometry directly rather than eyeballing pixels: adjacent ground tiles must
agree on the colour of the corner they share, and every triangle in the land mesh must front-face
the way its stored normal points. Both are compared against the V6.40 baseline.
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
OLD = H.baseline("6.40")
fails = []


def chk(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- static
html = NEW.read_text()
chk("version label bumped", "V6.43 \u00b7" in html and chr(34)+"6.43"+chr(34) in html)

DEAD = ["buildTerrain", "groundTile", "roadTile", "drawPool", "drawBarrel", "drawRubble",
        "drawCrater", "drawWreck", "drawSandbags", "drawDeadtree", "drawBuilding", "drawDropship",
        "roadNeighbors", "VOID_COL", "TMARGIN", "CLIFF_H"]
left = [d for d in DEAD if re.search(r"\b" + d + r"\b", html)]
chk("dead 2D terrain bake fully removed", not left, left)
# V6.42 added the obstacle pool, clustering and accents on top, so the net saving is smaller
chk("still smaller than V6.40 despite later additions", len(html) < len(OLD.read_text()),
    "%d -> %d bytes" % (len(OLD.read_text()), len(html)))

# ---------------------------------------------------------------- geometry probes
# Walk the land mesh: (a) colour agreement at shared world positions on up-facing ground quads,
# (b) triangle winding vs stored normal.
PROBE = """
(mapIdx) => {
  const G = __GAME;
  G.S.endless = false; G.S.campaign = false; G.S.isDaily = false; G.S.isLab = false;
  G.S.mapIndex = mapIdx; G.selectMap(mapIdx); G.reset(); G.S.screen = 'playing'; G.render();
  const sc = G.G3D.scene;
  let land = null, meshes = 0;
  const visit = (o) => { if (o.isMesh) { meshes++;
      const m = o.material;
      if (m.type === 'MeshLambertMaterial' && m.vertexColors && o.geometry.attributes.color) land = o; }
    (o.children || []).forEach(visit); };
  visit(sc);
  if (!land) return { err: 'no land mesh' };
  const pos = land.geometry.attributes.position.array;
  const nor = land.geometry.attributes.normal.array;
  const col = land.geometry.attributes.color.array;
  const idx = land.geometry.index.array;

  // (a) seam test — only up-facing vertices (ground tops), keyed by rounded world x/z
  const byPos = new Map();
  let worstSeam = 0, seamPairs = 0;
  for (let v = 0; v < pos.length / 3; v++) {
    if (nor[v * 3 + 1] < 0.99) continue;                 // up-facing only
    const k = Math.round(pos[v * 3] * 4) + ':' + Math.round(pos[v * 3 + 1] * 4) + ':' + Math.round(pos[v * 3 + 2] * 4);
    const c = [col[v * 3], col[v * 3 + 1], col[v * 3 + 2]];
    const prev = byPos.get(k);
    if (prev) {
      const d = Math.abs(prev[0] - c[0]) + Math.abs(prev[1] - c[1]) + Math.abs(prev[2] - c[2]);
      worstSeam = Math.max(worstSeam, d); seamPairs++;
    } else byPos.set(k, c);
  }

  // (b) winding test — cross(b-a, c-a) must agree with the stored normal
  let flipped = 0, tris = 0;
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz); if (len < 1e-6) continue;
    tris++;
    if ((nx * nor[a] + ny * nor[a + 1] + nz * nor[a + 2]) / len < -0.2) flipped++;
  }
  return { seamPairs, worstSeam: +worstSeam.toFixed(4), tris, flipped, meshes,
           calls: G.G3D.renderer.info.render.calls };
}
"""


def probe(path, label):
    errs = []
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": 400, "height": 800})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(path.as_uri())
        pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
        pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24')")
        pg.reload()
        pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
        pg.wait_for_timeout(800)
        for mi in (0, 9, 24):
            pg.wait_for_timeout(400)
            out[mi] = pg.evaluate(PROBE, mi)
        # frame cost on a populated field
        pg.evaluate("""() => { const G = __GAME; G.S.scrap = 999999;
          let n = 0; outer: for (let r = 0; r < 30; r++) for (let c = 0; c < 30; c++) {
            if (n >= 40) break outer; if (G.build(c, r, 'tesla')) n++; } }""")
        pg.wait_for_timeout(600)
        ft = pg.evaluate("""() => new Promise(res => { const t = []; let last = performance.now(), k = 0;
          const step = () => { const now = performance.now(); t.push(now - last); last = now;
            if (++k < 70) requestAnimationFrame(step); else { t.sort((a,b)=>a-b); res(+t[Math.floor(t.length/2)].toFixed(2)); } };
          requestAnimationFrame(step); });""")
        out["frame"] = ft
        out["errs"] = errs
        b.close()
    print("  [%s] %s" % (label, {k: v for k, v in out.items() if k != "errs"}))
    return out


print("\n-- probing V6.40 baseline --")
old = probe(OLD, "V6.40")
print("-- probing V6.41 --")
new = probe(NEW, "V6.41")

# ---------------------------------------------------------------- assertions
for mi in (0, 9, 24):
    o, n = old[mi], new[mi]
    chk("map%d: ground seams removed (was %.3f)" % (mi, o["worstSeam"]),
        n["worstSeam"] < 0.001 and o["worstSeam"] > 0.02,
        "V6.40 worst %.4f -> V6.41 worst %.4f over %d shared corners" % (o["worstSeam"], n["worstSeam"], n["seamPairs"]))
    chk("map%d: no back-facing land triangles (was %d)" % (mi, o["flipped"]),
        n["flipped"] == 0 and o["flipped"] > 0,
        "V6.40 %d/%d flipped -> V6.41 %d/%d" % (o["flipped"], o["tris"], n["flipped"], n["tris"]))
    # V6.42 turned the 2D obstacle overlay into pooled 3D geometry: 64 groups x 6 parts are
    # allocated up front, so the scene-wide mesh count rises by a fixed 384 regardless of map.
    chk("map%d: mesh count rises only by the obstacle pool" % mi, n["meshes"] - o["meshes"] == 384 - 2 or abs(n["meshes"] - o["meshes"] - 382) <= 8,
        "%d -> %d (+%d)" % (o["meshes"], n["meshes"], n["meshes"] - o["meshes"]))
    chk("map%d: draw calls not increased" % mi, n["calls"] <= o["calls"],
        "%d vs %d" % (o["calls"], n["calls"]))

chk("frame cost not regressed >10%% (SwiftShader, relative only)",
    new["frame"] <= old["frame"] * 1.10 + 0.5,
    "V6.40 %.1fms -> V6.41 %.1fms median software-rendered" % (old["frame"], new["frame"]))
chk("no page errors", not new["errs"], new["errs"][:3])

print()
if fails:
    print("FAILED %d: %s" % (len(fails), fails))
    sys.exit(1)
print("verify641: ALL PASS")
