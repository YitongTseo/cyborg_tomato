# Data walkthrough

A plain-language tour of the data Nigel Wallbridge (Vivent) shared for the
tomato general-stress study. Read this first; `README.md` covers the tooling.

Last updated 7 Nov 2026. Figures referenced below are generated locally into
`figures/` (git-ignored) by `scripts/plot_recordings.py`; they will show up in
this document once you have run it.

---

## 1. The one-paragraph version

Vivent's PhytlSigns devices clip an electrode pair onto a tomato stem and record
the plant's electrical potential, in millivolts, continuously for days. For the
2021 paper *Identifying General Stress in Commercial Tomatoes Based on Machine
Learning Applied to Plant Electrophysiology* (Najdenovska et al., Appl. Sci.
11, 5640, open access), 36 greenhouse tomato plants were each recorded for 24 h
while healthy and 24 h while stressed, with the stress being drought, spider
mites, or one of four nutrient deficits. The paper chops those signals into
1-minute windows, computes 34 statistical features per window, and trains an
XGBoost classifier that tells "normal" from "stressed" with about 80 % accuracy.
What we have been given access to is that underlying signal dataset.

---

## 2. Two layers of "the data"

It helps to keep two things apart.

| Layer | What it is | Format | Have it? |
|---|---|---|---|
| **Device recordings** | What the PhytlSigns box writes to disk: one file per electrode channel, 8 channels per upload | `.raw` + `.txt` config | Only 3 small sample files (from Nigel's ETL tool) |
| **Paper dataset** | Curated, one file per plant, exactly 24 h normal + 24 h stressed | `.mat` (MATLAB), variables `mV` and `calaxis` | **Not yet downloaded** |

Nigel's note says the paper data lives in "an old directory in its original
`.raw` format" on NextCloud, while the readme that came with the paper PDFs
describes `.mat` files. Either way, the actual recordings are still on the
NextCloud share, which **expires at the end of November 2026**. The folder
downloaded on 4 Nov contains only the paper, its supplement, and that readme.

---

## 3. What is on disk right now

Everything below is git-ignored and lives under `data/` after running
`bash scripts/setup_data.sh`.

### 3a. `data/paper/` – the paper bundle

| File | What it is |
|---|---|
| `General Stress Paper (1).pdf` | The published article, 13 pages |
| `GeneralStress_SuppMat.pdf` | 3-page supplement: accuracy for every combination of feature groups |
| `Readme (copy).txt` | Dataset readme: file format, which plants are train vs test, which day is normal vs stressed |

The readme's key facts:

* each `.mat` file is one plant, named `<stressor>_<plantcode>`, e.g. `drought_G3C5`, `spidermites_B1`, `deficitFe2+_F4`
* `mV` is the signal, `calaxis` is the matching time vector
* **day 1 = normal state, day 2 = stressed state**
* 30 plants form the training set, 6 the test set (two drought, two spider mite, one Mn, one Ca); the exact list is in the readme

### 3b. `data/etl_bundle/` – Nigel's conversion tool

A 2021 Python project (`etl-raw-to-parquet`) that Vivent used to turn device
`.raw` folders into a partitioned Parquet dataset. Useful mainly as
documentation of the format; it is pinned to Python 3.6 / pandas 1.1 / pyarrow
2.0 and expects Docker. Inside:

| Path | What it is |
|---|---|
| `README.md` | Describes the `.raw` format, folder layout, and the Parquet schema |
| `app.py`, `psr-file-handler/RawHandler.py` | The ETL and the raw-file reader class (the reference implementation of the decoding) |
| `psr-file-handler/test/raw_files_dir/` | Three sample `.raw` recordings with configs (see §4) |
| `psr-file-handler/test/parquet_no_timezone/` | One example of the Parquet output |
| `log.txt` | 20 000-line debug log from a real run on Vivent's server (internal paths; keep private) |
| `ETL.env`, `run.sh` | Example environment settings; no secrets |

### 3c. The three sample recordings

`python scripts/inventory.py data/etl_bundle` gives:

| Recording | Samples | Rate | Duration | Start (UTC) | mV range | Note |
|---|---|---|---|---|---|---|
| `correct_raw_and_config/P1.raw` | 1 912 271 | 1 Hz | 22.1 days | 2021-01-11 | -223 to +215 | Real plant recording |
| `one/test.raw` | 4 963 782 | 256 Hz | 5.4 h | 2020-02-25 | 199 to 2000 | Synthetic square-wave test signal |
| `1.raw` | 7 680 | 256 Hz | 30 s | 2021-02-23 | -2500 flat | "Flooded" electrode test case |
| `multiple/1..3.raw` | 0 | – | – | – | – | Empty placeholders |

---

## 4. What a recording looks like

![overview](figures/etl_fixtures/overview.png)

### 4a. A real plant: `P1.raw`

![P1](figures/etl_fixtures/etl-raw-to-parquet-zip__psr-file-handler__test__raw_files_dir__correct_raw_and_config__P1.png)

Top panel, three weeks at 1 sample/s:

* The signal is a **slowly wandering baseline** in the range of a few hundred
  millivolts. Over hours it drifts; over days you can see repeating bumps.
  The paper calls this the *nychthemeral* (day/night) rhythm and it is the
  dominant structure in healthy-plant data.
* **Sudden steps** (around hour 95 and hour 355) are almost certainly
  interventions: electrode re-seating, irrigation, someone touching the plant.
  Expect these in the paper data too, and expect to have to decide whether to
  keep them.
* The **last ~30 hours get noisier**, typical of an electrode drying out or
  losing contact.

Middle panel, 60 s at full resolution: at 1 Hz the signal is smooth, about
1 mV of drift per minute. At the paper's 500 Hz you would instead see fast
fluctuations on top of this, which is where most of the 34 features live.

Bottom panel: the histogram is multimodal because the baseline sits at a few
different levels for days at a time. Any feature that depends on absolute
level (mean, min, max) will mostly be measuring *which plateau we are on*,
which is why the paper leans on level-independent features such as variance
and Hjorth complexity.

### 4b. A dead channel: `1.raw`

A constant -2500 mV (exactly `-mv_span/2`, the ADC's rail) means the
electrode is flooded, disconnected, or the channel was never wired. The ETL
has a "flooding detector" for this; `scripts/inventory.py` flags it in the
`flat` column. In an 8-channel upload it is normal for several channels to
look like this.

### 4c. The synthetic one: `test.raw`

![test](figures/etl_fixtures/etl-raw-to-parquet-zip__psr-file-handler__test__raw_files_dir__one__test.png)

Values jump between a handful of discrete levels (199, 630, 940, 2000 mV).
This is a generated fixture for unit tests, not a plant. Ignore it for
science; it is only useful for checking that decoding and timestamps work.

---

## 5. How plants behave under stress (from the paper, until our data arrives)

The paper's Figure 2 is the clearest picture of what we are going to see. It
shows one plant per stressor, 24 h healthy on top and 24 h stressed below,
with night shaded grey. Extracted locally to
`figures/paper/Fig2_normal_vs_stressed_by_stressor.png`
(the article is CC BY open access).

![Figure 2](figures/paper/Fig2_normal_vs_stressed_by_stressor.png)

What to look for, column by column:

| Stressor | Normal day | Stressed day | Rough reading |
|---|---|---|---|
| **Drought** | Flat and quiet at night (~20 mV), climbs to ~130 mV through the day, drops at dusk. Clean day/night rhythm. | Whole signal sits higher (100 to 200 mV), is far noisier, and the night-time quiet is gone; the rhythm is still visible but buried in fast fluctuations. | Wilting plant is "louder" at all hours; amplitude of fast activity is the giveaway. |
| **Ca deficit** | Small daytime hump (0 to 30 mV) over a quiet night baseline. | Baseline shifts negative, daytime hump is smaller, and the noise band is wider all day. | Subtler than drought: a loss of the daytime rise plus more high-frequency jitter. |
| **Spider mites** | Big, well-defined dawn rise (-60 to +100 mV) with a slow afternoon recovery. | Dawn rise collapses into a short spike; the rest of the day is bursty, square-ish noise with no diurnal shape. | The circadian structure falls apart; the signal switches between noisy and quiet in blocks. |

Three take-aways that match the paper's feature ranking:

1. **Absolute level is not diagnostic.** Healthy and stressed plants overlap
   in mV, and every plant has its own offset. That is why the mean rarely
   shows up as a top feature.
2. **Short-window variance is.** Within any 1-minute window, stressed plants
   fluctuate more. Variance is the single best feature in the supplement.
3. **Signal "shape" changes.** Hjorth complexity (how the frequency content
   wanders inside a window) is the most consistently ranked feature across
   window lengths. Stressed signals are less smooth, more irregular.

### 5a. Reproducing this view on the full dataset

`scripts/compare_states.py` is written for exactly this and has been
smoke-tested on the one real sample recording. Once the 36 plant files are in
`data/general_stress/`, run

```bash
python scripts/compare_states.py data/general_stress
```

and look in `figures/general_stress/` for:

| File | What it shows |
|---|---|
| `1_traces_by_stressor.png` | Figure 2 rebuilt from our data: one plant per stressor, normal row vs stressed row |
| `2_all_plants_<stressor>.png` | Every plant of that stressor with normal (green) and stressed (red) overlaid, so you can judge how consistent the effect is across plants |
| `3_features_by_stressor.png` | Boxplots of per-minute variance and Hjorth complexity, normal vs stressed, per stressor: the paper's two star features |
| `4_spectra_by_stressor.png` | Median power spectrum normal vs stressed, per stressor: where in frequency the extra activity lives |
| `features_per_minute.csv` | The per-window numbers behind the boxplots, ready for a classifier |

`--demo` runs the same pipeline on the first 48 h of the sample `P1`
recording (output in `figures/demo_compare_states/`). That is only a smoke
test: `P1` has no stressor and its "stressed" half is just hours 24 to 48.

---

## 6. Decoding the raw format by hand

A `.raw` file is nothing but little-endian 32-bit integers, one per sample.
Everything needed to interpret it is in the paired `.txt` config, which is a
two-column CSV:

```
parameter,value
sample_rate,256
mv_span,5000
timezone,2
start_timestamp,1582620317
stop_timestamp,1582620417.6009
```

Conversion, in three lines:

```python
import numpy as np
counts = np.fromfile("P1.raw", dtype="<i4")
mv = 5000 * counts / 2**32          # mv_span * int32 / 2^32
```

Points that bite:

* **Channels** are separate files; the channel number is the last character
  of the filename before `.raw`. One `config.txt` serves all 8.
* **Sample rate varies**: fixtures use 1 Hz and 256 Hz, the paper says 500 Hz.
  Never assume; read it from the config.
* **Timestamps are Unix seconds**, sometimes fractional. `timezone` is an
  hours offset the ETL stores but does not apply.
* Old recordings use `.note` instead of `.txt` for the config.
* `stop_timestamp` can be missing; the ETL then derives duration from the
  sample count.

For `.mat` files, `scripts/raw_loader.py::load_mat` reads `mV` and infers the
rate from `calaxis`; if the files are MATLAB v7.3 (HDF5) it falls back to
`h5py`, which you may need to `pip install`.

---

## 7. What the paper does with it (so you know what to reproduce)

1. **Notch filter** at 50 Hz and 100 Hz to remove mains hum.
2. **Sliding segments**: a segment of N windows of length l ending at time t0.
   In each window compute 34 features, in six groups:
   * basic stats: min, max, variance, skewness, kurtosis, IQR
   * signal-complexity: Hjorth mobility & complexity, Hurst exponent, wavelet entropy, RMS
   * shape: impulse, margin, shape, crest factor
   * frequency: centre, RMS, root variance
   * similarity to white/blue/brown/pink/purple noise
   * wavelet-decomposition stats at levels 1, 4, 8
   Then slide forward by one window and reuse the N-1 overlapping windows
   (this reuse is the paper's main speed-up).
3. **Label**: 0 if the segment ends in day 1 (normal), 1 if in day 2 (stressed).
4. **Model**: XGBoost, tuned over max_depth, min_child_weight, gamma, lambda,
   alpha, subsample, colsample_bytree. Train on 30 plants, test on 6.
5. **Headline result**: l = 1 min, N = 15 gives 80.2 % accuracy; 30 s windows
   collapse to ~57 %. Variance and Hjorth complexity are the most informative
   features; the supplement shows basic stats alone already reach 82.6 % on
   their split.

---

## 8. Open questions and next steps

* **Get the recordings.** Download the NextCloud directory itself (the `.mat`
  files or the `.raw` folders) into `data/general_stress/` before the link
  expires at the end of November 2026.
* **Confirm format and rate** on arrival with
  `python scripts/inventory.py data/general_stress`. Check that each plant is
  about 48 h long and that `calaxis` implies 500 Hz.
* **Find the day boundary.** The readme says day 1 is normal, day 2 stressed.
  Check whether `calaxis` carries absolute time so the night blocks line up
  with the paper's Figure 2.
* **Decide what to do with steps and dropouts** before computing features.
* **Reproduce the baseline**: 1-minute windows, 34 features, XGBoost, the
  readme's train/test split, target 80 % accuracy.

---

## 9. Glossary

| Term | Meaning |
|---|---|
| PhytlSigns | Vivent's plant electrophysiology recorder |
| PSR | Vivent's internal name for the raw file handler ("psr-file-handler") |
| mv_span | Full-scale voltage range of the ADC, usually 5000 mV |
| Flooded channel | A channel stuck at a rail value; electrode not making contact |
| Nychthemeral rhythm | The 24 h day/night cycle visible in the baseline |
| Hjorth complexity | A measure of how the signal's frequency content changes; the paper's star feature |
| Shard | In the ETL, one hour-sized chunk of a channel written as a Parquet file |
