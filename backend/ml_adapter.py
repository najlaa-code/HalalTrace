from dataclasses import dataclass
import importlib
import math
import sys
from typing import Any, Callable

from backend.config import PROJECT_ROOT
from backend.schemas import MLReading, Verdict


class PredictionUnavailableError(RuntimeError):
    pass


class InvalidPredictionError(RuntimeError):
    pass


@dataclass(frozen=True)
class MLAdapter:
    predict: Callable[[list[MLReading]], tuple[Verdict, float, dict[str, Any]]]

    @classmethod
    def load(cls) -> "MLAdapter":
        if "ml_adapter" in sys.modules:
            importlib.reload(sys.modules["ml_adapter"])
        ml_module = importlib.import_module("ml_adapter")
        return cls(predict=ml_module.predict)

    async def predict_async(self, readings: list[MLReading]) -> tuple[Verdict, float, dict[str, Any]]:
        loop = importlib.import_module("asyncio").get_running_loop()
        return await loop.run_in_executor(None, self.predict, readings)

class PredictionService:
    def __init__(self, use_stub: bool = False) -> None:
        self.use_stub = use_stub
        self._predictor: Callable[[list[dict[str, float]]], dict[str, Any]] | None = None

    def predict(self, readings: list[MLReading]) -> "PredictionOutput":
        if self.use_stub:
            return PredictionOutput(
                verdict=Verdict.PASS,
                confidence=1.0,
                top_features={},
                all_features={},
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

    def _load_predictor(self) -> Callable[[list[dict[str, float]]], dict[str, Any]]:

        ml_dir = str(PROJECT_ROOT / "ML")
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)
        try:
            module = importlib.import_module("predict_cycle")
            self._predictor = module.predict_cycle
        except Exception as exc:
            raise PredictionUnavailableError(
                "Najlaa's predict_cycle function could not be loaded."
            ) from exc
        return self._predictor

    @staticmethod
    def _normalize_result(raw_result: dict[str, Any]) -> PredictionOutput:
        try:
            verdict = Verdict(raw_result["verdict"])
            confidence = float(raw_result["confidence"])
            top_features = {
                str(name): float(value)
                for name, value in raw_result.get("top_features", {}).items()
            }
            all_features = {
                str(name): float(value)
                for name, value in raw_result.get("all_features", top_features).items()
            }
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidPredictionError(
                "The ML predictor returned an invalid result."
            ) from exc

        numeric_values = [confidence, *top_features.values(), *all_features.values()]
        if not 0 <= confidence <= 1 or not all(map(math.isfinite, numeric_values)):
            raise InvalidPredictionError(
                "The ML predictor returned non-finite values or invalid confidence."
            )
        
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
