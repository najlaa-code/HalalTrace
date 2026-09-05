"""
CIP pipeline, step 1: feature extraction.

Reads the raw per-second turbidity/temp time series
(datasets/cip_raw_timeseries.csv) and builds one feature row per cycle:

  - Manual domain features: each one ties to a physical/regulatory concept,
    so it's easy to reason about and explain in a pitch (turbidity AUC,
    decay rate, min turbidity in the final 60s, temp ramp time, temp
    overshoot, temp variance during hold, time-above-threshold ratio,
    cross-correlation between clearing and heating).
  - tsfresh generic features: hundreds of auto-extracted statistics
    (mean, variance, skewness, autocorrelation, FFT coefficients, peak
    counts, entropy, trend slope, etc.) computed independently on the
    turbidity and temperature channels.

Output: results/cip_features_expanded.csv (one row per cycle_id).
mRMR/LASSO (feature_selection.py) prunes this down next.
"""

import numpy as np
import pandas as pd
from scipy import stats

from common.paths import DATASETS_DIR, RESULTS_DIR
from common.ts_features import extract_tsfresh_features
import generate_cip_data

RAW_PATH = DATASETS_DIR / "cip_raw_timeseries.csv"
OUT_PATH = RESULTS_DIR / "cip_features_expanded.csv"

# regulatory thresholds (same as the generator)
TEMP_TARGET_MIN = 71.0
TEMP_TARGET_MAX = 82.0
TURBIDITY_CLEAR_THRESHOLD = 50.0
CYCLE_LENGTH = 600


def domain_features(t, turb, temp):
    """Physical/regulatory-concept features -- the ones worth explaining
    in a pitch or to a certifier, each computed straight off the raw
    turbidity/temp signal for one cycle."""
    feats = {}

    # --- turbidity: verifies rinse water ran clear ---
    feats["turbidity_peak"] = turb.max()
    below = turb < TURBIDITY_CLEAR_THRESHOLD
    feats["time_to_clear"] = t[below][0] if below.any() else float(CYCLE_LENGTH)
    feats["turbidity_auc"] = np.trapezoid(turb, t)  # total residue exposure over the cycle
    feats["min_turbidity_last_60s"] = turb[t >= (t[-1] - 60)].min()  # stayed clear once cleared?

    # exponential decay rate: fit log(turb) ~ -k*t on the first 200s (where decay happens)
    mask = (t <= 200) & (turb > 1)
    if mask.sum() > 5:
        lr = stats.linregress(t[mask], np.log(turb[mask]))
        feats["turbidity_decay_rate"] = -lr.slope  # positive = faster clearing
    else:
        feats["turbidity_decay_rate"] = 0.0

    # --- temperature: verifies sanitation cycle hit required thermal threshold ---
    feats["temp_threshold_duration"] = np.sum(temp >= TEMP_TARGET_MIN)
    feats["time_above_threshold_ratio"] = np.mean(temp >= TEMP_TARGET_MIN)  # fraction of cycle compliant
    feats["temp_overshoot"] = max(0.0, temp.max() - TEMP_TARGET_MAX)
    hold_phase = temp[t >= t[-1] // 2]
    feats["temp_variance_hold"] = hold_phase.var()  # stability of the hold phase
    ramp_idx = np.argmax(temp >= TEMP_TARGET_MIN) if (temp >= TEMP_TARGET_MIN).any() else len(t) - 1
    feats["temp_ramp_time"] = t[ramp_idx]  # time to first reach target

    # --- cross-signal: catches "fake pass" patterns a single threshold would miss ---
    turb_n = (turb - turb.mean()) / (turb.std() + 1e-6)
    temp_n = (temp - temp.mean()) / (temp.std() + 1e-6)
    feats["cross_correlation"] = float(np.corrcoef(turb_n, temp_n)[0, 1])

    return feats


def extract_all_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    domain_rows = []
    for cid, cycle_df in raw_df.groupby("cycle_id"):
        t = cycle_df["t_sec"].values
        turb = cycle_df["turbidity_ntu"].values
        temp = cycle_df["temp_c"].values
        row = {"cycle_id": cid}
        row.update(domain_features(t, turb, temp))
        row["true_label"] = cycle_df["true_label"].iloc[0]
        domain_rows.append(row)
    domain_df = pd.DataFrame(domain_rows).sort_values("cycle_id").reset_index(drop=True)

    tsfresh_df = extract_tsfresh_features(
        raw_df[["cycle_id", "t_sec", "turbidity_ntu", "temp_c"]],
        column_id="cycle_id",
        column_sort="t_sec",
        fc_preset="efficient",
    )
    tsfresh_df.index.name = "cycle_id"
    tsfresh_df = tsfresh_df.reset_index()

    merged = domain_df.merge(tsfresh_df, on="cycle_id", how="left")
    merged["verdict"] = np.where(merged["true_label"] == "PASS", "PASS", "FAIL")
    return merged


def main() -> pd.DataFrame:
    if not RAW_PATH.exists():
        print(f"{RAW_PATH} not found -- generating synthetic placeholder cycles.")
        generate_cip_data.main()

    raw_df = pd.read_csv(RAW_PATH)
    expanded_df = extract_all_features(raw_df)
    expanded_df.to_csv(OUT_PATH, index=False)

    n_feature_cols = expanded_df.shape[1] - 3  # minus cycle_id, true_label, verdict
    print(f"Expanded feature table: {expanded_df.shape[0]} cycles x {n_feature_cols} features")
    print("Saved to", OUT_PATH)
    return expanded_df


if __name__ == "__main__":
    df = main()
    print(df.head())
