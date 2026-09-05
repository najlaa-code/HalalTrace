from fastapi import FastAPI

from backend.config import settings
from backend.schemas import HealthResponse


app = FastAPI(
    title = settings.app_name,
    version = settings.app_version,
    description = "cycle based cleaning verification backend for HalalTrace.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status = "ok")


