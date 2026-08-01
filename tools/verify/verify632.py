"""C3: every overlay screen is reachable in landscape and on tablets; portrait unchanged."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
from playwright.sync_api import sync_playwright
CHROME = H.chrome()
URL=H.target().as_uri()
SCREENS=["menu","campaign","freeplay","settings","armory","howto","ach","stats","daily","lab","log","intro"]
errors=[]
PROBE="""(()=>{const p=document.querySelector('#overlay .panel');
  if(!p) return {err:'no panel'};
  const btns=[...p.querySelectorAll('button')];
  const pr0=p.getBoundingClientRect();
  const fitsViewport = pr0.top >= -1 && pr0.bottom <= window.innerHeight+1;
  if(!btns.length) return {box:p.clientHeight, content:p.scrollHeight, w:Math.round(pr0.width), btns:0, fitsViewport, lastReachable:true};
  const last=btns[btns.length-1];
  p.scrollTop=p.scrollHeight;
  const pr=p.getBoundingClientRect(), lr=last.getBoundingClientRect();
  return {box:p.clientHeight, content:p.scrollHeight, w:Math.round(pr.width), btns:btns.length,
          fitsViewport, lastReachable: lr.top>=pr.top-1 && lr.bottom<=pr.bottom+1,
          lastText:(last.textContent||'').trim().slice(0,18)};})()"""
def sweep(pg,label):
    print("\n== %s ==" % label)
    bad=[]
    for sc in SCREENS:
        pg.evaluate("__GAME.S.screen='%s'; if(__GAME.S.screen==='intro'){__GAME.S.introCard=0;} __GAME.render();" % sc)
        pg.wait_for_timeout(160)
        r=pg.evaluate(PROBE)
        print("  %-9s %s" % (sc,r))
        if r.get("err"): bad.append((sc,"no panel")); continue
        if not r["fitsViewport"]: bad.append((sc,"panel escapes the viewport"))
        if not r["lastReachable"]: bad.append((sc,"last button unreachable"))
    return bad
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":740,"height":360}); pg.on("pageerror",lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1300)
    pg.evaluate("localStorage.setItem('seenIntro','true')"); pg.reload(); pg.wait_for_timeout(1000)

    bad = sweep(pg,"LANDSCAPE PHONE 740x360")
    land_menu = pg.evaluate("__GAME.S.screen='menu'; __GAME.render(); document.querySelector('#overlay .panel').getBoundingClientRect().width")
    assert land_menu > 560, "landscape panel should widen to trade horizontal space for less scrolling, got %s" % land_menu

    pg.set_viewport_size({"width":360,"height":720}); pg.wait_for_timeout(300)
    bad += sweep(pg,"PORTRAIT PHONE 360x720")
    port_menu = pg.evaluate("__GAME.S.screen='menu'; __GAME.render(); document.querySelector('#overlay .panel').getBoundingClientRect().width")
    assert abs(port_menu-324) < 6, "PORTRAIT PANEL WIDTH CHANGED (expected ~324, got %s)" % port_menu

    pg.set_viewport_size({"width":1280,"height":800}); pg.wait_for_timeout(300)
    bad += sweep(pg,"TABLET LANDSCAPE 1280x800")
    pg.set_viewport_size({"width":800,"height":1280}); pg.wait_for_timeout(300)
    bad += sweep(pg,"TABLET PORTRAIT 800x1280")

    print("\nFAILURES:",bad if bad else "none")
    assert not bad, bad
    b.close()
print("\nPAGE ERRORS:",errors); assert not errors,errors
print("\n=== V6.32 C3 VERIFY PASSED ===")
