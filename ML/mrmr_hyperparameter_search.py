"""
CIP pipeline, optional step between feature_selection.py and
train_models.py.

Sweeps mRMR's K (number of features selected) and cross-validates a
decision tree at each K to find how many features you actually need.
Answers: "more features from mRMR -> better tree, or just overfitting?"

Uses 5-fold stratified CV (not a single train/test split) since with
only a few hundred cycles a single split is noisy -- CV gives a more
honest picture of which K generalizes.

Output: results/mrmr_k_search.png (F1 vs K plot) + printed table +
        results/cip_selected_features.csv overwritten with the best K's
        features (so train_models.py automatically uses the searched-for
        optimum)
"""

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier

from common.paths import RESULTS_DIR
from common.selection import run_mrmr

FEATURES_PATH = RESULTS_DIR / "cip_features_expanded.csv"
OUT_PLOT_PATH = RESULTS_DIR / "mrmr_k_search.png"
OUT_SELECTED_PATH = RESULTS_DIR / "cip_selected_features.csv"

NON_FEATURE_COLS = ["cycle_id", "true_label", "verdict"]
K_RANGE = range(2, 21)          # try 2 to 20 features
CV_FOLDS = 5
TREE_MAX_DEPTH = 4
RANDOM_STATE = 42


def main():
    df = pd.read_csv(FEATURES_PATH)
    feature_names = [c for c in df.columns if c not in NON_FEATURE_COLS]
    X_full = df[feature_names]
    y = df["verdict"]

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)

    results = []
    max_k = max(K_RANGE)
    # compute the largest mRMR ranking once, then just take prefixes -- avoids
    # recomputing relevance/redundancy from scratch for every K
    full_ranking = run_mrmr(X_full, y, max_k)["feature"].tolist()

    for k in K_RANGE:
        selected = full_ranking[:k]
        X_k = df[selected]
        clf = DecisionTreeClassifier(
            max_depth=TREE_MAX_DEPTH, class_weight="balanced", random_state=RANDOM_STATE
        )
        scores = cross_val_score(clf, X_k, y, cv=cv, scoring="f1_macro")
        results.append({
            "k": k,
            "mean_f1": scores.mean(),
            "std_f1": scores.std(),
            "features": selected,
        })
        print(f"K={k:2d}  mean F1={scores.mean():.4f}  std={scores.std():.4f}")

    results_df = pd.DataFrame(results)
    best_row = results_df.loc[results_df["mean_f1"].idxmax()]

    # prefer the smallest K within 1% of the best score (Occam's razor --
    # don't pay for extra features that don't actually help)
    threshold = best_row["mean_f1"] - 0.01
    simplest_good = results_df[results_df["mean_f1"] >= threshold].sort_values("k").iloc[0]

    print(f"\nBest raw F1:      K={int(best_row['k'])}  (F1={best_row['mean_f1']:.4f})")
    print(f"Simplest good K:  K={int(simplest_good['k'])}  (F1={simplest_good['mean_f1']:.4f}, "
          f"within 1% of best -- recommended)")
    print(f"Recommended features: {simplest_good['features']}")

    # plot
    plt.figure(figsize=(9, 5))
    plt.errorbar(results_df["k"], results_df["mean_f1"], yerr=results_df["std_f1"],
                 marker="o", capsize=3)
    plt.axvline(simplest_good["k"], color="green", linestyle="--",
                label=f"recommended K={int(simplest_good['k'])}")
    plt.xlabel("Number of mRMR features (K)")
    plt.ylabel("Cross-validated F1 (macro)")
    plt.title("Decision tree performance vs. mRMR feature count")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_PLOT_PATH, dpi=150)
    print(f"\nPlot saved to {OUT_PLOT_PATH}")

    # overwrite selected features file with the recommended K's features
    pd.DataFrame({"selected_feature": simplest_good["features"]}).to_csv(OUT_SELECTED_PATH, index=False)
    print(f"Updated {OUT_SELECTED_PATH} with recommended K={int(simplest_good['k'])} features "
          f"-- re-run train_models.py to use them")

    return simplest_good.to_dict()


if __name__ == "__main__":
    main()