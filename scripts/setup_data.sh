#!/usr/bin/env bash
# Unpack the collaborator bundles into the git-ignored data/ folder.
#
# Expects, in the repo root (all git-ignored):
#   etl-raw-to-parquet-zip.zip     Nigel's ETL tool + sample .raw fixtures
#   OneDrive_*.zip                 paper PDFs + dataset readme (optional)
#   General stress paper to share Oct 2026/   same, already unzipped (optional)
#
# Everything lands under data/, which .gitignore excludes.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p data
if [[ -f etl-raw-to-parquet-zip.zip ]]; then
  unzip -q -o etl-raw-to-parquet-zip.zip -d data/etl_bundle
  rm -rf data/etl_bundle/__MACOSX
  echo "ETL bundle -> data/etl_bundle"
fi
for z in OneDrive_*.zip; do
  [[ -f "$z" ]] || continue
  unzip -q -o "$z" -d data/paper
  echo "$z -> data/paper"
done
if [[ -d "General stress paper to share Oct 2026" ]]; then
  mkdir -p data/paper
  cp -n "General stress paper to share Oct 2026"/* data/paper/ 2>/dev/null || true
  echo "paper folder -> data/paper"
fi

echo
echo "git must still see nothing but code:"
git status --short
