"""Render every map wide and measure how lively they are (props, terrain relief, colour spread).

Usage: python3 tools/mapsheet.py [outdir]      (target = $FG_TARGET or the newest build)
Writes one PNG per map plus sheet25.png, and prints a per-map table.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent / "verify"))
import _harness as H
import statistics, math
from playwright.sync_api import sync_playwright
CHROME = H.chrome()
OUT = str(H.scratch() / "maps") if len(_sys.argv) < 2 else _sys.argv[1]
import os; os.makedirs(OUT, exist_ok=True)
rows=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":360,"height":720}, device_scale_factor=2)
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file:///home/user/Test/fallengrid-v6.42.html"); pg.wait_for_function("window.__GAME !== undefined",timeout=30000)
    pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24')")
    pg.reload(); pg.wait_for_function("window.__GAME !== undefined",timeout=30000); pg.wait_for_timeout(800)
    n = pg.evaluate("()=>__GAME.__MAPCOUNT || 25")
    for mi in range(n):
        r = pg.evaluate("""(mi)=>{const G=__GAME;
          G.S.endless=false;G.S.campaign=false;G.S.isDaily=false;G.S.isLab=false;
          G.S.difficulty='hard'; G.S.mapIndex=mi; G.selectMap(mi); G.reset();
          G.S.screen='playing'; G.S.tip=null; G.S.tipQ=[]; G.S.usedStrike=true; G.fitCamera(); G.render();
          // terrain: how many distinct slab heights, and how the ground colours spread
          const sc=G.G3D.scene; let land=null;
          const visit=(o)=>{ if(o.isMesh && o.material.type==='MeshLambertMaterial' && o.material.vertexColors && o.geometry.attributes.color) land=o; (o.children||[]).forEach(visit); };
          visit(sc);
          const pos=land.geometry.attributes.position.array, nor=land.geometry.attributes.normal.array, col=land.geometry.attributes.color.array;
          const heights=new Set(); const lum=[];
          for(let v=0;v<pos.length/3;v++){ if(nor[v*3+1]<0.99) continue;
            heights.add(Math.round(pos[v*3+1]*10)/10);
            lum.push(0.299*col[v*3]+0.587*col[v*3+1]+0.114*col[v*3+2]); }
          lum.sort((a,b)=>a-b);
          const mean=lum.reduce((a,b)=>a+b,0)/lum.length;
          const sd=Math.sqrt(lum.reduce((a,b)=>a+(b-mean)*(b-mean),0)/lum.length);
          let plots=0, tiles=0;
          for(let rr=0;rr<40;rr++)for(let cc=0;cc<40;cc++){ if(G.buildable(cc,rr)) plots++; }
          const dec=G.__decor;
          const types={}; for(const d of dec) types[d.type]=(types[d.type]||0)+1;
          return { props:dec.length, plots, blocked:G.blocked.size, heights:[...heights].length,
                   lumSd:+sd.toFixed(4), lumRange:+(lum[lum.length-1]-lum[0]).toFixed(3),
                   types, cells:dec.map(d=>[d.c,d.r]) };
        }""", mi)
        pg.wait_for_timeout(500)
        pg.screenshot(path="%s/m%02d.png"%(OUT,mi))
        rows.append((mi,r))
    b.close()
def nn(d):
    if len(d)<2: return 0,0,0
    out=[]
    for i,(c,r) in enumerate(d):
        bst=1e9
        for j,(c2,r2) in enumerate(d):
            if i!=j: bst=min(bst,math.hypot(c-c2,r-r2))
        out.append(bst)
    return statistics.mean(out), statistics.pvariance(out), max(out)
print("%-4s %6s %6s %7s %7s %8s %8s %7s  %s" % ("map","props","plots","props/plot","heights","lumSD","lumRange","nnVar","types"))
for mi,r in rows:
    m,v,mx = nn(r["cells"])
    print("%-4d %6d %6d %10.2f %7d %8.4f %8.3f %7.2f  %d kinds" %
          (mi, r["props"], r["plots"], r["props"]/max(1,r["plots"]), r["heights"], r["lumSd"], r["lumRange"], v, len(r["types"])))
allp=[r["props"] for _,r in rows]; allr=[r["props"]/max(1,r["plots"]) for _,r in rows]
print("\nprops/plot: min %.2f  median %.2f  max %.2f" % (min(allr), statistics.median(allr), max(allr)))
print("maps with < 0.10 props per plot (sparse):", [mi for mi,r in rows if r["props"]/max(1,r["plots"]) < 0.10])
if errs: print("PAGE ERRORS", errs[:3])

# contact sheet
try:
    from PIL import Image
    import glob as _g
    fs = sorted(_g.glob(OUT + "/m*.png"))
    if fs:
        TW, TH = 260, 300
        sheet = Image.new("RGB", (5 * TW, 5 * TH), (8, 10, 13))
        for i, f in enumerate(fs[:25]):
            im = Image.open(f).convert("RGB"); w, h = im.size
            sheet.paste(im.crop((0, int(h * .13), w, int(h * .80))).resize((TW, TH)), ((i % 5) * TW, (i // 5) * TH))
        sheet.save(OUT + "/sheet25.png")
        print("\ncontact sheet:", OUT + "/sheet25.png")
except ImportError:
    print("\n(pip install pillow for the contact sheet)")
