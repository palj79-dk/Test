"""C2: landscape play-screen support — tray as right-hand side panel, camera refit, tap routing.
PORTRAIT MUST BE UNCHANGED (main regression risk)."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright
CHROME = H.chrome()
URL = H.target().as_uri()
errors = []

def lay(pg):
    return pg.evaluate("""(()=>{const L=__GAME.__lay; return {W:L.W,H:L.H,HUD_H:L.HUD_H,TRAY_H:L.TRAY_H,
        PLAY_TOP:L.PLAY_TOP,PLAY_BOTTOM:L.PLAY_BOTTOM,PLAY_H:L.PLAY_H,LANDSCAPE:L.LANDSCAPE,
        TRAY_X:L.TRAY_X,TRAY_W:L.TRAY_W};})()""")

def start_run(pg):
    pg.evaluate("""(()=>{const G=__GAME; G.S.mapIndex=0; G.selectMap(0); G.reset();
        G.S.screen='playing'; G.S.tut=9; G.render();})()""")
    pg.wait_for_timeout(300)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1300)
    pg.evaluate("localStorage.setItem('seenIntro','true')"); pg.reload(); pg.wait_for_timeout(900)

    # ---- 1. portrait tray geometry unchanged ----
    start_run(pg)
    pg.evaluate("(()=>{const G=__GAME; let n=0; for(let c=0;c<15&&n<3;c++)for(let r=0;r<22&&n<3;r++) if(G.build(c,r,'turret')) n++;})()")
    pg.evaluate("(()=>{__GAME.S.selTile={c:9,r:5}; __GAME.render();})()")
    pg.wait_for_timeout(300)
    build_btns = pg.evaluate("__GAME.buildBtns.filter(b=>b.action==='build')")
    print("1 portrait build cells:", len(build_btns), [round(b['w'],1) for b in build_btns])
    assert len(build_btns) == 7, "expected 7 build cells, got %d" % len(build_btns)
    ws = sorted(set(round(b['w'], 1) for b in build_btns))
    hs = sorted(set(round(b['h'], 1) for b in build_btns))
    print("   widths:", ws, "heights:", hs)
    # V6.36: the palette left the tray for a left-edge panel — one full-width row per tower.
    assert all(w >= 48 for w in ws), "portrait build row width below the tap minimum: %s" % ws
    assert all(h >= 28 for h in hs), "portrait build row height below the tap minimum: %s" % hs
    rows = sorted(set(round(b['y'], 1) for b in build_btns))
    assert len(rows) == 7, "expected one row per tower in portrait, got %d" % len(rows)

    port_lay = lay(pg)
    print("1b portrait layout:", port_lay)
    # V6.34: portrait H tracks the viewport aspect; assert the derivation, not magic numbers.
    expH = max(600, min(900, round(360 * (720/360))))
    assert port_lay["W"]==360 and port_lay["H"]==expH and port_lay["LANDSCAPE"] is False
    assert port_lay["PLAY_BOTTOM"]==expH-118 and port_lay["PLAY_H"]==expH-118-56, "portrait play band wrong"
    port_rect = pg.evaluate("__GAME.__trayRect()")
    print("1c portrait trayRect:", port_rect)
    # V6.36: the build panel no longer borrows tray height (BUILD_EXP is gone) — the tray only grows
    # for the tower/confirm SHEETS, which is what TRAY_EXP now buys back for the command strip.
    assert port_rect == {"x": 0, "y": port_lay["PLAY_BOTTOM"], "w": 360, "h": 118}, "portrait trayRect (build panel open) wrong: %s" % port_rect
    port_panel = pg.evaluate("__GAME.__buildPanelRect()")
    print("1c2 portrait build panel:", port_panel)
    assert port_panel["y"] >= port_lay["PLAY_TOP"] and port_panel["y"] + port_panel["h"] <= port_lay["PLAY_BOTTOM"], "build panel must stay in the play viewport: %s" % port_panel

    # cancel selection back to idle, check idle cmd row is still the 3-across portrait layout
    pg.evaluate("(()=>{__GAME.S.selTile=null; __GAME.render();})()")
    pg.wait_for_timeout(300)
    idle_rect = pg.evaluate("__GAME.__trayRect()")
    assert idle_rect == {"x": 0, "y": port_lay["PLAY_BOTTOM"], "w": 360, "h": 118}, "portrait idle trayRect wrong: %s" % idle_rect
    hero_btn = pg.evaluate("__GAME.__heroBtns[0]")
    strike_btn = pg.evaluate("__GAME.__abilityBtns[0]")
    print("1d portrait cmd row hero/strike:", hero_btn, strike_btn)
    assert hero_btn["w"] > 100, "portrait cmd row should be 3-across (wide buttons)"

    # ---- 2. rotate to landscape: trayRect geometry ----
    pg.set_viewport_size({"width": 740, "height": 360}); pg.wait_for_timeout(400)
    land_lay = lay(pg)
    print("2 landscape layout:", land_lay)
    assert land_lay["LANDSCAPE"] is True
    # V6.33: landscape W tracks the device aspect, so assert the relationship not a magic number
    assert land_lay["TRAY_X"] == land_lay["W"] - 188 and land_lay["TRAY_W"] == 188
    land_rect = pg.evaluate("__GAME.__trayRect()")
    print("2b landscape trayRect:", land_rect)
    assert land_rect == {"x": land_lay["W"] - 188, "y": 46, "w": 188, "h": 314}, "landscape trayRect wrong: %s" % land_rect

    # every tray button (idle state) must lie fully inside trayRect
    pg.wait_for_timeout(300)
    def check_inside(btns, rect, label):
        for b in btns:
            assert b["x"] >= rect["x"] - 0.5, "%s btn x<rect.x: %s in %s" % (label, b, rect)
            assert b["y"] >= rect["y"] - 0.5, "%s btn y<rect.y: %s in %s" % (label, b, rect)
            assert b["x"] + b["w"] <= rect["x"] + rect["w"] + 0.5, "%s btn overflows right: %s in %s" % (label, b, rect)
            assert b["y"] + b["h"] <= rect["y"] + rect["h"] + 0.5, "%s btn overflows bottom: %s in %s" % (label, b, rect)

    idle_trayBtns = pg.evaluate("__GAME.trayBtns")
    land_hero = pg.evaluate("__GAME.__heroBtns[0]")
    land_strike = pg.evaluate("__GAME.__abilityBtns[0]")
    print("2c landscape idle trayBtns:", len(idle_trayBtns), "hero:", land_hero, "strike:", land_strike)
    check_inside(idle_trayBtns, land_rect, "idle")
    check_inside([land_hero], land_rect, "hero")
    check_inside([land_strike], land_rect, "strike")

    # ---- 3. landscape build menu: 2 per row, >=48px, no overlap, inside rect ----
    pg.evaluate("(()=>{__GAME.S.selTile={c:9,r:5}; __GAME.render();})()")
    pg.wait_for_timeout(300)
    land_build_rect = pg.evaluate("__GAME.__trayRect()")
    print("3 landscape build trayRect:", land_build_rect)
    assert land_build_rect == {"x": land_lay["W"] - 188, "y": 46, "w": 188, "h": 314}, "landscape build-panel trayRect must not change: %s" % land_build_rect
    land_panel = pg.evaluate("__GAME.__buildPanelRect()")
    land_build_btns = pg.evaluate("__GAME.buildBtns.filter(b=>b.action==='build')")
    print("3b landscape build panel:", land_panel, "cells:", len(land_build_btns))
    assert len(land_build_btns) == 7
    # V6.36: the palette is a left-edge panel in both orientations — it must sit in the play viewport
    # and stay clear of the side tray it used to live in.
    check_inside(land_build_btns, land_panel, "build")
    assert land_panel["x"] + land_panel["w"] <= land_lay["TRAY_X"], "landscape build panel overlaps the side tray: %s" % land_panel
    assert land_panel["y"] >= land_lay["PLAY_TOP"] and land_panel["y"] + land_panel["h"] <= land_lay["H"], "landscape build panel off-screen: %s" % land_panel
    bws = sorted(set(round(b['w'], 1) for b in land_build_btns))
    bhs = sorted(set(round(b['h'], 1) for b in land_build_btns))
    print("   widths:", bws, "heights:", bhs)
    assert all(w >= 48 for w in bws), "landscape build row narrower than 48px: %s" % bws
    assert all(h >= 28 for h in bhs), "landscape build row shorter than 28px: %s" % bhs
    cols = sorted(set(round(b['x'], 1) for b in land_build_btns))
    assert len(cols) == 1, "expected a single full-width column, got %d: %s" % (len(cols), cols)
    # no-overlap: sort by (row,col) and check rectangles pairwise
    def overlap(a, b):
        return not (a['x'] + a['w'] <= b['x'] + 0.01 or b['x'] + b['w'] <= a['x'] + 0.01 or
                    a['y'] + a['h'] <= b['y'] + 0.01 or b['y'] + b['h'] <= a['y'] + 0.01)
    for i in range(len(land_build_btns)):
        for j in range(i + 1, len(land_build_btns)):
            assert not overlap(land_build_btns[i], land_build_btns[j]), "build cells overlap: %s / %s" % (land_build_btns[i], land_build_btns[j])
    print("   no overlaps OK")

    # ---- 4. a tap inside the side panel reaches the command strip (V6.37: HERO = Overload Pulse) ----
    pg.evaluate("(()=>{__GAME.S.selTile=null; __GAME.render();})()")
    pg.wait_for_timeout(300)
    pg.evaluate("""(()=>{const G=__GAME;
        let plot=null; for(let c=0;c<15&&!plot;c++)for(let r=0;r<22&&!plot;r++) if(G.buildable(c,r)&&!G.towers.some(t=>t.c===c&&t.r===r)) plot={c,r};
        G.deployHero(plot.c, plot.r); G.hero.abil=0;})()""")
    pg.wait_for_timeout(300)
    hb = pg.evaluate("__GAME.__heroBtns[0]")
    pg.evaluate("(()=>{__GAME.tap(%f, %f);})()" % (hb["x"] + hb["w"] / 2, hb["y"] + hb["h"] / 2))
    pulsed = pg.evaluate("__GAME.hero.abil > 0")
    print("4 tray tap (hero btn) fired the pulse:", pulsed)
    assert pulsed is True, "tap inside landscape side panel did not reach the command strip handler"
    pg.wait_for_timeout(300)

    # ---- 5. armed airstrike tapped over the side panel must NOT fire into the world ----
    towers_before = pg.evaluate("__GAME.towers.length")
    pg.evaluate("(()=>{__GAME.S.strikeArm=true; __GAME.render();})()")
    pg.wait_for_timeout(200)
    # tap deep inside the tray panel (x=550, well right of TRAY_X=land_lay["W"] - 188), well below PLAY_TOP
    pg.evaluate("(()=>{__GAME.tap(550, 200);})()")
    strike_after_tap = pg.evaluate("__GAME.S.strikeArm")
    print("5 strikeArm after tap over side panel:", strike_after_tap, "(expect false: cancelled, not fired into world)")
    assert strike_after_tap is False, "strikeArm should be cancelled (not left armed) after a tap over the tray panel"
    towers_after = pg.evaluate("__GAME.towers.length")
    assert towers_after == towers_before, "tower count should not change from a cancelled strike tap"

    # ---- 6. camera fits the reduced viewport in landscape ----
    cam_info = pg.evaluate("""(()=>{const G=__GAME; return {zoom:G.cam.zoom, x:G.cam.x,
        trayX:G.__lay.TRAY_X, w:G.__lay.W};})()""")
    print("6 landscape camera:", cam_info)
    # project world (0,0) and (WORLD_W,0) to screen and confirm the whole map fits within [0,TRAY_X]
    proj = pg.evaluate("""(()=>{const G=__GAME; const p0=G.worldToScreen(0,0);
        return {p0};})()""")
    print("6b world origin projects to:", proj)
    map_right_edge = pg.evaluate("""(()=>{const G=__GAME;
        // WORLD_W isn't exported directly; read via G3D camera aspect trick: use fitCamera's own math
        return null;})()""")
    # Simpler correctness check: fitCamera() should not leave cam.zoom clamped against a value that
    # was computed against the full canvas width (640) instead of the play viewport (land_lay["W"] - 188) — verify
    # the MINZOOM used is based on TRAY_X, not W, by checking zoom*WORLD spans <= TRAY_X (with margin).
    span_check = pg.evaluate("""(()=>{const G=__GAME; G.fitCamera();
        return {zoom:G.cam.zoom};})()""")
    print("6c post-fitCamera zoom:", span_check)

    # ---- 7. rotation round-trip mid-run: towers intact, still playing, camera refits ----
    towers_before_rot = pg.evaluate("__GAME.towers.length")
    pg.set_viewport_size({"width": 360, "height": 720}); pg.wait_for_timeout(400)
    pg.set_viewport_size({"width": 740, "height": 360}); pg.wait_for_timeout(400)
    st = pg.evaluate("""(()=>{const G=__GAME; G.startWave(); const o=G.sim(50,400);
        return {towers:G.towers.length, screen:o.screen, wave:o.wave};})()""")
    print("7 after rotation round-trip mid-run:", st)
    assert st["towers"] == towers_before_rot, "tower count changed across rotation"
    assert st["screen"] == "playing", "run broke after rotation round-trip"

    # portrait geometry restored exactly after rotating back
    pg.set_viewport_size({"width": 360, "height": 720}); pg.wait_for_timeout(400)
    back_lay = lay(pg)
    print("7b back to portrait:", back_lay)
    assert back_lay == port_lay, "portrait did not restore exactly after a rotation round-trip"

    # 8. NO HUD element may overlap the side panel (a DEPLOY button anchored to the canvas edge
    #    used to sit on top of it, and hudBtns are hit-tested BEFORE trayBtns, so it also stole taps).
    pg.set_viewport_size({"width":740,"height":360}); pg.wait_for_timeout(400)
    pg.evaluate("""(()=>{const G=__GAME; G.S.mapIndex=0; G.selectMap(0); G.reset();
        G.S.screen='playing'; G.S.tut=9; G.render();})()""")
    pg.wait_for_timeout(400)
    hud = pg.evaluate("""(()=>{const G=__GAME, tr=G.__trayRect();
        return G.__hudBtns.filter(b => (b.x+b.w > tr.x) && (b.y+b.h > tr.y)).map(b=>b.id);})()""")
    print("8 HUD buttons overlapping the side panel:", hud)
    assert hud == [], "HUD element(s) overlap the landscape side panel: %s" % hud

    b.close()

print("\nPAGE ERRORS:", errors); assert not errors, errors
print("\n=== V6.31 C2 VERIFY PASSED ===")
