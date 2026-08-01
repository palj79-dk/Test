#!/usr/bin/env python3
"""V6.39 verify: the play-log export actually delivers the log.

The bug this guards: an <a download> of a blob: URL is a no-op inside Android's WebView, and the old
code swallowed that in an empty catch, so the button failed silently. The new path must (a) put the
real JSON on the clipboard, (b) report success or failure visibly, (c) offer a manual raw-text route,
and (d) not advertise the file download inside the app where it cannot work.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import sys, json
from playwright.sync_api import sync_playwright

URL = "" + H.target().as_uri() + ""
CHROME = H.chrome()
errs = []


def log(n, v):
    print(n, v, flush=True)


with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    ctx = br.new_context(viewport={"width": 360, "height": 720})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.evaluate("localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true')")
    pg.reload()
    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg.wait_for_timeout(500)

    # seed a couple of real runs through the telemetry path
    pg.evaluate("""() => {
      const G = window.__GAME;
      G.Telemetry.setEnabled(true);
      for (let k = 0; k < 2; k++) {
        G.selectMap(k); G.reset(); G.S.screen = 'playing'; G.S.tut = -1;
        G.Telemetry.begin(); G.S.wave = 20; G.S.kills = 300 + k; G.Telemetry.end('victory');
      }
    }""")
    n = pg.evaluate("() => window.__GAME.Telemetry.runs.length")
    log("1 runs seeded", n)
    if n < 2:
        errs.append("telemetry did not record the seeded runs: %s" % n)

    # the export payload is real, parseable JSON containing those runs
    txt = pg.evaluate("() => window.__GAME.__exportText()")
    try:
        parsed = json.loads(txt)
        log("2 payload parses", {"runs": len(parsed), "bytes": len(txt), "keys": sorted(parsed[0].keys())[:6]})
    except Exception as e:
        parsed = None
        errs.append("export payload is not valid JSON: %s" % e)
    if parsed is not None and len(parsed) != n:
        errs.append("payload run count %s != stored %s" % (len(parsed), n))

    # open the Play Log screen
    pg.evaluate("() => { const G = window.__GAME; G.S.screen = 'log'; G.render(); }")
    pg.wait_for_timeout(300)
    ui = pg.evaluate("""() => {
      const ov = document.getElementById('overlay');
      return { copy: !!document.getElementById('exp'), msg: !!document.getElementById('expmsg'),
               rawToggle: !!document.getElementById('rawt'), rawBox: !!document.getElementById('raw'),
               dl: !!document.getElementById('dl'), native: window.__GAME.__isNativeApp(),
               copyLabel: document.getElementById('exp') ? document.getElementById('exp').textContent.trim() : null };
    }""")
    log("3 log screen", ui)
    if not (ui["copy"] and ui["msg"] and ui["rawToggle"]):
        errs.append("log screen is missing the export controls: %s" % ui)
    if ui["native"] or not ui["dl"]:
        errs.append("in a plain browser the file-download button should be offered: %s" % ui)

    # tapping Copy puts the payload on the real clipboard and reports success
    pg.click("#exp")
    pg.wait_for_timeout(600)
    res = pg.evaluate("""async () => {
      const el = document.getElementById('expmsg');
      let clip = null;
      try { clip = await navigator.clipboard.readText(); } catch (e) { clip = 'READ-FAILED: ' + e.message; }
      return { msg: el ? el.textContent.trim() : null, color: el ? el.style.color : null, clipLen: clip ? clip.length : 0, clipHead: (clip || '').slice(0, 24) };
    }""")
    log("4 copy result", res)
    if not res["msg"] or "Copied" not in res["msg"]:
        errs.append("copy did not report success: %s" % res)
    if res["clipLen"] != len(txt):
        errs.append("clipboard content length %s != payload %s" % (res["clipLen"], len(txt)))
    try:
        clip_full = pg.evaluate("async () => await navigator.clipboard.readText()")
        if json.loads(clip_full) != parsed:
            errs.append("clipboard JSON does not match the payload")
        else:
            log("5 clipboard round-trip", "identical JSON, %d runs" % len(json.loads(clip_full)))
    except Exception as e:
        errs.append("clipboard did not round-trip as JSON: %s" % e)

    # the raw box is a genuine manual fallback carrying the same text
    pg.click("#rawt")
    pg.wait_for_timeout(350)
    raw = pg.evaluate("""() => {
      const t = document.getElementById('raw');
      return { present: !!t, len: t ? t.value.length : 0, readonly: t ? t.hasAttribute('readonly') : null,
               toggle: document.getElementById('rawt') ? document.getElementById('rawt').textContent.trim() : null };
    }""")
    log("6 raw fallback", raw)
    if not raw["present"] or raw["len"] != len(txt):
        errs.append("raw box missing or truncated: %s" % raw)
    pg.click("#rawt")
    pg.wait_for_timeout(300)
    if pg.evaluate("() => !!document.getElementById('raw')"):
        errs.append("raw box did not toggle off")

    # failure must be visible, not silent: break the clipboard and confirm the UI says so
    pg.evaluate("""() => {
      const G = window.__GAME;
      Object.defineProperty(navigator, 'clipboard', { get: () => undefined, configurable: true });
      document.execCommand = () => false;
      G.S.screen = 'log'; G.render();
    }""")
    pg.wait_for_timeout(300)
    pg.click("#exp")
    pg.wait_for_timeout(400)
    fail = pg.evaluate("() => { const el = document.getElementById('expmsg'); return { msg: el ? el.textContent.trim() : null, color: el ? el.style.color : null }; }")
    log("7 blocked clipboard reports failure", fail)
    if not fail["msg"] or "Clipboard blocked" not in fail["msg"]:
        errs.append("a blocked clipboard failed silently again: %s" % fail)

    # and the manual route still exists in that state
    pg.click("#rawt")
    pg.wait_for_timeout(350)
    if not pg.evaluate("() => !!document.getElementById('raw')"):
        errs.append("raw fallback unavailable when the clipboard is blocked")
    else:
        log("8 manual route survives", "raw box still available")

    # simulate the app: window.Capacitor present -> no file-download button
    pg.evaluate("""() => {
      window.Capacitor = { isNativePlatform: () => true };
      window.__GAME.S.screen = 'log'; window.__GAME.render();
    }""")
    pg.wait_for_timeout(300)
    app = pg.evaluate("() => ({ native: window.__GAME.__isNativeApp(), dl: !!document.getElementById('dl'), copy: !!document.getElementById('exp'), rawt: !!document.getElementById('rawt') })")
    log("9 in-app controls", app)
    if not app["native"] or app["dl"]:
        errs.append("the file download is still offered inside the app: %s" % app)
    if not (app["copy"] and app["rawt"]):
        errs.append("in-app is missing copy/raw: %s" % app)

    # nothing else regressed on the way in or out of the screen
    pg.evaluate("() => { const G = window.__GAME; G.S.screen = 'settings'; G.render(); }")
    pg.wait_for_timeout(250)
    log("10 back out", pg.evaluate("() => window.__GAME.S.screen"))

    br.close()

print()
print("PAGE ERRORS:", errs)
if errs:
    print("=== V6.39 VERIFY FAILED ===")
    sys.exit(1)
print("=== V6.39 VERIFY PASSED ===")
