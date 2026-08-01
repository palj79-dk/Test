#!/bin/bash
# Syntax-check the GAME script block only — never three.js, never the audio bank.
# The block is identified by two markers that appear in the game and nowhere else; if they ever
# match more or less than one block the check fails loudly rather than validating the wrong code.
# NEVER select a script block by size: three.js is the largest one.
set -u
F="${1:-}"; [ -z "$F" ] && { echo "usage: tools/gamecheck.sh <file.html>"; exit 2; }
OUT="$(mktemp -t gameblock.XXXXXX.js)"
trap 'rm -f "$OUT"' EXIT
python3 - "$F" "$OUT" <<'PY'
import re, sys
s = open(sys.argv[1], encoding='utf-8').read()
blocks = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
game = [b for b in blocks if 'PLAY_BOTTOM' in b and 'function drawTray' in b]
if len(game) != 1:
    print("FATAL: expected exactly 1 game block, found %d" % len(game)); sys.exit(1)
open(sys.argv[2], 'w', encoding='utf-8').write(game[0])
print("game block: %d chars" % len(game[0]))
PY
[ $? -ne 0 ] && exit 1
node --check "$OUT" && echo "GAME SYNTAX OK"
