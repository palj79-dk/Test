# Harness

Everything here is committed on purpose. The verification suites used to live in a session
scratchpad, which meant they died with the conversation that created them and a new session could
not run the definition of done at all. **Nothing in this directory may reference a path outside the
repo.**

## Run the definition of done

```
tools/verify/run_all.sh                    # newest fallengrid-v*.html
tools/verify/run_all.sh fallengrid-v6.43.html
```

That is game-block syntax, both wave-progression guards, the filename/label agreement the APK
workflow enforces, and every suite in `verify/`. Per-suite logs land in `/tmp/fg-<suite>.log`.

## What is here

| | |
|---|---|
| `gamecheck.sh` | `node --check` on the **game** script block, selected by markers (`PLAY_BOTTOM` + `function drawTray`). Never selects by size — three.js is the largest block. |
| `verify/` | one suite per iteration, plus `run_all.sh` |
| `verify/_harness.py` | finds the build, the browser, and **recovers old builds from git history** for the before/after suites |
| `mapsheet.py` | renders all 25 maps + measures props, relief and colour spread; writes a contact sheet |
| `enemysheet.py` | renders all 12 enemies at one camera and measures how confusable they are as thumbnails |
| `propmeasure.py` | prop count and nearest-neighbour spread, before/after a baseline build |
| `heromeasure.py` | Commander damage share vs the tower line |
| `render_audio.py` | offline sound renderer → `audiobank.js`, spliced into the HTML as its own `<script>` |
| `audiobank.js` | its output. **Do not hand-edit** — re-run the renderer |

## Environment

- **playwright** + Chromium at `/opt/pw-browsers/chromium*/chrome-linux/chrome`. Override with
  `$CHROME`. Launch args are always `--no-sandbox --enable-unsafe-swiftshader` (software rendering,
  so absolute frame times are meaningless — only before/after comparisons are).
- **node** for `gamecheck.sh`.
- **pillow** for the contact sheets (`pip install pillow`).
- **numpy** and an **ffmpeg** binary for `render_audio.py` only. `npm install ffmpeg-static` gives
  one; pass it with `--ffmpeg`.

`$FG_TARGET` overrides which build every tool operates on.

## Two traps that have each cost a debugging session

1. The tray, HUD and build panel are drawn by `requestAnimationFrame`, **not** by `render()`. Wait
   250-300 ms before reading `__GAME.trayBtns` / `buildBtns` / `hudBtns`.
2. The RAF loop applies `clampCam()` **after** you set `cam`. Reading `worldToScreen` immediately
   reports where the camera was *asked* to go, not where it ended up — wait a frame first.
