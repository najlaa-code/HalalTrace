from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.ml_adapter import (
    InvalidPredictionError,
    PredictionService,
    PredictionUnavailableError,
)
from backend.schemas import MLReading, Verdict


def reading(t_sec: float) -> MLReading:
    return MLReading(t_sec=t_sec, turbidity_ntu=100.0 + t_sec, temp_c=72.0)


class PredictionServiceTests(unittest.TestCase):
    def test_stub_returns_explicit_development_result(self) -> None:
        result = PredictionService(use_stub=True).predict([reading(0)])

        self.assertEqual(result.verdict, Verdict.PASS)
        self.assertEqual(result.confidence, 0.5)
        self.assertTrue(result.development_stub)

    def test_predict_passes_complete_ordered_cycle_to_predictor(self) -> None:
        received: list[dict[str, float]] = []

        def fake_predictor(readings: list[dict[str, float]]) -> dict[str, object]:
            received.extend(readings)
            return {
                "verdict": "FAIL",
                "confidence": 0.91,
                "top_features": {"turbidity_peak": 103.0},
            }

        service = PredictionService()
        service._predictor = fake_predictor

        result = service.predict([reading(0), reading(3)])

        self.assertEqual([item["t_sec"] for item in received], [0.0, 3.0])
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.top_features, {"turbidity_peak": 103.0})

    def test_invalid_predictor_result_is_rejected(self) -> None:
        service = PredictionService()
        service._predictor = lambda _: {
            "verdict": "PASS",
            "confidence": float("nan"),
            "top_features": {},
        }

        with self.assertRaises(InvalidPredictionError):
            service.predict([reading(0)])

    def test_missing_artifacts_are_reported_without_importing_ml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            with patch("backend.ml_adapter.PROJECT_ROOT", Path(temp_directory)):
                with self.assertRaisesRegex(
                    PredictionUnavailableError,
                    "cip_model.pkl.*cip_report.json.*cip_selected_features.json",
                ):
                    PredictionService().predict([reading(0)])


if __name__ == "__main__":
    unittest.main()
