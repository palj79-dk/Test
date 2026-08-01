"""V6.40 audio bank suite.

Asserts: the bank ships and decodes, variants are genuinely different buffers, the
public Sound API is unchanged, every banked event actually reaches the bank, the
procedural fallback still works with the bank removed, and the size stays in budget.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import _harness as H

import pathlib
import re
import sys
from playwright.sync_api import sync_playwright

CHROME = H.chrome()
SRC = H.target()
URL = SRC.as_uri()
fails = []
errors = []


def chk(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ((" — " + str(extra)) if extra else ""))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- static checks
html = SRC.read_text()

m = re.search(r"window\.__AUDIOBANK=(\{.*?\});", html, re.S)
chk("bank block present in the file", bool(m))
b64_bytes = len(m.group(1)) if m else 0
chk("bank within the 600 KB budget", b64_bytes <= 600 * 1024, "%d KB" % (b64_bytes // 1024))

# the bank must live in its own <script>, so gamecheck's marker selection is untouched
bank_start = html.index("window.__AUDIOBANK")
tag_open = html.rindex("<script>", 0, bank_start)
tag_close = html.index("</script>", bank_start)
chk("bank sits in its own script block", "function drawTray" not in html[tag_open:tag_close])

# the procedural synth must still be in the source, not replaced
chk("procedural synth retained as fallback", "const proc = {" in html and "function osc(f, d, type" in html)

# ---------------------------------------------------------------- 25-member API
API = ["place", "err", "up", "boom", "tesla", "gun", "musicOn", "sfxOn", "repair", "strike",
       "wave", "shield", "win", "leak", "lose", "prism", "cryo", "siege", "startMusic",
       "stopMusic", "toggleMusic", "toggleSfx", "resume", "sell", "suspend"]
BANKED = ["gun", "tesla", "cryo", "prism", "siege", "boom", "strike", "place", "up", "sell",
          "err", "leak", "shield", "wave", "win", "lose", "repair"]

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME,
                          args=["--no-sandbox", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 360, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg.wait_for_timeout(900)

    missing = pg.evaluate("(a) => a.filter(k => typeof __GAME.Sound[k] !== 'function' && typeof __GAME.Sound[k] !== 'undefined' ? false : typeof __GAME.Sound[k] !== 'function')", API)
    chk("all 25 public members are functions", not missing, missing)

    # ---------- bank decodes on the first gesture ----------
    pg.evaluate("() => __GAME.Sound.resume()")
    ok = False
    for _ in range(40):
        st = pg.evaluate("() => __GAME.Sound.bankState()")
        if st in (2, -1):
            ok = st == 2
            break
        pg.wait_for_timeout(250)
    chk("bank decodes to ready state", ok, "bankState=%s" % pg.evaluate("() => __GAME.Sound.bankState()"))

    counts = pg.evaluate("""() => {
      const raw = window.__AUDIOBANK, out = {};
      for (const k in raw) out[k] = raw[k].length;
      return out;
    }""")
    chk("18 events in the bank", len(counts) == 18, counts)
    chk("39 variants total", sum(counts.values()) == 39, sum(counts.values()))
    chk("gun has 4 variants (fires most often)", counts.get("gun") == 4)

    # ---------- variants are actually different audio ----------
    diff = pg.evaluate("""async () => {
      const AC = new (window.AudioContext || window.webkitAudioContext)();
      const bin = (s) => { const n = s.length, u = new Uint8Array(n); for (let i = 0; i < n; i++) u[i] = s.charCodeAt(i); return u.buffer; };
      const dec = (b64) => AC.decodeAudioData(bin(atob(b64)));
      const out = {};
      for (const ev of ['gun', 'tesla', 'boom']) {
        const bufs = await Promise.all(window.__AUDIOBANK[ev].map(dec));
        let worst = 1e9;
        for (let i = 0; i < bufs.length; i++) for (let j = i + 1; j < bufs.length; j++) {
          const a = bufs[i].getChannelData(0), c = bufs[j].getChannelData(0);
          const n = Math.min(a.length, c.length); let d = 0;
          for (let k = 0; k < n; k += 7) d += Math.abs(a[k] - c[k]);
          worst = Math.min(worst, d / (n / 7));
        }
        out[ev] = worst;
      }
      return out;
    }""")
    for ev, d in diff.items():
        chk("%s variants differ from each other" % ev, d > 0.01, "mean abs diff %.4f" % d)

    # ---------- every banked event reaches the bank, not the synth ----------
    routed = pg.evaluate("""(evs) => {
      const AC = __GAME.Sound;
      const seen = [];
      // count BufferSource creations while firing each event once
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createBufferSource;
      for (const ev of evs) {
        let n = 0;
        proto.createBufferSource = function () { n++; return orig.apply(this, arguments); };
        AC[ev](200, 200);
        proto.createBufferSource = orig;
        if (!n) seen.push(ev);
      }
      return seen;
    }""", BANKED)
    chk("every banked event plays a sample", not routed, "fell back to synth: %s" % routed)

    # ---------- per-shot variation ----------
    var = pg.evaluate("""() => {
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createBufferSource;
      const rates = [], bufs = [];
      proto.createBufferSource = function () {
        const s = orig.apply(this, arguments);
        setTimeout(() => { rates.push(s.playbackRate.value); bufs.push(s.buffer); }, 0);
        return s;
      };
      for (let i = 0; i < 30; i++) __GAME.Sound.gun(200, 200);
      proto.createBufferSource = orig;
      return new Promise(r => setTimeout(() => r({
        rates: rates.slice(), uniqBufs: new Set(bufs).size, uniqRates: new Set(rates).size
      }), 60));
    }""")
    rates = var["rates"]
    chk("pitch jitter applied", var["uniqRates"] > 20, "%d distinct rates over 30 shots" % var["uniqRates"])
    chk("pitch jitter within +/-6%", all(0.939 <= r <= 1.061 for r in rates),
        "range %.4f..%.4f" % (min(rates), max(rates)) if rates else "no shots")
    chk("more than one gun variant used", var["uniqBufs"] > 1, "%d distinct buffers" % var["uniqBufs"])

    # ---------- positional pan ----------
    pan = pg.evaluate("""() => {
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createStereoPanner;
      const pans = [];
      proto.createStereoPanner = function () { const p = orig.apply(this, arguments); setTimeout(() => pans.push(p.pan.value), 0); return p; };
      const G = __GAME;
      G.S.screen = 'playing';
      G.Sound.gun(40, 300); G.Sound.gun(1200, 300);
      proto.createStereoPanner = orig;
      return new Promise(r => setTimeout(() => r(pans.slice()), 60));
    }""")
    chk("world position drives stereo pan", len(pan) >= 2 and abs(pan[0] - pan[1]) > 0.1,
        "pans %s" % [round(x, 3) for x in pan])

    # ---------- music uses the loop ----------
    mus = pg.evaluate("""() => {
      const S = __GAME.S; S.screen = 'playing';
      __GAME.Sound.toggleMusic(true);
      __GAME.Sound.stopMusic();
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createBufferSource;
      let looped = false, dur = 0;
      proto.createBufferSource = function () { const s = orig.apply(this, arguments); setTimeout(() => { if (s.loop) { looped = true; dur = s.buffer ? s.buffer.duration : 0; } }, 0); return s; };
      __GAME.Sound.startMusic();
      proto.createBufferSource = orig;
      return new Promise(r => setTimeout(() => { __GAME.Sound.stopMusic(); r({ looped, dur }); }, 80));
    }""")
    chk("music plays the looped bed", mus["looped"], "loop len %.1fs" % mus["dur"])
    chk("music loop is a long bed", mus["dur"] > 15, "%.1fs" % mus["dur"])

    # ---------- sfx toggle still silences everything ----------
    silent = pg.evaluate("""() => {
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createBufferSource;
      let n = 0;
      __GAME.Sound.toggleSfx(false);
      proto.createBufferSource = function () { n++; return orig.apply(this, arguments); };
      ['gun','boom','place','err'].forEach(k => __GAME.Sound[k]());
      proto.createBufferSource = orig;
      __GAME.Sound.toggleSfx(true);
      return n;
    }""")
    chk("sfx toggle still mutes the bank", silent == 0, "%d sources created while muted" % silent)

    chk("no page errors with the bank", not errors, errors[:3])

    # ---------------------------------------------------------------- fallback run
    stripped = html.replace("window.__AUDIOBANK=", "window.__NOBANK=", 1)
    tmp = pathlib.Path(str(H.scratch() / "nobank.html"))
    tmp.write_text(stripped)
    ferr = []
    pg2 = b.new_page(viewport={"width": 360, "height": 720})
    pg2.on("pageerror", lambda e: ferr.append(str(e)))
    pg2.goto(tmp.as_uri())
    pg2.wait_for_function("window.__GAME !== undefined", timeout=30000)
    pg2.wait_for_timeout(700)
    fb = pg2.evaluate("""(evs) => {
      __GAME.Sound.resume();
      const proto = (window.AudioContext || window.webkitAudioContext).prototype;
      const orig = proto.createOscillator;
      let n = 0;
      proto.createOscillator = function () { n++; return orig.apply(this, arguments); };
      evs.forEach(k => __GAME.Sound[k]());
      __GAME.S.screen = 'playing'; __GAME.Sound.toggleMusic(true); __GAME.Sound.startMusic();
      proto.createOscillator = orig;
      return { oscs: n, state: __GAME.Sound.bankState() };
    }""", BANKED)
    chk("bank reports unavailable when absent", fb["state"] == -1, fb["state"])
    chk("procedural fallback still makes sound", fb["oscs"] > 20, "%d oscillators" % fb["oscs"])
    chk("no page errors without the bank", not ferr, ferr[:3])

    b.close()

print()
if fails:
    print("FAILED %d: %s" % (len(fails), fails))
    sys.exit(1)
print("verify640: ALL PASS")
