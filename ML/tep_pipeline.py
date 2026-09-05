"""
Standalone pipeline: Tennessee Eastman Process (TEP) simulation data ->
fault/no-fault classifier.

TEP is a chemical-plant process simulation (52 sensor/actuator channels:
xmeas_1..41, xmv_1..11), not a food-processing line -- it's included as a
second independent proof that the tsfresh -> mRMR/LASSO -> classifier
workflow generalizes to real multivariate process time series, not just
the CIP rig. Kept separate from the CIP pipeline: different sensors,
different process, own label space (faultNumber == 0 vs != 0).

The full *_Training.RData files are 250k-5M rows; only the Training files
are used (Testing files are the same fault set, just held out, and would
roughly double load time for no pipeline benefit here) and a subsample of
simulation runs is taken per class -- see MAX_FAULTFREE_RUNS /
FAULT_NUMBERS / MAX_RUNS_PER_FAULT below -- to keep tsfresh extraction
tractable. The subsample is cached to datasets/_cache/tep_subsample.csv
after the first run so repeat runs skip the ~70s RData load.

Output: results/tep_<model>.joblib, results/tep_report.json
"""

import pandas as pd
import pyreadr

from common.modeling import train_and_compare
from common.paths import CACHE_DIR, DATASETS_DIR, RESULTS_DIR
from common.selection import select_features
from common.ts_features import extract_tsfresh_features

FAULTFREE_PATH = DATASETS_DIR / "TEP_FaultFree_Training.RData"
FAULTY_PATH = DATASETS_DIR / "TEP_Faulty_Training.RData"
CACHE_PATH = CACHE_DIR / "tep_subsample.csv"

# a representative subset of TEP's 20 fault types (mix of easy/subtle ones
# from the Rieth et al. benchmark), not all 20 -- keeps runtime reasonable
FAULT_NUMBERS = [1, 2, 4, 6, 8, 13]
MAX_FAULTFREE_RUNS = 20
MAX_RUNS_PER_FAULT = 12
FINAL_N = 8

VALUE_COLUMNS = [f"xmeas_{i}" for i in range(1, 42)] + [f"xmv_{i}" for i in range(1, 12)]


def _subsample_runs(df: pd.DataFrame, n_runs: int) -> pd.DataFrame:
    runs = sorted(df["simulationRun"].unique())[:n_runs]
    return df[df["simulationRun"].isin(runs)]


def load_subsample() -> pd.DataFrame:
    if CACHE_PATH.exists():
        print(f"Loading cached TEP subsample from {CACHE_PATH}")
        return pd.read_csv(CACHE_PATH)

    print(f"No cache found -- loading {FAULTFREE_PATH.name} (~20MB, fast)")
    faultfree = next(iter(pyreadr.read_r(str(FAULTFREE_PATH)).values()))
    faultfree = _subsample_runs(faultfree, MAX_FAULTFREE_RUNS)

    print(f"Loading {FAULTY_PATH.name} (~470MB, takes ~1min)")
    faulty_all = next(iter(pyreadr.read_r(str(FAULTY_PATH)).values()))
    faulty = pd.concat([
        _subsample_runs(faulty_all[faulty_all["faultNumber"] == fn], MAX_RUNS_PER_FAULT)
        for fn in FAULT_NUMBERS
    ], ignore_index=True)

    subsample = pd.concat([faultfree, faulty], ignore_index=True)
    subsample.to_csv(CACHE_PATH, index=False)
    print(f"Cached subsample ({len(subsample)} rows) to {CACHE_PATH}")
    return subsample


def main() -> dict:
    df = load_subsample()
    df["cycle_id"] = df["faultNumber"].astype(int).astype(str) + "_" + df["simulationRun"].astype(int).astype(str)

    labels = df.drop_duplicates("cycle_id").set_index("cycle_id")["faultNumber"].astype(int)
    y = (labels != 0).astype(int)  # 1 = fault present

    n_cycles = df["cycle_id"].nunique()
    print(f"{n_cycles} simulation runs ({df.groupby('cycle_id').size().iloc[0]} samples each), "
          f"{len(VALUE_COLUMNS)} process variables")
    print(y.value_counts().rename({0: "fault_free", 1: "faulty"}).to_string(), "\n")

    long_df = df[["cycle_id", "sample", *VALUE_COLUMNS]]
    # MinimalFCParameters: 52 channels x ~10 features/channel is already
    # hundreds of features -- Efficient/Comprehensive here would be far
    # too slow for this many wide, long-running simulation series
    features = extract_tsfresh_features(long_df, column_id="cycle_id", column_sort="sample", fc_preset="minimal")
    features = features.loc[y.index]

    selection = select_features(features, y, k_mrmr=min(FINAL_N + 7, features.shape[1]), final_n=FINAL_N)
    print("Selected features:", selection["final_features"])

    X_selected = features[selection["final_features"]]
    return train_and_compare(X_selected, y, out_prefix="tep", results_dir=RESULTS_DIR, pos_label=1)


if __name__ == "__main__":
    main()
