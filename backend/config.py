from dataclasses import dataclass
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "halaltrace.db"

def _read_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        f"{name} must be one of: 1, 0, true, false, yes, no, on, off"
    )


def _read_origins() -> tuple[str, ...]:
    raw_value = os.getenv(
        "HALALTRACE_FRONTEND_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    )
    return tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:

    app_name: str
    app_version: str
    environment: str
    database_path: Path
    use_ml_stub: bool
    frontend_origins: tuple[str, ...]


def load_settings() -> Settings:
    database_path = Path(
        os.getenv("HALALTRACE_DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
    ).expanduser()

    return Settings(
        app_name="HalalTrace API",
        app_version="0.1.0",
        environment=os.getenv("HALALTRACE_ENVIRONMENT", "development"),
        database_path=database_path,
        use_ml_stub=_read_bool("HALALTRACE_USE_ML_STUB", default=False),
        frontend_origins=_read_origins(),
    )


settings = load_settings()

