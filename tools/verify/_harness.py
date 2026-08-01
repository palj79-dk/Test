"""Shared harness helpers so the suites survive a fresh container.

Everything here used to be hardcoded to a session scratchpad, which meant the whole standing suite
set vanished with the conversation that created it. Nothing in this package may depend on a path
outside the repo or on a file that is not in git.
"""
import glob
import os
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _vkey(p):
    return [int(x) for x in re.findall(r"\d+", pathlib.Path(p).stem)]


def latest_build():
    """The newest fallengrid-v*.html in the repo — the same selection the APK workflow makes."""
    files = glob.glob(str(ROOT / "fallengrid-v*.html"))
    if not files:
        raise SystemExit("no fallengrid-v*.html in %s" % ROOT)
    return pathlib.Path(sorted(files, key=_vkey)[-1])


def target():
    """Suite target: $FG_TARGET, else the newest build."""
    t = os.environ.get("FG_TARGET")
    return pathlib.Path(t) if t else latest_build()


def chrome():
    c = os.environ.get("CHROME")
    if c:
        return c
    found = sorted(glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome"))
    return found[-1] if found else "chromium"


# Debug hooks the probes need. Builds older than the iteration that added a hook do not have it,
# so it is injected into the recovered copy — a test-only patch of a historical artifact, applied
# here explicitly rather than by hand-editing a file that then only exists on one machine.
_HOOK_ANCHOR = 'get blocked() { return BLOCKED_SET; }'
_HOOKS = [('__decor', 'get __decor() { return DECOR; }'),
          ('__ENEMIES', '__ENEMIES: ENEMIES'),
          ('__TOWERS', '__TOWERS: TOWERS')]


def _inject_hooks(html):
    if _HOOK_ANCHOR not in html:
        return html
    add = [frag for name, frag in _HOOKS if name not in html]
    if not add:
        return html
    return html.replace(_HOOK_ANCHOR, _HOOK_ANCHOR + ", " + ", ".join(add), 1)


def baseline(version):
    """Materialise an older build out of git history, with probe hooks patched in.

    The before/after suites used to read a copy sitting in the scratchpad. Reading it from git
    instead means a fresh clone can run them.
    """
    name = "fallengrid-v%s.html" % version
    out = pathlib.Path(tempfile.gettempdir()) / ("fg-baseline-%s.html" % version)
    if out.exists() and out.stat().st_size > 1000:
        return out
    revs = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--all", "--full-history", "--", name],
                          capture_output=True, text=True).stdout.split()
    for rev in revs:
        for spec in ("%s:%s" % (rev, name), "%s^:%s" % (rev, name)):
            r = subprocess.run(["git", "-C", str(ROOT), "show", spec], capture_output=True)
            if r.returncode == 0 and len(r.stdout) > 1000:
                out.write_text(_inject_hooks(r.stdout.decode("utf-8")), encoding="utf-8")
                return out
    raise SystemExit("could not recover %s from git history" % name)


def game_block(html):
    """Just the GAME <script> block, selected by the same markers gamecheck.sh uses.

    Any suite that greps the raw file is also grepping three.js (one ~607 KB minified line) and the
    base64 audio bank, so a source assertion can pass or fail on vendored code it never meant to
    look at. That is the same "never select a script block by size / never scan the whole file"
    trap HANDOFF 2.7 records. Scope source assertions with this instead.
    """
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    game = [b for b in blocks if "PLAY_BOTTOM" in b and "function drawTray" in b]
    if len(game) != 1:
        raise SystemExit("expected exactly 1 game block, found %d" % len(game))
    return game[0]


def scratch():
    """A writable temp dir for screenshots and throwaway HTML."""
    d = pathlib.Path(tempfile.gettempdir()) / "fg-verify"
    d.mkdir(exist_ok=True)
    return d
