from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from backend.broadcaster import DashboardBroadcaster
from backend.config import Settings, settings
from backend.cycle_manager import (
    CycleConflictError,
    CycleError,
    CycleManager,
    CycleNotFoundError,
    InvalidCycleStateError,
)
from backend.database import AuditDatabase, DuplicateReceiptError
from backend.ml_adapter import (
    InvalidPredictionError,
    PredictionOutput,
    PredictionService,
    PredictionUnavailableError,
)
from backend.schemas import (
    AuditReceipt,
    AuditSummary,
    CycleEndRequest,
    CycleStartRequest,
    CycleState,
    CycleStateMessage,
    HealthResponse,
    Identifier,
    MLReading,
    ReadingMessage,
    ReadingRequest,
    VerdictMessage,
)


Predictor = Callable[[list[MLReading]], PredictionOutput]


def _cycle_http_error(exc: CycleError) -> HTTPException:
    if isinstance(exc, CycleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if isinstance(exc, (CycleConflictError, InvalidCycleStateError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected cycle state error.",
    )


def _verdict_message(receipt: AuditReceipt) -> VerdictMessage:
    return VerdictMessage(
        line_id=receipt.line_id,
        cycle_id=receipt.cycle_id,
        verdict=receipt.verdict,
        confidence=receipt.confidence,
        top_features=receipt.top_features,
    )


def create_app(
    app_settings: Settings = settings,
    *,
    database: AuditDatabase | None = None,
    cycle_manager: CycleManager | None = None,
    predictor: Predictor | None = None,
) -> FastAPI:
    db = database or AuditDatabase(app_settings.database_path)
    cycles = cycle_manager or CycleManager()

    prediction_service = PredictionService(use_stub=app_settings.use_ml_stub)
    predict = predictor or prediction_service.predict
    broadcaster = DashboardBroadcaster()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await run_in_threadpool(db.initialize)
        yield

    api = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Cleaning-cycle verification API for HalalTrace.",
        lifespan=lifespan,
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    api.state.settings = app_settings
    api.state.database = db
    api.state.cycle_manager = cycles
    api.state.predictor = predict
    api.state.broadcaster = broadcaster

    @api.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        mode = "development_stub" if app_settings.use_ml_stub else "real"
        return HealthResponse(status="ok", model_mode=mode)

    @api.post(
        "/api/line/{line_id}/cycle/start",
        response_model=CycleStateMessage, 
        status_code=status.HTTP_201_CREATED,
        tags=["cycles"],
    )
    async def start_cycle(
        line_id: Identifier, request: CycleStartRequest
    ) -> CycleStateMessage:
        if await run_in_threadpool(db.get_receipt, request.cycle_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cycle id {request.cycle_id!r} already has an audit receipt.",
            )
        try:
            cycles.start_cycle(line_id, request.cycle_id)
        except CycleError as exc:
            raise _cycle_http_error(exc) from exc

        message = CycleStateMessage(
            line_id=line_id,
            cycle_id=request.cycle_id,
            state=CycleState.CLEANING,
        )
        await broadcaster.broadcast(message)
        return message

    @api.post(
        "/api/line/{line_id}/reading",
        response_model=ReadingMessage,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["cycles"],
    )
    async def add_reading(
        line_id: Identifier, request: ReadingRequest
    ) -> ReadingMessage:
        reading = MLReading(
            t_sec=request.t_sec,
            turbidity_ntu=request.turbidity_ntu,
            temp_c=request.temp_c,
        )
        try:
            cycles.add_reading(line_id, request.cycle_id, reading)
        except CycleError as exc:
            raise _cycle_http_error(exc) from exc

        message = ReadingMessage(
            line_id=line_id,
            cycle_id=request.cycle_id,
            ts=reading.t_sec,
            temp=reading.temp_c,
            turbidity=reading.turbidity_ntu,
        )
        await broadcaster.broadcast(message)
        return message

    @api.post(
        "/api/line/{line_id}/cycle/end",
        response_model=VerdictMessage,
        tags=["cycles"],
    )
    async def end_cycle(
        line_id: Identifier, request: CycleEndRequest
    ) -> VerdictMessage:
        existing_receipt = await run_in_threadpool(db.get_receipt, request.cycle_id)
        if existing_receipt is not None:
            if existing_receipt.line_id != line_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cycle id {request.cycle_id!r} belongs to another line.",
                )
            return _verdict_message(existing_receipt)

        try:
            cycle = cycles.begin_verification(line_id, request.cycle_id)
        except CycleError as exc:
            raise _cycle_http_error(exc) from exc

        await broadcaster.broadcast(
            CycleStateMessage(
                line_id=line_id,
                cycle_id=request.cycle_id,
                state=CycleState.VERIFYING,
            )
        )

        readings = list(cycle.readings)
        ended_at = datetime.now(timezone.utc)
        try:
            prediction = await run_in_threadpool(predict, readings)
        except (PredictionUnavailableError, InvalidPredictionError) as exc:
            cycles.verification_failed(line_id, request.cycle_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            cycles.verification_failed(line_id, request.cycle_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The cycle could not be evaluated.",
            ) from exc

        receipt = AuditReceipt(
            line_id=line_id,
            cycle_id=request.cycle_id,
            started_at=cycle.started_at,
            ended_at=ended_at,
            verdict=prediction.verdict,
            confidence=prediction.confidence,
            peak_turbidity=prediction.peak_turbidity,
            time_above_threshold=prediction.time_above_threshold,
            readings=readings,
            features=prediction.all_features,
            top_features=prediction.top_features,
            model_mode=("development_stub" if prediction.development_stub else "real"),
        )
        try:
            await run_in_threadpool(db.insert_receipt, receipt)
        except DuplicateReceiptError:
            stored_receipt = await run_in_threadpool(
                db.get_receipt, request.cycle_id
            )
            if stored_receipt is None:
                cycles.verification_failed(line_id, request.cycle_id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The cycle receipt could not be stored uniquely.",
                )
            if stored_receipt.line_id != line_id:
                cycles.verification_failed(line_id, request.cycle_id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cycle id {request.cycle_id!r} belongs to another line.",
                )
            receipt = stored_receipt
        except Exception as exc:
            cycles.verification_failed(line_id, request.cycle_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The cycle was evaluated but its audit receipt could not be stored.",
            ) from exc

        cycles.complete_cycle(line_id, request.cycle_id)
        final_state = (
            CycleState.PASSED
            if receipt.verdict.value == "PASS"
            else CycleState.FAILED
        )
        await broadcaster.broadcast(
            CycleStateMessage(
                line_id=line_id,
                cycle_id=request.cycle_id,
                state=final_state,
            )
        )
        verdict_message = _verdict_message(receipt)
        await broadcaster.broadcast(verdict_message)
        return verdict_message

    @api.get(
        "/api/audit-log", response_model=list[AuditSummary], tags=["audit"]
    )
    async def audit_log(
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[AuditSummary]:
        return await run_in_threadpool(db.list_receipts, limit, offset)

    @api.get(
        "/api/cycle/{cycle_id}", response_model=AuditReceipt, tags=["audit"]
    )
    async def get_cycle(cycle_id: Identifier) -> AuditReceipt:
        receipt = await run_in_threadpool(db.get_receipt, cycle_id)
        if receipt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No completed cycle {cycle_id!r} was found.",
            )
        return receipt

    @api.websocket("/ws/dashboard")
    async def dashboard_socket(websocket: WebSocket) -> None:
        await broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await broadcaster.disconnect(websocket)

    return api


app = create_app()
