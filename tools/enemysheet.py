"""Render every enemy at an identical camera and measure how confusable they are as thumbnails."""
import sys, itertools, math
from playwright.sync_api import sync_playwright
from PIL import Image
CHROME="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
URL, OUTDIR, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
E = ['stalker','raider','brute','sentinel','wraith','warden','mender','splitter','phantom','cinder','insulator','juggernaut']
MK = """(o) => Object.assign({type:'raider',alive:true,hp:1e9,maxHp:1e9,shield:0,shieldMax:0,armor:false,
  r:18,pi:0,route:0,slowT:0,slowF:1,frost:0,face:0,bob:0,walk:0,speed:0,flying:false,camo:false,revealed:9,
  slowResist:0,energyResist:0,body:'#888',dark:'#444',eye:'#fff',shape:'raider',flash:0}, o)"""
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
    # match the viewport to the layout the game picks, so page coords == layout coords
    pg=b.new_page(viewport={"width":360,"height":720}, device_scale_factor=3)
    pg.on("pageerror", lambda e: print("PAGEERROR",e))
    pg.goto(URL); pg.wait_for_function("window.__GAME !== undefined",timeout=30000)
    pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24')")
    pg.reload(); pg.wait_for_function("window.__GAME !== undefined",timeout=30000); pg.wait_for_timeout(800)
    pg.evaluate("""()=>{const G=__GAME; G.S.endless=false;G.S.campaign=false;G.S.isDaily=false;G.S.isLab=false;
      G.S.mapIndex=0;G.selectMap(0);G.reset();G.S.screen='playing';G.S.tut=-1;}""")
    pg.wait_for_timeout(400)
    # a reference frame with no enemy, so each subject can be masked off the background
    pg.evaluate("""()=>{const G=__GAME,l=G.__lay; G.fitCamera();
      const mid=G.screenToWorld(l.W/2,(l.PLAY_TOP+l.PLAY_BOTTOM)/2);
      G.enemies.length=0; G.S.tip=null; G.S.tipQ=[]; G.S.usedStrike=true;
      G.cam.x=mid.x;G.cam.y=mid.y;G.cam.zoom=3.0;G.render(); window.__MID=mid;}""")
    pg.wait_for_timeout(420)
    _ref = pg.evaluate("""()=>{const G=__GAME,l=G.__lay,p=G.worldToScreen(window.__MID.x,window.__MID.y);
      return {x:p.x,y:p.y,W:l.W,H:l.H,top:l.PLAY_TOP,bot:l.PLAY_BOTTOM};}""")
    _h=78
    _rx=int(max(0,min(_ref["W"]-_h*2,_ref["x"]-_h))); _ry=int(max(_ref["top"]+6,min(_ref["H"]-_h*2,_ref["y"]-_h*1.32)))
    REFP="%s/enemy_%s_REF.png"%(OUTDIR,TAG)
    pg.screenshot(path=REFP, clip={"x":_rx,"y":_ry,"width":_h*2,"height":_h*2})
    tiles=[]
    for tp in E:
        pos = pg.evaluate("""([tp,mk])=>{const G=__GAME,f=eval('('+mk+')');
          const src=(G.__ENEMIES&&G.__ENEMIES[tp])||null;
          const l=G.__lay;
          // A world point guaranteed to be inside the view: whatever is under the middle of the
          // play area after a fit. Placing the subject there means the camera never has to travel.
          G.fitCamera();
          const mid=G.screenToWorld(l.W/2,(l.PLAY_TOP+l.PLAY_BOTTOM)/2);
          G.enemies.length=0;
          G.enemies.push(f({type:tp, shape:(src&&src.shape)||'raider', body:(src&&src.body)||'#888',
            dark:(src&&src.dark)||'#444', eye:(src&&src.eye)||'#fff', r:(src&&src.r)||18,
            flying:tp==='wraith', camo:false, x:mid.x, y:mid.y,
            shield:tp==='warden'?60:tp==='juggernaut'?420:0, shieldMax:tp==='warden'?60:tp==='juggernaut'?420:0,
            armor:tp==='sentinel'}));
          // drive the camera straight at it instead of iterating zoomAt, which drifts
          G.cam.x=mid.x; G.cam.y=mid.y; G.cam.zoom=3.0; G.render();
          return {mx:mid.x,my:mid.y};
        }""", [tp, MK])
        pg.wait_for_timeout(420)
        # read the projection *after* the RAF loop has applied clampCam, or it reports where the
        # camera was asked to go rather than where it ended up
        pos = pg.evaluate("""([mx,my])=>{const G=__GAME,l=G.__lay;const p=G.worldToScreen(mx,my);
          return {x:p.x,y:p.y,W:l.W,H:l.H,top:l.PLAY_TOP,bot:l.PLAY_BOTTOM,zoom:G.cam.zoom};}""",
          [pos["mx"], pos["my"]])
        sc, half = 1, 78    # Playwright clip is in CSS px, not device px
        cx, cy = pos["x"]*sc, pos["y"]*sc
        W, H = pos["W"]*sc, pos["H"]*sc
        if not (0 <= cx <= W and 0 <= cy <= H):
            print("  !! %s projected off-screen at (%.0f,%.0f) in %dx%d" % (tp, cx, cy, W, H))
        x = int(max(0, min(W-half*2, cx-half))); y = int(max(pos["top"] + 6, min(H - half * 2, cy - half * 1.32)))
        p = "%s/enemy_%s_%s.png" % (OUTDIR, TAG, tp)
        pg.screenshot(path=p, clip={"x":x,"y":y,"width":half*2,"height":half*2})
        tiles.append((tp,p))
    b.close()
# contact sheet + pairwise thumbnail distance
sheet = Image.new("RGB",(4*220,3*220),(10,12,15))
thumbs={}
for i,(tp,p) in enumerate(tiles):
    im=Image.open(p).convert("RGB").resize((220,220))
    sheet.paste(im,((i%4)*220,(i//4)*220))
    thumbs[tp]=list(im.resize((24,24)).getdata())
sheet.save("%s/sheet_%s.png"%(OUTDIR,TAG))
# Mask to the subject: compare only where at least one of the two differs from the empty-ground
# reference. Comparing whole tiles measures mostly background — for the small units the subject is
# ~15% of the pixels, which is why the unmasked numbers could not resolve anything.
ref=list(Image.open(REFP).convert("RGB").resize((220,220)).resize((24,24)).get_flattened_data()) \
    if hasattr(Image.Image,'get_flattened_data') else list(Image.open(REFP).convert("RGB").resize((220,220)).resize((24,24)).getdata())
def subj(t):
    return [k for k in range(len(t)) if abs(t[k][0]-ref[k][0])+abs(t[k][1]-ref[k][1])+abs(t[k][2]-ref[k][2]) > 24]
masks={tp:set(subj(thumbs[tp])) for tp in E}
print("%s subject coverage: %s" % (TAG, {tp:len(masks[tp]) for tp in E}))
d=[]
for a,c in itertools.combinations(E,2):
    A,B=thumbs[a],thumbs[c]
    idx=sorted(masks[a]|masks[c])
    if not idx: d.append((0.0,a,c)); continue
    s=sum(abs(A[k][0]-B[k][0])+abs(A[k][1]-B[k][1])+abs(A[k][2]-B[k][2]) for k in idx)/(len(idx)*3)
    d.append((s,a,c))
d.sort()
print("%s worst-confusable pairs (mean abs channel diff at 24x24):" % TAG)
for s,a,c in d[:5]: print("   %-11s vs %-11s %6.2f" % (a,c,s))
print("%s  min=%.2f  median=%.2f" % (TAG, d[0][0], d[len(d)//2][0]))
