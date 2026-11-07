"""Compare plant signals in the normal state vs the stressed state.

Usage:
    python scripts/compare_states.py data/general_stress [--out figures/general_stress]
    python scripts/compare_states.py --demo            # smoke test on the sample P1 recording

Input: a folder of per-plant recordings (.mat from the paper, or .raw) whose
file names start with the stressor, e.g. ``drought_G3C5.mat``,
``spidermites_B1.mat``, ``deficitFe2+_F4.mat``. Each recording is assumed to be
the first ``--day-hours`` (default 24) of normal state followed by the same
length of stressed state, as described in the dataset readme.

Outputs (PNG, written to --out, which is git-ignored):
    1_traces_by_stressor.png   one representative plant per stressor,
                               normal day on top, stressed day below (like
                               Figure 2 of the paper)
    2_all_plants_<stressor>.png every plant of that stressor, normal vs
                               stressed overlaid on the same axes
    3_features_by_stressor.png boxplots of per-minute variance and Hjorth
                               complexity, normal vs stressed, per stressor
    4_spectra_by_stressor.png  median power spectral density, normal vs
                               stressed, per stressor
    features_per_minute.csv    the per-window feature table behind figure 3
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.signal import welch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raw_loader import Recording, iter_recordings, load_raw  # noqa: E402

NORMAL, STRESSED = "normal", "stressed"
COLORS = {NORMAL: "tab:green", STRESSED: "tab:red"}
STRESSOR_LABELS = {
    "drought": "Drought",
    "spidermites": "Spider mites",
    "deficitMn2+": "Mn deficit",
    "deficitFe2+": "Fe deficit",
    "deficitN": "N deficit",
    "deficitCa2+": "Ca deficit",
}


# --------------------------------------------------------------------- helpers

def stressor_of(name: str) -> str:
    return name.split("_", 1)[0] if "_" in name else "unknown"


def split_days(rec: Recording, day_hours: float) -> dict[str, np.ndarray]:
    """First day_hours -> normal, next day_hours -> stressed."""
    n = int(day_hours * 3600 * rec.sample_rate)
    if rec.n_samples < 2 * n:
        n = rec.n_samples // 2
    return {NORMAL: rec.mv[:n], STRESSED: rec.mv[n:2 * n]}


def decimate(x: np.ndarray, n: int = 8000) -> tuple[np.ndarray, np.ndarray]:
    if x.size <= n:
        return np.arange(x.size), x
    idx = np.linspace(0, x.size - 1, n).astype(int)
    return idx, x[idx]


def hjorth(x: np.ndarray) -> tuple[float, float]:
    """Hjorth mobility and complexity of a 1-D signal."""
    dx = np.diff(x)
    ddx = np.diff(dx)
    v0, v1, v2 = np.var(x), np.var(dx), np.var(ddx)
    if v0 == 0 or v1 == 0:
        return np.nan, np.nan
    mob = np.sqrt(v1 / v0)
    comp = np.sqrt(v2 / v1) / mob
    return float(mob), float(comp)


def per_minute_features(x: np.ndarray, rate: float) -> pd.DataFrame:
    """Variance, IQR, Hjorth mobility/complexity for every 1-minute window."""
    w = int(60 * rate)
    rows = []
    for i in range(0, x.size - w + 1, w):
        seg = x[i:i + w]
        mob, comp = hjorth(seg)
        rows.append({
            "minute": i // w,
            "mean_mV": float(seg.mean()),
            "variance": float(seg.var()),
            "iqr": float(np.subtract(*np.percentile(seg, [75, 25]))),
            "hjorth_mobility": mob,
            "hjorth_complexity": comp,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- figures

def fig_traces_by_stressor(groups: dict, out: Path, day_hours: float) -> Path:
    stressors = sorted(groups)
    fig, axes = plt.subplots(2, len(stressors), figsize=(max(9, 4.2 * len(stressors)), 6.5), squeeze=False, constrained_layout=True)
    for j, s in enumerate(stressors):
        name, rec, days = groups[s][0]  # representative = first plant
        for i, state in enumerate((NORMAL, STRESSED)):
            ax = axes[i, j]
            idx, y = decimate(days[state])
            ax.plot(idx / rec.sample_rate / 3600, y, lw=0.4, color=COLORS[state])
            ax.set_xlim(0, day_hours)
            ax.set_ylabel("mV")
            if i == 0:
                ax.set_title(f"{STRESSOR_LABELS.get(s, s)}\n({name})", fontsize=10)
            if i == 1:
                ax.set_xlabel("hours into the day")
        axes[0, 0].text(-0.28, 0.5, "NORMAL", transform=axes[0, 0].transAxes, rotation=90, va="center", fontsize=12, color=COLORS[NORMAL])
        axes[1, 0].text(-0.28, 0.5, "STRESSED", transform=axes[1, 0].transAxes, rotation=90, va="center", fontsize=12, color=COLORS[STRESSED])
    fig.suptitle("One representative plant per stressor: normal day vs stressed day", fontsize=13)
    p = out / "1_traces_by_stressor.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    return p


def fig_all_plants(stressor: str, plants: list, out: Path, day_hours: float) -> Path:
    n = len(plants)
    cols = min(3, n)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 2.8 * rows), squeeze=False, constrained_layout=True)
    for k, (name, rec, days) in enumerate(plants):
        ax = axes[k // cols, k % cols]
        for state in (NORMAL, STRESSED):
            idx, y = decimate(days[state], 4000)
            ax.plot(idx / rec.sample_rate / 3600, y, lw=0.4, color=COLORS[state], alpha=0.8, label=state)
        ax.set_title(name, fontsize=9)
        ax.set_xlim(0, day_hours)
        ax.set_ylabel("mV")
    for k in range(n, rows * cols):
        axes[k // cols, k % cols].axis("off")
    axes[0, 0].legend(loc="upper right", fontsize=8)
    fig.suptitle(f"{STRESSOR_LABELS.get(stressor, stressor)}: every plant, normal (green) vs stressed (red)", fontsize=12)
    safe = re.sub(r"[^A-Za-z0-9]+", "", stressor)
    p = out / f"2_all_plants_{safe}.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    return p


def fig_features(feats: pd.DataFrame, out: Path) -> Path:
    stressors = sorted(feats["stressor"].unique())
    metrics = [("variance", "per-minute variance (mV²)", True), ("hjorth_complexity", "per-minute Hjorth complexity", False)]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(1.6 * len(stressors) + 4, 7.5), constrained_layout=True)
    for ax, (col, label, logy) in zip(axes, metrics):
        data, positions, colors = [], [], []
        for j, s in enumerate(stressors):
            for k, state in enumerate((NORMAL, STRESSED)):
                v = feats[(feats.stressor == s) & (feats.state == state)][col].dropna().values
                data.append(v); positions.append(j * 3 + k); colors.append(COLORS[state])
        bp = ax.boxplot(data, positions=positions, widths=0.8, showfliers=False, patch_artist=True)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.5)
        ax.set_xticks([j * 3 + 0.5 for j in range(len(stressors))])
        ax.set_xticklabels([STRESSOR_LABELS.get(s, s) for s in stressors])
        ax.set_ylabel(label)
        if logy:
            ax.set_yscale("log")
    axes[0].set_title("Normal (green) vs stressed (red), pooled over plants and minutes", fontsize=11)
    p = out / "3_features_by_stressor.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    return p


def fig_spectra(groups: dict, out: Path) -> Path:
    stressors = sorted(groups)
    fig, axes = plt.subplots(1, len(stressors), figsize=(max(7, 4.2 * len(stressors)), 3.8), squeeze=False, constrained_layout=True)
    for j, s in enumerate(stressors):
        ax = axes[0, j]
        for state in (NORMAL, STRESSED):
            psds = []
            for name, rec, days in groups[s]:
                x = days[state] - days[state].mean()
                nper = int(min(x.size, 256 * rec.sample_rate))  # <= 256 s windows
                f, pxx = welch(x, fs=rec.sample_rate, nperseg=max(16, nper))
                psds.append(pxx)
            med = np.median(np.vstack(psds), axis=0)
            ax.loglog(f[1:], med[1:], color=COLORS[state], label=state, lw=1)
        ax.set_title(STRESSOR_LABELS.get(s, s), fontsize=10)
        ax.set_xlabel("Hz")
        if j == 0:
            ax.set_ylabel("PSD (mV²/Hz), median over plants")
            ax.legend(fontsize=8)
    p = out / "4_spectra_by_stressor.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    return p


# ------------------------------------------------------------------------ main

def load_demo() -> list[Recording]:
    """Smoke-test input: first 48 h of the real 1 Hz sample recording, renamed."""
    root = Path("data/etl_bundle/etl-raw-to-parquet-zip/psr-file-handler/test/raw_files_dir/correct_raw_and_config")
    rec = load_raw(root / "P1.raw")
    n = int(48 * 3600 * rec.sample_rate)
    rec.mv = rec.mv[:n]
    rec.name = "demo_P1"
    return [rec]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--day-hours", type=float, default=24.0)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo:
        recs = load_demo()
        out = args.out or Path("figures/demo_compare_states")
    else:
        if not args.root:
            ap.error("give a data folder or --demo")
        recs = [r for r in iter_recordings(args.root) if r.n_samples > 0]
        out = args.out or Path("figures") / args.root.name
    out.mkdir(parents=True, exist_ok=True)
    if not recs:
        print("no recordings found"); return

    groups: dict[str, list] = defaultdict(list)
    feat_rows = []
    for rec in recs:
        days = split_days(rec, args.day_hours)
        s = stressor_of(rec.name)
        groups[s].append((rec.name, rec, days))
        for state, x in days.items():
            f = per_minute_features(x, rec.sample_rate)
            f.insert(0, "state", state); f.insert(0, "plant", rec.name); f.insert(0, "stressor", s)
            feat_rows.append(f)
        print(f"{rec.name}: stressor={s} rate={rec.sample_rate:g} Hz, {rec.n_samples / rec.sample_rate / 3600:.1f} h -> "
              f"{len(days[NORMAL]) / rec.sample_rate / 3600:.1f} h normal + {len(days[STRESSED]) / rec.sample_rate / 3600:.1f} h stressed")

    feats = pd.concat(feat_rows, ignore_index=True)
    feats.to_csv(out / "features_per_minute.csv", index=False)

    print("wrote", fig_traces_by_stressor(groups, out, args.day_hours))
    for s, plants in groups.items():
        print("wrote", fig_all_plants(s, plants, out, args.day_hours))
    print("wrote", fig_features(feats, out))
    print("wrote", fig_spectra(groups, out))

    summary = feats.groupby(["stressor", "state"])[["variance", "hjorth_complexity"]].median()
    print("\nMedian per-minute features:\n", summary.to_string())


if __name__ == "__main__":
    main()
