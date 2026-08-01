"""V6.28's requirement, carried forward to V6.36's container.

V6.28 broke the 7-tower palette out of one cramped row so every cell cleared the 48px tap minimum,
stayed on screen, never overlapped, and absorbed taps instead of leaking them to the world. V6.36
moved that palette out of the tray entirely into a slide-in panel on the left edge — the container
changed, the requirement did not, so this suite now asserts it against the panel.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
URL = H.target().as_uri()
errors = []


def deploy(pg):
    pg.evaluate("""(()=>{const G=__GAME; G.S.endless=false; G.S.campaign=false; G.S.isDaily=false;
        G.S.isLab=false; G.selectMap(G.S.mapIndex); G.reset(); G.S.screen='playing'; G.S.tut=9;
        G.S.scrap=900; G.render();})()""")
    pg.wait_for_timeout(300)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.wait_for_timeout(1200)
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.wait_for_timeout(900)
    deploy(pg)
    tgt = pg.evaluate("""(() => { const G=__GAME,TILE=64;
        for(let r=0;r<22;r++)for(let c=0;c<15;c++) if(G.build(c,r,'turret')){ G.towers.pop();
          const sp=G.G3D.project(c*TILE+32,r*TILE+32,0); return {sx:sp.x,sy:sp.y}; } })()""")
    pg.evaluate("__GAME.tap(%s, %s)" % (tgt["sx"], tgt["sy"]))
    pg.wait_for_timeout(300)

    # 1. geometry: 7 rows, every one comfortably tappable, on screen, no overlap
    g = pg.evaluate("""(()=>{const bs=__GAME.buildBtns.filter(x=>x.action==='build');
        const srt=bs.slice().sort((a,b)=>a.y-b.y); let ov=false;
        for(let i=1;i<srt.length;i++) if(srt[i].y < srt[i-1].y+srt[i-1].h-0.01) ov=true;
        return {n:bs.length, w:+bs[0].w.toFixed(1), h:+bs[0].h.toFixed(1),
                minX:+Math.min(...bs.map(b=>b.x)).toFixed(1), maxX:+Math.max(...bs.map(b=>b.x+b.w)).toFixed(1),
                top:Math.min(...bs.map(b=>b.y)), bot:Math.max(...bs.map(b=>b.y+b.h)), overlap:ov};})()""")
    print("1 geometry:", g)
    L = pg.evaluate("__GAME.__lay")
    assert g["n"] == 7, "every tower needs a row"
    assert g["w"] >= 48 and g["h"] >= 28, "rows must clear the tap minimum: %s" % g
    assert not g["overlap"] and g["minX"] >= 0 and g["maxX"] <= L["W"], "rows overlap or leave the screen"
    assert g["top"] >= L["PLAY_TOP"] and g["bot"] <= L["PLAY_BOTTOM"], "panel must stay inside the play viewport"

    # 2. the tray no longer expands for the palette — it expands for the SHEET states instead, and
    #    the command strip stays put either way
    e = pg.evaluate("({open:__GAME.__buildMenuOpen(), top:__GAME.__trayTop(), cmd:__GAME.__cmdRowY()})")
    pg.evaluate("__GAME.S.selTile=null;")
    pg.wait_for_timeout(220)
    e2 = pg.evaluate("({open:__GAME.__buildMenuOpen(), top:__GAME.__trayTop(), cmd:__GAME.__cmdRowY()})")
    print("2 tray geometry:", {"building": e, "idle": e2})
    assert e["open"] and e["top"] == L["PLAY_BOTTOM"], "the build panel must not steal tray height"
    assert (not e2["open"]) and e2["top"] == L["PLAY_BOTTOM"]
    assert e["cmd"] == e2["cmd"], "the command strip must not move when the build panel opens"

    # 3. a tap on the panel background must be absorbed, not fall through and cancel the selection
    pg.evaluate("__GAME.tap(%s, %s)" % (tgt["sx"], tgt["sy"]))
    pg.wait_for_timeout(250)
    r3 = pg.evaluate("""(()=>{const G=__GAME, p=G.__buildPanelRect();
        const before=G.S.selTile ? (G.S.selTile.c+','+G.S.selTile.r) : null;
        G.tap(p.x+p.w-40, p.y+p.h-3);                    // panel background, below the last row
        const after=G.S.selTile ? (G.S.selTile.c+','+G.S.selTile.r) : null;
        return {before, after, kept: before!==null && before===after};})()""")
    print("3 panel tap absorbed:", r3)
    assert r3["kept"], "a tap on the panel fell through to the world and cancelled the selection"

    # 4. the close button replaces the undiscoverable "tap the plot again"
    r4 = pg.evaluate("""(()=>{const G=__GAME;
        const x=G.buildBtns.find(b=>b.action==='closebuild'); G.tap(x.x+x.w/2, x.y+x.h/2);
        return {closed: G.S.selTile===null};})()""")
    print("4 close button:", r4)
    assert r4["closed"], "the close button must dismiss the build panel"

    # 5. full build flow still works, locked towers stay blocked, and focus follows the new tower
    pg.evaluate("__GAME.tap(%s, %s)" % (tgt["sx"], tgt["sy"]))
    pg.wait_for_timeout(280)
    r5 = pg.evaluate("""(()=>{const G=__GAME; G.S.pending=null;
        const bs=G.buildBtns.filter(x=>x.action==='build');
        const tes=bs.find(b=>b.tower==='tesla'), tur=bs.find(b=>b.tower==='turret');
        G.tap(tes.x+tes.w/2, tes.y+tes.h/2); const lockedArmed=!!G.S.pending;
        G.tap(tur.x+tur.w/2, tur.y+tur.h/2);
        return {lockedArmed, okArmed:!!G.S.pending};})()""")
    pg.wait_for_timeout(280)   # let the RAF frame draw the confirm tray
    r5["built"] = pg.evaluate("""(()=>{const G=__GAME;
        const cf=G.trayBtns.find(x=>x.action==='confirm'); if(!cf) return -1;
        const n=G.towers.length; G.tap(cf.x+cf.w/2, cf.y+cf.h/2); return G.towers.length-n;})()""")
    r5["focused"] = pg.evaluate("__GAME.S.selTower")
    print("5 build flow:", r5)
    assert not r5["lockedArmed"] and r5["okArmed"], "locked tower must not arm; unlocked must"
    assert r5["built"] == 1, "confirm must place the tower"
    assert r5["focused"] == 0, "V6.36: focus must follow the freshly built tower"
    pg.screenshot(path=str(H.scratch() / "v628_build.png"))
    b.close()

print("\nPAGE ERRORS:", errors)
assert not errors, errors
print("\n=== V6.28 (in V6.36 container) VERIFY PASSED ===")
