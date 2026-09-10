# Technical Debt & Architecture Concerns

## Security & Access Control Considerations
1. **Permissive CORS Configuration**:
   - `CORSMiddleware` uses `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. While acceptable for local dev sandboxing, this must be documented or restricted if exposed in a shared or hosted environment.
2. **Unauthenticated Agent Attribution**:
   - `agent_id` and `X-Agent-Id` are untrusted client inputs without cryptographic signing or authentication tokens. Any agent can claim any identity.

## Concurrency & Performance Limits
1. **Synchronous File I/O in Async Handlers**:
   - `load_policy()` and `log_decision()` perform blocking synchronous file system reads and writes (`with open(...)`) inside an `async def` FastAPI endpoint.
   - For high-concurrency benchmarks or large audit logs, moving to async file I/O (e.g. `aiofiles`) or offloading to a threadpool (`run_in_threadpool`) / queue worker will prevent blocking the event loop.
2. **Global Write Lock Contention**:
   - `_audit_lock` synchronizes all audit writes across requests. In heavy parallel agent testing environments, disk write lock contention could impact throughput.

## Missing Features & Roadmap Gaps
1. **CI/CD & Automated Testing Pipeline**:
   - No GitHub Actions workflow exists yet to run automated pytest checks on pull requests.
2. **Framework Integration Examples**:
   - Missing concrete example scripts for popular agent frameworks like LangChain, CrewAI, AutoGen, and LangGraph.
3. **Custom Mock Return Data**:
   - Currently, all successful evaluations return a static `{"status": "simulated success"}` payload. There is no mechanism in `policy.json` to return resource-specific mock schemas/fixtures (e.g., sample emails or calendar events).
4. **Fine-Grained Policy Rules**:
   - Policy rules are strictly boolean (`read: true/false`). No support yet for parameter-level constraints (e.g., rate limits, payload size limits, or field-level filters).
