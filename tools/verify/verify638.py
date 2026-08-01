#!/usr/bin/env python3
"""V6.38 verify: the guided tour walks the whole UI and ends with a Commander on the field
before wave 1, plus the screen-anatomy briefing card."""
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


def fresh(pg, landscape=False):
    """A genuinely new account: no seenIntro, no tutDone."""
    pg.set_viewport_size({"width": 740, "height": 360} if landscape else {"width": 360, "height": 720})
    pg.goto(URL)
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg.wait_for_timeout(600)


def state(pg):
    return pg.evaluate("""() => {
      const G = window.__GAME, st = G.__tutStep();
      return { tut: G.S.tut, id: st && st.id, readOnly: !!st && !st.done, wave: G.S.wave,
               towers: G.towers.length, hero: !!G.hero, screen: G.S.screen };
    }""")


def tap_center(pg):
    pg.evaluate("() => { const G = window.__GAME, l = G.__lay; G.tap(l.PLAY_TOP ? (l.LANDSCAPE ? l.TRAY_X : l.W) / 2 : 100, l.PLAY_TOP + 40); }")


with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = br.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # ------------------------------------------------------ briefing cards
    fresh(pg)
    intro = pg.evaluate("""() => {
      const G = window.__GAME;
      return { screen: G.S.screen, n: G.__INTRO_CARDS().length, titles: G.__INTRO_CARDS().map(c => c.title) };
    }""")
    log("1 briefing cards", intro)
    if intro["screen"] != "intro" or "YOUR SCREEN" not in intro["titles"]:
        errs.append("first launch did not open the briefing with the anatomy card: %s" % intro)

    # walk to the anatomy card and check it renders as real DOM inside the panel
    an = pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.introCard = G.__INTRO_CARDS().findIndex(c => c.title === 'YOUR SCREEN');
      G.render();
      const ov = document.getElementById('overlay');
      const panel = ov.querySelector('.panel');
      const tag = ov.querySelector('.tag');
      return { html: ov.innerHTML.indexOf('WAVE INTEL') >= 0 && ov.innerHTML.indexOf('BATTLEFIELD') >= 0,
               strays: ov.querySelectorAll('p > div').length,
               fits: panel.scrollHeight <= panel.clientHeight + 2 || getComputedStyle(panel).overflowY === 'auto',
               tagH: tag ? tag.getBoundingClientRect().height : 0,
               btn: !!document.getElementById('nx') };
    }""")
    log("2 anatomy card", an)
    if not an["html"] or an["strays"] or not an["btn"] or an["tagH"] < 120:
        errs.append("anatomy card did not render cleanly: %s" % an)

    # BEGIN drops straight into mission 1 with the tour armed
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.introCard = G.__INTRO_CARDS().length - 1; G.render();
      document.getElementById('nx').click();
    }""")
    pg.wait_for_timeout(700)
    log("3 begin mission", state(pg))
    s0 = state(pg)
    if s0["screen"] != "playing" or s0["tut"] != 0 or s0["id"] != "hud":
        errs.append("BEGIN did not start the tour at the HUD step: %s" % s0)

    # ------------------------------------------------------ walk the tour
    # step 0: read-only -> any tap advances
    tap_center(pg)
    pg.wait_for_timeout(280)
    s1 = state(pg)
    log("4 after hud tap", s1)
    if s1["id"] != "build":
        errs.append("HUD card did not advance on tap: %s" % s1)

    # the build panel is locked to the Auto-Gun for this step
    lock = pg.evaluate("""() => {
      const G = window.__GAME;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r)) plot = { c, r };
      G.S.selTile = plot; G.S.sheetAnim = 1;
      return { plot };
    }""")
    pg.wait_for_timeout(320)
    lk = pg.evaluate("""() => {
      const G = window.__GAME;
      const rows = G.buildBtns.filter(b => b.action === 'build' || b.action === 'buildhero');
      return { open: rows.length, allowed: rows.filter(b => !b.banned).map(b => b.tower || 'hero'),
               heroAllowed: G.__tutAllows('hero'), turretAllowed: G.__tutAllows('turret') };
    }""")
    log("5 build step locks the panel", lk)
    if lk["allowed"] != ["turret"] or lk["heroAllowed"]:
        errs.append("build step did not lock the panel to the Auto-Gun: %s" % lk)

    # build it through the real UI
    pg.evaluate("() => { const G = window.__GAME, b = G.buildBtns.find(x => x.tower === 'turret'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(300)
    mid = pg.evaluate("() => ({ msg: window.__GAME.__tutStep().msg(), pending: window.__GAME.S.pending && window.__GAME.S.pending.kind })")
    log("6 build step follows the flow", mid)
    if mid["pending"] != "build" or "CONFIRM" not in mid["msg"]:
        errs.append("build step did not follow through to the confirm: %s" % mid)
    pg.evaluate("() => { const G = window.__GAME, b = G.trayBtns.find(x => x.action === 'confirm'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(320)
    s2 = state(pg)
    log("7 after build", s2)
    if s2["id"] != "upgrade" or s2["towers"] != 1:
        errs.append("tour did not advance to the upgrade step: %s" % s2)

    # upgrade (focus already follows the build, so the upgrade button is right there)
    pg.evaluate("() => { const G = window.__GAME, b = G.trayBtns.find(x => x.action === 'upgrade'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { const G = window.__GAME, b = G.trayBtns.find(x => x.action === 'confirm'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(320)
    s3 = state(pg)
    log("8 after upgrade", s3)
    if s3["id"] != "hero":
        errs.append("tour did not advance to the Commander step: %s" % s3)

    # the Commander step locks the panel to the hero row
    pg.evaluate("""() => {
      const G = window.__GAME;
      let plot = null;
      for (let c = 0; c < 30 && !plot; c++) for (let r = 0; r < 30 && !plot; r++) if (G.buildable(c, r) && !G.towers.some(t => t.c === c && t.r === r)) plot = { c, r };
      G.S.selTile = plot; G.S.selTower = null; G.S.pending = null; G.S.sheetAnim = 1;
    }""")
    pg.wait_for_timeout(320)
    hl = pg.evaluate("""() => {
      const G = window.__GAME;
      const rows = G.buildBtns.filter(b => b.action === 'build' || b.action === 'buildhero');
      return { allowed: rows.filter(b => !b.banned).map(b => b.tower || 'hero') };
    }""")
    log("9 hero step locks the panel", hl)
    if hl["allowed"] != ["hero"]:
        errs.append("Commander step did not lock the panel to the hero row: %s" % hl)
    pg.evaluate("() => { const G = window.__GAME, b = G.buildBtns.find(x => x.action === 'buildhero'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { const G = window.__GAME, b = G.trayBtns.find(x => x.action === 'confirm'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(320)
    s4 = state(pg)
    log("10 commander deployed before wave 1", s4)
    if not s4["hero"] or s4["wave"] != 0 or s4["id"] != "cmd":
        errs.append("the Commander is still not on the field before wave 1: %s" % s4)

    # the two read-only UI cards, then DEPLOY
    tap_center(pg)
    pg.wait_for_timeout(280)
    s5 = state(pg)
    log("11 command bar card", s5)
    tap_center(pg)
    pg.wait_for_timeout(280)
    s6 = state(pg)
    log("12 wave intel card", s6)
    if s5["id"] != "intel" or s6["id"] != "deploy":
        errs.append("the read-only UI cards did not advance in order: %s -> %s" % (s5, s6))

    # every spotlight must resolve to something on screen at its own step
    spots = pg.evaluate("""() => {
      const G = window.__GAME, out = [];
      for (let i = 0; i < G.__TUT.length; i++) {
        const st = G.__TUT[i];
        let sp = null; try { sp = st.spot ? st.spot() : null; } catch (e) { sp = 'THREW: ' + e.message; }
        out.push({ id: st.id, has: !!sp, kind: sp && (sp.pt ? 'point' : 'rect') });
      }
      return out;
    }""")
    log("13 spotlights resolve", spots)
    for sp in spots:
        if not sp["has"]:
            errs.append("tour step %s has no spotlight at its own step" % sp["id"])

    pg.evaluate("() => { const G = window.__GAME, b = G.hudBtns.find(x => x.id === 'nextwave'); G.tap(b.x + b.w / 2, b.y + b.h / 2); }")
    pg.wait_for_timeout(400)
    s7 = state(pg)
    log("14 wave 1 away, tour done", s7)
    if s7["wave"] != 1 or s7["tut"] != -1:
        errs.append("the tour did not close out on wave 1: %s" % s7)
    if not pg.evaluate("() => JSON.parse(localStorage.getItem('tutDone') || 'false')"):
        errs.append("tutDone was not persisted")

    # ------------------------------------------------------ SKIP still works at step 0
    fresh(pg)
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.introCard = G.__INTRO_CARDS().length - 1; G.render();
      document.getElementById('nx').click();
    }""")
    pg.wait_for_timeout(600)
    sk = pg.evaluate("""() => {
      const G = window.__GAME;
      const b = G.__tutSkipBtn();
      if (!b) return { skip: false };
      G.tap(b.x + b.w / 2, b.y + b.h / 2);
      return { skip: true, tut: G.S.tut };
    }""")
    log("15 skip", sk)
    if not sk["skip"] or sk["tut"] != -1:
        errs.append("SKIP did not end the tour: %s" % sk)
    fresh(pg, landscape=True)
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.introCard = G.__INTRO_CARDS().length - 1; G.render();
      document.getElementById('nx').click();
    }""")
    pg.wait_for_timeout(700)

    # the SKIP button is hit-tested before everything else, so it must not sit on the DEPLOY control
    ov = pg.evaluate("""() => {
      const G = window.__GAME, sk = G.__tutSkipBtn(), nw = G.hudBtns.find(b => b.id === 'nextwave');
      if (!sk || !nw) return { checked: false };
      const hit = sk.x < nw.x + nw.w && sk.x + sk.w > nw.x && sk.y < nw.y + nw.h && sk.y + sk.h > nw.y;
      return { checked: true, hit, sk, nw };
    }""")
    log("15b skip vs deploy", ov)
    if not ov["checked"] or ov["hit"]:
        errs.append("SKIP overlaps the DEPLOY button and would steal its taps: %s" % ov)

    # ------------------------------------------------------ landscape geometry
    fresh(pg, landscape=True)
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.S.introCard = G.__INTRO_CARDS().length - 1; G.render();
      document.getElementById('nx').click();
    }""")
    pg.wait_for_timeout(700)
    L = pg.evaluate("""() => {
      const G = window.__GAME, lay = G.__lay;
      const cs = G.__cmdStripRect(), ir = G.__intelRect();
      const inTray = (r) => r.x >= lay.TRAY_X - 1 && r.x + r.w <= lay.W + 1 && r.y >= lay.PLAY_TOP - 4 && r.y + r.h <= lay.H + 1;
      return { landscape: lay.LANDSCAPE, cmd: cs, intel: ir, cmdOk: inTray(cs), intelOk: inTray(ir), tut: G.S.tut };
    }""")
    log("16 landscape spot rects", L)
    if not L["cmdOk"] or not L["intelOk"]:
        errs.append("landscape tour spotlights fall outside the side panel: %s" % L)

    br.close()

print()
print("PAGE ERRORS:", errs)
if errs:
    print("=== V6.38 VERIFY FAILED ===")
    sys.exit(1)
print("=== V6.38 VERIFY PASSED ===")
