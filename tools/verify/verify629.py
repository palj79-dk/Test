"""V6.29 Onboarding: B0 post-run Armory nudge, B1 first-launch briefing, B2 hero/strike TIPS."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
URL = H.target().as_uri()
errors = []

MK_ENEMY = """(o) => Object.assign({type:'raider',alive:true,hp:1e9,maxHp:1e9,shield:0,shieldMax:0,armor:false,
  r:18,pi:0,route:0,slowT:0,slowF:1,frost:0,face:0,bob:0,walk:0,speed:100,flying:false,camo:false,revealed:0,
  slowResist:0,energyResist:0,body:'#888',dark:'#444',eye:'#fff',shape:'raider',flash:0}, o)"""

def fresh(pg, seen_intro=True):
    # a truly blank account, optionally pre-marked as having seen the briefing (used by tests that
    # are not exercising the briefing itself, so the menu/screens they need are reachable directly)
    seed = "localStorage.setItem('seenIntro', JSON.stringify(true));" if seen_intro else ""
    pg.evaluate(f"localStorage.clear(); {seed}")
    pg.reload(); pg.wait_for_timeout(800)

def deploy(pg):
    pg.evaluate("""(()=>{const G=__GAME; G.S.endless=false; G.S.campaign=false; G.S.isDaily=false;
        G.S.isLab=false; G.selectMap(G.S.mapIndex); G.reset(); G.S.screen='playing'; G.S.tut=-1; G.render();})()""")
    pg.wait_for_timeout(200)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # ---------- 1. Fresh account -> briefing shows; SKIP dismisses it and it never returns ----------
    fresh(pg, seen_intro=False)
    scr = pg.evaluate("__GAME.S.screen")
    html = pg.evaluate("document.getElementById('overlay').innerHTML")
    print("1a fresh screen:", scr)
    assert scr == "intro", f"fresh account should land on the briefing, got {scr}"
    assert "BRIEFING 1/4" in html and "THE GRID HAS FALLEN" in html, "card 1 (the world) missing/wrong"
    assert 'id="sk"' in html and "SKIP" in html, "SKIP control missing"
    assert 'id="nx"' in html and "NEXT" in html, "card 1 should offer NEXT, not BEGIN"
    pg.click("#sk"); pg.wait_for_timeout(150)
    seen = pg.evaluate("localStorage.getItem('seenIntro')")
    scr2 = pg.evaluate("__GAME.S.screen")
    print("1b after SKIP:", {"seenIntro": seen, "screen": scr2})
    assert seen == "true", "SKIP must persist seenIntro"
    assert scr2 == "menu", "SKIP (from boot) should land on the main menu"
    pg.reload(); pg.wait_for_timeout(800)
    scr3 = pg.evaluate("__GAME.S.screen")
    html3 = pg.evaluate("document.getElementById('overlay').innerHTML")
    print("1c after reload:", scr3)
    assert scr3 == "menu" and "BRIEFING" not in html3, "briefing must not reappear after SKIP+reload"
    print("test 1 (skip, one-time) PASSED")

    # ---------- 2. Fresh account -> click through all 4 cards to BEGIN; also gated after reload ----------
    fresh(pg, seen_intro=False)
    assert pg.evaluate("__GAME.S.screen") == "intro"
    pg.click("#nx"); pg.wait_for_timeout(120)
    h2 = pg.evaluate("document.getElementById('overlay').innerHTML")
    assert "BRIEFING 2/4" in h2 and "HOLD THE LINE" in h2, "card 2 (stakes) missing/wrong"
    pg.click("#nx"); pg.wait_for_timeout(120)
    h3 = pg.evaluate("document.getElementById('overlay').innerHTML")
    assert "BRIEFING 3/4" in h3 and "YOUR EDGE" in h3, "card 3 (currencies) missing/wrong"
    assert "Scrap" in h3 and "Alloy" in h3 and "Armory" in h3, "card 3 must name Scrap/Alloy/Armory"
    assert "Auto-Gun" in h3 and "Cryo" in h3, "card 3 must explain the starting-tower gate"
    pg.click("#nx"); pg.wait_for_timeout(120)
    # V6.38 card 4: a labelled wireframe of the real screen
    h4 = pg.evaluate("document.getElementById('overlay').innerHTML")
    assert "BRIEFING 4/4" in h4 and "YOUR SCREEN" in h4, "card 4 (screen anatomy) missing/wrong"
    for tok in ("SCRAP", "CORE", "BATTLEFIELD", "WAVE INTEL", "PULSE", "STRIKE"):
        assert tok in h4, f"anatomy card must label {tok}"
    assert 'id="nx"' in h4 and "BEGIN" in h4, "last card must offer BEGIN"
    h3 = h4
    pg.click("#nx"); pg.wait_for_timeout(150)
    st2 = pg.evaluate("({seen:localStorage.getItem('seenIntro'), screen:__GAME.S.screen, camp:__GAME.S.campaign, map:__GAME.S.mapIndex})")
    print("2 after BEGIN:", st2)
    # BEGIN deploys straight into campaign Mission 1 (per PLAN-feedback.md iteration B1)
    assert st2["seen"] == "true", "BEGIN must persist seenIntro"
    assert st2["screen"] == "playing" and st2["camp"] is True and st2["map"] == 0, \
        "BEGIN must deploy into campaign Mission 1"
    pg.reload(); pg.wait_for_timeout(800)
    assert pg.evaluate("__GAME.S.screen") == "menu", "briefing must not reappear after BEGIN+reload"
    print("test 2 (begin -> Mission 1) PASSED")

    # ---------- 2b. SKIP goes to the menu instead, and back-button dismisses ----------
    fresh(pg, seen_intro=False)
    assert pg.evaluate("__GAME.S.screen") == "intro"
    pg.click("#sk"); pg.wait_for_timeout(150)
    sk = pg.evaluate("({seen:localStorage.getItem('seenIntro'), screen:__GAME.S.screen})")
    print("2b after SKIP:", sk)
    assert sk["seen"] == "true" and sk["screen"] == "menu", "SKIP must end the briefing at the menu"
    fresh(pg, seen_intro=False)
    bk = pg.evaluate("({handled:__GAME.onBack(), screen:__GAME.S.screen})")
    print("2b back-button on intro:", bk)
    assert bk["handled"] is True and bk["screen"] == "menu", \
        "back must dismiss the briefing and be handled (never fall through and exit the app)"
    print("test 2b (skip + back) PASSED")

    # ---------- 3. Codex re-entry ----------
    fresh(pg, seen_intro=True)
    pg.click("#h"); pg.wait_for_timeout(150)
    assert pg.evaluate("__GAME.S.screen") == "howto", "Codex button should open howto"
    hc = pg.evaluate("document.getElementById('overlay').innerHTML")
    assert 'id="brief"' in hc and "Replay Briefing" in hc, "Codex must offer a briefing re-entry point"
    pg.click("#brief"); pg.wait_for_timeout(150)
    hb = pg.evaluate("document.getElementById('overlay').innerHTML")
    assert pg.evaluate("__GAME.S.screen") == "intro" and "BRIEFING 1/4" in hb, "Replay Briefing must reopen card 1"
    pg.click("#sk"); pg.wait_for_timeout(150)
    assert pg.evaluate("__GAME.S.screen") == "howto", "SKIP from the Codex re-entry should return to the Codex"
    print("test 3 (codex re-entry) PASSED")

    # ---------- 4. Run-end nudge: earned + unspent alloy, and names an affordable node ----------
    fresh(pg, seen_intro=True)
    r4 = pg.evaluate("""(()=>{const G=__GAME;
        G.Meta.alloy = 5000; G.Meta.save();
        G.S.lastAlloy = 561; G.S.wave = 7; G.S.kills = 42; G.S.endless=false; G.S.campaign=false;
        G.S.newAch = []; G.S.medalMsg = ""; G.S.achChecked = true;
        G.S.screen = 'gameover'; G.render();
        return document.getElementById('overlay').innerHTML; })()""")
    print("4a gameover with affordable research: contains EARNED/UNSPENT/READY?",
          "561" in r4 and "ALLOY EARNED" in r4 and "UNSPENT" in r4 and "READY TO RESEARCH" in r4)
    assert "+561" in r4 and "ALLOY EARNED" in r4, "earned amount must be prominent"
    assert "5000 UNSPENT" in r4, "unspent wallet total must be shown"
    assert "READY TO RESEARCH" in r4, "an affordable node must be named when the wallet can afford one"
    assert 'id="a"' in r4 and 'class="btn primary" id="a"' in r4, "Armory must be the primary action when research is affordable"
    assert 'id="r"' in r4 and 'class="btn " id="r"' in r4, "Redeploy must be demoted when Armory is primary"

    r4b = pg.evaluate("""(()=>{const G=__GAME;
        G.Meta.alloy = 0; G.Meta.save();
        G.S.lastAlloy = 30; G.S.screen = 'gameover'; G.render();
        return document.getElementById('overlay').innerHTML; })()""")
    print("4b gameover with 0 alloy: no nudge present?", "READY TO RESEARCH" not in r4b)
    assert "READY TO RESEARCH" not in r4b, "must not invent a nudge when nothing is affordable"
    assert 'class="btn primary" id="r"' in r4b, "Redeploy stays primary when there is nothing to research"

    # same check on the victory screen
    r4c = pg.evaluate("""(()=>{const G=__GAME;
        G.Meta.alloy = 5000; G.Meta.save(); G.S.lastAlloy = 200; G.S.campaign=false; G.S.isDaily=false;
        G.S.newAch = []; G.S.medalMsg = ""; G.S.wave = 20; G.S.kills = 80;
        G.S.screen = 'victory'; G.render();
        return document.getElementById('overlay').innerHTML; })()""")
    assert "+200" in r4c and "ALLOY EARNED" in r4c and "5000 UNSPENT" in r4c, "victory screen missing earned/unspent"
    assert "READY TO RESEARCH" in r4c and 'class="btn primary" id="a"' in r4c, "victory screen must also promote Armory"
    print("test 4 (run-end nudge) PASSED")

    # ---------- 5. Main menu Armory badge ----------
    fresh(pg, seen_intro=True)
    m1 = pg.evaluate("""(()=>{const G=__GAME; G.Meta.alloy=5000; G.Meta.save(); G.S.screen='menu'; G.render();
        return document.getElementById('overlay').innerHTML;})()""")
    m0 = pg.evaluate("""(()=>{const G=__GAME; G.Meta.alloy=0; G.Meta.save(); G.S.screen='menu'; G.render();
        return document.getElementById('overlay').innerHTML;})()""")
    print("5 menu badge: shown-when-affordable?", "●" in m1, "hidden-when-not?", "●" not in m0)
    assert "●" in m1, "Armory badge must appear on the menu when research is affordable"
    assert "●" not in m0, "Armory badge must NOT appear when nothing is affordable"
    print("test 5 (menu armory badge) PASSED")

    # ---------- 6. Hero tip: fires at wave 2 if the Hero has not been deployed ----------
    fresh(pg, seen_intro=True); deploy(pg)
    pg.evaluate("__GAME.startWave()"); pg.wait_for_timeout(250)   # wave 1
    pg.evaluate("__GAME.startWave()"); pg.wait_for_timeout(300)   # wave 2 -> should queue 'hero'
    seenTips = pg.evaluate("JSON.parse(localStorage.getItem('seenTips')||'{}')")
    print("6a hero tip after wave2 (no hero deployed):", seenTips)
    assert seenTips.get("hero") == 1, "hero tip must fire once the Hero has still not been used by wave 2"

    # negative: if the Hero was already deployed, the tip must not fire
    fresh(pg, seen_intro=True); deploy(pg)
    pg.evaluate("__GAME.deployHero(2,2)")
    pg.evaluate("__GAME.startWave()"); pg.wait_for_timeout(250)
    pg.evaluate("__GAME.startWave()"); pg.wait_for_timeout(300)
    seenTips2 = pg.evaluate("JSON.parse(localStorage.getItem('seenTips')||'{}')")
    print("6b hero tip suppressed when hero already deployed:", seenTips2)
    assert not seenTips2.get("hero"), "hero tip must NOT fire if the Hero is already deployed this run"
    print("test 6 (hero tip) PASSED")

    # ---------- 7. Strike tip: fires the first time it's ready with enemies on the field ----------
    fresh(pg, seen_intro=True); deploy(pg)
    pg.evaluate(f"(()=>{{const mk={MK_ENEMY}; __GAME.enemies.push(mk({{x:100,y:100}}));}})()")
    pg.wait_for_timeout(300)
    seenTips3 = pg.evaluate("JSON.parse(localStorage.getItem('seenTips')||'{}')")
    print("7a strike tip with enemies on field, unused:", seenTips3)
    assert seenTips3.get("strike") == 1, "strike tip must fire once ready with enemies on the field"

    # negative: if the strike was already used this run, the tip must not fire
    fresh(pg, seen_intro=True); deploy(pg)
    pg.evaluate("__GAME.S.usedStrike = true")
    pg.evaluate(f"(()=>{{const mk={MK_ENEMY}; __GAME.enemies.push(mk({{x:100,y:100}}));}})()")
    pg.wait_for_timeout(300)
    seenTips4 = pg.evaluate("JSON.parse(localStorage.getItem('seenTips')||'{}')")
    print("7b strike tip suppressed when already used:", seenTips4)
    assert not seenTips4.get("strike"), "strike tip must NOT fire if the strike was already used this run"
    print("test 7 (strike tip) PASSED")

    pg.screenshot(path=str(H.scratch() / "v629_scratch.png"))
    b.close()

print("\nPAGE ERRORS:", errors)
assert not errors, errors
print("\n=== V6.29 ONBOARDING VERIFY PASSED ===")
