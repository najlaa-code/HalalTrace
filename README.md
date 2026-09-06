# HalalTrace

HalalTrace verifies one complete cleaning-in-place cycle from its turbidity
and temperature trace. Hardware sends cycle events and readings to FastAPI;
the backend buffers them until cycle end, asks the ML predictor for one
PASS/FAIL verdict, stores a local SQLite audit receipt, and broadcasts live
updates to the dashboard.

## Backend status

The cycle-based backend provides:

- `POST /api/line/{line_id}/cycle/start`
- `POST /api/line/{line_id}/reading`
- `POST /api/line/{line_id}/cycle/end`
- `GET /api/audit-log`
- `GET /api/cycle/{cycle_id}`
- `WS /ws/dashboard`
- `GET /health`

Active cycles are buffered in memory. Completed receipts are stored in local
SQLite. A process restart preserves completed receipts but discards unfinished
cycles.

## Install

From the repository root:

```bash
python3 -m pip install -r backend/requirements.txt
```

The backend requirements include the root ML requirements because real
prediction imports Najlaa's existing pipeline.

## Run with the explicit development stub

The real model artifacts are not currently committed. For backend and frontend
development only, enable the clearly marked deterministic stub:

```bash
HALALTRACE_USE_ML_STUB=true python3 -m uvicorn backend.main:app --reload
```

The stub always returns `PASS` with confidence `0.5`. It is disabled by
default. Health and audit responses label its results as `development_stub`,
so they cannot be presented as real model receipts.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Simulate one cycle

Start it:

```bash
curl -X POST http://127.0.0.1:8000/api/line/line_A/cycle/start \
  -H 'Content-Type: application/json' \
  -d '{"cycle_id":"c-0007"}'
```

Send readings with strictly increasing `t_sec` values:

```bash
curl -X POST http://127.0.0.1:8000/api/line/line_A/reading \
  -H 'Content-Type: application/json' \
  -d '{"cycle_id":"c-0007","t_sec":0,"turbidity_ntu":812.3,"temp_c":19.1}'

curl -X POST http://127.0.0.1:8000/api/line/line_A/reading \
  -H 'Content-Type: application/json' \
  -d '{"cycle_id":"c-0007","t_sec":1,"turbidity_ntu":700.0,"temp_c":20.2}'
```

End it and trigger the one allowed prediction:

```bash
curl -X POST http://127.0.0.1:8000/api/line/line_A/cycle/end \
  -H 'Content-Type: application/json' \
  -d '{"cycle_id":"c-0007"}'
```

Read the stored receipt:

```bash
curl http://127.0.0.1:8000/api/audit-log
curl http://127.0.0.1:8000/api/cycle/c-0007
```

## Real ML mode

Leave `HALALTRACE_USE_ML_STUB` unset. Cycle end requires:

- `results/cip_model.pkl`
- `results/cip_selected_features.json`
- `results/cip_report.json`
- `results/cip_scaler.pkl` when the selected model uses scaling

The backend passes the complete ordered reading list directly to
`predict_cycle(readings)`. It does not duplicate feature extraction. If the
artifacts or predictor are unavailable, cycle end returns HTTP 503 and retains
the buffered readings for a retry; it does not create a false PASS or FAIL.

## Configuration

- `HALALTRACE_DATABASE_PATH`: SQLite path; defaults to
  `backend/data/halaltrace.db`.
- `HALALTRACE_USE_ML_STUB`: explicit `true`/`false`; defaults to `false`.
- `HALALTRACE_FRONTEND_ORIGINS`: comma-separated allowed browser origins;
  defaults to ports 3000 and 5173 on localhost.
- `HALALTRACE_ENVIRONMENT`: environment label; defaults to `development`.

Cycle IDs are treated as globally unique. One active cycle is allowed per
line, and readings must arrive with strictly increasing timestamps.

## Tests

The focused backend suite uses Python's standard library:

```bash
python3 -m unittest discover -s tests/backend -p 'test_*.py' -v
```

Tests use temporary SQLite databases and an injected predictor. They do not
contact hardware, shared databases, or external services.
