"""
CIP pipeline, step 2: feature selection.

Runs LASSO + mRMR (common/selection.py) on the expanded feature table from
extract_features.py and combines them into a final feature set for
train_models.py.

Output: results/cip_selected_features.csv
"""

import pandas as pd

from common.paths import RESULTS_DIR
from common.selection import select_features

IN_PATH = RESULTS_DIR / "cip_features_expanded.csv"
OUT_PATH = RESULTS_DIR / "cip_selected_features.csv"

K_MRMR = 10       # how many features mRMR selects
LASSO_C = 0.3     # inverse regularization strength (lower = more sparsity)
FINAL_N = 6       # target size of final feature set for the models

NON_FEATURE_COLS = ["cycle_id", "true_label", "verdict"]


def main() -> list:
    df = pd.read_csv(IN_PATH)
    feature_names = [c for c in df.columns if c not in NON_FEATURE_COLS]
    X = df[feature_names]
    y = (df["verdict"] == "FAIL").astype(int)

    print(f"Running selection on {len(feature_names)} candidate features, {len(y)} cycles\n")
    result = select_features(X, y, k_mrmr=K_MRMR, lasso_C=LASSO_C, final_n=FINAL_N)

    print("=== Top LASSO features (by |coef|) ===")
    print(result["lasso_ranking"].head(10).to_string(index=False))
    print("\n=== mRMR-selected features ===")
    print(result["mrmr_ranking"].to_string(index=False))
    print(f"\nLASSO n mRMR agreement: {result['agreement']}")
    print(f"\n=== FINAL feature set for the models ({len(result['final_features'])}) ===")
    print(result["final_features"])

    pd.DataFrame({"selected_feature": result["final_features"]}).to_csv(OUT_PATH, index=False)
    print("\nSaved final feature list to", OUT_PATH)
    return result["final_features"]


if __name__ == "__main__":
    main()
