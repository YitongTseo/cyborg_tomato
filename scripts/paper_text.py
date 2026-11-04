"""Dump the text of the PDFs that came with the dataset, for quick grepping.

Usage:
    python scripts/paper_text.py "data/General stress paper to share Oct 2026" [--out data/paper_text]

Writes one .txt per PDF into the (git-ignored) output folder and prints the
first page of each so you can confirm it extracted correctly.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/paper_text"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for pdf in sorted(args.folder.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        text = "\n\n".join(f"===== page {i + 1} =====\n{p.get_text()}" for i, p in enumerate(doc))
        target = args.out / (pdf.stem + ".txt")
        target.write_text(text)
        print(f"{pdf.name}: {len(doc)} pages -> {target}")
        print(doc[0].get_text()[:800], "\n...")


if __name__ == "__main__":
    main()
