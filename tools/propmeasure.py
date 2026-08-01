import sys, statistics, math, json
from playwright.sync_api import sync_playwright
CHROME="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
MAPS=[0,3,9,16,24]
def run(url,label):
    out={}
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=CHROME,args=["--no-sandbox","--enable-unsafe-swiftshader"])
        pg=b.new_page(viewport={"width":360,"height":720})
        pg.on("pageerror", lambda e: print("PAGEERROR",label,e))
        pg.goto(url); pg.wait_for_function("window.__GAME !== undefined",timeout=30000)
        pg.evaluate("localStorage.clear(); localStorage.setItem('seenIntro','true'); localStorage.setItem('tutDone','true'); localStorage.setItem('camp','24')")
        pg.reload(); pg.wait_for_function("window.__GAME !== undefined",timeout=30000); pg.wait_for_timeout(700)
        for mi in MAPS:
            d=pg.evaluate("""(mi)=>{const G=__GAME; G.S.endless=false;G.S.campaign=false;G.S.isDaily=false;G.S.isLab=false;G.S.mapIndex=mi;G.selectMap(mi);G.reset();
              return __GAME.__decor.map(d=>[d.c,d.r,d.type]);}""", mi)
            out[mi]=d
        b.close()
    return out
def stats(d):
    n=len(d)
    if n<2: return n,0,0
    nn=[]
    for i,(c,r,_) in enumerate(d):
        best=1e9
        for j,(c2,r2,_) in enumerate(d):
            if i==j: continue
            best=min(best, math.hypot(c-c2,r-r2))
        nn.append(best)
    return n, statistics.mean(nn), statistics.pvariance(nn)
old=run("file:///tmp/claude-0/-home-user-Test/18cea54a-c2bc-5c03-961e-20540c52637e/scratchpad/base640.html","V6.40")
new=run("file:///home/user/Test/fallengrid-v6.42.html","V6.42")
print("%-6s %28s %28s" % ("map","V6.40  n / meanNN / varNN","V6.42  n / meanNN / varNN"))
tn=to=0
for mi in MAPS:
    a=stats(old[mi]); bb=stats(new[mi]); to+=a[0]; tn+=bb[0]
    print("%-6d %8d %8.2f %8.3f   |%8d %8.2f %8.3f   count %+.0f%%  meanNN %+.0f%%  var x%.2f"
          % (mi,a[0],a[1],a[2],bb[0],bb[1],bb[2],100*(bb[0]-a[0])/a[0],100*(bb[1]-a[1])/a[1], (bb[2]/a[2]) if a[2] else 0))
print("TOTAL count %d -> %d  (%+.1f%%)" % (to,tn,100*(tn-to)/to))
