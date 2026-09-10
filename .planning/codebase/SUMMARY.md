# Brownfield Onboarding Summary: agent-guardrail

## Codebase At A Glance
- **Project Name**: `agent-guardrail`
- **Core Purpose**: Lightweight mock API server for verifying AI agent permission boundaries and fail-closed security guarantees prior to production API access.
- **Primary Stack**: Python 3.12+, FastAPI, Uvicorn, Pydantic, Pytest, Docker.
- **Entrypoint**: `src/policy_engine.py` (`uvicorn policy_engine:app --port 8080`)
- **Key Artifacts**:
  - `src/policy.json`: Configuration defining synthetic users and resource permissions.
  - `src/audit.jsonl`: Append-only machine-readable audit trail.
  - `tests/`: 3 regression test suites covering boolean validation, audit reasons, and agent attribution.

## Artifacts Generated During Onboarding

### 1. Codebase Map (`.planning/codebase/`)
- [STACK.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/STACK.md): Runtime, frameworks, dependencies, and environment configuration.
- [INTEGRATIONS.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/INTEGRATIONS.md): API routes, audit schema, headers, and agent framework targets.
- [ARCHITECTURE.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/ARCHITECTURE.md): System architecture, dynamic routing, fail-closed patterns, and audit lifecycle.
- [STRUCTURE.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/STRUCTURE.md): Directory layout, module breakdowns, and responsibilities.
- [CONVENTIONS.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/CONVENTIONS.md): PEP 8 standards, strict typing, audit-before-raise, and testing conventions.
- [TESTING.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/TESTING.md): Pytest suites (L1, L2, L3), test fixtures, and execution commands.
- [CONCERNS.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/codebase/CONCERNS.md): Technical debt, synchronous I/O, unauthenticated agent attribution, and roadmap opportunities.

### 2. Planning State (`.planning/`)
- [PROJECT.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/PROJECT.md): Core context, problem statement, invariants, and guarantees.
- [REQUIREMENTS.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/REQUIREMENTS.md): Baseline capabilities (REQ-01 through REQ-07) and planned features (REQ-08 through REQ-11).
- [ROADMAP.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/ROADMAP.md): Milestone 1 (Completed) and Milestone 2 (Phase 5: CI/CD, Phase 6: Framework Integrations, Phase 7: Dynamic Payloads).
- [STATE.md](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/STATE.md): Current position, key decisions, and active state.
- [config.json](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/.planning/config.json): Workflow configuration.

---

## Next Steps
To begin work on the next phase in the roadmap (e.g. CI/CD automation or framework integrations), run:
- `/gsd-plan-phase 5` to plan the automated CI/CD pipeline.
- `/gsd-progress` to inspect overall project status and next actions.
