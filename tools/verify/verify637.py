#!/usr/bin/env python3
"""V6.37 verify: Commander deployed from the build panel (Pulse-only strip button),
build panel as a strict toggle, hero range ring on demand."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import sys
from playwright.sync_api import sync_playwright

URL = "" + H.target().as_uri() + ""
CHROME = H.chrome()
errs = []


def log(n, v):
    print(n, v, flush=True)


def boot(pg, landscape=False):
    pg.set_viewport_size({"width": 740, "height": 360} if landscape else {"width": 360, "height": 720})
    pg.goto(URL)
    pg.evaluate("localStorage.setItem('seenIntro','true')")
    pg.reload()
    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg.wait_for_timeout(400)
    pg.evaluate("""() => {
      const G = window.__GAME;
      localStorage.setItem('camp', JSON.stringify(20));
      G.Meta.alloy = 999999; G.Meta.save();
      const T = G.Tech; for (let i = 0; i < 4; i++) { let g = 0; while (T.buy(i) && g++ < 20) {} }
      G.selectMap(0); G.reset(); G.S.screen = 'playing'; G.S.tut = -1; G.S.scrap = 4000; G.render();
    }""")
    pg.wait_for_timeout(300)


# Only plots whose screen position is clear of the build panel — the panel overlays the left of the
# play area, so a plot behind it cannot be tapped and would make these toggle tests meaningless.
PLOTS = """() => {
  const G = window.__GAME, lay = G.__lay, p = G.__buildPanelRect(), out = [];
  for (let c = 0; c < 30; c++) for (let r = 0; r < 30; r++) {
    if (!G.buildable(c, r) || G.towers.some(t => t.c === c && t.r === r)) continue;
    const sp = G.worldToScreen((c + 0.5) * G.__TILE, (r + 0.5) * G.__TILE);
    if (sp.x < p.x + p.w + 14) continue;
    if (sp.x > (lay.LANDSCAPE ? lay.TRAY_X : lay.W) - 14) continue;
    if (sp.y < lay.PLAY_TOP + 14 || sp.y > lay.PLAY_BOTTOM - 14) continue;
    out.push({ c, r });
  }
  return out.slice(0, 6);
}"""


def tap_plot(pg, plot):
    pg.evaluate("""(pl) => {
      const G = window.__GAME;
      const p = G.worldToScreen((pl.c + 0.5) * G.__TILE, (pl.r + 0.5) * G.__TILE);
      G.tap(p.x, p.y);
    }""", plot)


with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = br.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    boot(pg)
    plots = pg.evaluate(PLOTS)

    # ---------------------------------------------------------- 2. strict toggle
    tap_plot(pg, plots[0])
    pg.wait_for_timeout(280)
    a = pg.evaluate("() => ({ sel: window.__GAME.S.selTile, open: window.__GAME.__buildMenuOpen(), rows: window.__GAME.buildBtns.filter(b => b.action === 'build' || b.action === 'buildhero').length })")
    log("1 open on first plot", a)
    tap_plot(pg, plots[1])                     # a DIFFERENT plot must also close it
    pg.wait_for_timeout(280)
    b1 = pg.evaluate("() => ({ sel: window.__GAME.S.selTile, open: window.__GAME.__buildMenuOpen(), btns: window.__GAME.buildBtns.length })")
    log("2 different plot closes", b1)
    if not a["open"] or b1["open"] or b1["sel"] is not None or b1["btns"] != 0:
        errs.append("build panel is not a strict toggle: open=%s -> %s" % (a, b1))
    tap_plot(pg, plots[1])                     # ...and re-opens on the next tap
    pg.wait_for_timeout(280)
    c1 = pg.evaluate("() => ({ sel: window.__GAME.S.selTile, open: window.__GAME.__buildMenuOpen() })")
    log("3 reopens on next tap", c1)
    if not c1["open"] or c1["sel"]["c"] != plots[1]["c"]:
        errs.append("build panel did not reopen on the new plot: %s" % c1)
    tap_plot(pg, plots[1])                     # same plot still closes (unchanged behaviour)
    pg.wait_for_timeout(280)
    d1 = pg.evaluate("() => window.__GAME.__buildMenuOpen()")
    log("4 same plot still closes", d1)
    if d1:
        errs.append("same-plot toggle broke")

    # ---------------------------------------------------------- 1. hero in the panel
    tap_plot(pg, plots[2])
    pg.wait_for_timeout(300)
    h = pg.evaluate("""() => {
      const G = window.__GAME;
      const rows = G.__panelRows();
      const hr = G.buildBtns.find(b => b.action === 'buildhero');
      return { rows, first: rows[0], heroRow: !!hr, hrW: hr && Math.round(hr.w), hrH: hr && Math.round(hr.h),
               panelH: Math.round(G.__buildPanelRect().h), heroExists: !!G.hero };
    }""")
    log("5 hero row present", h)
    if h["first"] != "hero" or not h["heroRow"] or len(h["rows"]) != 8:
        errs.append("Commander is not the first build-panel row: %s" % h)
    if h["hrH"] < 28 or h["hrW"] < 48:
        errs.append("hero row below the tap minimum: %s" % h)

    # pressing the hero row previews its range, tapping it raises the confirm sheet
    pg.evaluate("() => { const G = window.__GAME, b = G.buildBtns.find(x => x.action === 'buildhero'); G.__previewFromPoint ? 0 : 0; G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(300)
    h2 = pg.evaluate("""() => {
      const G = window.__GAME;
      return { pending: G.S.pending && G.S.pending.kind, ring: !!G.S.rangePreview && G.S.rangePreview.range > 0,
               confirm: G.trayBtns.some(x => x.action === 'confirm'), deployed: !!G.hero };
    }""")
    log("6 hero confirm from panel", h2)
    if h2["pending"] != "hero" or not h2["ring"] or not h2["confirm"] or h2["deployed"]:
        errs.append("hero row did not raise the confirm sheet: %s" % h2)
    pg.evaluate("() => { const G = window.__GAME, b = G.trayBtns.find(x => x.action === 'confirm'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(300)
    h3 = pg.evaluate("""() => {
      const G = window.__GAME;
      return { deployed: !!G.hero, selTile: G.S.selTile, rows: G.__panelRows().length,
               heroRingT: Math.round(G.S.heroRingT * 10) / 10 };
    }""")
    log("7 deployed", h3)
    if not h3["deployed"] or h3["selTile"] is not None or h3["rows"] != 7:
        errs.append("deploy from the panel left bad state: %s" % h3)
    if h3["heroRingT"] <= 0:
        errs.append("range ring did not flash on deploy: %s" % h3)

    # ---------------------------------------------------------- strip button is Pulse only
    st = pg.evaluate("""() => {
      const G = window.__GAME;
      G.hero.abil = 0;
      const before = G.hero.abil;
      const b = G.__heroBtns[0];
      G.tap(b.x + b.w / 2, b.y + b.h / 2);
      const pulsed = G.hero.abil > 0;
      return { btns: G.__heroBtns.length, pulsed, armGone: !('heroArm' in G.S) };
    }""")
    log("8 strip pulses", st)
    if not st["pulsed"] or not st["armGone"]:
        errs.append("strip HERO button is not the Pulse control: %s" % st)

    # with no Commander on the field the strip button must not arm anything
    pg.evaluate("() => { const G = window.__GAME; G.selectMap(0); G.reset(); G.S.screen = 'playing'; G.S.tut = -1; G.S.scrap = 4000; }")
    pg.wait_for_timeout(300)
    st2 = pg.evaluate("""() => {
      const G = window.__GAME, b = G.__heroBtns[0];
      G.tap(b.x + b.w / 2, b.y + b.h / 2);
      return { hero: !!G.hero, selTile: G.S.selTile, pending: G.S.pending, banner: G.S.banner.text };
    }""")
    log("9 strip with no commander", st2)
    if st2["hero"] or st2["pending"] is not None:
        errs.append("strip button still places the Commander: %s" % st2)

    # ---------------------------------------------------------- 3. ring on demand
    plots = pg.evaluate(PLOTS)
    pg.evaluate("""(pl) => { const G = window.__GAME; G.deployHero(pl.c, pl.r); G.S.heroRingT = 0; G.S.heroSel = false; }""", plots[3])
    pg.wait_for_timeout(300)
    r = pg.evaluate("() => ({ sel: window.__GAME.S.heroSel, t: window.__GAME.S.heroRingT, visible: window.__GAME.G3D.heroRingOn() })")
    log("10 ring hidden by default", r)
    if r["visible"]:
        errs.append("hero range ring is still always on: %s" % r)
    tap_plot(pg, plots[3])                     # tap the Commander
    pg.wait_for_timeout(300)
    r2 = pg.evaluate("() => ({ sel: window.__GAME.S.heroSel, visible: window.__GAME.G3D.heroRingOn(), selTile: window.__GAME.S.selTile })")
    log("11 tap commander shows ring", r2)
    if not r2["sel"] or not r2["visible"] or r2["selTile"] is not None:
        errs.append("tapping the Commander did not reveal its range: %s" % r2)
    tap_plot(pg, plots[3])                     # tap again to hide
    pg.wait_for_timeout(300)
    r3 = pg.evaluate("() => ({ sel: window.__GAME.S.heroSel, visible: window.__GAME.G3D.heroRingOn() })")
    log("12 tap again hides ring", r3)
    if r3["sel"] or r3["visible"]:
        errs.append("the ring did not toggle off: %s" % r3)
    # selecting a plot must drop the hero selection
    pg.evaluate("() => { window.__GAME.S.heroSel = true; }")
    tap_plot(pg, plots[4])
    pg.wait_for_timeout(300)
    r4 = pg.evaluate("() => ({ sel: window.__GAME.S.heroSel, open: window.__GAME.__buildMenuOpen() })")
    log("13 plot tap clears hero selection", r4)
    if r4["sel"]:
        errs.append("hero selection survived a plot tap: %s" % r4)

    # ---------------------------------------------------------- landscape fit with 8 rows
    boot(pg, landscape=True)
    plots = pg.evaluate(PLOTS)
    tap_plot(pg, plots[0])
    pg.wait_for_timeout(350)
    L = pg.evaluate("""() => {
      const G = window.__GAME, p = G.__buildPanelRect(), lay = G.__lay;
      const rows = G.buildBtns.filter(b => b.action === 'build' || b.action === 'buildhero');
      return { n: rows.length, rowH: rows[0] && Math.round(rows[0].h), rowW: rows[0] && Math.round(rows[0].w),
               bottom: Math.round(p.y + p.h), H: lay.H, right: p.x + p.w, trayX: lay.TRAY_X };
    }""")
    log("14 landscape with hero row", L)
    if L["n"] != 8 or L["bottom"] > L["H"] or L["right"] > L["trayX"] or L["rowH"] < 28:
        errs.append("landscape panel does not fit 8 rows: %s" % L)

    # ---------------------------------------------------------- full headless run unaffected
    boot(pg)
    fr = pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      G.selectMap(0); G.reset(); S.screen = 'playing'; S.tut = -1;
      const TY = ['tesla', 'mortar', 'turret', 'cryo', 'pyre', 'siege', 'prism'];
      let n = 0;
      for (let c = 0; c < 15; c++) for (let r = 0; r < 22; r++) if (G.build(c, r, TY[n % 7])) { const t = G.towers[G.towers.length - 1]; t.lvl = 3; t.branch = (n % 2) ? 'a' : 'b'; n++; }
      S.scrap = 0; G.startWave();
      return G.sim(50, 200000);
    }""")
    log("15 full run", fr)
    if fr["screen"] != "victory":
        errs.append("headless run did not reach victory: %s" % fr)

    br.close()

print()
print("PAGE ERRORS:", errs)
if errs:
    print("=== V6.37 VERIFY FAILED ===")
    sys.exit(1)
print("=== V6.37 VERIFY PASSED ===")
