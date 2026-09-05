"""
tsfresh wrapper shared by every pipeline.

Each pipeline hands tsfresh a "long format" table (one row per
id/timestamp/reading) and gets back one row of auto-extracted statistical
features (mean, variance, skewness, autocorrelation, FFT coefficients, peak
counts, entropy, trend slope, etc.) per id. This is the "hand tsfresh more
features than you need" step -- mRMR/LASSO in common/selection.py does the
pruning afterwards.
"""

import pandas as pd
from tsfresh import extract_features
from tsfresh.feature_extraction import (
    ComprehensiveFCParameters,
    EfficientFCParameters,
    MinimalFCParameters,
)
from tsfresh.utilities.dataframe_functions import impute

FC_PARAMETER_PRESETS = {
    "minimal": MinimalFCParameters,
    "efficient": EfficientFCParameters,
    "comprehensive": ComprehensiveFCParameters,
}


def extract_tsfresh_features(
    long_df: pd.DataFrame,
    column_id: str,
    column_sort: str,
    fc_preset: str = "efficient",
    n_jobs: int = 0,
    disable_progressbar: bool = False,
) -> pd.DataFrame:
    """Run tsfresh over every numeric column in ``long_df`` (grouped by
    ``column_id``, ordered by ``column_sort``) and return one row of
    features per id, NaN/inf-imputed and ready for feature selection.

    ``fc_preset`` trades breadth for runtime:
      - "minimal":       ~10 features/column, seconds -- for wide datasets
                          (many sensor columns, e.g. TEP's 52 channels).
      - "efficient":      ~80 features/column, fast -- default, good balance.
      - "comprehensive":  ~180 features/column, slower -- max breadth for a
                          small number of channels (e.g. turbidity + temp).
    """
    fc_parameters = FC_PARAMETER_PRESETS[fc_preset]()
    value_cols = [
        c for c in long_df.columns
        if c not in (column_id, column_sort) and pd.api.types.is_numeric_dtype(long_df[c])
    ]
    features = extract_features(
        long_df[[column_id, column_sort, *value_cols]],
        column_id=column_id,
        column_sort=column_sort,
        default_fc_parameters=fc_parameters,
        n_jobs=n_jobs,
        disable_progressbar=disable_progressbar,
    )
    impute(features)
    return features
