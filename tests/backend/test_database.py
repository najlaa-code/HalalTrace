from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from backend.database import AuditDatabase, DuplicateReceiptError
from backend.schemas import AuditReceipt, MLReading, Verdict


class AuditDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = AuditDatabase(
            Path(self.temp_directory.name) / "audit" / "halaltrace.db"
        )
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def receipt(self, cycle_id: str = "c-0007") -> AuditReceipt:
        started_at = datetime.now(timezone.utc)
        return AuditReceipt(
            line_id="line_A",
            cycle_id=cycle_id,
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=10),
            verdict=Verdict.PASS,
            confidence=0.87,
            peak_turbidity=812.3,
            time_above_threshold=270,
            readings=[MLReading(t_sec=0, turbidity_ntu=812.3, temp_c=19.1)],
            features={"turbidity_peak": 812.3, "temp_threshold_duration": 270},
            top_features={"turbidity_peak": 812.3},
            model_mode="real",
        )

    def test_receipt_round_trip(self) -> None:
        receipt = self.receipt()
        self.database.insert_receipt(receipt)

        stored = self.database.get_receipt(receipt.cycle_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored, receipt)

    def test_receipts_are_immutable(self) -> None:
        receipt = self.receipt()
        self.database.insert_receipt(receipt)

        with self.assertRaises(DuplicateReceiptError):
            self.database.insert_receipt(receipt)

    def test_audit_log_is_newest_first(self) -> None:
        older = self.receipt("c-old")
        newer = self.receipt("c-new").model_copy(
            update={"ended_at": older.ended_at + timedelta(minutes=1)}
        )
        self.database.insert_receipt(older)
        self.database.insert_receipt(newer)

        summaries = self.database.list_receipts(limit=10, offset=0)

        self.assertEqual([item.cycle_id for item in summaries], ["c-new", "c-old"])


if __name__ == "__main__":
    unittest.main()
