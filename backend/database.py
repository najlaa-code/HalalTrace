from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from backend.schemas import AuditReceipt, AuditSummary, MLReading, Verdict


class DuplicateReceiptError(Exception):
    pass


class AuditDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS completed_cycles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        line_id TEXT NOT NULL,
                        cycle_id TEXT NOT NULL UNIQUE,
                        started_at TEXT NOT NULL,
                        ended_at TEXT NOT NULL,
                        verdict TEXT NOT NULL CHECK (verdict IN ('PASS', 'FAIL')),
                        confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                        peak_turbidity REAL,
                        time_above_threshold REAL,
                        readings_json TEXT NOT NULL,
                        features_json TEXT NOT NULL,
                        top_features_json TEXT NOT NULL DEFAULT '{}',
                        model_mode TEXT NOT NULL DEFAULT 'real'
                            CHECK (model_mode IN ('real', 'development_stub')),
                        created_at TEXT NOT NULL
                    )
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(completed_cycles)"
                    ).fetchall()
                }
                if "top_features_json" not in columns:
                    connection.execute(
                        """
                        ALTER TABLE completed_cycles
                        ADD COLUMN top_features_json TEXT NOT NULL DEFAULT '{}'
                        """
                    )
                if "model_mode" not in columns:
                    connection.execute(
                        """
                        ALTER TABLE completed_cycles
                        ADD COLUMN model_mode TEXT NOT NULL DEFAULT 'real'
                        """
                    )

    def insert_receipt(self, receipt: AuditReceipt) -> None:
        readings_json = json.dumps(
            [reading.model_dump(mode="json") for reading in receipt.readings],
            sort_keys=True,
            separators=(",", ":"),
        )
        features_json = json.dumps(
            receipt.features, sort_keys=True, separators=(",", ":")
        )
        top_features_json = json.dumps(
            receipt.top_features, sort_keys=True, separators=(",", ":")
        )
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO completed_cycles (
                            line_id, cycle_id, started_at, ended_at, verdict,
                            confidence, peak_turbidity, time_above_threshold,
                            readings_json, features_json, top_features_json,
                            model_mode, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            receipt.line_id,
                            receipt.cycle_id,
                            receipt.started_at.isoformat(),
                            receipt.ended_at.isoformat(),
                            receipt.verdict.value,
                            receipt.confidence,
                            receipt.peak_turbidity,
                            receipt.time_above_threshold,
                            readings_json,
                            features_json,
                            top_features_json,
                            receipt.model_mode,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
        except sqlite3.IntegrityError as exc:
            raise DuplicateReceiptError(
                f"A receipt for cycle {receipt.cycle_id!r} already exists."
            ) from exc

    def get_receipt(self, cycle_id: str) -> AuditReceipt | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM completed_cycles WHERE cycle_id = ?", (cycle_id,)
            ).fetchone()
        return self._row_to_receipt(row) if row is not None else None

    def list_receipts(self, limit: int, offset: int) -> list[AuditSummary]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT line_id, cycle_id, started_at, ended_at, verdict,
                       confidence, peak_turbidity, time_above_threshold,
                       model_mode
                FROM completed_cycles
                ORDER BY ended_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        defaults = connection.execute("PRAGMA database_list").fetchall()
        if not any(row["file"] == str(self.path) for row in defaults):
            sqlite3.register_adapter(Path, str)
            sqlite3.register_converter("path", Path)
            connection.execute(f"ATTACH DATABASE ? AS main", (self.path,))
        return connection

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> AuditSummary:
        return AuditSummary(
            line_id=row["line_id"],
            cycle_id=row["cycle_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]),
            verdict=Verdict(row["verdict"]),
            confidence=row["confidence"],
            peak_turbidity=row["peak_turbidity"],
            time_above_threshold=row["time_above_threshold"],
            model_mode=row["model_mode"],
        )

    @classmethod
    def _row_to_receipt(cls, row: sqlite3.Row) -> AuditReceipt:
        summary = cls._row_to_summary(row)
        readings: list[dict[str, Any]] = json.loads(row["readings_json"])
        features: dict[str, float] = json.loads(row["features_json"])
        top_features: dict[str, float] = json.loads(row["top_features_json"])
        return AuditReceipt(
            **summary.model_dump(),
            readings=[MLReading.model_validate(item) for item in readings],
            features=features,
            top_features=top_features,
        )
