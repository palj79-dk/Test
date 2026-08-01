#!/bin/bash
# The full definition of done: syntax, the two wave-progression guards, and every standing suite.
# Usage: tools/verify/run_all.sh [path/to/build.html]     (defaults to the newest fallengrid-v*.html)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="${1:-$(ls -1 "$ROOT"/fallengrid-v*.html | sort -V | tail -1)}"
export FG_TARGET="$TARGET"
echo "target: $TARGET"
echo

fail=0
echo "== 1. game block syntax =="
bash "$ROOT/tools/gamecheck.sh" "$TARGET" || fail=1

echo
echo "== 2. wave-progression guards (HANDOFF 1.10) =="
for pat in 'id: "nextwave"' 'S.countdown -= raw'; do
  n=$(grep -c "$pat" "$TARGET")
  if [ "$n" = "1" ]; then echo "OK   $pat"; else echo "FAIL $pat  (found $n, expected 1)"; fail=1; fi
done

echo
echo "== 3. filename/label agreement (the APK workflow enforces this too) =="
ver=$(echo "$TARGET" | sed -E 's#.*/fallengrid-v([0-9.]+)\.html#\1#')
if grep -q "V${ver} ·" "$TARGET"; then echo "OK   label matches v$ver"; else echo "FAIL label does not say V$ver"; fail=1; fi

echo
echo "== 4. suites =="
for f in "$ROOT"/tools/verify/verify*.py; do
  name=$(basename "$f" .py)
  printf "%-16s " "$name"
  if timeout 1800 python3 "$f" >/tmp/fg-$name.log 2>&1; then echo "PASS"; else echo "FAIL  (see /tmp/fg-$name.log)"; fail=1; fi
done

echo
[ $fail -eq 0 ] && echo "ALL GREEN" || echo "FAILURES ABOVE"
exit $fail
