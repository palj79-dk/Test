"""V6.35: capstone campaign gate + coverage reshape (damage intact)."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright
CHROME = H.chrome()
URL=H.target().as_uri()
errors=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":360,"height":720}); pg.on("pageerror",lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1300)
    pg.evaluate("localStorage.setItem('seenIntro','true')"); pg.reload(); pg.wait_for_timeout(900)

    # 1. DAMAGE IS UNCHANGED - this fix must not weaken the late brutal maps
    r=pg.evaluate("""(()=>{const T=__GAME.__TOWERS||null; const G=__GAME;
        const grab=(ty)=>{let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,ty)) t=G.towers[G.towers.length-1];
          const out={}; t.lvl=0; out.l1=G.tStats(t).dmg; t.lvl=2; t.branch='a'; out.a=G.tStats(t).dmg;
          t.lvl=3; out.a4=G.tStats(t).dmg; t.lvl=2; t.branch='b'; out.b=G.tStats(t).dmg; t.lvl=3; out.b4=G.tStats(t).dmg;
          t.lvl=0; t.branch=null; out.rng1=G.tStats(t).range; t.lvl=2; t.branch='a'; out.rngA=G.tStats(t).range;
          t.lvl=3; out.rngA4=G.tStats(t).range; out.splA4=G.tStats(t).splash||0;
          G.towers.length=0; return out;};
        G.S.mapIndex=0; G.selectMap(0); G.reset(); G.S.screen='playing'; G.S.tut=9;
        G.Meta.alloy=999999; G.Tech.research={ord:8,arc:8}; G.Tech.recompute();
        return {siege:grab('siege'), prism:grab('prism')};})()""")
    print("1 siege:",r["siege"]); print("1 prism:",r["prism"])
    assert r["siege"]["a4"]==340 and r["siege"]["b4"]==760, "SIEGE DAMAGE MUST BE UNCHANGED"
    assert r["prism"]["a4"]==190 and r["prism"]["b4"]==470, "PRISM DAMAGE MUST BE UNCHANGED"
    # coverage cut
    assert r["siege"]["rng1"]==148 and r["siege"]["rngA4"]==190, "siege range should be cut"
    assert r["siege"]["splA4"]==118, "siege splash should be cut"
    assert r["prism"]["rng1"]==202 and r["prism"]["rngA4"]==256, "prism range should be cut"

    # 2. CAMPAIGN GATE: capstone unbuyable before mission 12 even with infinite alloy
    pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true')"); pg.reload(); pg.wait_for_timeout(900)
    g=pg.evaluate("""(()=>{const G=__GAME, T=G.Tech;
        G.Meta.alloy=999999; localStorage.setItem('camp', JSON.stringify(3));
        T.research={ord:7, arc:7}; T.recompute();
        const blkO=T.blockedBy(0), blkA=T.blockedBy(1);
        const boughtO=T.buy(0), boughtA=T.buy(1);
        return {blkO, blkA, boughtO, boughtA, siege:T.isUnlocked('siege'), prism:T.isUnlocked('prism')};})()""")
    print("2 gated at camp 3:",g)
    assert g["blkO"] and "12" in g["blkO"], "ordnance capstone must report the mission requirement"
    assert g["boughtO"] is False and g["boughtA"] is False, "capstones must be unbuyable before mission 12"
    assert not g["siege"] and not g["prism"], "capstone towers must stay locked"

    # 3. and buyable once the campaign requirement is met
    o=pg.evaluate("""(()=>{const G=__GAME, T=G.Tech;
        localStorage.setItem('camp', JSON.stringify(12)); G.Meta.alloy=999999;
        T.research={ord:7, arc:7}; T.recompute();
        const blk=T.blockedBy(0), ok=T.buy(0) && T.buy(1);
        return {blk, ok, siege:T.isUnlocked('siege'), prism:T.isUnlocked('prism')};})()""")
    print("3 at camp 12:",o)
    assert o["blk"] is None and o["ok"] and o["siege"] and o["prism"], "capstones must unlock at mission 12"

    # 4. the run-end nudge must not advertise a gated node
    n=pg.evaluate("""(()=>{const G=__GAME;
        localStorage.setItem('camp', JSON.stringify(2)); G.Meta.alloy=999999;
        G.Tech.research={ord:7, arc:7}; G.Tech.recompute();
        const c=G.__cheapestAffordable ? G.__cheapestAffordable() : null;
        return {name: c ? c.node.name : null};})()""")
    print("4 nudge at camp 2:",n)
    assert n["name"] not in ("Siege Battery","Prism"), "the nudge must never advertise a gated capstone"

    # 5. Armory UI shows the lock instead of a dead button
    pg.evaluate("""(()=>{const G=__GAME; localStorage.setItem('camp', JSON.stringify(2));
        G.Meta.alloy=999999; G.Tech.research={ord:7,arc:7}; G.Tech.recompute();
        G.S.screen='armory'; G.S.armBranch=0; G.render();})()""")
    pg.wait_for_timeout(250)
    html=pg.evaluate("document.getElementById('overlay').innerHTML")
    assert "MISSION 12 REQUIRED" in html, "armory must show the campaign requirement"
    assert 'id="rb_0"' not in html, "gated capstone must not render a RESEARCH button"
    print("5 armory shows the gate")
    b.close()
print("\nPAGE ERRORS:",errors); assert not errors,errors
print("\n=== V6.35 VERIFY PASSED ===")
