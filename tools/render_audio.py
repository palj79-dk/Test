#!/usr/bin/env python3
"""Render the Fallen Grid audio bank offline and emit it as an embeddable JS block.

Why offline: the game used to synthesise every sound live from oscillators, which caps quality at
one frame's worth of CPU and — far worse — made almost every sound byte-identical on every play.
Rendering here costs nothing per sound, so each one gets convolution reverb, multi-stage filtering
and saturation, and each EVENT gets several distinct variants the game picks between.

Output: tools/audiobank.js  (window.__AUDIOBANK = { ev: [b64, ...], ... })
        tools/preview/*.wav (uncompressed, for listening before accepting the bank)

Requires numpy and an ffmpeg binary with libopus:
    pip install numpy
    npm install ffmpeg-static      # then pass --ffmpeg node_modules/ffmpeg-static/ffmpeg
"""
import argparse, base64, json, os, shutil, subprocess, sys, wave
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, "preview")
TMP = os.path.join(HERE, ".render")

# Deterministic: the same commit must always produce the same bank.
RNG = np.random.default_rng(20260728)


# --------------------------------------------------------------------------- DSP helpers
def env(n, a, d, sus=0.0, r=0.0):
    """Attack / decay / sustain / release envelope of exactly n samples."""
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    S = max(0, n - A - D - R)
    parts = [np.linspace(0, 1, max(1, A)), np.linspace(1, sus, max(1, D)),
             np.full(S, sus), np.linspace(sus, 0, max(1, R))]
    return np.concatenate(parts)[:n]


def noise(n):
    return RNG.uniform(-1, 1, n)


def lp(x, cut):
    """One-pole lowpass. `cut` may be an array for a sweep."""
    a = np.exp(-2 * np.pi * np.asarray(cut, dtype=float) / SR)
    a = np.broadcast_to(a, x.shape)
    y = np.empty_like(x)
    p = 0.0
    for i in range(len(x)):
        p = (1 - a[i]) * x[i] + a[i] * p
        y[i] = p
    return y


def hp(x, cut):
    return x - lp(x, cut)


def bp(x, centre, q=3.0):
    """Crude band-pass: lowpass above, highpass below."""
    c = np.asarray(centre, dtype=float)
    return lp(hp(x, c / q), c * q)


def sweep(f0, f1, n, curve=1.0):
    """Instantaneous-phase sine sweeping f0 -> f1 over n samples."""
    f = f0 + (f1 - f0) * np.linspace(0, 1, n) ** curve
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def tone(f, n, kind="sine", detune=0.0):
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * t + detune * t
    if kind == "sine":
        return np.sin(ph)
    if kind == "saw":
        return 2 * ((f * t) % 1.0) - 1.0
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "tri":
        return 2 * np.abs(2 * ((f * t) % 1.0) - 1) - 1
    raise ValueError(kind)


def sat(x, k):
    return np.tanh(x * k) / np.tanh(k)


def reverb(x, decay=1.4, wet=0.28, damp=3800):
    """Convolution with a decaying, damped noise impulse — a plate, effectively."""
    n = int(decay * SR)
    ir = lp(noise(n) * np.exp(-np.linspace(0, 7, n)), damp)
    y = np.convolve(x, ir)[: len(x) + SR // 2]
    dry = np.pad(x, (0, len(y) - len(x)))
    return dry + wet * (y / max(1e-9, np.abs(y).max()))


def norm(x, peak=0.89):
    x = np.nan_to_num(x)
    x = x - x.mean() * 0.02                      # nudge out any DC the filters introduced
    m = np.abs(x).max()
    return x / m * peak if m > 1e-9 else x


def fade(x, ms=6):
    """Short fades so a truncated tail never clicks."""
    k = int(ms / 1000 * SR)
    if len(x) > 2 * k:
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
    return x


# --------------------------------------------------------------------------- sound designs
# Each function takes a variant index and returns mono float audio. Variants differ in pitch,
# filter and length — not just level — so they read as different events, not the same one quieter.

def s_gun(v):
    """Auto-cannon: mechanical crack, short pitched body, sub thump."""
    n = int(0.26 * SR)
    p = [1.0, 0.94, 1.07, 0.89][v]
    crack = lp(noise(n) * env(n, 0.0004, 0.03), np.linspace(9500 * p, 900, n))
    body = sweep(330 * p, 108 * p, n) * env(n, 0.001, 0.11)
    sub = sweep(140 * p, 50, n) * env(n, 0.002, 0.19)
    return reverb(sat(1.5 * crack + 0.7 * body + 0.62 * sub, 2.2), 0.5, 0.15)


def s_tesla(v):
    """Rail-tesla: electric zap — resonant noise sweeping down over a ringing tail."""
    n = int(0.5 * SR)
    p = [1.0, 1.12, 0.9][v]
    zap = bp(noise(n), np.linspace(5200 * p, 620, n), 2.4) * env(n, 0.001, 0.16)
    ring = (tone(1180 * p, n) + 0.5 * tone(1770 * p, n)) * env(n, 0.002, 0.34)
    crk = hp(noise(n), 4000) * env(n, 0.0003, 0.02) * 0.5
    return reverb(sat(1.3 * zap + 0.5 * ring + crk, 1.9), 1.2, 0.34)


def s_cryo(v):
    """Frost orb impact: glassy cluster, fast shimmer, no low end."""
    n = int(0.55 * SR)
    p = [1.0, 1.09, 0.93][v]
    glass = sum(tone(f * p, n) * np.exp(-np.arange(n) / SR * d)
                for f, d in ((1568, 5.0), (2093, 7.0), (3136, 9.0)))
    frost = hp(noise(n), 5200) * env(n, 0.004, 0.3) * 0.45
    return reverb(0.5 * glass * env(n, 0.001, 0.42) + frost, 1.5, 0.4, 6500)


def s_prism(v):
    """Refracting beam: harmonic stack with tremolo — sustained, not percussive."""
    n = int(0.62 * SR)
    p = [1.0, 1.06, 0.95][v]
    t = np.arange(n) / SR
    stack = sum(tone(f * p, n) / (i + 1) for i, f in enumerate((660, 990, 1320, 1980)))
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 34 * t)
    beam = stack * trem * env(n, 0.012, 0.5)
    air = hp(noise(n), 7000) * env(n, 0.01, 0.4) * 0.2
    return reverb(sat(0.45 * beam + air, 1.5), 1.4, 0.36, 7000)


def s_siege(v):
    """Siege battery: deep artillery thump with a long, dark tail."""
    n = int(1.1 * SR)
    p = [1.0, 0.93, 1.06][v]
    thump = sweep(150 * p, 34, n, 0.5) * env(n, 0.002, 0.55)
    blast = lp(noise(n), np.linspace(1900 * p, 90, n)) * env(n, 0.001, 0.7)
    metal = bp(noise(n), 2400 * p, 3.0) * env(n, 0.0006, 0.06) * 0.4
    return reverb(sat(1.1 * thump + 0.95 * blast + metal, 1.7), 1.9, 0.4)


def s_boom(v):
    """Explosion: blast, punch, debris."""
    n = int(1.5 * SR)
    p = [1.0, 0.9, 1.08][v]
    blast = lp(noise(n), np.linspace(2600 * p, 70, n)) * env(n, 0.001, 1.35)
    punch = sweep(122 * p, 26, n) * env(n, 0.002, 0.7)
    deb = lp(noise(n), 5200) * env(n, 0.06, 1.1) * 0.22
    return reverb(sat(1.25 * blast + 0.95 * punch + deb, 1.8), 2.2, 0.42)


def s_strike(v):
    """Airstrike: falling whistle into a very large detonation."""
    n = int(2.0 * SR)
    p = [1.0, 0.95][v]
    whistle = np.zeros(n)
    w = int(0.7 * SR)
    whistle[:w] = sweep(2300 * p, 520, w, 1.6) * env(w, 0.05, 0.6) * 0.3
    x = np.zeros(n)
    b0 = int(0.62 * SR)
    m = n - b0
    x[b0:] = (lp(noise(m), np.linspace(3000, 55, m)) * env(m, 0.001, 1.2) * 1.3
              + sweep(140, 22, m) * env(m, 0.002, 0.9))
    return reverb(sat(whistle + x, 1.7), 2.6, 0.46)


def s_place(v):
    """Build: a mechanical clunk that settles."""
    n = int(0.3 * SR)
    p = [1.0, 1.08][v]
    thunk = sweep(280 * p, 92, n, 0.6) * env(n, 0.001, 0.13)
    click = hp(noise(n), 2600) * env(n, 0.0004, 0.035) * 0.6
    return reverb(sat(thunk + click, 1.6), 0.5, 0.18)


def s_up(v):
    """Upgrade: rising three-note figure, bright and affirmative."""
    n = int(0.62 * SR)
    base = [523.25, 587.33][v]
    out = np.zeros(n)
    for k, mul in enumerate((1.0, 1.26, 1.5)):
        s = int(k * 0.075 * SR)
        m = n - s
        out[s:] += (tone(base * mul, m) + 0.4 * tone(base * mul * 2, m)) * env(m, 0.004, 0.3) * 0.5
    return reverb(out, 1.1, 0.34, 8000)


def s_sell(v):
    """Sell: descending pair with a metallic shimmer."""
    n = int(0.5 * SR)
    out = np.zeros(n)
    for k, f in enumerate((784, 523.25)):
        s = int(k * 0.09 * SR)
        m = n - s
        out[s:] += tone(f, m) * env(m, 0.004, 0.26) * 0.55
    shim = hp(noise(n), 6000) * env(n, 0.01, 0.2) * 0.16
    return reverb(out + shim, 0.9, 0.3, 8000)


def s_err(v):
    """Blocked action: short, low, unmistakably negative."""
    n = int(0.2 * SR)
    p = [1.0, 0.92][v]
    buzz = sat(tone(112 * p, n, "square") * env(n, 0.002, 0.14), 2.4) * 0.5
    return reverb(lp(buzz, 1500), 0.35, 0.14)


def s_leak(v):
    """Core hit: a heavy impact under a brief alarm."""
    n = int(1.1 * SR)
    p = [1.0, 0.94][v]
    hit = sweep(190 * p, 40, n, 0.7) * env(n, 0.002, 0.5)
    alarm = tone(660 * p, n) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 7 * np.arange(n) / SR))) * env(n, 0.02, 0.6) * 0.22
    return reverb(sat(hit + alarm, 1.7), 1.6, 0.36)


def s_shield(v):
    """Shield hit: glassy ring with a hard edge."""
    n = int(0.45 * SR)
    p = [1.0, 1.11][v]
    ring = sum(tone(f * p, n) / (i + 1.4) for i, f in enumerate((1320, 1980, 2640)))
    tick = hp(noise(n), 6000) * env(n, 0.0004, 0.02) * 0.45
    return reverb(0.55 * ring * env(n, 0.001, 0.32) + tick, 1.3, 0.4, 7500)


def s_wave(v):
    """Wave incoming: a brass-like stab."""
    n = int(1.0 * SR)
    base = [174.61, 196.0][v]
    stack = sum(tone(base * k, n, "saw") / k for k in (1, 2, 3, 4))
    horn = lp(sat(stack * 0.4, 2.6), np.linspace(900, 2600, n)) * env(n, 0.03, 0.2, 0.45, 0.5)
    return reverb(horn, 1.8, 0.4)


def s_win(v):
    """Victory: rising major arpeggio into a held chord."""
    n = int(2.2 * SR)
    out = np.zeros(n)
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        s = int(k * 0.13 * SR)
        m = n - s
        out[s:] += (tone(f, m) + 0.35 * tone(f * 2, m)) * env(m, 0.006, 0.7) * 0.4
    for f in (261.63, 329.63, 392.0):
        s = int(0.52 * SR)
        m = n - s
        out[s:] += tone(f, m) * env(m, 0.05, 1.4) * 0.22
    return reverb(out, 2.4, 0.42, 8000)


def s_lose(v):
    """Defeat: sagging minor cluster."""
    n = int(2.4 * SR)
    out = np.zeros(n)
    for k, f in enumerate((329.63, 261.63, 196.0)):
        s = int(k * 0.2 * SR)
        m = n - s
        out[s:] += sweep(f, f * 0.94, m) * env(m, 0.03, 1.6) * 0.35
    rum = lp(noise(n), 260) * env(n, 0.2, 1.9) * 0.3
    return reverb(out + rum, 2.6, 0.4)


def s_repair(v):
    """Core repair: mechanical latch plus an ascending confirmation."""
    n = int(0.7 * SR)
    p = [1.0, 1.05][v]
    latch = hp(noise(n), 2200) * env(n, 0.0006, 0.05) * 0.5
    out = np.zeros(n)
    for k, f in enumerate((440 * p, 660 * p)):
        s = int(k * 0.1 * SR)
        m = n - s
        out[s:] += tone(f, m) * env(m, 0.005, 0.34) * 0.45
    return reverb(out + latch, 1.2, 0.34, 8000)


def s_music(v):
    """Ambient bed: A-minor pad, sub pulse, sparse bells, wind. Loop-safe."""
    dur = 24.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    pad = np.zeros(n)
    for f in (110.0, 130.81, 164.81, 220.0):
        for det in (-0.16, 0.0, 0.16):
            pad += np.sin(2 * np.pi * (f + det) * t + np.sin(2 * np.pi * 0.06 * t) * 0.7)
    pad = lp(pad / 12, 400 + 320 * (1 + np.sin(2 * np.pi * 0.038 * t)))
    pad *= 0.55 + 0.12 * np.sin(2 * np.pi * 0.09 * t)
    pulse = tone(55, n) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * (72 / 60 / 2) * t))) * 0.2
    bells = np.zeros(n)
    for bt, bf in ((3.0, 880), (8.5, 1174.7), (14.0, 987.77), (19.5, 659.25)):
        s = int(bt * SR)
        m = min(int(2.6 * SR), n - s)
        tt = np.arange(m) / SR
        bells[s:s + m] += (np.sin(2 * np.pi * bf * tt) + 0.4 * np.sin(2 * np.pi * bf * 2.01 * tt)) * np.exp(-tt * 2.0) * 0.15
    wind = lp(noise(n), 620) * 0.045
    mix = reverb(pad + pulse + bells + wind, 2.8, 0.3)[:n]
    # crossfade the tail into the head so the loop point is inaudible
    x = int(1.5 * SR)
    head = mix[:x] * np.linspace(0, 1, x)
    mix[:x] = head + mix[-x:] * np.linspace(1, 0, x)
    return mix[:-x]


BANK = {
    "gun": (s_gun, 4, 32), "tesla": (s_tesla, 3, 40), "cryo": (s_cryo, 3, 40),
    "prism": (s_prism, 3, 40), "siege": (s_siege, 3, 40), "boom": (s_boom, 3, 44),
    "strike": (s_strike, 2, 44), "place": (s_place, 2, 32), "up": (s_up, 2, 40),
    "sell": (s_sell, 1, 40), "err": (s_err, 2, 28), "leak": (s_leak, 2, 40),
    "shield": (s_shield, 2, 40), "wave": (s_wave, 2, 40), "win": (s_win, 1, 48),
    "lose": (s_lose, 1, 44), "repair": (s_repair, 2, 40), "music": (s_music, 1, 56),
}


# --------------------------------------------------------------------------- IO
def write_wav(path, x):
    x = fade(norm(x))
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes())
    w.close()
    return x


def encode(ffmpeg, src, dst, kbps):
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                    "-c:a", "libopus", "-b:a", "%dk" % kbps, "-ar", "48000", "-ac", "1", dst],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    ap.add_argument("--out", default=os.path.join(HERE, "audiobank.js"))
    a = ap.parse_args()
    if not (os.path.isfile(a.ffmpeg) or shutil.which(a.ffmpeg)):
        sys.exit("ffmpeg not found: %s  (npm install ffmpeg-static)" % a.ffmpeg)

    for d in (PREVIEW, TMP):
        os.makedirs(d, exist_ok=True)

    out, total, rows = {}, 0, []
    for ev, (fn, nvar, kbps) in BANK.items():
        out[ev] = []
        for v in range(nvar):
            wav = os.path.join(TMP, "%s_%d.wav" % (ev, v))
            opus = os.path.join(TMP, "%s_%d.opus" % (ev, v))
            x = write_wav(wav, fn(v))
            shutil.copy(wav, os.path.join(PREVIEW, "%s_%d.wav" % (ev, v)))
            encode(a.ffmpeg, wav, opus, kbps)
            raw = open(opus, "rb").read()
            out[ev].append(base64.b64encode(raw).decode("ascii"))
            total += len(raw)
            rows.append((ev, v, len(x) / SR, len(raw),
                         float(np.abs(x).max()), float(np.sqrt((x ** 2).mean())),
                         int((np.abs(x) > 0.995).sum())))

    b64 = sum(len(b) for lst in out.values() for b in lst)
    js = "window.__AUDIOBANK=%s;\n" % json.dumps(out, separators=(",", ":"))
    open(a.out, "w", encoding="utf-8").write(js)

    print("%-8s %3s %7s %9s %7s %7s %8s" % ("event", "var", "secs", "opus B", "peak", "rms", "clipped"))
    for r in rows:
        print("%-8s %3d %7.2f %9d %7.2f %7.3f %8d" % r)
    print("\n%d variants, %d events" % (len(rows), len(BANK)))
    print("opus total   %8d B  (%.0f KB)" % (total, total / 1024))
    print("base64 total %8d B  (%.0f KB)" % (b64, b64 / 1024))
    print("wrote %s" % a.out)
    print("previews in %s" % PREVIEW)
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
