"""
Standalone pipeline: water_potability.csv -> potable/not-potable classifier.

This dataset has NO time axis (one row = one static water sample, not a
sensor time series), so tsfresh doesn't apply here -- there's no cycle to
extract statistics from. Its 9 raw chemistry columns (already includes its
own Turbidity reading) go straight into mRMR/LASSO feature selection and
model training. Kept separate from the CIP pipeline: this model classifies
a water sample's chemistry, not a cleaning cycle's sensor trace, and the
two are never merged into one feature space or label.

Output: results/potability_<model>.joblib, results/potability_report.json
"""

import pandas as pd

from common.modeling import train_and_compare
from common.paths import DATASETS_DIR, RESULTS_DIR
from common.selection import select_features

IN_PATH = DATASETS_DIR / "water_potability.csv"
FINAL_N = 6


def main() -> dict:
    df = pd.read_csv(IN_PATH)
    df = df.fillna(df.median(numeric_only=True))  # ph/Sulfate/Trihalomethanes have missing values

    feature_names = [c for c in df.columns if c != "Potability"]
    X = df[feature_names]
    y = df["Potability"].astype(int)  # 1 = potable

    print(f"Loaded {len(df)} water samples, {len(feature_names)} raw chemistry features (no time series)\n")
    selection = select_features(X, y, k_mrmr=min(FINAL_N + 3, len(feature_names)), final_n=FINAL_N)
    print("Selected features:", selection["final_features"])

    X_selected = X[selection["final_features"]]
    return train_and_compare(X_selected, y, out_prefix="potability", results_dir=RESULTS_DIR, pos_label=0)
    # pos_label=0 (non-potable): that's the "fraud/contamination" analog we care about catching


if __name__ == "__main__":
    main()
