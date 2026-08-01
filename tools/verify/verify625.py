"""V6.25 P2+P3 verification: Siege Battery + Prism as real towers —
capstone unlock, gating, combat behaviour (splash/pierce/air/chain), art, SFX, tray fit."""
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
    pg.evaluate("(()=>{const G=__GAME; G.S.endless=false; G.S.campaign=false; G.S.isDaily=false; G.S.isLab=false; G.selectMap(G.S.mapIndex); G.reset(); G.S.screen='playing'; G.render();})()")
    pg.wait_for_timeout(300)

MK = """(o) => Object.assign({type:'raider',alive:true,hp:1e9,maxHp:1e9,shield:0,shieldMax:0,armor:false,
  r:18,pi:0,route:0,slowT:0,slowF:1,frost:0,face:0,bob:0,walk:0,speed:0,flying:false,camo:false,revealed:0,
  slowResist:0,energyResist:0,body:'#888',dark:'#444',eye:'#fff',shape:'raider',flash:0}, o)"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # 1. ROSTER: 7 towers; the two new ones locked on a fresh account
    fresh(pg)
    r = pg.evaluate("""(()=>{const G=__GAME,T=G.Tech; return {
        order:G.__order, n:Object.keys(G.__towers).length,
        siegeLocked:!T.isUnlocked('siege'), prismLocked:!T.isUnlocked('prism'),
        siegeAir:G.__air('lob'), prismAir:G.__air('beam')};})()""") if False else pg.evaluate("""(()=>{const G=__GAME,T=G.Tech;
        return { siegeLocked:!T.isUnlocked('siege'), prismLocked:!T.isUnlocked('prism'), start:[...T.unlockedTowers].sort() };})()""")
    print("1 roster:", r)
    assert r["siegeLocked"] and r["prismLocked"] and r["start"] == ["cryo", "turret"]

    # 2. CAPSTONE UNLOCKS: completing Ordnance grants Siege; completing Arc grants Prism
    r = pg.evaluate("""(()=>{const G=__GAME,T=G.Tech; G.Meta.alloy=99999;
        localStorage.setItem('camp', JSON.stringify(24)); T.recompute();   // V6.35 capstones need campaign progress
        for(let i=0;i<12 && T.owned(0) < 8;i++) T.buy(0);
        const siege=T.isUnlocked('siege');
        for(let i=0;i<12 && T.owned(1) < 8;i++) T.buy(1);
        return {siege, prism:T.isUnlocked('prism'), ordDone:T.owned(0), arcDone:T.owned(1), branches:T.branchesComplete()};})()""")
    print("2 capstones:", r)
    assert r["siege"] and r["prism"] and r["ordDone"] == 8 and r["arcDone"] == 8 and r["branches"] == 2

    # 3. SIEGE combat: ground-only, splash + pierce, big damage on an armored target
    fresh(pg); deploy(pg)
    r = pg.evaluate(f"""(()=>{{const G=__GAME,TILE=64,mk={MK};
        let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,'siege')) t=G.towers[G.towers.length-1];
        const p={{x:t.c*TILE+32,y:t.r*TILE+32}};
        const arm=mk({{x:p.x+70,y:p.y,armor:true}}), near=mk({{x:p.x+82,y:p.y+18,armor:true}});
        const fly=mk({{x:p.x+60,y:p.y-20,flying:true}});
        G.enemies.push(arm,near,fly);
        const h0=arm.hp, n0=near.hp, f0=fly.hp;
        G.sim(40,120);
        return {{armorDmg:h0-arm.hp, splashDmg:n0-near.hp, flyDmg:f0-fly.hp, st:G.tStats(t)}};}})()""")
    print("3 siege combat:", {k: r[k] for k in ("armorDmg", "splashDmg", "flyDmg")})
    assert r["armorDmg"] > 0, "siege must damage its target"
    assert r["splashDmg"] > 0, "siege splash must hit a nearby foe"
    assert r["flyDmg"] == 0, "siege (lob) must NOT hit flyers"
    assert r["st"]["pierce"] is True, "siege must be armor-piercing"

    # 4. PRISM combat: hits air, chains to nearby foes
    fresh(pg); deploy(pg)
    r = pg.evaluate(f"""(()=>{{const G=__GAME,TILE=64,mk={MK};
        let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,'prism')) t=G.towers[G.towers.length-1];
        const p={{x:t.c*TILE+32,y:t.r*TILE+32}};
        const fly=mk({{x:p.x+70,y:p.y,flying:true}});
        const c1=mk({{x:p.x+95,y:p.y+30}}), c2=mk({{x:p.x+120,y:p.y+55}});
        G.enemies.push(fly,c1,c2);
        const f0=fly.hp,a0=c1.hp,b0=c2.hp; G.sim(40,80);
        return {{flyDmg:f0-fly.hp, chain1:a0-c1.hp, chain2:b0-c2.hp}};}})()""")
    print("4 prism combat:", r)
    assert r["flyDmg"] > 0, "prism (beam) must hit flyers"
    assert r["chain1"] > 0 or r["chain2"] > 0, "prism must chain to nearby foes"

    # 5. BRANCHES: both new towers upgrade through a/b + t4 with sane stat progression
    r = pg.evaluate("""(()=>{const G=__GAME, out={};
        for (const ty of ['siege','prism']) { const sp=G.__TOWERS ? G.__TOWERS[ty] : null; }
        const T=(t)=>({l:[0,1,2].map(i=>t.levels[i].dmg), a:t.branches.a.dmg, a4:t.branches.a.t4.dmg, b:t.branches.b.dmg, b4:t.branches.b.t4.dmg});
        return {siege:T(__GAME.tStats && window.__TOWERS_SIEGE || {levels:[{dmg:0}],branches:{a:{dmg:0,t4:{dmg:0}},b:{dmg:0,t4:{dmg:0}}}})};})()""") if False else pg.evaluate("""(()=>{const G=__GAME;
        // drive a real tower through every tier and read tStats at each step
        const res={};
        for (const ty of ['siege','prism']) {
          let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,ty)) t=G.towers[G.towers.length-1];
          const d=[]; t.lvl=0; d.push(G.tStats(t).dmg); t.lvl=1; d.push(G.tStats(t).dmg);
          t.lvl=2; t.branch='a'; d.push(G.tStats(t).dmg); t.lvl=3; d.push(G.tStats(t).dmg);
          t.lvl=2; t.branch='b'; d.push(G.tStats(t).dmg); t.lvl=3; d.push(G.tStats(t).dmg);
          res[ty]=d;
        }
        return res;})()""")
    print("5 branch ladders (L1,L2,a3,a4,b3,b4):", r)
    for ty in ("siege", "prism"):
        d = r[ty]
        assert d[0] < d[1] < d[2] < d[3], f"{ty} branch-a ladder must rise: {d}"
        assert d[4] < d[5] and d[4] > d[1], f"{ty} branch-b ladder must rise: {d}"

    # 6. TRAY FIT: all 7 slots inside the 360px screen, no overlap, locked ones flagged
    fresh(pg); deploy(pg)
    pg.evaluate("__GAME.S.tut = 9")   # past the tutorial, so only RESEARCH gating remains
    tgt = pg.evaluate("""(() => { const G=__GAME,TILE=64;
        for(let r=0;r<22;r++)for(let c=0;c<15;c++) if(G.build(c,r,'turret')){ G.towers.pop(); const sp=G.G3D.project(c*TILE+32,r*TILE+32,0); return {sx:sp.x,sy:sp.y}; } })()""")
    pg.evaluate(f"__GAME.tap({tgt['sx']}, {tgt['sy']})"); pg.wait_for_timeout(150)
    tray = pg.evaluate("""(()=>{const bs=__GAME.buildBtns.filter(x=>x.action==='build');
        const minX=Math.min(...bs.map(b=>b.x)), maxX=Math.max(...bs.map(b=>b.x+b.w));
        // V6.28 made the palette TWO ROWS, so overlap must be checked per row - comparing all
        // seven by x alone falsely flags row 2 against row 1.
        let overlap=false; const rows=[...new Set(bs.map(b=>Math.round(b.y)))];
        for(const ry of rows){ const r=bs.filter(b=>Math.round(b.y)===ry).sort((a,b)=>a.x-b.x);
          for(let i=1;i<r.length;i++) if(r[i].x < r[i-1].x+r[i-1].w-0.01) overlap=true; }
        return {n:bs.length, minX:+minX.toFixed(1), maxX:+maxX.toFixed(1), overlap,
                locked:bs.filter(b=>b.banned).map(b=>b.tower).sort()};})()""")
    print("6 tray:", tray)
    assert tray["n"] == 7, "all 7 towers must have a tray slot"
    assert tray["minX"] >= 0 and tray["maxX"] <= 360, f"tray overflows the 360px screen: {tray}"
    assert not tray["overlap"], "tray slots must not overlap"
    assert tray["locked"] == ["mortar", "prism", "pyre", "siege", "tesla"], tray["locked"]
    pg.screenshot(path="v625_tray.png")

    # 7. ART + SFX: render both new towers at every tier for many frames — no draw/audio errors
    fresh(pg); deploy(pg)
    pg.evaluate("""(()=>{const G=__GAME; let n=0;
        for(let c=0;c<15;c++)for(let r=0;r<22;r++){ if(n>=8)break; const ty=(n%2)?'prism':'siege';
          if(G.build(c,r,ty)){const t=G.towers[G.towers.length-1]; t.lvl=n%4; if(t.lvl>=2)t.branch=(n%2)?'a':'b'; n++;} }
        G.startWave();})()""")
    pg.wait_for_timeout(2500)   # live RAF rendering + firing => art paths and both new SFX exercised
    fired = pg.evaluate("({wave:__GAME.S.wave, kills:__GAME.S.kills, towers:__GAME.towers.length})")
    print("7 art+sfx live frames:", fired)
    assert fired["towers"] == 8
    pg.screenshot(path="v625_field.png")

    # 8. CODEX lists both new towers with their branch names
    pg.evaluate("__GAME.S.screen='howto'; __GAME.S.codexTab='tw'; __GAME.render();"); pg.wait_for_timeout(400)
    cx = pg.evaluate("document.getElementById('overlay').innerHTML")
    for tok in ["Siege Battery", "Prism", "Bombard", "Breaker", "Refraction", "Lance"]:
        assert tok in cx, f"codex missing {tok}"
    print("8 codex ok")

    # 9. FULL-ROSTER WIN still holds (all 7 types, maxed) — no regression in the win path
    fresh(pg); pg.evaluate("__GAME.S.mapIndex=0"); deploy(pg)
    win = pg.evaluate("""(()=>{const G=__GAME; let n=0; const TY=['tesla','mortar','turret','cryo','pyre','siege','prism'];
        for(let c=0;c<15;c++)for(let r=0;r<22;r++) if(G.build(c,r,TY[n%7])){const t=G.towers[G.towers.length-1];t.lvl=3;t.branch=(n%2)?'a':'b';n++;}
        G.S.scrap=0; G.startWave(); return G.sim(50,200000);})()""")
    print("9 full-roster win:", win)
    assert win["screen"] == "victory", win

    b.close()

print("\nPAGE ERRORS:", errors)
assert not errors, errors
print("\n=== V6.25 P2+P3 VERIFY PASSED ===")
