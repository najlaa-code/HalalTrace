import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import DEFAULT_DATABASE_PATH, load_settings
from backend.main import app
from backend.schemas import ReadingMessage, ReadingRequest, VerdictMessage


client = TestClient(app)


class FoundationTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "model_mode": "real"})

    def test_settings_use_safe_local_defaults(self) -> None:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"HALALTRACE_DATABASE_PATH", "HALALTRACE_USE_ML_STUB"}
        }
        with patch.dict(os.environ, environment, clear=True):
            current_settings = load_settings()

        self.assertEqual(current_settings.database_path, DEFAULT_DATABASE_PATH)
        self.assertFalse(current_settings.use_ml_stub)
        self.assertIsInstance(current_settings.database_path, Path)

    def test_reading_request_rejects_non_finite_values(self) -> None:
        with self.assertRaises(ValidationError):
            ReadingRequest(
                cycle_id="c-0007",
                t_sec=42,
                turbidity_ntu=float("nan"),
                temp_c=19.1,
            )

    def test_reading_request_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            ReadingRequest(
                cycle_id="c-0007",
                t_sec=42,
                turbidity_ntu=812.3,
                temp_c=19.1,
                unexpected=True,
            )

    def test_reading_request_rejects_numeric_strings(self) -> None:
        with self.assertRaises(ValidationError):
            ReadingRequest(
                cycle_id="c-0007",
                t_sec="42",
                turbidity_ntu=812.3,
                temp_c=19.1,
            )

    def test_dashboard_messages_use_frozen_field_names(self) -> None:
        reading = ReadingMessage(
            line_id="line_A",
            cycle_id="c-0007",
            ts=42,
            temp=19.1,
            turbidity=812.3,
        )
        verdict = VerdictMessage(
            line_id="line_A",
            cycle_id="c-0007",
            verdict="PASS",
            confidence=0.87,
            top_features={},
        )

        self.assertEqual(
            reading.model_dump(by_alias=True),
            {
                "type": "reading",
                "lineId": "line_A",
                "cycleId": "c-0007",
                "ts": 42.0,
                "temp": 19.1,
                "turbidity": 812.3,
            },
        )
        self.assertEqual(verdict.model_dump(by_alias=True)["topFeatures"], {})


if __name__ == "__main__":
    unittest.main()
