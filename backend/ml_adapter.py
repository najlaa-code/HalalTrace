from dataclasses import dataclass, replace
import importlib.util
import json
import math
from pathlib import Path
import sys
from threading import Lock
from typing import Any, Callable, Mapping

from backend.config import PROJECT_ROOT
from backend.schemas import MLReading, Verdict


class PredictionUnavailableError(RuntimeError):
    pass


class InvalidPredictionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PredictionOutput:
    verdict: Verdict
    confidence: float
    top_features: dict[str, float]
    all_features: dict[str, float]
    peak_turbidity: float | None
    time_above_threshold: float | None
    development_stub: bool = False


class PredictionService:
    def __init__(self, use_stub: bool = False) -> None:
        self.use_stub = use_stub
        self._predictor: Callable[[list[dict[str, float]]], dict[str, Any]] | None = None
        self._load_lock = Lock()

    def predict(self, readings: list[MLReading]) -> PredictionOutput:
        if self.use_stub:
            return PredictionOutput(
                verdict=Verdict.PASS,
                confidence=0.5,
                top_features={},
                all_features={},
                peak_turbidity=None,
                time_above_threshold=None,
                development_stub=True,
            )

        predictor = self._load_predictor()
        raw_readings = []
        for reading in readings:
            reading_dict = reading.model_dump()
            raw_readings.append(reading_dict)
        try:
            raw_result = predictor(raw_readings)
        except Exception as exc:
            raise PredictionUnavailableError(
                "The cycle could not be evaluated by the ML predictor."
            ) from exc
        result = self._normalize_result(raw_result)
        if result.peak_turbidity is None and readings:
            result = replace(
                result,
                peak_turbidity=max(reading.turbidity_ntu for reading in readings),
            )
        return result

    def _load_predictor(
        self,
    ) -> Callable[[list[dict[str, float]]], dict[str, Any]]:
        if self._predictor is not None:
            return self._predictor

        with self._load_lock:
            if self._load_lock is not None:
                return self._load_lock

            results_dir = PROJECT_ROOT / "results"
            required_paths = (
                results_dir / "cip_model.pkl",
                results_dir / "cip_selected_features.json",
                results_dir / "cip_report.json",
            )
            missing = [path.name for path in required_paths if not path.is_file()]
            if missing:
                raise PredictionUnavailableError(
                    "Missing ML artifacts: " + ", ".join(sorted(missing))
                )

            self._validate_artifacts(results_dir)

            ml_dir = str(PROJECT_ROOT / "ML")
            module_path = PROJECT_ROOT / "ML" / "predict_cycle.py"
            if not module_path.is_file():
                raise PredictionUnavailableError(
                    "Predict_cycle module is missing."
                )

            added_to_path = ml_dir not in sys.path
            if added_to_path:
                sys.path.insert(0, ml_dir)

            module_name = "_halaltrace_predict_cycle"
            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    raise ImportError("Could not create a predictor module spec.")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                predictor = getattr(module, "predict_cycle")
                if not callable(predictor):
                    raise TypeError("predict_cycle is not callable")
                self._predictor = predictor
            except Exception as exc:
                raise PredictionUnavailableError(
                    "predict_cycle function could not be loaded."
                ) from exc
            finally:
                if added_to_path:
                    try:
                        sys.path.remove(ml_dir)
                    except ValueError:
                        pass

        return self._predictor

    @staticmethod
    def _validate_artifacts(results_dir: Path) -> None:
        try:
            selected_features = json.loads(
                (results_dir / "cip_selected_features.json").read_text()
            )
            report = json.loads((results_dir / "cip_report.json").read_text())
            best_model = report["best_model"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PredictionUnavailableError(
                "The ML artifact metadata is invalid."
            ) from exc

        if not isinstance(selected_features, list) or not selected_features:
            raise PredictionUnavailableError(
                "The selected-feature artifact must contain a non-empty list."
            )
        if not all(isinstance(name, str) and name for name in selected_features):
            raise PredictionUnavailableError(
                "The selected-feature artifact contains invalid feature names."
            )

        supported_models = {
            "decision_tree",
            "logistic_regression",
            "svm_linear",
            "svm_rbf",
        }
        if best_model not in supported_models:
            raise PredictionUnavailableError(
                "The ML report names an unsupported model."
            )

        report_features = report.get("features")
        if report_features is not None and report_features != selected_features:
            raise PredictionUnavailableError(
                "The ML report and selected-feature artifact do not match."
            )

        scaler_path = results_dir / "cip_scaler.pkl"
        if best_model == "decision_tree" and scaler_path.exists():
            raise PredictionUnavailableError(
                "A decision-tree artifact must not include a scaler."
            )
        if best_model != "decision_tree" and not scaler_path.is_file():
            raise PredictionUnavailableError(
                "The selected ML model requires cip_scaler.pkl."
            )

    @staticmethod
    def _normalize_result(raw_result: Mapping[str, Any]) -> PredictionOutput:
        try:
            verdict = Verdict(raw_result["verdict"])
            confidence = float(raw_result["confidence"])
            top_features = PredictionService._numeric_mapping(
                raw_result.get("top_features", {}), "top_features"
            )
            all_features = PredictionService._numeric_mapping(
                raw_result.get("all_features", {}), "all_features"
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidPredictionError(
                "The ML predictor returned an invalid result."
            ) from exc

        numeric_values = [confidence, *top_features.values(), *all_features.values()]
        if not 0 <= confidence <= 1 or not all(map(math.isfinite, numeric_values)):
            raise InvalidPredictionError(
                "The ML predictor returned non-finite values or invalid confidence."
            )

        peak_turbidity = PredictionService._optional_float(
            raw_result.get("peak_turbidity", all_features.get("turbidity_peak"))
        )
        time_above_threshold = PredictionService._optional_float(
            raw_result.get(
                "time_above_threshold",
                all_features.get("temp_threshold_duration"),
            )
        )
        return PredictionOutput(
            verdict=verdict,
            confidence=confidence,
            top_features=top_features,
            all_features=all_features,
            peak_turbidity=peak_turbidity,
            time_above_threshold=time_above_threshold,
        )

    @staticmethod
    def _numeric_mapping(value: Any, field_name: str) -> dict[str, float]:
        if not isinstance(value, Mapping):
            raise InvalidPredictionError(f"{field_name} must be an object.")
        return {str(name): float(number) for name, number in value.items()}

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise InvalidPredictionError(
                "The ML predictor returned an invalid metric."
            ) from exc
        if not math.isfinite(number):
            raise InvalidPredictionError("The ML predictor returned a non-finite metric.")
        return number
