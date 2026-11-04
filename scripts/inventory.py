"""Print a summary table of every recording found under a directory.

Usage:
    python scripts/inventory.py data/some_folder [--csv out.csv]

Walks the folder, loads each .raw / .mat file via raw_loader, and prints one
row per recording: sample count, rate, duration, start time, mV statistics and
whether the channel is flat (a constant signal usually means a flooded or
disconnected electrode).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raw_loader import iter_recordings  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, help="directory to scan (git-ignored data folder)")
    ap.add_argument("--csv", type=Path, help="optional path to write the table as CSV")
    args = ap.parse_args()

    rows = []
    for rec in iter_recordings(args.root):
        row = rec.summary()
        row["path"] = str(rec.source.relative_to(args.root))
        rows.append(row)

    if not rows:
        print(f"No .raw or .mat files found under {args.root}")
        return

    df = pd.DataFrame(rows)
    with pd.option_context("display.max_rows", 500, "display.width", 200, "display.float_format", "{:,.2f}".format):
        print(df.drop(columns=["path"]).to_string(index=False))
    print(f"\n{len(df)} recordings, {df['hours'].sum():,.1f} channel-hours total")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.csv, index=False)
        print(f"wrote {args.csv}")


if __name__ == "__main__":
    main()
