"""Render overview figures for every recording under a directory.

Usage:
    python scripts/plot_recordings.py data/some_folder [--out figures]

For each recording a PNG is written with three panels:
  1. the full signal, decimated to ~20k points so long recordings stay readable
  2. a 60 s close-up from the middle of the recording at full resolution
  3. a histogram of the millivolt values

A final ``overview.png`` stacks the decimated traces of all recordings.
Figures are written to a git-ignored folder; they are derived from private
data and must not be committed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raw_loader import Recording, iter_recordings  # noqa: E402

MAX_POINTS = 20_000


def decimate(x: np.ndarray, n: int = MAX_POINTS) -> tuple[np.ndarray, np.ndarray]:
    """Return (index, value) for at most ``n`` evenly spaced samples."""
    if x.size <= n:
        return np.arange(x.size), x
    idx = np.linspace(0, x.size - 1, n).astype(int)
    return idx, x[idx]


def label_for(rec: Recording, root: Path) -> str:
    """Unique, filesystem-safe label built from the path relative to root."""
    rel = rec.source.relative_to(root).with_suffix("")
    return "__".join(rel.parts)


def plot_one(rec: Recording, out: Path, label: str) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), constrained_layout=True)
    fig.suptitle(f"{label}   {rec.sample_rate:g} Hz   {rec.duration_s / 3600:.2f} h   {rec.n_samples:,} samples")

    idx, y = decimate(rec.mv)
    hours = idx / rec.sample_rate / 3600
    axes[0].plot(hours, y, lw=0.5)
    axes[0].set(xlabel="hours from start", ylabel="mV", title="full recording (decimated)")

    win = int(60 * rec.sample_rate)
    mid = rec.n_samples // 2
    lo, hi = max(0, mid - win // 2), min(rec.n_samples, mid + win // 2)
    t = np.arange(lo, hi) / rec.sample_rate
    axes[1].plot(t - t[0] if t.size else t, rec.mv[lo:hi], lw=0.6)
    axes[1].set(xlabel="seconds", ylabel="mV", title="60 s close-up from the middle, full resolution")

    axes[2].hist(rec.mv[np.isfinite(rec.mv)], bins=200, color="tab:gray")
    axes[2].set(xlabel="mV", ylabel="count", title="value distribution")

    path = out / f"{label}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def plot_overview(recs: list[tuple[str, Recording]], out: Path) -> Path:
    fig, axes = plt.subplots(len(recs), 1, figsize=(11, 2.2 * len(recs)), sharex=False, constrained_layout=True)
    axes = np.atleast_1d(axes)
    for ax, (label, rec) in zip(axes, recs):
        idx, y = decimate(rec.mv, 5_000)
        ax.plot(idx / rec.sample_rate / 3600, y, lw=0.5)
        ax.set_ylabel("mV")
        ax.set_title(f"{label}  ({rec.sample_rate:g} Hz, {rec.duration_s / 3600:.1f} h)", fontsize=9, loc="left")
    axes[-1].set_xlabel("hours from start")
    path = out / "overview.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, default=Path("figures"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    recs = []
    for rec in iter_recordings(args.root):
        if rec.n_samples == 0:
            print("skipping empty recording", rec.source)
            continue
        recs.append((label_for(rec, args.root), rec))
    if not recs:
        print(f"No non-empty recordings under {args.root}")
        return
    for label, rec in recs:
        print("wrote", plot_one(rec, args.out, label))
    print("wrote", plot_overview(recs, args.out))


if __name__ == "__main__":
    main()
