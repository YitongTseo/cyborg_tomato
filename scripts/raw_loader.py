"""Loaders for Vivent / PhytlSigns plant-electrophysiology recordings.

Two on-disk formats are supported:

* ``.raw`` + ``.txt`` (or ``.note``) config pairs, as produced by the devices.
  The .raw file is a flat stream of little-endian int32 samples; the config is
  a two-column CSV (``parameter,value``) holding sample_rate, mv_span,
  timezone, start_timestamp and stop_timestamp.
  Millivolts are recovered with ``mV = mv_span * int32 / 2**32``.

* ``.mat`` files as distributed with Najdenovska et al. 2021
  (Appl. Sci. 11, 5640): one file per plant with variables ``mV`` (signal)
  and ``calaxis`` (time axis). Recordings are 24 h normal state followed by
  24 h stressed state at 500 Hz.

No data is bundled in this repository; point the functions at a local,
git-ignored directory (see README.md).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_SAMPLE_RATE = 256.0
DEFAULT_MV_SPAN = 5000.0


@dataclass
class Recording:
    """One channel of signal plus the metadata needed to interpret it."""

    name: str
    mv: np.ndarray           # signal in millivolts
    sample_rate: float       # Hz
    start: dt.datetime | None  # UTC start time if known
    source: Path
    extra: dict

    @property
    def n_samples(self) -> int:
        return int(self.mv.size)

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.sample_rate

    @property
    def seconds(self) -> np.ndarray:
        """Elapsed time of each sample in seconds from the start."""
        return np.arange(self.n_samples) / self.sample_rate

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame({"seconds": self.seconds, "mV": self.mv})
        if self.start is not None:
            df["timestamp"] = self.start + pd.to_timedelta(df["seconds"], unit="s")
        return df

    def summary(self) -> dict:
        return {
            "name": self.name,
            "samples": self.n_samples,
            "rate_hz": self.sample_rate,
            "hours": round(self.duration_s / 3600, 2),
            "start_utc": self.start.isoformat(timespec="seconds") if self.start else "",
            "mv_min": float(np.nanmin(self.mv)) if self.n_samples else np.nan,
            "mv_mean": float(np.nanmean(self.mv)) if self.n_samples else np.nan,
            "mv_max": float(np.nanmax(self.mv)) if self.n_samples else np.nan,
            "flat": bool(self.n_samples and np.nanstd(self.mv) == 0),
        }


# --------------------------------------------------------------------------- .raw

def load_config(path: Path) -> dict:
    """Parse a ``parameter,value`` config file into a dict of floats/strings."""
    cfg: dict = {}
    for line in Path(path).read_text().splitlines():
        key, _, value = line.strip().partition(",")
        key, value = key.strip(), value.strip()
        if not key or key == "parameter":
            continue
        try:
            cfg[key] = float(value)
        except ValueError:
            cfg[key] = value
    return cfg


def find_config_for(raw_path: Path) -> Path | None:
    """Locate the config file that belongs to a .raw file.

    Device uploads put one ``config.txt`` next to all channels; the ETL test
    fixtures use ``<stem>.txt``. Old recordings used ``.note``.
    """
    raw_path = Path(raw_path)
    candidates = [
        raw_path.with_suffix(".txt"),
        raw_path.with_suffix(".note"),
        raw_path.parent / "config.txt",
    ]
    for c in candidates:
        if c.exists():
            return c
    txts = sorted(raw_path.parent.glob("*.txt")) + sorted(raw_path.parent.glob("*.note"))
    return txts[0] if txts else None


def load_raw(raw_path: Path, config_path: Path | None = None) -> Recording:
    """Read a .raw file and convert it to millivolts using its config."""
    raw_path = Path(raw_path)
    config_path = Path(config_path) if config_path else find_config_for(raw_path)
    cfg = load_config(config_path) if config_path else {}

    counts = np.fromfile(raw_path, dtype="<i4")
    span = float(cfg.get("mv_span", DEFAULT_MV_SPAN))
    mv = span * counts.astype(np.float64) / 2**32

    rate = float(cfg.get("sample_rate", DEFAULT_SAMPLE_RATE))
    start = None
    if "start_timestamp" in cfg:
        start = dt.datetime.fromtimestamp(float(cfg["start_timestamp"]), tz=dt.timezone.utc)

    return Recording(
        name=raw_path.stem,
        mv=mv,
        sample_rate=rate,
        start=start,
        source=raw_path,
        extra={"config": str(config_path) if config_path else None, **cfg},
    )


# --------------------------------------------------------------------------- .mat

def load_mat(mat_path: Path, sample_rate: float = 500.0) -> Recording:
    """Read one plant's .mat file from the 2021 general-stress dataset.

    The readme shipped with the data says each file holds ``mV`` (signal) and
    ``calaxis`` (time vector). The sample rate is inferred from ``calaxis``
    when it is present, otherwise ``sample_rate`` (paper: 500 Hz) is used.
    """
    from scipy.io import loadmat

    mat_path = Path(mat_path)
    try:
        m = loadmat(mat_path, squeeze_me=True)
    except NotImplementedError:
        # MATLAB v7.3 files are HDF5; fall back to h5py if available.
        import h5py

        with h5py.File(mat_path, "r") as f:
            m = {k: np.array(f[k]).squeeze() for k in f.keys()}

    keys = [k for k in m if not k.startswith("__")]
    if "mV" not in m:
        raise KeyError(f"{mat_path.name}: expected variable 'mV', found {keys}")
    mv = np.asarray(m["mV"], dtype=np.float64).ravel()

    rate = sample_rate
    calaxis = None
    if "calaxis" in m:
        calaxis = np.asarray(m["calaxis"], dtype=np.float64).ravel()
        if calaxis.size > 1:
            step = np.nanmedian(np.diff(calaxis))
            if step > 0:
                # calaxis may be in seconds or in MATLAB datenum days.
                rate = 1.0 / step if step < 1 else 1.0 / (step * 86400.0)

    return Recording(
        name=mat_path.stem,
        mv=mv,
        sample_rate=float(rate),
        start=None,
        source=mat_path,
        extra={"variables": keys, "calaxis_len": int(calaxis.size) if calaxis is not None else 0},
    )


# --------------------------------------------------------------------------- walk

def iter_recordings(root: Path):
    """Yield a Recording for every .raw or .mat file under ``root``."""
    root = Path(root)
    for p in sorted(root.rglob("*")):
        if "__MACOSX" in p.parts or p.name.startswith("._"):
            continue
        if p.suffix == ".raw":
            yield load_raw(p)
        elif p.suffix == ".mat":
            yield load_mat(p)
