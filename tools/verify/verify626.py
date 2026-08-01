"""V6.26 verify: Wave Intel command bar + camo fairness gate."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
URL = H.target().as_uri()
errors = []

def fresh(pg):
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(800)

def deploy(pg):
    pg.evaluate("""(()=>{const G=__GAME; G.S.endless=false; G.S.campaign=false; G.S.isDaily=false;
        G.S.isLab=false; G.selectMap(G.S.mapIndex); G.reset(); G.S.screen='playing'; G.S.tut=9; G.render();})()""")
    pg.wait_for_timeout(300)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # ---------- CAMO FAIRNESS ----------
    # 1. No detector researched -> phantoms never spawn, at ANY wave; raiders replace them
    fresh(pg); deploy(pg)
    r = pg.evaluate("""(()=>{const G=__GAME; const out={};
        for (const w of [7,10,14,19]) { const c={}; G.__waveComp(w).forEach(e=>c[e.type]=(c[e.type]||0)+1);
          out[w]={phantom:c.phantom||0, raider:c.raider||0, total:G.__waveComp(w).length}; }
        return {detect:G.Tech.isUnlocked('tesla')||G.Tech.isUnlocked('prism'), out};})()""")
    print("1 no-detector waves:", r)
    assert r["detect"] is False
    for w in ("7", "10", "14", "19"):
        assert r["out"][w]["phantom"] == 0, f"wave {w} spawned cloaked foes with no detector available"

    # 2. Research Tesla -> phantoms return, and the wave stays the same size (raiders swapped back)
    r2 = pg.evaluate("""(()=>{const G=__GAME; const before={}; G.__waveComp(14).forEach(e=>before[e.type]=(before[e.type]||0)+1);
        const nBefore=G.__waveComp(14).length;
        G.Meta.alloy=99999; G.Tech.buy(1);                       // Arc node 0 = Tesla
        const after={}; G.__waveComp(14).forEach(e=>after[e.type]=(after[e.type]||0)+1);
        return {tesla:G.Tech.isUnlocked('tesla'), phBefore:before.phantom||0, phAfter:after.phantom||0,
                rdBefore:before.raider||0, rdAfter:after.raider||0,
                nBefore, nAfter:G.__waveComp(14).length};})()""")
    print("2 after researching Tesla:", r2)
    assert r2["tesla"] and r2["phAfter"] > 0, "phantoms must return once a detector is researched"
    assert r2["rdAfter"] < r2["rdBefore"], "raider substitution must be undone"
    assert r2["nBefore"] == r2["nAfter"], "wave size must be unchanged by the substitution"

    # 3. Prism also reveals camo (P3 tower parity with Tesla)
    fresh(pg); deploy(pg)
    r3 = pg.evaluate("""(()=>{const G=__GAME,TILE=64;
        const mk=(o)=>Object.assign({type:'phantom',alive:true,hp:1e9,maxHp:1e9,shield:0,shieldMax:0,armor:false,
          r:15,pi:0,route:0,slowT:0,slowF:1,frost:0,face:0,bob:0,walk:0,speed:0,flying:false,camo:true,revealed:0,
          slowResist:0,energyResist:0,body:'#586a86',dark:'#28323f',eye:'#fff',shape:'stalker',flash:0}, o);
        let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,'prism')) t=G.towers[0];
        const p={x:t.c*TILE+32,y:t.r*TILE+32}; const e=mk({x:p.x+60,y:p.y}); G.enemies.push(e);
        const h0=e.hp; G.sim(40,60);
        return {revealed:e.revealed>0, damaged:h0-e.hp>0};})()""")
    print("3 prism reveals camo:", r3)
    assert r3["revealed"] and r3["damaged"], "Prism must reveal and then damage cloaked foes"

    # ---------- WAVE INTEL BAR ----------
    # 4. Idle tray exposes HERO / STRIKE / REPAIR as real buttons inside the tray band
    fresh(pg); deploy(pg)
    pg.evaluate("(()=>{const G=__GAME; G.S.core=10; G.S.coreMax=20; G.S.scrap=900;})()")
    pg.wait_for_timeout(250)   # let a RAF frame rebuild the tray buttons
    r4 = pg.evaluate("""(()=>{const G=__GAME;
        const L=G.__lay; const inTray=(b)=>b.y>=L.PLAY_BOTTOM && b.y+b.h<=L.H;
        const hero=G.__heroBtns[0], st=G.__abilityBtns[0], rp=G.trayBtns.filter(x=>x.action==='repair').pop();
        return {hero:!!hero&&inTray(hero), strike:!!st&&inTray(st), repair:!!rp&&inTray(rp),
                heroW:hero?Math.round(hero.w):0, heroH:hero?hero.h:0, idle:G.__trayIsIdle()};})()""")
    print("4 command buttons:", r4)
    assert r4["idle"] and r4["hero"] and r4["strike"] and r4["repair"], "HERO/STRIKE/REPAIR must be real tray buttons"
    assert r4["heroW"] >= 100 and r4["heroH"] >= 30, f"command buttons too small: {r4}"

    # 5. V6.37: the strip HERO button is the Overload Pulse control. Deploying moved to the build
    #    panel, so this button must fire the pulse on a deployed Commander and place nothing.
    r5 = pg.evaluate("""(()=>{const G=__GAME;
        let plot=null; for(let c=0;c<15&&!plot;c++)for(let r=0;r<22&&!plot;r++) if(G.buildable(c,r)&&!G.towers.some(t=>t.c===c&&t.r===r)) plot={c,r};
        const b=G.__heroBtns[0];
        G.tap(b.x+b.w/2, b.y+b.h/2); const placedNothing = !G.hero && !G.S.pending;
        G.deployHero(plot.c, plot.r); G.hero.abil=0;
        G.tap(b.x+b.w/2, b.y+b.h/2);
        return {placedNothing, pulsed:G.hero.abil>0};})()""")
    print("5 hero button tap:", r5)
    assert r5["placedNothing"], "the strip button must not place the Commander"
    assert r5["pulsed"], "the strip button must fire the Overload Pulse"

    # 6. Intel counts match waveComp exactly, and warnings fire only when unanswerable
    r6 = pg.evaluate("""(()=>{const G=__GAME; G.S.wave=8; G.render();
        const comp={}; G.__waveComp(9).forEach(e=>comp[e.type]=(comp[e.type]||0)+1);
        const intel=G.__waveIntel(9);
        const match=intel.every(e=>comp[e.k]===e.n);
        const sorted=intel.every((e,i)=>i===0||intel[i-1].n>=e.n);
        return {match, sorted, top:intel.slice(0,3).map(e=>e.k+':'+e.n),
                airNow:G.__boardCan('air'), detectNow:G.__boardCan('detect')};})()""")
    print("6 intel accuracy:", r6)
    assert r6["match"], "intel counts must equal waveComp counts"
    assert r6["sorted"], "intel must be sorted by count desc"

    # 7. boardCan reacts to what is actually built (air warning clears once anti-air exists)
    r7 = pg.evaluate("""(()=>{const G=__GAME; G.towers.length=0; const before=G.__boardCan('air');
        for(let r=0;r<22;r++)for(let c=0;c<15;c++) if(G.build(c,r,'turret')) return {before, after:G.__boardCan('air')};})()""")
    print("7 anti-air detection:", r7)
    assert r7["before"] is False and r7["after"] is True, "boardCan('air') must flip once a direct-fire tower exists"

    # 8. V6.36: HERO/STRIKE are PERMANENT tray buttons — they no longer swap to floating map FABs
    #    when a plot is selected (that swap was the "airstrike lives in two places" complaint).
    idleHeroY = pg.evaluate("__GAME.__heroBtns[0].y")
    pg.evaluate("""(()=>{const G=__GAME,TILE=64;
        let tile=null; for(let r=0;r<22&&!tile;r++)for(let c=0;c<15&&!tile;c++) if(G.buildable(c,r)&&!G.towers.some(t=>t.c===c&&t.r===r)) tile={c,r};
        const sp=G.G3D.project(tile.c*TILE+32, tile.r*TILE+32, 0); G.tap(sp.x,sp.y);})()""")
    pg.wait_for_timeout(250)   # let the RAF frame redraw in build mode
    r8 = pg.evaluate("({buildIdle:__GAME.__trayIsIdle(), buildHeroY:__GAME.__heroBtns[0]?__GAME.__heroBtns[0].y:null})")
    r8["idleHeroY"] = idleHeroY
    print("8 FAB placement:", r8)
    PB = pg.evaluate("__GAME.__lay.PLAY_BOTTOM")
    assert r8["idleHeroY"] >= PB, "idle hero button must sit in the tray"
    assert r8["buildIdle"] is False, "selecting a plot must leave the idle tray state"
    assert r8["buildHeroY"] == idleHeroY, "the hero button must not move when the build panel opens"

    # 9. Live render of the command bar — many frames, no errors
    fresh(pg); deploy(pg)
    pg.evaluate("""(()=>{const G=__GAME; G.S.core=12; G.S.scrap=700;
        for(let c=0;c<15;c++)for(let r=0;r<22;r++){ if(G.towers.length>=3)break; G.build(c,r,'turret'); }
        G.startWave();})()""")
    pg.wait_for_timeout(2200)
    pg.screenshot(path=str(H.scratch() / "v626_intel.png"))
    print("9 live frames ok")

    b.close()

print("\nPAGE ERRORS:", errors)
assert not errors, errors
print("\n=== V6.26 VERIFY PASSED ===")
