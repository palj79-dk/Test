"""C1: layout constants are live and orientation-aware; PORTRAIT IS UNCHANGED."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright
CHROME = H.chrome()
URL=H.target().as_uri()
errors=[]
LAY="({W:__GAME.__lay.W, H:__GAME.__lay.H, HUD_H:__GAME.__lay.HUD_H, TRAY_H:__GAME.__lay.TRAY_H, PLAY_TOP:__GAME.__lay.PLAY_TOP, PLAY_BOTTOM:__GAME.__lay.PLAY_BOTTOM, PLAY_H:__GAME.__lay.PLAY_H, LANDSCAPE:__GAME.__lay.LANDSCAPE, TRAY_X:__GAME.__lay.TRAY_X, TRAY_W:__GAME.__lay.TRAY_W})"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":360,"height":720}); pg.on("pageerror",lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1300)
    pg.evaluate("localStorage.setItem('seenIntro','true')"); pg.reload(); pg.wait_for_timeout(900)

    # 1. PORTRAIT must be byte-identical to the pre-C1 constants
    port=pg.evaluate(LAY)
    print("1 portrait:",port)
    # V6.34: portrait H now tracks the device aspect (clamped) so the canvas fills the screen.
    # At a 360x720 viewport that is H=720. Assert the DERIVATION, not a magic number.
    expH = max(600, min(900, round(360 * (720/360))))
    assert port["W"]==360 and port["H"]==expH, "portrait H should track the viewport aspect (expected %s, got %s)" % (expH, port["H"])
    assert port["HUD_H"]==56 and port["TRAY_H"]==118 and port["PLAY_TOP"]==56, "portrait bands changed"
    assert port["PLAY_BOTTOM"]==expH-118 and port["PLAY_H"]==expH-118-56, "portrait play band wrong"
    assert port["LANDSCAPE"] is False and port["TRAY_X"]==360 and port["TRAY_W"]==0

    # 2. rotating to landscape recomputes the space
    pg.set_viewport_size({"width":740,"height":360}); pg.wait_for_timeout(400)
    land=pg.evaluate(LAY)
    print("2 landscape:",land)
    assert land["LANDSCAPE"] is True, "landscape not detected"
    # V6.33: landscape W follows the DEVICE aspect (clamped) so the canvas fills the width,
    # instead of a hardcoded 640. Assert the relationship, not a magic number.
    expW = max(560, min(1120, round(360 * (740/360))))
    assert land["H"]==360 and land["W"]==expW, "landscape logical width should track the viewport aspect (expected %s, got %s)" % (expW, land["W"])
    assert land["PLAY_BOTTOM"]==360 and land["PLAY_TOP"]==46, "landscape play band wrong"
    assert land["TRAY_W"]==188 and land["TRAY_X"]==land["W"]-188, "side tray must sit flush to the right edge"
    assert land["PLAY_H"]==314, "landscape play height wrong"

    # 3. rotating BACK restores portrait exactly (no drift)
    pg.set_viewport_size({"width":360,"height":720}); pg.wait_for_timeout(400)
    back=pg.evaluate(LAY)
    print("3 back to portrait:",back)
    assert back==port, "portrait did not restore exactly after a rotation round-trip"

    # 4. the game still runs after a rotation round-trip (no stale-constant crash)
    pg.evaluate("""(()=>{const G=__GAME; G.S.mapIndex=0; G.selectMap(0); G.reset();
        G.S.screen='playing'; G.S.tut=9; G.render();})()""")
    pg.wait_for_timeout(300)
    pg.set_viewport_size({"width":740,"height":360}); pg.wait_for_timeout(400)
    pg.set_viewport_size({"width":360,"height":720}); pg.wait_for_timeout(400)
    st=pg.evaluate("""(()=>{const G=__GAME; let n=0;
        for(let c=0;c<15&&n<3;c++)for(let r=0;r<22&&n<3;r++) if(G.build(c,r,'turret')) n++;
        G.startWave(); const o=G.sim(50,400);
        return {towers:G.towers.length, screen:o.screen, wave:o.wave};})()""")
    print("4 gameplay after rotation round-trip:",st)
    assert st["towers"]==3 and st["screen"]=="playing", "gameplay broke after rotation"
    b.close()
print("\nPAGE ERRORS:",errors); assert not errors,errors
print("\n=== V6.30 C1 VERIFY PASSED ===")
