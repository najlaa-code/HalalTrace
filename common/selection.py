"""
Shared mRMR + LASSO feature selection, used by every pipeline.

Workflow: hand tsfresh (or raw) features to two independent selectors --
  - LASSO (L1-logistic regression): which features survive regularization
  - mRMR (minimum Redundancy Maximum Relevance, via the `mrmr_selection`
    package -- Peng et al. 2005): which features are both relevant to the
    label and non-redundant with each other
Then combine: prefer features both methods agree on; fall back to the
union, ranked, if they don't overlap enough. This is the standard
"auto-extract everything, then prune to the handful that matter" workflow.
"""

import warnings

import numpy as np
import pandas as pd
from mrmr import mrmr_classif
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def run_lasso(X: pd.DataFrame, y: pd.Series, lasso_C: float = 0.3) -> pd.DataFrame:
    if y.nunique() < 2:
        raise ValueError(
            f"LASSO needs at least 2 classes in the label, got only {y.unique().tolist()} -- "
            "check the labeling thresholds/logic that produced y."
        )
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    # l1_ratio=1 is the current sklearn spelling of what used to be penalty="l1"
    clf = LogisticRegression(solver="liblinear", C=lasso_C, l1_ratio=1, random_state=42)
    clf.fit(Xs, y)
    result = pd.DataFrame({"feature": X.columns, "lasso_coef": clf.coef_[0]})
    result["lasso_abs_coef"] = result["lasso_coef"].abs()
    return result.sort_values("lasso_abs_coef", ascending=False).reset_index(drop=True)


def run_mrmr(X: pd.DataFrame, y: pd.Series, k: int) -> pd.DataFrame:
    k = min(k, X.shape[1])
    selected, relevance, redundancy = mrmr_classif(
        X=X, y=y, K=k, return_scores=True, show_progress=False,
    )
    return pd.DataFrame({
        "feature": selected,
        "mrmr_rank": range(1, len(selected) + 1),
        "relevance": [relevance[f] for f in selected],
    })


def select_features(
    X: pd.DataFrame,
    y: pd.Series,
    k_mrmr: int = 15,
    lasso_C: float = 0.3,
    final_n: int = 8,
    lasso_threshold: float = 1e-4,
    min_agreement: int = 3,
) -> dict:
    """Returns dict with lasso_ranking, mrmr_ranking, final_features."""
    X = X.loc[:, X.nunique(dropna=False) > 1]  # drop constant columns, mRMR chokes on them
    lasso_ranking = run_lasso(X, y, lasso_C)
    mrmr_ranking = run_mrmr(X, y, k_mrmr)

    lasso_top = set(lasso_ranking[lasso_ranking["lasso_abs_coef"] > lasso_threshold]["feature"].head(k_mrmr))
    mrmr_top = set(mrmr_ranking["feature"])
    agreement = sorted(lasso_top & mrmr_top)

    if len(agreement) >= min_agreement:
        final_features = agreement[:final_n]
    else:
        union_ranked = list(dict.fromkeys(
            list(lasso_ranking["feature"].head(final_n)) + list(mrmr_ranking["feature"].head(final_n))
        ))
        final_features = union_ranked[:final_n]

    return {
        "lasso_ranking": lasso_ranking,
        "mrmr_ranking": mrmr_ranking,
        "agreement": agreement,
        "final_features": final_features,
    }
