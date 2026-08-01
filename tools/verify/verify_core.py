"""Consolidated regression suite — run after EVERY iteration (V5.1+).
Covers: frost on-hit + diminishing stacking, custom difficulty, alloy coupling,
anti-snowball damper, confirm flow, congestion cap, route sims, campaign, daily."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
URL = H.target().as_uri()
errors = []

def fresh(pg):
    # V6.29 added a one-time first-launch briefing gated on seenIntro; this suite tests existing
    # gameplay systems, not onboarding (that's verify629.py), so pre-mark it seen on every "fresh" wipe.
    # V6.38 also made the in-mission tutorial a guided tour whose first card swallows a tap; this
    # suite drives the UI directly, so pre-mark that seen too (onboarding lives in verify629/638).
    pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro', JSON.stringify(true)); localStorage.setItem('tutDone', JSON.stringify(true))")
    pg.reload(); pg.wait_for_timeout(800)

def deploy(pg):
    # V6.6: the old "#p" menu button is gone; start a standard run directly (menu-independent).
    pg.evaluate("(()=>{const G=__GAME; G.S.endless=false; G.S.campaign=false; G.S.isDaily=false; G.S.isLab=false; G.selectMap(G.S.mapIndex); G.reset(); G.S.screen='playing'; G.render();})()")
    pg.wait_for_timeout(300)

MK_ENEMY = """(o) => Object.assign({type:'raider',alive:true,hp:1e9,maxHp:1e9,shield:0,shieldMax:0,armor:false,
  r:18,pi:0,route:0,slowT:0,slowF:1,frost:0,face:0,bob:0,walk:0,speed:100,flying:false,camo:false,revealed:0,
  slowResist:0,energyResist:0,body:'#888',dark:'#444',eye:'#fff',shape:'raider',flash:0}, o)"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # ---------- 1. FROST: on-hit only (no passive aura) + diminishing stack + cinder immune ----------
    fresh(pg); deploy(pg)
    r = pg.evaluate(f"""(() => {{ const G=__GAME, TILE=64, mk={MK_ENEMY};
      let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,'cryo')){{ t=G.towers[0]; t.lvl=2; t.branch='a'; }}
      const p={{x:t.c*TILE+32,y:t.r*TILE+32}};
      const e=mk({{x:p.x+30,y:p.y}}); G.enemies.push(e);
      t.cd=1e9;                       // tower cannot fire -> in range but NO slow may apply
      G.sim(40,25);
      const auraSlow = e.slowT>0 || e.slowF<1;
      t.cd=0; G.sim(40,40);           // let it fire; orb lands -> slow applies
      const hit1 = +e.slowF.toFixed(3);
      return {{ auraSlow, hit1 }}; }})()""")
    print("frost on-hit:", r)
    assert not r["auraSlow"], "enemy was slowed WITHOUT being hit (aura leak)"
    assert 0.34 < r["hit1"] < 0.55, f"single landed Glacier hit should slow to ~0.40, got {r['hit1']}"

    # stacking: 2 glaciers landing on the same foe -> small extra step, still above asymptote
    fresh(pg); deploy(pg)
    r2 = pg.evaluate(f"""(() => {{ const G=__GAME, TILE=64, mk={MK_ENEMY};
      const ts=[]; for(let r=0;r<22&&ts.length<2;r++)for(let c=0;c<15&&ts.length<2;c++) if(G.build(c,r,'cryo')){{ const t=G.towers[G.towers.length-1]; t.lvl=2; t.branch='a'; ts.push(t); }}
      const p={{x:ts[0].c*TILE+32,y:ts[0].r*TILE+32}};
      const e=mk({{x:p.x+30,y:p.y}}); G.enemies.push(e);
      G.sim(40,60);
      const cin=mk({{x:p.x+30,y:p.y,type:'cinder',slowResist:1}}); G.enemies.push(cin);
      G.sim(40,60);
      return {{ two:+e.slowF.toFixed(3), cinder:+cin.slowF.toFixed(3) }}; }})()""")
    print("frost stack + cinder:", r2)
    assert 0.28 <= r2["two"] < r["hit1"], f"2 landing towers should slow a bit more than 1 ({r['hit1']}), got {r2['two']}"
    assert (r["hit1"] - r2["two"]) < 0.12, "2nd tower must only add a LITTLE"
    assert r2["cinder"] == 1.0, "cinder must ignore landed frost"

    # ---------- 2. CUSTOM DIFFICULTY: sliders flow into hp/dmg/core/scrap/alloy ----------
    pg.evaluate("localStorage.clear(); localStorage.setItem('difficulty', JSON.stringify('custom')); localStorage.setItem('seenIntro', JSON.stringify(true)); location.reload()"); pg.wait_for_timeout(800)
    pg.click("#free"); pg.wait_for_timeout(200)
    assert pg.evaluate("!!document.getElementById('cs_hp')"), "custom slider panel missing"
    # slider input handler updates CustomDiff + alloy readout
    pg.evaluate("""(() => { const el=document.getElementById('cs_hp'); el.value=2; el.dispatchEvent(new Event('input')); })()""")
    assert pg.evaluate("__GAME.CustomDiff.get().hp") == 2, "slider input did not persist"
    pg.evaluate("__GAME.CustomDiff.set('scrap',300); __GAME.CustomDiff.set('core',30); __GAME.CustomDiff.set('dmg',2); __GAME.CustomDiff.set('earn',1)")
    pg.screenshot(path="v51_custom_panel.png")
    deploy(pg)
    st = pg.evaluate("({scrap:__GAME.S.scrap, core:__GAME.S.core, alloy:__GAME.diffCfg().alloy})")
    print("custom start state:", st)
    assert st["scrap"] == 300 and st["core"] == 30, "custom scrap/core not applied"
    # hp x2: spawn wave 1, first enemy hp should be 2x the normal-baseline (stalker w1 = 16)
    hp2 = pg.evaluate("(() => { const G=__GAME; G.startWave(); G.sim(40,30); return G.enemies[0] ? G.enemies[0].maxHp : 0; })()")
    print("custom hp x2 -> first spawn maxHp:", hp2); assert hp2 >= 28, f"enemy HP not scaled (got {hp2})"
    # dmg x2: a turret hit should strip 2x base dmg (turret L1 dmg 9 -> 18)
    dmg = pg.evaluate(f"""(() => {{ const G=__GAME, TILE=64, mk={MK_ENEMY};
      G.enemies.length=0; G.S.queue=[];
      let t=null; for(let r=0;r<22&&!t;r++)for(let c=0;c<15&&!t;c++) if(G.build(c,r,'turret')) t=G.towers[G.towers.length-1];
      const e=mk({{x:t.c*TILE+64+32-34,y:t.r*TILE+32}}); G.enemies.push(e);
      const h0=e.hp; G.sim(40,30); return h0-e.hp; }})()""")
    print("custom dmg x2 -> turret hit for:", dmg)
    assert dmg >= 18, f"tower damage slider not applied (expected >=18, got {dmg})"
    # alloy coupling: easy settings -> low multiplier; hard -> high
    am = pg.evaluate("""(() => { const C=__GAME.CustomDiff;
      C.set('hp',0.5);C.set('spd',0.5);C.set('dmg',2);C.set('earn',2);C.set('core',40);C.set('scrap',300); const easy=C.alloyMul();
      C.set('hp',2);C.set('spd',2);C.set('dmg',0.5);C.set('earn',0.5);C.set('core',5);C.set('scrap',75); const hard=C.alloyMul();
      C.set('hp',1);C.set('spd',1);C.set('dmg',1);C.set('earn',1);C.set('core',20);C.set('scrap',150); const base=C.alloyMul();
      return {easy,hard,base}; })()""")
    print("alloy coupling:", am)
    assert am["easy"] <= 0.3 and am["hard"] >= 2.5 and abs(am["base"] - 1) < 0.05, f"alloy scaling wrong: {am}"

    # ---------- 3. ANTI-SNOWBALL: early bonus damped by congestion ----------
    fresh(pg); deploy(pg)
    r3 = pg.evaluate(f"""(() => {{ const G=__GAME, mk={MK_ENEMY};
      G.S.wave=3; G.S.countdown=10; G.S.scrap=0; G.S.core=99999;
      for(let i=0;i<30;i++) G.enemies.push(mk({{x:100,y:100,hp:999,maxHp:999,speed:0}}));
      return null; }})()""")
    pg.wait_for_timeout(120)
    r3 = pg.evaluate("""(() => { const G=__GAME;
      const pre={wave:G.S.wave,scrap:G.S.scrap,cd:G.S.countdown,n:G.enemies.length};
      const btn=G.hudBtns.find(x=>x.id==='nextwave'); if(btn) G.tap(btn.x+btn.w/2,btn.y+btn.h/2);
      return {pre, post:{wave:G.S.wave,scrap:G.S.scrap}}; })()""")
    exp_early = round(r3["pre"]["cd"] * (0.5 + 3 * 0.1) * max(0, 1 - r3["pre"]["n"] / 45))  # V6.10 smaller bonus
    salvage = 20 + 3 * 3
    got = r3["post"]["scrap"] - r3["pre"]["scrap"]
    print(f"anti-snowball: hostiles={r3['pre']['n']} -> early {exp_early} + salvage {salvage}, got {got}")
    assert got == exp_early + salvage, f"damped bonus wrong: got {got}, expected {exp_early+salvage}"
    assert exp_early < 12, "bonus not damped at 30 hostiles"

    # ---------- 4. CONFIRM FLOW: build needs confirm ----------
    fresh(pg); deploy(pg)
    tgt = pg.evaluate("""(() => { const G=__GAME,TILE=64;
      for(let r=0;r<22;r++)for(let c=0;c<15;c++) if(G.build(c,r,'turret')){ G.towers.pop(); const sp=G.G3D.project(c*TILE+32,r*TILE+32,0); return {sx:sp.x,sy:sp.y}; } })()""")
    pg.evaluate(f"__GAME.tap({tgt['sx']}, {tgt['sy']})"); pg.wait_for_timeout(120)
    pg.evaluate("(() => { const b=__GAME.buildBtns.find(x=>x.action==='build'); __GAME.tap(b.x+b.w/2,b.y+b.h/2); })()"); pg.wait_for_timeout(100)
    cf = pg.evaluate("({pending: !!__GAME.S.pending, towers: __GAME.towers.length})")
    assert cf["pending"] and cf["towers"] == 0, "confirm flow broken"
    pg.evaluate("(() => { const b=__GAME.trayBtns.find(x=>x.action==='confirm'); __GAME.tap(b.x+b.w/2,b.y+b.h/2); })()"); pg.wait_for_timeout(100)
    assert pg.evaluate("__GAME.towers.length") == 1, "confirm did not build"
    print("confirm flow ok")

    # ---------- 5. CONGESTION CAP holds auto-launch ----------
    hold = pg.evaluate(f"""(() => {{ const G=__GAME, mk={MK_ENEMY};
      G.S.wave=3; G.S.countdown=5; G.S.core=99999; G.enemies.length=0; G.S.queue=[];
      for(let i=0;i<60;i++) G.enemies.push(mk({{x:100,y:100,hp:999,maxHp:999,speed:0}}));
      const c0=G.S.countdown; G.sim(50,40);
      return {{held: Math.abs(G.S.countdown-c0)<0.001}}; }})()""")
    assert hold["held"], "congestion cap failed"
    print("congestion cap ok")

    # ---------- 6. DAILY determinism + rotation ----------
    fresh(pg)
    dd = pg.evaluate("""(() => { const a=__GAME.dailyConfig(new Date(Date.UTC(2026,0,1))), b=__GAME.dailyConfig(new Date(Date.UTC(2026,0,2)));
      return {m1:a.map,m2:b.map,mod1:!!a.mod}; })()""")
    assert dd["m1"] != dd["m2"] and dd["mod1"], "daily rotation broken"
    print("daily rotation ok")

    # ---------- 7. ROUTE SIM + VICTORY + CAMPAIGN regressions ----------
    fresh(pg); pg.evaluate("__GAME.S.mapIndex=0"); deploy(pg)
    lose = pg.evaluate("(()=>{__GAME.startWave();return __GAME.sim(50,200000);})()")
    assert lose["screen"] == "gameover", lose
    print("no-tower -> gameover ok")
    fresh(pg); pg.evaluate("__GAME.S.mapIndex=0"); deploy(pg)
    win = pg.evaluate("""(()=>{const G=__GAME; let n=0; for(let c=0;c<15;c++)for(let r=0;r<22;r++) if(G.build(c,r,['tesla','mortar','turret','cryo','pyre'][n%5])){const t=G.towers[G.towers.length-1];t.lvl=3;t.branch=(n%2)?'a':'b';n++;} G.S.scrap=0; G.startWave(); return G.sim(50,200000);})()""")
    assert win["screen"] == "victory", win
    print("maxed diverse -> victory ok")

    # V5.4: wave 1 waits for manual deploy (no auto-launch)
    fresh(pg); pg.evaluate("__GAME.S.mapIndex=0"); deploy(pg)
    w1 = pg.evaluate("({cd:__GAME.S.countdown, wave:__GAME.S.wave})")
    idle = pg.evaluate("(()=>{__GAME.sim(50,200); return {wave:__GAME.S.wave, screen:__GAME.S.screen};})()")
    print("wave-1 manual: at start", w1, "after 10s idle", idle)
    assert w1["cd"] == 0 and w1["wave"] == 0, "wave 1 should idle at countdown 0"
    assert idle["wave"] == 0 and idle["screen"] == "playing", "wave 1 auto-launched (should wait for deploy)"
    started = pg.evaluate("(()=>{const b=__GAME.hudBtns.find(x=>x.id==='nextwave'); __GAME.tap(b.x+b.w/2,b.y+b.h/2); return {wave:__GAME.S.wave, cd:Math.round(__GAME.S.countdown)};})()")
    print("after manual deploy:", started); assert started["wave"] == 1 and started["cd"] > 6, "manual deploy should start wave 1 + arm timer"
    fresh(pg); pg.click("#cp"); pg.wait_for_timeout(150)   # V6.7: cp opens the campaign screen
    assert pg.evaluate("__GAME.S.screen") == "campaign", "cp should open campaign screen"
    pg.click("#cgo"); pg.wait_for_timeout(200)             # deploy the selected mission
    assert pg.evaluate("({m:__GAME.S.mapIndex,c:__GAME.S.campaign,s:__GAME.S.screen})") == {"m":0,"c":True,"s":"playing"}
    print("campaign ok")

    b.close()

print("\nPAGE ERRORS:", errors)
assert not errors, errors
print("\n=== CORE REGRESSION SUITE PASSED ===")
