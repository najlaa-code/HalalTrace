import unittest

from backend.cycle_manager import (
    CycleConflictError,
    CycleManager,
    CycleNotFoundError,
    InvalidCycleStateError,
)
from backend.schemas import CycleState, MLReading


def reading(t_sec: float) -> MLReading:
    return MLReading(t_sec=t_sec, turbidity_ntu=100, temp_c=72)


class CycleManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = CycleManager()

    def test_complete_lifecycle(self) -> None:
        cycle = self.manager.start_cycle("line_A", "c-0007")
        self.assertEqual(cycle.state, CycleState.CLEANING)

        self.manager.add_reading("line_A", "c-0007", reading(0))
        verifying = self.manager.begin_verification("line_A", "c-0007")
        self.assertEqual(verifying.state, CycleState.VERIFYING)
        self.manager.complete_cycle("line_A", "c-0007")

        with self.assertRaises(CycleNotFoundError):
            self.manager.add_reading("line_A", "c-0007", reading(1))

    def test_one_active_cycle_per_line(self) -> None:
        self.manager.start_cycle("line_A", "c-0007")
        with self.assertRaises(CycleConflictError):
            self.manager.start_cycle("line_A", "c-0008")

    def test_cycle_ids_are_globally_unique_while_active(self) -> None:
        self.manager.start_cycle("line_A", "c-0007")
        with self.assertRaises(CycleConflictError):
            self.manager.start_cycle("line_B", "c-0007")

    def test_timestamps_must_increase(self) -> None:
        self.manager.start_cycle("line_A", "c-0007")
        self.manager.add_reading("line_A", "c-0007", reading(2))
        with self.assertRaises(CycleConflictError):
            self.manager.add_reading("line_A", "c-0007", reading(2))

    def test_empty_cycle_cannot_end(self) -> None:
        self.manager.start_cycle("line_A", "c-0007")
        with self.assertRaises(InvalidCycleStateError):
            self.manager.begin_verification("line_A", "c-0007")

    def test_failed_verification_can_be_retried(self) -> None:
        self.manager.start_cycle("line_A", "c-0007")
        self.manager.add_reading("line_A", "c-0007", reading(0))
        self.manager.begin_verification("line_A", "c-0007")

        with self.assertRaises(CycleConflictError):
            self.manager.begin_verification("line_A", "c-0007")

        self.manager.verification_failed("line_A", "c-0007")
        retried = self.manager.begin_verification("line_A", "c-0007")
        self.assertTrue(retried.verification_in_progress)


if __name__ == "__main__":
    unittest.main()
