from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import create_app
from backend.ml_adapter import PredictionOutput, PredictionUnavailableError
from backend.schemas import MLReading, Verdict


def passing_predictor(readings: list[MLReading]) -> PredictionOutput:
    if not readings:
        raise AssertionError("Predictor must receive the complete cycle.")
    return PredictionOutput(
        verdict=Verdict.PASS,
        confidence=0.87,
        top_features={"turbidity_peak": 812.3},
        all_features={
            "turbidity_peak": 812.3,
            "temp_threshold_duration": 270.0,
        },
        peak_turbidity=812.3,
        time_above_threshold=270.0,
    )


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        test_settings = replace(
            settings,
            database_path=Path(self.temp_directory.name) / "halaltrace.db",
            frontend_origins=("http://localhost:5173",),
        )
        self.client_context = TestClient(
            create_app(test_settings, predictor=passing_predictor)
        )
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temp_directory.cleanup()

    def start_cycle(self, cycle_id: str = "c-0007"):
        return self.client.post(
            "/api/line/line_A/cycle/start", json={"cycle_id": cycle_id}
        )

    def add_reading(self, cycle_id: str = "c-0007", t_sec: float = 0):
        return self.client.post(
            "/api/line/line_A/reading",
            json={
                "cycle_id": cycle_id,
                "t_sec": t_sec,
                "turbidity_ntu": 812.3,
                "temp_c": 19.1,
            },
        )

    def end_cycle(self, cycle_id: str = "c-0007"):
        return self.client.post(
            "/api/line/line_A/cycle/end", json={"cycle_id": cycle_id}
        )

    def test_complete_cycle_and_read_audit_receipt(self) -> None:
        self.assertEqual(self.start_cycle().status_code, 201)
        self.assertEqual(self.add_reading(t_sec=0).status_code, 202)
        self.assertEqual(self.add_reading(t_sec=1).status_code, 202)

        verdict = self.end_cycle()
        summary = self.client.get("/api/audit-log")
        receipt = self.client.get("/api/cycle/c-0007")

        self.assertEqual(verdict.status_code, 200)
        self.assertEqual(verdict.json()["verdict"], "PASS")
        self.assertEqual(verdict.json()["topFeatures"], {"turbidity_peak": 812.3})
        self.assertEqual(len(summary.json()), 1)
        self.assertEqual(len(receipt.json()["readings"]), 2)
        self.assertEqual(
            receipt.json()["features"]["temp_threshold_duration"], 270.0
        )

    def test_end_is_idempotent(self) -> None:
        self.start_cycle()
        self.add_reading()

        first = self.end_cycle()
        second = self.end_cycle()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.client.get("/api/audit-log").json()), 1)

    def test_lifecycle_errors_do_not_call_predictor(self) -> None:
        before_start = self.add_reading()
        self.start_cycle()
        empty_end = self.end_cycle()

        self.assertEqual(before_start.status_code, 404)
        self.assertEqual(empty_end.status_code, 409)
        self.assertEqual(self.client.get("/api/audit-log").json(), [])

    def test_dashboard_receives_frozen_messages(self) -> None:
        with self.client.websocket_connect("/ws/dashboard") as websocket:
            self.start_cycle()
            self.assertEqual(
                websocket.receive_json(),
                {
                    "type": "cycle_state",
                    "lineId": "line_A",
                    "cycleId": "c-0007",
                    "state": "cleaning",
                },
            )

            self.add_reading()
            self.assertEqual(websocket.receive_json()["type"], "reading")

            self.end_cycle()
            self.assertEqual(websocket.receive_json()["state"], "verifying")
            self.assertEqual(websocket.receive_json()["state"], "passed")
            self.assertEqual(websocket.receive_json()["type"], "verdict")


class PredictionFailureTests(unittest.TestCase):
    def test_prediction_failure_keeps_cycle_for_retry(self) -> None:
        attempts = 0

        def flaky_predictor(readings: list[MLReading]) -> PredictionOutput:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise PredictionUnavailableError("Model unavailable for test.")
            return passing_predictor(readings)

        with tempfile.TemporaryDirectory() as temp_directory:
            test_settings = replace(
                settings, database_path=Path(temp_directory) / "halaltrace.db"
            )
            with TestClient(
                create_app(test_settings, predictor=flaky_predictor)
            ) as client:
                client.post(
                    "/api/line/line_A/cycle/start", json={"cycle_id": "c-retry"}
                )
                client.post(
                    "/api/line/line_A/reading",
                    json={
                        "cycle_id": "c-retry",
                        "t_sec": 0,
                        "turbidity_ntu": 100,
                        "temp_c": 72,
                    },
                )

                failed = client.post(
                    "/api/line/line_A/cycle/end", json={"cycle_id": "c-retry"}
                )
                retried = client.post(
                    "/api/line/line_A/cycle/end", json={"cycle_id": "c-retry"}
                )

                self.assertEqual(failed.status_code, 503)
                self.assertEqual(retried.status_code, 200)
                self.assertEqual(attempts, 2)


if __name__ == "__main__":
    unittest.main()
