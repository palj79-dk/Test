#!/usr/bin/env python3
"""V6.36 verify: build focus, Armory re-cost, left build panel + permanent command strip,
hero range/placement, overclock confirm+cap, wave soft-block."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import sys
from playwright.sync_api import sync_playwright

URL = "" + H.target().as_uri() + ""
CHROME = H.chrome()
errs = []
out = []


def log(n, v):
    out.append("%s %s" % (n, v))
    print(n, v, flush=True)


def boot(pg, landscape=False):
    pg.set_viewport_size({"width": 740, "height": 360} if landscape else {"width": 360, "height": 720})
    pg.goto(URL)
    pg.evaluate("localStorage.setItem('seenIntro','true')")
    pg.reload()
    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg.wait_for_timeout(400)


def start_run(pg, camp=0, alloy=0):
    pg.evaluate("""([camp, alloy]) => {
      const G = window.__GAME;
      localStorage.setItem('camp', JSON.stringify(camp));
      G.Meta.alloy = alloy; G.Meta.save();
      G.selectMap(0); G.reset(); G.S.screen = 'playing'; G.S.tut = -1; G.S.scrap = 4000; G.render();
    }""", [camp, alloy])
    pg.wait_for_timeout(300)


with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = br.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # ---------------------------------------------------------------- 2. Armory re-cost
    boot(pg)
    log("1 tree cost", pg.evaluate("""() => {
      const T = window.__GAME.TECH;
      const per = T.map(b => b.nodes.reduce((a, n) => a + n.cost, 0));
      const total = per.reduce((a, b) => a + b, 0);
      const gated = T.reduce((a, b) => a + b.nodes.filter(n => n.reqCamp).reduce((x, n) => x + n.cost, 0), 0);
      const first2 = T.reduce((a, b) => a + b.nodes[0].cost + b.nodes[1].cost, 0);
      return { total, per, reachable: total - gated, first2 };
    }"""))

    # ---------------------------------------------------------------- 1. build focus
    start_run(pg)
    log("2 build focus", pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      S.selTile = { c: G.__tutPlot ? 0 : 0, r: 0 };
      // find a genuinely buildable plot
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r)) plot = { c, r };
      S.selTile = plot; S.selTower = null;
      S.pending = { kind: 'build', tower: 'turret' };
      G.__doPending();
      return { selTower: S.selTower, towers: G.towers.length, sameTile: S.selTower != null && G.towers[S.selTower].c === plot.c };
    }"""))

    # ---------------------------------------------------------------- 5. overclock
    log("3 overclock model", pg.evaluate("""() => {
      const G = window.__GAME, t = G.towers[0];
      t.lvl = 3; t.branch = 'a'; t.oc = 0;
      const base = G.tStats(t), c0 = G.overclockCost(t);
      t.oc = 1; const oc1 = G.tStats(t), c1 = G.overclockCost(t);
      t.oc = 3; const capped = G.__ocAvailable(t);
      t.oc = 0;
      return { c0, c1, baseDmg: base.dmg, oc1Dmg: oc1.dmg, baseRate: base.rate, oc1Rate: oc1.rate, availAt0: G.__ocAvailable(t), availAt3: capped };
    }"""))

    log("4 overclock confirms", pg.evaluate("""() => {
      const G = window.__GAME, S = G.S, t = G.towers[0];
      t.lvl = 3; t.branch = 'a'; t.oc = 0;
      S.selTower = 0; S.pending = null;
      const before = S.scrap;
      G.__trayAction({ action: 'overclock', canUp: true });
      const raised = S.pending && S.pending.kind === 'overclock' && S.scrap === before;
      const info = G.__pendingInfo();
      G.__doPending();
      return { raised, verb: info && info.verb, dmgUp: info && info.next.dmg > info.cur.dmg, rateUp: info && info.next.rate < info.cur.rate, ocAfter: t.oc, spent: before - S.scrap };
    }"""))
    pg.wait_for_timeout(300)
    log("5 oc field marker", pg.evaluate("() => { const G = window.__GAME; return { anyOc: G.towers.some(t => t.oc > 0) }; }"))

    # ---------------------------------------------------------------- 6. wave soft-block
    log("6 soft block", pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      S.wave = 5; S.waveSize = 20; S.countdown = 3;
      S.queue = []; for (let i = 0; i < 10; i++) S.queue.push({ w: 5, t: 5000, type: 'stalker' });
      const heldMany = G.__autoHold();
      S.queue = S.queue.slice(0, 3);         // 15% left -> inside the tail
      const heldTail = G.__autoHold();
      S.queue = [];
      const heldClear = G.__autoHold();
      return { heldMany, heldTail, heldClear };
    }"""))

    log("7 hold freezes countdown", pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      S.wave = 5; S.waveSize = 20; S.countdown = 4; S.screen = 'playing';
      S.queue = []; for (let i = 0; i < 10; i++) S.queue.push({ w: 5, t: 90000, type: 'stalker' });
      const c0 = S.countdown;
      for (let i = 0; i < 120; i++) G.__simStep(50);
      const held = S.countdown;
      S.queue = [];
      for (let i = 0; i < 120; i++) G.__simStep(50);
      return { c0, held, frozen: Math.abs(held - c0) < 0.05, launched: S.wave > 5 };
    }"""))

    # ---------------------------------------------------------------- 3+4 UI, portrait
    boot(pg)
    start_run(pg, camp=20, alloy=99999)
    pg.evaluate("() => { const T = window.__GAME.Tech; for (let i = 0; i < 4; i++) while (T.buy(i)) {} }")
    pg.wait_for_timeout(300)

    log("8 idle strip", pg.evaluate("""() => {
      const G = window.__GAME;
      return { hero: G.__heroBtns.length, strike: G.__abilityBtns.length, build: G.buildBtns.length, idle: G.__trayIsIdle() };
    }"""))

    # open the build panel on a real plot
    pg.evaluate("""() => {
      const G = window.__GAME;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r) && !G.towers.some(t => t.c === c && t.r === r)) plot = { c, r };
      G.S.selTile = plot; G.S.selTower = null; G.S.pending = null; G.S.sheetAnim = 1;
    }""")
    pg.wait_for_timeout(320)

    p = pg.evaluate("""() => {
      const G = window.__GAME, rect = G.__trayRect(), pr = G.__buildPanelRect();
      const rows = G.buildBtns.filter(b => b.action === 'build');
      const close = G.buildBtns.filter(b => b.action === 'closebuild');
      const swallow = G.buildBtns.filter(b => b.action === 'none');
      const hit = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
      return {
        open: G.__buildMenuOpen(), rows: rows.length, close: close.length, swallow: swallow.length,
        rowW: rows[0] && Math.round(rows[0].w), rowH: rows[0] && Math.round(rows[0].h),
        panel: { x: pr.x, y: Math.round(pr.y), w: pr.w, h: Math.round(pr.h) },
        overlapsTray: hit(pr, rect),
        heroStillThere: G.__heroBtns.length === 1 && G.__abilityBtns.length === 1,
        repairStillThere: G.trayBtns.some(b => b.action === 'repair') || G.S.core >= G.S.coreMax,
        cmdRowY: Math.round(G.__cmdRowY()),
        panelBottom: Math.round(pr.y + pr.h),
        playBottom: G.__trayTop(),
      };
    }""")
    log("9 build panel", p)
    if not p["open"] or p["rows"] != 7 or p["close"] != 1 or p["swallow"] != 1:
        errs.append("build panel shape wrong: %s" % p)
    if p["rowW"] < 48 or p["rowH"] < 28:
        errs.append("build row below tap minimum: %sx%s" % (p["rowW"], p["rowH"]))
    if p["overlapsTray"]:
        errs.append("build panel overlaps the tray")
    if not p["heroStillThere"]:
        errs.append("HERO/STRIKE vanished while the build panel is open")

    # every HUD button must stay clear of the tray (V6.31 C2 regression guard)
    log("10 hud vs tray", pg.evaluate("""() => {
      const G = window.__GAME, r = G.__trayRect();
      const bad = G.hudBtns.filter(b => b.x < r.x + r.w && b.x + b.w > r.x && b.y < r.y + r.h && b.y + b.h > r.y);
      return { bad: bad.map(b => b.id) };
    }"""))

    # tapping a row raises the confirm sheet; the strip survives it
    pg.evaluate("""() => {
      const G = window.__GAME, row = G.buildBtns.find(b => b.action === 'build' && b.tower === 'turret');
      G.tap(row.x + row.w / 2, row.y + row.h / 2);
    }""")
    pg.wait_for_timeout(300)
    c = pg.evaluate("""() => {
      const G = window.__GAME;
      return { pending: G.S.pending && G.S.pending.kind, hero: G.__heroBtns.length, strike: G.__abilityBtns.length,
               confirm: G.trayBtns.some(b => b.action === 'confirm'), buildBtns: G.buildBtns.length,
               trayTop: Math.round(G.__trayTop()), cmdY: Math.round(G.__cmdRowY()) };
    }""")
    log("11 confirm keeps strip", c)
    if c["pending"] != "build" or c["hero"] != 1 or c["strike"] != 1 or not c["confirm"]:
        errs.append("confirm sheet broke the command strip: %s" % c)
    if c["buildBtns"] != 0:
        errs.append("build panel hit-boxes survived the panel closing")

    # close button clears the selection
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.pending = null;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r) && !G.towers.some(t => t.c === c && t.r === r)) plot = { c, r };
      G.S.selTile = plot; G.S.sheetAnim = 1;
    }""")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { const G = window.__GAME, b = G.buildBtns.find(x => x.action === 'closebuild'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(250)
    cl = pg.evaluate("() => ({ selTile: window.__GAME.S.selTile, buildBtns: window.__GAME.buildBtns.length })")
    log("12 close button", cl)
    if cl["selTile"] is not None:
        errs.append("✕ did not close the build panel")

    # ---------------------------------------------------------------- 4. hero flow
    # V6.37 moved the entry point from an arm-the-map mode to a build-panel row; the V6.36 promise
    # (a confirm sheet with the range ring, not an instant drop) is what this still guards.
    h = pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      S.selTower = null; S.pending = null; S.heroSel = false;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r) && !G.towers.some(t => t.c === c && t.r === r)) plot = { c, r };
      S.selTile = plot; S.sheetAnim = 1;
      return { plot };
    }""")
    pg.wait_for_timeout(320)
    h = pg.evaluate("""() => {
      const G = window.__GAME;
      const row = G.buildBtns.find(b => b.action === 'buildhero');
      if (!row) return { heroRow: false };
      G.tap(row.x + row.w / 2, row.y + row.h / 2);
      return { heroRow: true, pending: G.S.pending && G.S.pending.kind, heroYet: !!G.hero };
    }""")
    log("13 hero placement", h)
    if not h["heroRow"] or h["pending"] != "hero" or h["heroYet"]:
        errs.append("hero placement did not route through the confirm sheet: %s" % h)
    pg.wait_for_timeout(300)
    h2 = pg.evaluate("""() => {
      const G = window.__GAME;
      const rp = G.S.rangePreview;
      const ok = G.trayBtns.some(b => b.action === 'confirm');
      G.__doPending();
      return { rangeShown: !!rp && rp.range > 0, confirmBtn: ok, deployed: !!G.hero, heroBtns: G.__heroBtns.length };
    }""")
    log("14 hero confirm", h2)
    if not h2["rangeShown"] or not h2["confirmBtn"] or not h2["deployed"]:
        errs.append("hero confirm sheet incomplete: %s" % h2)
    pg.wait_for_timeout(300)
    log("15 hero ring", pg.evaluate("() => ({ hero: !!window.__GAME.hero, heroRange: window.__GAME.hero && window.__GAME.__HERO.levels[window.__GAME.hero.lvl].range })"))

    # ---------------------------------------------------------------- landscape
    boot(pg, landscape=True)
    start_run(pg, camp=20, alloy=99999)
    pg.evaluate("() => { const T = window.__GAME.Tech; for (let i = 0; i < 4; i++) while (T.buy(i)) {} }")
    pg.evaluate("""() => {
      const G = window.__GAME;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r)) plot = { c, r };
      G.S.selTile = plot; G.S.sheetAnim = 1;
    }""")
    pg.wait_for_timeout(350)
    L = pg.evaluate("""() => {
      const G = window.__GAME, pr = G.__buildPanelRect(), r = G.__trayRect();
      const rows = G.buildBtns.filter(b => b.action === 'build');
      const hit = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
      const cmdBottom = G.__abilityBtns.concat(G.__heroBtns).reduce((m, b) => Math.max(m, b.y + b.h), 0);
      return { landscape: G.__lay.LANDSCAPE, rows: rows.length, rowH: rows[0] && Math.round(rows[0].h),
               panelBottom: Math.round(pr.y + pr.h), H: G.__lay.H, overlapsTray: hit(pr, r),
               hero: G.__heroBtns.length, strike: G.__abilityBtns.length, cmdBottom: Math.round(cmdBottom) };
    }""")
    log("16 landscape panel", L)
    if L["rows"] != 7 or L["overlapsTray"] or L["hero"] != 1 or L["strike"] != 1:
        errs.append("landscape build panel wrong: %s" % L)
    if L["panelBottom"] > L["H"]:
        errs.append("landscape build panel runs off the bottom: %s" % L)
    if L["cmdBottom"] > L["H"]:
        errs.append("landscape command strip runs off the bottom: %s" % L)

    # ---------------------------------------------------------------- full headless run
    # Same shape as the V6.25 win test: every plot filled with a maxed tower, then G.sim() drives the
    # run — which now routes the auto-launch through autoHold(), so this also proves the soft block
    # cannot deadlock the wave loop.
    boot(pg)
    r = pg.evaluate("""() => {
      const G = window.__GAME, S = G.S;
      G.selectMap(0); G.reset(); S.screen = 'playing'; S.tut = -1;
      const TY = ['tesla', 'mortar', 'turret', 'cryo', 'pyre', 'siege', 'prism'];
      let n = 0;
      for (let c = 0; c < 15; c++) for (let r2 = 0; r2 < 22; r2++) if (G.build(c, r2, TY[n % 7])) { const t = G.towers[G.towers.length - 1]; t.lvl = 3; t.branch = (n % 2) ? 'a' : 'b'; n++; }
      S.scrap = 0; G.startWave();
      const res = G.sim(50, 200000);
      return Object.assign(res, { towers: G.towers.length });
    }""")
    log("17 full run", r)
    if r["screen"] != "victory":
        errs.append("headless run did not reach victory: %s" % r)

    br.close()

print()
print("PAGE ERRORS:", errs)
if errs:
    print("=== V6.36 VERIFY FAILED ===")
    sys.exit(1)
print("=== V6.36 VERIFY PASSED ===")
