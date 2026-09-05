"""
CIP pipeline runner: chains the 3 CIP-specific steps together.

  1. extract_features.py   -- domain features + tsfresh generic features
  2. feature_selection.py  -- mRMR + LASSO -> final feature set
  3. train_models.py       -- train + compare Decision Tree / Logistic
                               Regression / Linear SVM / RBF SVM

Uses synthetic placeholder cycles (generate_cip_data.py) until real
ESP32 turbidity/temp data replaces datasets/cip_raw_timeseries.csv.
"""

import extract_features
import feature_selection
import train_models


def main() -> dict:
    extract_features.main()
    feature_selection.main()
    return train_models.main()


if __name__ == "__main__":
    main()
