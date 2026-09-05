"""
Inference helper for the backend team (Aya).

Mirrors BioWatch's backend/ml_service.py "load artifacts, expose /predict"
pattern, but the request shape is fundamentally different: BioWatch's
model consumes a handful of named rolling-window scalars
(Turbidity_Delta_24h, Temp_Rolling_Mean_48h, ...) computed by the
backend itself. The CIP classifier consumes tsfresh + domain features
computed from the FULL raw per-second trace of one cycle, so the
backend can't hand-roll the feature dict the way compute_features() did
in server.py -- it has to hand this module the whole buffered cycle and
let it run the same feature-extraction code used at training time.

Usage from the backend (e.g. inside ml_service.py's /predict handler):

    from predict_cycle import predict_cycle
    result = predict_cycle(readings)
    # readings = [{"t_sec": 0, "turbidity_ntu": 812.3, "temp_c": 19.1}, ...]
    # result   = {"verdict": "PASS", "confidence": 0.87,
    #             "model": "decision_tree", "top_features": {...}}

Requires results/cip_model.pkl + results/cip_scaler.pkl +
results/cip_selected_features.json -- run export_for_backend.py once
after (re)training to produce them.
"""

import json

import joblib
import pandas as pd

from common.paths import RESULTS_DIR
from extract_features import domain_features
from common.ts_features import extract_tsfresh_features

MODEL_PATH = RESULTS_DIR / "cip_model.pkl"
SCALER_PATH = RESULTS_DIR / "cip_scaler.pkl"
FEATURES_PATH = RESULTS_DIR / "cip_selected_features.json"

_model = None
_scaler = None
_feature_names = None


def _load_artifacts():
    global _model, _scaler, _feature_names
    if not (MODEL_PATH.exists() and FEATURES_PATH.exists()):
        return
    _model = joblib.load(MODEL_PATH)
    _scaler = joblib.load(SCALER_PATH) if SCALER_PATH.exists() else None
    with open(FEATURES_PATH) as f:
        _feature_names = json.load(f)


_load_artifacts()


def predict_cycle(readings: list[dict]) -> dict:
    """readings: list of {"t_sec": float, "turbidity_ntu": float, "temp_c": float}
    for ONE closed cycle, in time order. Returns verdict + confidence."""
    if _model is None:
        raise RuntimeError(
            f"No model artifacts at {RESULTS_DIR} -- run train_models.py then "
            "export_for_backend.py first."
        )

    df = pd.DataFrame(readings)
    df["cycle_id"] = 0  # single cycle -- tsfresh still needs an id column

    t, turb, temp = df["t_sec"].values, df["turbidity_ntu"].values, df["temp_c"].values
    domain_row = domain_features(t, turb, temp)

    tsfresh_row = extract_tsfresh_features(
        df[["cycle_id", "t_sec", "turbidity_ntu", "temp_c"]],
        column_id="cycle_id", column_sort="t_sec", fc_preset="efficient",
        disable_progressbar=True,
    ).iloc[0].to_dict()

    all_features = {**domain_row, **tsfresh_row}
    X = pd.DataFrame([{f: all_features.get(f, 0.0) for f in _feature_names}])
    if _scaler is not None:
        X = pd.DataFrame(_scaler.transform(X), columns=_feature_names)

    pred = _model.predict(X)[0]  # 1 = FAIL, 0 = PASS
    proba = dict(zip(_model.classes_, _model.predict_proba(X)[0])) if hasattr(_model, "predict_proba") else {}
    confidence = float(proba.get(pred, 1.0))

    return {
        "verdict": "FAIL" if pred == 1 else "PASS",
        "confidence": round(confidence, 3),
        "top_features": {f: round(all_features.get(f, 0.0), 4) for f in _feature_names},
    }
