"""Boundary between the backend and Najlaa's cycle prediction module."""

from dataclasses import dataclass
import importlib
import math
import sys
from threading import Lock
from typing import Any, Callable, Mapping

from backend.config import PROJECT_ROOT
from backend.schemas import MLReading, Verdict


class PredictionUnavailableError(RuntimeError):
    """Raised when the predictor or its exported artifacts are unavailable."""


class InvalidPredictionError(RuntimeError):
    """Raised when the predictor returns data outside the backend contract."""


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
    """Load the ML entry point lazily and normalize its result."""

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
        raw_readings = [reading.model_dump() for reading in readings]
        try:
            raw_result = predictor(raw_readings)
        except Exception as exc:
            raise PredictionUnavailableError(
                "The cycle could not be evaluated by the ML predictor."
            ) from exc
        return self._normalize_result(raw_result)

    def _load_predictor(
        self,
    ) -> Callable[[list[dict[str, float]]], dict[str, Any]]:
        if self._predictor is not None:
            return self._predictor

        with self._load_lock:
            if self._predictor is not None:
                return self._predictor

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

            ml_dir = str(PROJECT_ROOT / "ML")
            added_to_path = ml_dir not in sys.path
            if added_to_path:
                sys.path.insert(0, ml_dir)
            try:
                module = importlib.import_module("predict_cycle")
                predictor = getattr(module, "predict_cycle")
                if not callable(predictor):
                    raise TypeError("predict_cycle is not callable")
                self._predictor = predictor
            except Exception as exc:
                raise PredictionUnavailableError(
                    "Najlaa's predict_cycle function could not be loaded."
                ) from exc
            finally:
                if added_to_path:
                    try:
                        sys.path.remove(ml_dir)
                    except ValueError:
                        pass

        return self._predictor

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
