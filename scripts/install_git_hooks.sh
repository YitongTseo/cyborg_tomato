#!/usr/bin/env bash
# Install a pre-commit hook that refuses to commit collaborator data.
# Run once per clone:  bash scripts/install_git_hooks.sh
set -euo pipefail
cd "$(dirname "$0")/.."
HOOK=.git/hooks/pre-commit
cat > "$HOOK" <<'HOOK_EOF'
#!/usr/bin/env bash
# Block data files and anything over 5 MB from being committed.
set -euo pipefail
blocked_ext='\.(raw|mat|parquet|zip|pdf|note|env|csv|h5|hdf5|npy|npz|pkl)$'
blocked_path='^(data/|figures/|General stress paper|Nigels_advice\.txt|etl-raw-to-parquet)'
fail=0
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  if echo "$f" | grep -Eiq "$blocked_ext" || echo "$f" | grep -Eq "$blocked_path"; then
    echo "pre-commit: refusing to commit data file: $f" >&2; fail=1
  elif [[ -f "$f" ]] && [[ $(stat -f%z "$f" 2>/dev/null || stat -c%s "$f") -gt 5242880 ]]; then
    echo "pre-commit: refusing to commit file over 5 MB: $f" >&2; fail=1
  fi
done < <(git diff --cached --name-only --diff-filter=AM)
if [[ $fail -ne 0 ]]; then
  echo "pre-commit: this repo is public; collaborator data must stay local (see README.md)." >&2
  exit 1
fi
HOOK_EOF
chmod +x "$HOOK"
echo "installed $HOOK"
