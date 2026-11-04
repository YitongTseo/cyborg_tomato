#!/usr/bin/env bash
# The exploratory shell commands used on 2026-11-04 to get a first look at the
# collaborator bundles without committing anything. Safe to re-run any time.
#
#   bash scripts/first_look.sh
set -uo pipefail
cd "$(dirname "$0")/.."

echo "===== repo state: nothing but code should be tracked ====="
git status --short --ignored
echo

echo "===== zips in the repo root (git-ignored) ====="
for z in *.zip; do
  [[ -f "$z" ]] || continue
  echo "--- $z ---"
  unzip -l "$z" | tail -n +4 | head -40
  echo "    file types:"
  unzip -Z1 "$z" | grep -v '/$' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -12 | sed 's/^/    /'
done
echo

echo "===== scan unpacked data/ for credentials or private links ====="
if [[ -d data ]]; then
  grep -rIniE 'password|passwd|secret|token|api[_-]?key|https?://' data \
    --exclude-dir=__MACOSX --exclude='*.txt.log' --exclude='log.txt' 2>/dev/null | head -30 \
    || echo "(none found)"
else
  echo "data/ not present; run scripts/setup_data.sh first"
fi
echo

echo "===== config files that accompany .raw recordings ====="
find data -type f \( -name '*.txt' -o -name '*.note' \) -path '*raw*' 2>/dev/null | while read -r f; do
  echo "--- $f ---"; cat "$f"; echo
done
