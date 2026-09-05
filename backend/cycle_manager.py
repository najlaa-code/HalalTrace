from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock

from backend.schemas import CycleState, MLReading


class CycleError(Exception):
    pass


class CycleNotFoundError(CycleError):
    pass


class CycleConflictError(CycleError):
    pass


class InvalidCycleStateError(CycleError):
    pass


@dataclass
class ActiveCycle:
    line_id: str
    cycle_id: str
    started_at: datetime
    state: CycleState = CycleState.CLEANING
    readings: list[MLReading] = field(default_factory=list)
    verification_in_progress: bool = False


class CycleManager:
    def __init__(self) -> None:
        self._cycles: dict[tuple[str, str], ActiveCycle] = {}
        self._active_cycle_by_line: dict[str, str] = {}
        self._line_by_cycle_id: dict[str, str] = {}
        self._lock = RLock()

    def start_cycle(self, line_id: str, cycle_id: str) -> ActiveCycle:
        with self._lock:
            key = (line_id, cycle_id)
            if key in self._cycles:
                raise CycleConflictError(
                    f"Cycle {cycle_id!r} is already active on line {line_id!r}."
                )

            existing_line = self._line_by_cycle_id.get(cycle_id)
            if existing_line is not None:
                raise CycleConflictError(
                    f"Cycle id {cycle_id!r} is already active on line {existing_line!r}."
                )

            active_cycle_id = self._active_cycle_by_line.get(line_id)
            if active_cycle_id is not None:
                raise CycleConflictError(
                    f"Line {line_id!r} already has active cycle {active_cycle_id!r}."
                )

            cycle = ActiveCycle(
                line_id=line_id,
                cycle_id=cycle_id,
                started_at=datetime.now(timezone.utc),
            )
            self._cycles[key] = cycle
            self._active_cycle_by_line[line_id] = cycle_id
            self._line_by_cycle_id[cycle_id] = line_id
            return cycle

    def add_reading(
        self, line_id: str, cycle_id: str, reading: MLReading
    ) -> ActiveCycle:
        with self._lock:
            cycle = self._get_cycle(line_id, cycle_id)
            if cycle.state != CycleState.CLEANING:
                raise InvalidCycleStateError(
                    f"Cycle {cycle_id!r} is {cycle.state.value}; it is not accepting readings."
                )

            if cycle.readings and reading.t_sec <= cycle.readings[-1].t_sec:
                raise CycleConflictError(
                    "Reading timestamps must be strictly increasing within a cycle."
                )

            cycle.readings.append(reading)
            return cycle

    def begin_verification(self, line_id: str, cycle_id: str) -> ActiveCycle:
        with self._lock:
            cycle = self._get_cycle(line_id, cycle_id)
            if not cycle.readings:
                raise InvalidCycleStateError("A cycle cannot end without readings.")
            if cycle.state == CycleState.CLEANING:
                cycle.state = CycleState.VERIFYING
            elif cycle.state != CycleState.VERIFYING:
                raise InvalidCycleStateError(
                    f"Cycle {cycle_id!r} cannot be verified from state {cycle.state.value}."
                )
            if cycle.verification_in_progress:
                raise CycleConflictError(
                    f"Cycle {cycle_id!r} is already being verified."
                )
            cycle.verification_in_progress = True
            return cycle

    def verification_failed(self, line_id: str, cycle_id: str) -> None:
        with self._lock:
            cycle = self._get_cycle(line_id, cycle_id)
            if cycle.state != CycleState.VERIFYING:
                raise InvalidCycleStateError(
                    f"Cycle {cycle_id!r} is not being verified."
                )
            cycle.verification_in_progress = False

    def complete_cycle(self, line_id: str, cycle_id: str) -> None:
        with self._lock:
            cycle = self._get_cycle(line_id, cycle_id)
            if cycle.state != CycleState.VERIFYING:
                raise InvalidCycleStateError(
                    f"Cycle {cycle_id!r} is not being verified."
                )
            del self._cycles[(line_id, cycle_id)]
            self._active_cycle_by_line.pop(line_id, None)
            self._line_by_cycle_id.pop(cycle_id, None)

    def _get_cycle(self, line_id: str, cycle_id: str) -> ActiveCycle:
        try:
            return self._cycles[(line_id, cycle_id)]
        except KeyError as exc:
            raise CycleNotFoundError(
                f"No active cycle {cycle_id!r} exists on line {line_id!r}."
            ) from exc
