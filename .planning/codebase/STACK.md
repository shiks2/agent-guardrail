# Technology Stack

## Core Language & Runtime
- **Language**: Python 3.12+ (tested with `python:3.12-slim`)
- **Runtime Environment**: CPython on Linux / macOS / Windows

## Web Framework & Server
- **Web Framework**: FastAPI 0.115.0 (`fastapi`)
- **ASGI Server**: Uvicorn 0.30.0 (`uvicorn`)
- **Data Modeling & Validation**: Pydantic 2.7.0 (`pydantic`)
- **Environment Management**: python-dotenv 1.0.1 (`python-dotenv`)

## Concurrency & Synchronization
- Standard Library `threading.Lock` used for synchronizing file writes to `audit.jsonl`.

## Containerization & Deployment
- **Container**: Dockerfile based on `python:3.12-slim`
- **Exposed Port**: Default 8080 (configurable via `AGENT_GUARDRAIL_PORT` environment variable)

## Development & Test Tooling
- **Testing Framework**: `pytest` with `fastapi.testclient.TestClient`
- **Package Management**: `pip` with `requirements.txt`
