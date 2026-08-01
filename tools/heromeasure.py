"""B.2 — how much does the Commander actually contribute?

Four conditions per (map, difficulty), same auto-player, same build order:
  none  : no hero, no Command nodes
  hero  : hero deployed, no Command nodes
  cmd   : hero deployed + all 8 Command nodes bought
  ord   : no hero, the same Alloy spent in Ordnance instead

Reports paper-DPS share (hero DPS vs summed tower DPS) and outcome (wave, core, kills).
"""
import pathlib
import statistics
import sys
from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
URL = pathlib.Path("/home/user/Test/fallengrid-v6.40.html").as_uri()

# Auto-player: build a ring of towers along the route, upgrade, push waves at a sane pace.
AUTOPLAY = """
([mapIdx, diff, mode]) => {
  const G = __GAME, S = G.S, TILE = 64;
  const COST = { turret:50, cryo:65, mortar:85, tesla:95, pyre:80 };
  const seq = ['tesla','tesla','cryo','tesla','mortar','turret'];

  G.startWave();
  // Plot discovery from the map itself, not from where enemies happened to walk in 5 seconds.
  // A tile is road if it is un-buildable and not an obstacle; candidates are buildable tiles
  // touching road, ranked by how much road they cover.
  const blocked = G.blocked;
  const isRoad = (c,r) => !G.buildable(c,r) && !blocked.has(c+','+r) && !G.towers.some(t=>t.c===c&&t.r===r);
  const cand = [];
  for (let r=0;r<40;r++) for (let c=0;c<40;c++) {
    if (!G.buildable(c,r)) continue;
    let touch = 0;
    for (const [dc,dr] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]]) if (isRoad(c+dc,r+dr)) touch++;
    if (touch) cand.push([c,r,touch]);
  }
  cand.sort((a,b)=>b[2]-a[2]);
  if (!cand.length) return { screen:'nocand', wave:0, coreEnd:0, coreMax:0, worst:0, kills:0, towers:0,
                             heroLvl:0, towerDps:0, heroDps:0, pulseDps:0, pulses:0, cand:0 };

  // the Commander goes on the first free plot, same spot every condition
  if (mode === 'hero' || mode === 'cmd') { for (const [c,r] of cand) { if (G.buildable(c,r)) { G.deployHero(c,r); break; } } }

  let ti=0;
  const bOf = (t) => t.type==='cryo' ? 'a' : 'b';
  const tryBuild = () => { for(const [c,r] of cand){ const tp=seq[ti%seq.length];
      if(S.scrap>=COST[tp] && G.build(c,r,tp)){ S.scrap-=COST[tp]; ti++; return true; } } return false; };
  const upCost = (t) => t.lvl===0 ? 60 : t.lvl===1 ? 100 : 170;
  const tryUp = () => { for(const t of G.towers){ if(t.lvl>=3) continue; const c=upCost(t);
      if(S.scrap>=c){ S.scrap-=c; if(t.lvl===1){ t.lvl=2; t.branch=bOf(t); } else t.lvl++; return true; } } return false; };
  for(let i=0;i<6;i++) tryBuild();

  let worst = S.core, guard = 0;
  const pulses = [];
  while(S.screen==='playing' && guard++ < 5000){
    let acted = true; while(acted && S.scrap > 0){ acted = tryUp() || tryBuild(); }
    if (G.hero && G.hero.abil <= 0 && G.enemies.length > 3) { G.doPulse(); pulses.push(S.wave); }
    if(S.wave < 20 && S.countdown > 0 && G.enemies.length < 35){ G.startWave(); }
    G.sim(50, 20);
    worst = Math.min(worst, S.core);
    if(S.wave >= 20 && G.enemies.length === 0 && S.queue.length === 0) break;
  }

  // paper DPS: hero vs the whole tower line, using the game's own stat resolvers
  let towerDps = 0;
  for (const t of G.towers) { const st = G.tStats(t); if (st && st.dmg && st.rate) towerDps += st.dmg * 1000 / st.rate; }
  // hero paper DPS from the same tables the game uses (HERO levels + Tech bonuses)
  const LV = [{dmg:22,rate:440,pdmg:60},{dmg:30,rate:415,pdmg:92},{dmg:41,rate:390,pdmg:130},
              {dmg:55,rate:365,pdmg:180},{dmg:74,rate:340,pdmg:250}];
  const B = G.Tech.bonus || {};
  const h = G.hero;
  const hs = h ? LV[h.lvl] : null;
  const dmgMul = 1 + (B.hero || 0), rateMul = 1 - (B.hrate || 0), abilCd = 16 - (B.pulse || 0);
  const heroDps = h ? (hs.dmg * dmgMul) * 1000 / (hs.rate * rateMul) : 0;
  const pulseDps = h ? (hs.pdmg * dmgMul) / abilCd : 0;

  return { screen:S.screen, wave:S.wave, coreEnd:S.core, coreMax:S.coreMax, worst, kills:S.kills,
           towers:G.towers.length, heroLvl: h ? h.lvl+1 : 0,
           towerDps:+towerDps.toFixed(1), heroDps:+heroDps.toFixed(1), pulseDps:+pulseDps.toFixed(1),
           pulses: pulses.length, cand: cand.length };
}
"""

MAPS = [0, 5, 9, 16, 24]
DIFFS = ["hard", "brutal"]
MODES = ["none", "hero", "cmd", "ord"]


def main():
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": 360, "height": 720})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL)
        pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
        pg.wait_for_timeout(900)

        for mi in MAPS:
            for diff in DIFFS:
                for mode in MODES:
                    pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24');")
                    pg.reload()
                    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
                    pg.wait_for_timeout(500)
                    spend = pg.evaluate("""([mode]) => {
                      const G = __GAME, T = G.Tech;
                      G.Meta.alloy = 999999; G.Meta.save();
                      // every condition owns the three unconditional branches in full
                      let spent = 0;
                      for (const bi of [0,1,2]) { let g=0; while (T.buy(bi) && g++ < 20) {} }
                      const before = G.Meta.alloy;
                      if (mode === 'cmd') { let g=0; while (T.buy(3) && g++ < 20) {} }
                      spent = before - G.Meta.alloy;
                      return { spent, owned: [0,1,2,3].map(i => T.owned(i)) };
                    }""", [mode])
                    pg.evaluate("""([mi, diff]) => {
                      const G = __GAME, S = G.S;
                      S.endless=false; S.campaign=false; S.isDaily=false; S.isLab=false;
                      S.difficulty = diff; S.mapIndex = mi; G.selectMap(mi); G.reset(); S.screen='playing'; S.tut=-1;
                    }""", [mi, diff])
                    r = pg.evaluate(AUTOPLAY, [mi, diff, mode])
                    r.update(map=mi, diff=diff, mode=mode, cmdSpent=spend["spent"], owned=spend["owned"])
                    rows.append(r)
                    print("map%-3d %-7s %-5s wave=%-3d core=%2d/%-2d worst=%-3d kills=%-4d towers=%-3d "
                          "heroL=%d heroDps=%-6.1f pulse=%-5.1f towerDps=%-7.1f %s"
                          % (mi, diff, mode, r["wave"], r["coreEnd"], r["coreMax"], r["worst"], r["kills"],
                             r["towers"], r["heroLvl"], r["heroDps"], r["pulseDps"], r["towerDps"], r["screen"]))
        b.close()
    if errs:
        print("\nPAGE ERRORS:", errs[:5])

    print("\n" + "=" * 96)
    print("%-8s %8s %8s %8s %8s %10s" % ("mode", "wins", "avg wave", "avg core", "avg worst", "hero DPS %"))
    for mode in MODES:
        sub = [r for r in rows if r["mode"] == mode]
        if not sub:
            continue
        wins = sum(1 for r in sub if r["screen"] == "victory")
        share = [100.0 * (r["heroDps"] + r["pulseDps"]) / max(1e-9, r["towerDps"] + r["heroDps"] + r["pulseDps"]) for r in sub]
        print("%-8s %5d/%-2d %8.1f %8.1f %8.1f %9.1f%%" % (
            mode, wins, len(sub),
            statistics.mean(r["wave"] for r in sub),
            statistics.mean(r["coreEnd"] for r in sub),
            statistics.mean(r["worst"] for r in sub),
            statistics.mean(share)))
    return rows


if __name__ == "__main__":
    main()
