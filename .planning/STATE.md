# Project State

## Current Position
- **Milestone**: Milestone 2 (Ecosystem & Developer Experience).
- **Completed**: Phase 1-6 (Core Engine, Validation, Audit Trail, Docker, CI/CD, Report CLI, Python SDK, Framework Integrations).
- **Next Phase**: Phase 7 (Custom Mock Payloads & High-Throughput I/O).
- **Test Suite**: 45 / 45 pytest tests passing.

## Key Decisions Record
- **Strict Boolean Typing**: Reject any non-boolean policy values with `503` fail-closed to avoid Python truthiness traps.
- **Method-Action Binding**: Enforce HTTP verb alignment per action (`read` -> `GET`/`HEAD`, `write` -> `POST`/`PUT`/`PATCH`, `delete` -> `DELETE`, with zero-config verb fallback).
- **Audit-First Exception Handling**: Always write to `audit.jsonl` before raising `HTTPException` or `500` so unauthorized probes, syntax errors, and unexpected exceptions are fully traceable.
- **Modular Separation of Concerns**: Partitioned responsibilities into `policy.py`, `audit.py`, `engine.py`, `cli.py`, `client.py`, and `policy_engine.py`.
- **Non-Blocking Handlers**: Defined route handlers as synchronous functions (`def`) so FastAPI/Starlette schedules filesystem I/O onto worker threads.
- **Container Hardening**: Dedicated non-root user `guardrail`, `HEALTHCHECK`, declared volume for `/app/src`, and `.dockerignore`.
- **CI/CD Integration**: Added GitHub Actions workflow with matrix testing and smoke curl verification.
- **Zero-Dependency SDK**: Implemented `GuardrailClient` using Python standard library `urllib.request`.

## Blockers & Open Items
- None. Ready for Phase 7 (Custom Mock Payloads & High-Throughput I/O).
