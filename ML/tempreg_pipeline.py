"""
Standalone pipeline: smart-manufacturing temperature regulation data ->
in-spec/out-of-spec classifier.

This dataset is one continuous PID-controlled temperature stream, not
discrete cleaning cycles, and it has no built-in pass/fail label. To turn
it into cycles: slice the stream into fixed-length windows (WINDOW_SIZE
rows each) and derive a label per window from the control error itself --
"out of spec" if the window's mean Steady-State Error crosses a
threshold, "in spec" otherwise. (Temperature Error itself reflects the
ramp-up transient and stays large all through the dataset, so it's not a
usable in/out-of-spec signal on its own -- Steady-State Error is the
settled-quality measure. Overshoot was tried too, but a per-window *max*
of a 0-10 range nearly always lands near the global max regardless of
window quality, so it doesn't discriminate at this window size -- it's
still handed to tsfresh as an input feature, just not used for the label
itself.) tsfresh then extracts generic
statistics per window per channel, same as the CIP pipeline, and
mRMR/LASSO + model training follow the same shared code path. Kept
separate from the CIP pipeline: different sensors, different process,
own label space.

Output: results/tempreg_<model>.joblib, results/tempreg_report.json
"""

import numpy as np
import pandas as pd

from common.modeling import train_and_compare
from common.paths import DATASETS_DIR, RESULTS_DIR
from common.selection import select_features
from common.ts_features import extract_tsfresh_features

IN_PATH = DATASETS_DIR / "ttemperature_regulation_smart_manufacturing.csv"

WINDOW_SIZE = 20                     # rows per synthetic "cycle"
STEADY_STATE_ERROR_THRESHOLD = 1.0   # degC mean steady-state error -> out of spec (~median split)
FINAL_N = 6

SENSOR_COLUMNS = [
    "Current Temperature (°C)",
    "Temperature Error (°C)",
    "PID Control Output (%)",
    "Fuzzy PID Control Output (%)",
    "Overshoot (°C)",
    "Response Time (s)",
    "Steady-State Error (°C)",
    "Ambient Temperature (°C)",
    "Humidity (%)",
]


def build_windows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.reset_index(drop=True)
    df["window_id"] = df.index // WINDOW_SIZE
    df = df[df.groupby("window_id")["window_id"].transform("size") == WINDOW_SIZE]  # drop partial tail window

    labels = df.groupby("window_id").agg(mean_steady_state_error=("Steady-State Error (°C)", "mean"))
    labels["label"] = (labels["mean_steady_state_error"] > STEADY_STATE_ERROR_THRESHOLD).astype(int)  # 1 = out of spec

    long_df = df[["window_id", *SENSOR_COLUMNS]].copy()
    long_df["t"] = df.groupby("window_id").cumcount()
    return long_df, labels["label"]


def main() -> dict:
    df = pd.read_csv(IN_PATH)
    long_df, y = build_windows(df)

    n_windows = long_df["window_id"].nunique()
    print(f"Loaded {len(df)} rows -> {n_windows} windows of {WINDOW_SIZE} rows each")
    print(y.value_counts().rename({0: "in_spec", 1: "out_of_spec"}).to_string(), "\n")

    features = extract_tsfresh_features(long_df, column_id="window_id", column_sort="t", fc_preset="efficient")
    features = features.loc[y.index]

    selection = select_features(features, y, k_mrmr=min(FINAL_N + 5, features.shape[1]), final_n=FINAL_N)
    print("Selected features:", selection["final_features"])

    X_selected = features[selection["final_features"]]
    return train_and_compare(X_selected, y, out_prefix="tempreg", results_dir=RESULTS_DIR, pos_label=1)


if __name__ == "__main__":
    main()
