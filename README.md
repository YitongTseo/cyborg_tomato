# cyborg_tomato

Tooling for exploring the plant-electrophysiology dataset behind
**Najdenovska et al. 2021, "Identifying General Stress in Commercial Tomatoes Based on
Machine Learning Applied to Plant Electrophysiology", Appl. Sci. 11, 5640**
(https://doi.org/10.3390/app11125640), shared privately by Nigel Wallbridge (Vivent).

> **This repository is public. The data is not ours and is never committed.**
> Only code and documentation live in git. Everything the collaborator sent stays in
> git-ignored folders on your machine (see *Data policy* below).

## What's in the repo

```
.
├── README.md                 this file
├── requirements.txt          numpy / pandas / scipy / matplotlib / pymupdf
├── .gitignore                blocks every data path and archive
└── scripts/
    ├── raw_loader.py         load .raw/.txt device recordings and the paper's .mat files
    ├── inventory.py          one-line summary per recording (samples, rate, hours, mV stats, flat?)
    ├── plot_recordings.py    PNG per recording (full trace, 60 s close-up, histogram) + overview
    ├── paper_text.py         dump the PDFs that came with the dataset to .txt for grepping
    ├── setup_data.sh         unzip the collaborator bundles into data/
    └── install_git_hooks.sh  pre-commit hook that refuses data files / anything > 5 MB
```

Git-ignored, local only (not in the repo):

```
├── Nigels_advice.txt                          collaborator's message describing the formats
├── etl-raw-to-parquet-zip.zip                 Vivent's Python ETL (raw -> parquet) + test fixtures
├── OneDrive_2026-11-04.zip                    paper PDF, supplementary PDF, dataset readme
├── General stress paper to share Oct 2026/    same, unzipped
├── data/                                      everything above, unpacked by scripts/setup_data.sh
│   ├── etl_bundle/                            Vivent ETL tool + sample .raw recordings
│   ├── paper/                                 PDFs + readme
│   └── paper_text/                            PDFs as .txt
└── figures/                                   plots generated from the data
```

## The dataset (what we have, what we're still missing)

From the readme shipped with the paper:

* 36 tomato plants (var. Admiro), PhytlSigns multichannel device, **500 Hz**.
* Each plant is one **`.mat` file** with variables `mV` (signal) and `calaxis` (time axis).
* Each recording is **24 h normal state followed by 24 h stressed state**.
* Stressors: drought (12 plants), spider mites (12), nutrient deficit (12: Mn, Fe, N, Ca x 3).
* Train/test split is listed in the readme: 30 plants train, 6 test
  (`deficitMn2+_B7, deficitCa2+_F4, drought_G1B6, drought_G3C3, spidermites_C1, spidermites_F5`).

**Status (4 Nov 2026):** the PDFs and readme have been downloaded. The 36 `.mat` files
(and/or the original `.raw` directory Nigel linked) have **not** been downloaded yet.
Nigel's NextCloud link expires at the end of November 2026.

### Raw device format (from Nigel's note and the ETL README)

* `.raw` = flat little-endian int32 samples, one file per channel, 8 channels per upload folder.
* Paired `.txt` (older: `.note`) config, CSV `parameter,value`: `sample_rate`, `mv_span`,
  `timezone`, `start_timestamp`, `stop_timestamp` (unix seconds).
* `mV = mv_span * int32 / 2**32`.
* A constant signal (e.g. -2500 mV) means a flooded or disconnected electrode.

## Quick start

```bash
pip install -r requirements.txt
bash scripts/install_git_hooks.sh      # once per clone: pre-commit guard against committing data
bash scripts/setup_data.sh             # unpack the zips into data/

# summary table of every .raw / .mat under a folder
python scripts/inventory.py data/etl_bundle --csv data/inventory.csv

# figures -> figures/<name>/
python scripts/plot_recordings.py data/etl_bundle --out figures/etl_fixtures

# once the paper's .mat files are downloaded into data/general_stress/:
python scripts/inventory.py data/general_stress
python scripts/plot_recordings.py data/general_stress --out figures/general_stress

# paper PDFs -> text
python scripts/paper_text.py data/paper --out data/paper_text
```

Use `python -I` when running scripts against freshly downloaded data if you want to be
strict about not importing anything from the data directory.

## Data policy

1. Never `git add` anything under `data/`, `figures/`, the zips, or the collaborator's note.
   `.gitignore` and the pre-commit hook both enforce this; do not use `git add -f`.
2. Before every commit, check `git status --short --ignored` and confirm only code is staged.
3. Do not upload the data or plots of it to third-party services.
4. Nigel's ETL bundle contains Vivent-internal logs and references a private GitHub
   submodule (`vivent-sarl/psr-file-handler`); treat it as confidential too.
