"""
CIP pipeline, step 3: train + compare models.

Trains Decision Tree / Logistic Regression / Linear SVM / RBF SVM
(common/modeling.py) on the final feature set chosen by
feature_selection.py, and saves the best one alongside a readable
tree-rules dump for the pitch/Q&A.

Output: results/cip_<model>.joblib, results/cip_tree_rules.txt,
results/cip_tree.png, results/cip_report.json
"""

import pandas as pd

from common.modeling import train_and_compare
from common.paths import RESULTS_DIR

FEATURES_PATH = RESULTS_DIR / "cip_features_expanded.csv"
SELECTED_PATH = RESULTS_DIR / "cip_selected_features.csv"


def main() -> dict:
    df = pd.read_csv(FEATURES_PATH)
    selected_features = pd.read_csv(SELECTED_PATH)["selected_feature"].tolist()

    X = df[selected_features]
    y = (df["verdict"] == "FAIL").astype(int)  # 1 = FAIL (positive class)

    return train_and_compare(X, y, out_prefix="cip", results_dir=RESULTS_DIR, pos_label=1)


if __name__ == "__main__":
    main()
