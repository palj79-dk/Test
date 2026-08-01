# V6.40 — Audio: offline-rendered sample bank with variation

**Status:** ✅ shipped as V6.40. Written 2026-07-28 against V6.39; the "What actually shipped"
section at the bottom records where the build diverged from the plan.

## The problem, measured

The whole game is synthesised live from oscillators. Counted in the `Sound` module of V6.39:

- **41 oscillator calls**, but only **4 uses of `Math.random` in the entire module**
- 1 convolver, 2 stereo-panner uses

So nearly every sound is **byte-identical every time it plays**. That is what the ear reads as
artificial — not the timbre, the *repetition*. A real auto-gun firing 200 times in a wave produces 200
slightly different sounds; this one produces the same waveform 200 times.

Runtime synthesis also caps quality: it has one frame's worth of CPU to spend, so no convolution
tails, no multi-stage processing, no per-sound tuning.

## The approach

Render every sound **offline** in Python/numpy — where compute is free — encode to Opus, embed as
base64, and play back as buffers with per-shot variation. Measured on the V6.39 proof: a gun shot is
**3.0 KB** as Opus, an explosion 9.1 KB, a 16-second music loop 110 KB.

Nothing about the platform changes. This is still one offline HTML file.

## Scope

**Bank:** 17 sound events, 38 variants total, plus one music loop.

| event | variants | why |
|---|---|---|
| gun | 4 | fires constantly — most exposed to repetition |
| tesla, cryo, prism, siege, boom | 3 each | frequent combat sounds |
| strike, place, up, err, leak, shield, wave, repair | 2 each | common but not per-frame |
| sell, win, lose | 1 each | rare, or deliberately fixed |

**Per-shot variation on top of the variants:** random variant pick, ±6% pitch (playbackRate) and
±1.5 dB gain jitter, so even the same variant is never identical twice.

**Positional audio:** pan and distance attenuation derived from world coordinates, so a tower firing
at the left edge is heard on the left.

**Mixer:** separate SFX and music buses into the existing tone-shave → compressor chain, so the music
ducks under combat instead of fighting it.

**Latency:** `AudioContext({ latencyHint: "interactive" })` — currently unset, which lets the browser
choose a large buffer.

## Non-negotiables

1. **The public `Sound.*` API does not change.** 25 members, ~70 call sites. Nothing existing breaks.
   Verified by asserting the API surface in the suite.
2. **The procedural synth stays as a fallback.** If the bank is missing, fails to decode, or the
   device refuses WebAudio, the game falls back to exactly today's behaviour. Silence is not an
   acceptable failure mode for a change that is supposed to *improve* audio.
3. **The renderer is committed and deterministic** (`tools/render_audio.py`, seeded RNG), so the bank
   can be regenerated and tuned rather than being an opaque blob.
4. Size budget: **≤ 600 KB of base64** added to the file.

## Steps

1. `tools/render_audio.py` — DSP for all 38 variants + music loop; ffmpeg → Opus; emit a JS block.
2. Splice the bank into the HTML as its own `<script>` (keeps the game block, and therefore
   `gamecheck.sh`'s marker-based selection, unchanged).
3. Rewrite the `Sound` internals: decode-on-first-gesture, variant picker, jitter, buses, positional
   helper, procedural fallback preserved.
4. `verify640.py` — bank decodes, variants differ from each other, API surface unchanged, fallback
   works with the bank removed, size within budget, no page errors.
5. All twelve existing suites, HANDOFF, commit, push, APK.

## The honest limitation

**I cannot hear any of this.** I can measure peak, RMS, clipping, DC offset and spectral centroid, and
I can reason about the DSP — but whether it *sounds good* is not something I can check. The user is
the ear. Every rendered sound is exported as WAV alongside the build so it can be listened to before
the bank is accepted.

## What actually shipped

Everything above, with two deliberate divergences worth writing down:

**Positional audio needed call sites after all.** The plan claimed *"not one call site is touched"*
in the same breath as promising pan derived from world coordinates. Those two cannot both be true:
`Sound.gun()` takes no arguments, so it has no way to know where the tower is. What shipped is the
backwards-compatible version — the banked events accept **optional** `(wx, wy)`, every existing
zero-argument call still works unchanged, and **10 call sites** now pass coordinates they already had
in scope (tower muzzle, impact point, hero, leak). The API surface assertion still holds; the claim
about call sites did not, and has been corrected rather than quietly dropped.

**A latent bug surfaced.** Threading `hero.x` into the hero ability's deferred
`setTimeout(() => Sound.boom(...))` threw when a run ended inside that 40 ms window. Coordinates are
now captured into locals before the timer is scheduled.

Final numbers: 17 events, 38 SFX variants + one 22.5 s music loop, **540 KB** of base64 (budget 600 KB),
0 clipped samples across all 39 renders, 24 assertions in `verify640.py`, and all thirteen pre-existing
suites still green.

The limitation below did not go away. Nothing in this document establishes that the bank *sounds*
better than the synth it replaces — only that it is measurably more varied, and that removing it
returns the game to exactly the old behaviour.
