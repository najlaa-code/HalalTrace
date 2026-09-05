"""Validated HTTP and WebSocket message shapes for HalalTrace."""

from datetime import datetime
from enum import Enum
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class StrictSchema(BaseModel):
    """Base schema that rejects undocumented request fields."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictSchema):
    status: Literal["ok"]
    model_mode: Literal["real", "development_stub"]


class CycleStartRequest(StrictSchema):
    cycle_id: Identifier


class CycleEndRequest(StrictSchema):
    cycle_id: Identifier


class ReadingRequest(StrictSchema):
    cycle_id: Identifier
    t_sec: float = Field(ge=0, strict=True)
    turbidity_ntu: float = Field(ge=0, strict=True)
    temp_c: float = Field(strict=True)

    @field_validator("t_sec", "turbidity_ntu", "temp_c")
    @classmethod
    def require_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sensor values must be finite numbers")
        return value


class MLReading(StrictSchema):
    """A reading in the exact shape accepted by Najlaa's predictor."""

    t_sec: float = Field(ge=0, strict=True)
    turbidity_ntu: float = Field(ge=0, strict=True)
    temp_c: float = Field(strict=True)

    @field_validator("t_sec", "turbidity_ntu", "temp_c")
    @classmethod
    def require_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sensor values must be finite numbers")
        return value


class CycleState(str, Enum):
    IDLE = "idle"
    CLEANING = "cleaning"
    VERIFYING = "verifying"
    PASSED = "passed"
    FAILED = "failed"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class DashboardSchema(StrictSchema):
    """Base for dashboard messages using the frozen camel-case contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ReadingMessage(DashboardSchema):
    type: Literal["reading"] = "reading"
    line_id: Identifier = Field(alias="lineId")
    cycle_id: Identifier = Field(alias="cycleId")
    ts: float = Field(ge=0)
    temp: float
    turbidity: float = Field(ge=0)

    @field_validator("ts", "temp", "turbidity")
    @classmethod
    def require_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sensor values must be finite numbers")
        return value


class CycleStateMessage(DashboardSchema):
    type: Literal["cycle_state"] = "cycle_state"
    line_id: Identifier = Field(alias="lineId")
    cycle_id: Identifier = Field(alias="cycleId")
    state: CycleState


class VerdictMessage(DashboardSchema):
    type: Literal["verdict"] = "verdict"
    line_id: Identifier = Field(alias="lineId")
    cycle_id: Identifier = Field(alias="cycleId")
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    top_features: dict[str, float] = Field(alias="topFeatures")

    @field_validator("confidence")
    @classmethod
    def require_finite_confidence(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("confidence must be a finite number")
        return value


class AuditSummary(StrictSchema):
    line_id: Identifier
    cycle_id: Identifier
    started_at: datetime
    ended_at: datetime
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    peak_turbidity: float | None = None
    time_above_threshold: float | None = None
    model_mode: Literal["real", "development_stub"]


class AuditReceipt(AuditSummary):
    readings: list[MLReading]
    features: dict[str, float]
    top_features: dict[str, float]
