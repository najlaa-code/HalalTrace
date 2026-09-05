"""
Packages the best CIP model (per results/cip_report.json) into the 3-file
artifact shape BioWatch's ml_service.py already knows how to load
(model.pkl / scaler.pkl / selected_features.json) -- so Aya's backend can
reuse that loading pattern almost unchanged.

Run this once after train_models.py produces results/cip_report.json.

Output: results/cip_model.pkl, results/cip_scaler.pkl,
results/cip_selected_features.json
"""

import json

import joblib

from common.paths import RESULTS_DIR

REPORT_PATH = RESULTS_DIR / "cip_report.json"


def main():
    with open(REPORT_PATH) as f:
        report = json.load(f)

    best_model_name = report["best_model"]
    bundle = joblib.load(RESULTS_DIR / f"cip_{best_model_name}.joblib")

    joblib.dump(bundle["model"], RESULTS_DIR / "cip_model.pkl")
    if bundle["scaler"] is not None:
        joblib.dump(bundle["scaler"], RESULTS_DIR / "cip_scaler.pkl")
    with open(RESULTS_DIR / "cip_selected_features.json", "w") as f:
        json.dump(bundle["feature_names"], f, indent=2)

    print(f"Exported best model ({best_model_name}, F1={report['metrics'][best_model_name]['f1']:.3f}) for backend:")
    print(f"  {RESULTS_DIR / 'cip_model.pkl'}")
    if bundle["scaler"] is not None:
        print(f"  {RESULTS_DIR / 'cip_scaler.pkl'}")
    print(f"  {RESULTS_DIR / 'cip_selected_features.json'}")


if __name__ == "__main__":
    main()
