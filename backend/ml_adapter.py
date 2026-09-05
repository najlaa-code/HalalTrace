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