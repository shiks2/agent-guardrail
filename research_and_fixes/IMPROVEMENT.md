# IMPROVEMENT.md — Agent Brief

**Audience:** coding agents (and humans) tasked with improving `agent-guardrail`.
**Status of repo:** research complete. `RESEARCH.md` documents 11 verified findings (F1–F11); `tests/`
encodes the evidence; `src/policy_engine_hardened.py` is a working reference fix.
**Your job:** land the fixes in priority order without regressing behavior the README already
promises, and without overclaiming.

Read in this order before writing any code:

1. `RESEARCH.md` — what is broken and the exact PoC for each finding
2. `tests/test_guardrail_research.py` — executable evidence
3. `src/policy_engine.py` — the shipped engine (the thing you are changing)
4. `src/policy_engine_hardened.py` — a working reference implementation of the fixes
5. `src/policy.json` / `src/policy.hardened.json` — current vs extended policy format

---

## 0. TL;DR — do these in order

| # | Work item | Findings | Effort | Risk if skipped |
|---|---|---|---|---|
| **P0-1** | Promote the hardened engine to be `policy_engine.py` | F1–F5, F8, F10 | S | Safety tool fails open |
| **P0-2** | Migrate the test suite from "documents bugs" to "asserts fixes" | — | S | Suite goes red on purpose |
| **P0-3** | Zero-config method binding fallback | F2 | XS | Breaks "any resource works out of the box" |
| **P0-4** | Make every decision path incapable of a bare 500 | F4 | XS | Policy typo → crash, no audit line |
| **P1-1** | Stop doing blocking file I/O in an `async def` handler | F10, perf | M | p99 under load (unproven — measure first) |
| **P1-2** | Audit-log rotation + optional SQLite sink | F9, F10 | M | Unbounded disk growth; no tail query |
| **P1-3** | Docker hardening (non-root, volume, bind, healthcheck) | F8, F9 | S | Network-exposed unauth service, lost logs |
| **P1-4** | Remove unused dep, add CI, fix stale docs | F11 | S | Rot |
| **P2-1** | Benchmark with a *correct* harness and substantiate or delete the perf claims | — | M | Unfounded marketing numbers |
| **P2-2** | Make README/landing copy match the FAQ | — | S | False confidence = the core harm |
| **P2-3** | `instruction_provenance` as an authorization context attribute | — | L | The actual novel direction |
| **P2-4** | Attenuated capability-token mode | — | L | Structural fix; makes F1-class bugs unrepresentable |

Do **not** start P2 until P0 + P1 are merged, tested, and green.

---

## 1. Ground rules for agents

1. **Never weaken a test to make it pass.** If a test in
   `TestOriginalDocumentsCurrentBehavior` fails because you *fixed* the bug it documents, that is
   expected — follow P0-2 to migrate it, do not delete the assertion's intent.
2. **Fail closed, always.** Any new code path that cannot positively establish
   `(explicit JSON `true`) AND (method bound to action)` must produce `DENY` (or `503` for a broken
   policy), must write an audit line, and must never raise an unhandled exception into a `500`.
3. **The audit log is the product.** Every outcome — ALLOW, DENY, 404, 503 — gets one record with a
   machine-readable `reason`. No silent paths.
4. **Keep the public contract stable.**
   - Route: `/api/{resource}/{user_id}/{action}`
   - Globals that tests monkeypatch: `PY` module-level `POLICY_PATH`, `AUDIT_LOG_PATH`
   - Response on allow: `{"user", "resource", "action", "status": "simulated success"}` (additive
     keys like `"method"` are fine; removing/renaming is not)
   - Policy format stays backward compatible: the existing `policy.json` must keep working with
     zero edits. New keys (`action_methods`) are optional with sane defaults.
5. **No new runtime dependencies** without justification in the PR description. This is a
   deliberately tiny tool; `requirements.txt` has one unused dep to remove, not five to add.
6. **Small, reviewable commits**, one work item each, commit message referencing the finding ID
   (e.g. `fix(F1): reject non-boolean policy leaves`).
7. **Do not claim something the code doesn't do.** If you touch README or any copy, the claim must
   be reproducible with a command you paste into the PR.

---

## 2. Repo map & existing artifacts

```
agent-guardrail/
├── src/
│   ├── policy_engine.py           # SHIPPED engine — has F1–F5, F8, F10
│   ├── policy_engine_hardened.py  # reference fix — promote this (P0-1)
│   ├── policy.json                # shipped policy (2 users × 3 resources × 2 actions)
│   ├── policy.hardened.json       # same + "action_methods" binding block
│   └── __init__.py                # empty, unused when run per README
├── tests/
│   ├── conftest.py                # fixtures for both engines; patches POLICY_PATH/AUDIT_LOG_PATH
│   └── test_guardrail_research.py # 18 tests: bug evidence + fix assertions
├── RESEARCH.md                    # the findings, PoCs, threat model
├── IMPROVEMENT.md                 # this file
├── requirements.txt               # fastapi/uvicorn/pydantic/python-dotenv (last one unused)
├── requirements-dev.txt           # -r requirements.txt + httpx + pytest
├── Dockerfile
└── README.md
```

**Finding index** (details + PoC in `RESEARCH.md`): F1 fail-open on non-bool · F2 method/action
decoupled · F3 unknown-user unaudited · F4 malformed policy 500 · F5 unbounded `agent_id` ·
F6 403/404 enumeration · F7 bodies ignored · F8 wildcard CORS + `0.0.0.0` · F9 Docker log not
persisted · F10 process-local lock / blocking I/O · F11 stale deps/docs.

---

## 3. Verification protocol

Run this **before** your first change (record the output) and **after** every work item.

```bash
# 1. tests — must be green before you start, and green (with migrated assertions) after
.venv/bin/pytest tests/ -q

# 2. the two PoCs must be FIXED after P0-1 (they return 200 before)
cd src && uvicorn policy_engine:app --port 8099 &
printf '{"synthetic_users":{"alice":{"emails":{"read":"false"}}}}' > policy.json
curl -s -o /dev/null -w 'F1 quoted-false -> %{http_code} (want 503)\n' 127.0.0.1:8099/api/emails/alice/read
git checkout policy.json
curl -s -o /dev/null -w 'F2 DELETE/read -> %{http_code} (want 403)\n' -X DELETE 127.0.0.1:8099/api/emails/alice/read
curl -s -o /dev/null -w 'F3 unknown user -> %{http_code} (want 404 + audit line)\n' 127.0.0.1:8099/api/emails/ghost/read
curl -s -o /dev/null -w 'README alice read -> %{http_code} (want 200)\n' 127.0.0.1:8099/api/emails/alice/read

# 3. audit log must contain every one of the above with a reason
cat audit.jsonl | python3 -c "import sys,json;[print(json.loads(l)['decision'],json.loads(l)['reason']) for l in sys.stdin]"

# 4. the four README examples must still return exactly what the README says
#    (see "Quick start" in README.md) — this is the backward-compat gate
```

Do not mark a work item done unless all four sections pass.

---

## 4. Work items

### P0-1 — Promote the hardened engine *(findings F1, F2, F3, F4, F5, F8, F10)*

**Problem.** The shipped route coerces the policy leaf with Python truthiness
(`allowed = resource_policy.get(action, False)`), ignores `request.method`, raises before logging
unknown users, and has no schema validation.

**Target.** `src/policy_engine.py` behaves like `src/policy_engine_hardened.py`.

**Steps.**
1. Copy the decision logic from `policy_engine_hardened.py` into `policy_engine.py`.
2. Keep the module-level names `POLICY_PATH`, `AUDIT_LOG_PATH`, `app` (tests patch the first two).
3. Extend `src/policy.json` with the `action_methods` block from `src/policy.hardened.json` —
   **or** rely on `DEFAULT_ACTION_METHODS` if you complete P0-3. Either way the shipped policy must
   keep producing identical verdicts for the four README examples.
4. Keep `policy_engine_hardened.py` for one release with a header comment
   `# DEPRECATED: logic promoted into policy_engine.py; delete after <date>` — or delete it and
   update `tests/conftest.py` accordingly. Pick one, don't leave both live and divergent.

**Acceptance criteria.**
- [ ] `"read": "false"` / `1` / `["x"]` / `{"x":true}` / `null` each produce `503` + a `POLICY_ERROR`
      audit line (never `200`, never `500`).
- [ ] `DELETE /api/emails/alice/read` → `403`, audit `reason == "METHOD_MISMATCH"`, `method == "DELETE"`.
- [ ] `GET /api/emails/ghost/read` → `404` **and** an audit line with `reason == "UNKNOWN_USER"`.
- [ ] Missing `synthetic_users`, `null` resource map, invalid JSON → `503`, not `500`.
- [ ] Audit records contain `method` and `reason` fields.
- [ ] `agent_id` longer than 128 chars is truncated in the audit log; `X-Agent-Id` header is honored.
- [ ] All four original README examples return the same status codes as before.

**Out of scope.** Auth on the guardrail itself, multi-tenancy, policy DSL.

---

### P0-2 — Migrate the test suite from bug-evidence to fix-assertions

**Problem.** `TestOriginalDocumentsCurrentBehavior` asserts the *buggy* behavior (e.g. that quoted
`"false"` returns 200). After P0-1 those tests fail by design. Leaving them red, or deleting them,
both lose information.

**Target.** The suite asserts the fixed contract, and the historical evidence survives.

**Steps.**
1. Preserve the bug evidence by moving the PoC descriptions into `RESEARCH.md` (already there) and
   adding a `docs/REGRESSION.md` with the *before* status codes, if you want a permanent record.
2. Rewrite `tests/test_guardrail_research.py` to a single `TestEngine` class asserting fixed
   behavior, keeping the existing hardened-behavior tests verbatim.
3. Keep one test per finding, named `test_F<n>_<slug>`, so traceability survives refactors.
4. Add a regression test that runs the exact four README curls and asserts the documented payloads.

**Acceptance criteria.**
- [ ] `pytest tests/ -q` green.
- [ ] No test asserts a known-buggy outcome.
- [ ] Every F1–F5 has at least one named regression test.
- [ ] New test: policy `{"synthetic_users": {}}` (empty) is rejected, not silently allow-none.

---

### P0-3 — Zero-config method binding fallback *(finding F2)*

**Problem.** `policy_engine_hardened.py` denies `action` values that are not in `action_methods`
or `DEFAULT_ACTION_METHODS` with `UNBOUND_ACTION`. That is safe but breaks the README/landing
promise that *"any resource/action combination works out of the box."* Exotic actions like
`approve` or `export` would start denying.

**Target.** Keep fail-closed, keep zero-config for the common case.

**Steps.**
1. In `action_methods_for()`, after the explicit map and defaults, add a fallback: if
   `action.upper()` is a valid HTTP verb (`GET/POST/PUT/PATCH/DELETE/HEAD`), bind to that verb.
   So action `"delete"` → `DELETE`, action `"post"` → `POST`.
2. Only deny `UNBOUND_ACTION` when the action is neither mapped nor an HTTP verb.
3. Document in README: *"actions that are HTTP verbs bind automatically; any other action name
   must be listed in `action_methods`."*

**Acceptance criteria.**
- [ ] `{"timesheets": {"approve": true}}` with no `action_methods` → `403 UNBOUND_ACTION`, audited.
- [ ] Adding `"action_methods": {"approve": ["POST"]}` → `POST .../approve` returns 200 when allowed.
- [ ] `"export": true` action still deniable via the same mechanism.
- [ ] `DEFAULT_ACTION_METHODS` covers `read/write/delete` so the shipped `policy.json` needs no edit.

---

### P0-4 — No decision path may produce a bare 500 *(finding F4)*

**Problem.** An unhandled `PolicyError` (e.g. from the defensive `_require_bool` call inside the
route, or a future refactor) escapes as a `500` with no audit line.

**Target.** Wrap the entire handler body in `try/except PolicyError` → audit `POLICY_ERROR` → `503`.
Also add a global exception handler that audits then returns `500` with a generic body, so no future
bug produces an unaudited failure.

**Acceptance criteria.**
- [ ] Fuzzing `policy.json` with a dozen malformed shapes never yields a `500` without an audit line.
- [ ] Add a test that asserts the count of audit lines equals the count of requests for a malformed
      policy.

---

### P1-1 — Remove blocking I/O from the async handler *(F10, perf)*

**Problem.** `async def check_and_simulate` performs synchronous `open()` + `json.load()` and a
blocking `os.write` + `print()` on the event loop for *every* request, and re-parses the policy on
every request to implement hot-reload. This serializes the single-threaded server and is a plausible
cause of the (unverified) latency claims on the landing page.

**Target.** Non-blocking, and hot-reload preserved.

**Steps (pick one, justify in the PR).**
- **Preferred:** make the handler synchronous (`def check_and_simulate(...)`). FastAPI automatically
  runs sync handlers in a threadpool, so file I/O no longer blocks the loop. Zero behavioral change.
- **Or:** cache the parsed policy keyed on `POLICY_PATH.stat().st_mtime_ns` (and optionally a hash),
  so hot-reload still works but parsing happens only on change.
- **Or:** wrap I/O in `starlette.concurrency.run_in_threadpool`.

**Then measure honestly (see P2-1).** Do **not** conclude anything from a load generator running on
the same box as the server without a control endpoint — a single-process `asyncio`/`httpx` client
saturates at roughly 450 req/s regardless of server cost (observed: `/healthz` and the policy route
performed identically at C=200 in this repo's own research). Use `hey`, `vegeta`, or `k6` from a
separate process/host, and always benchmark `/healthz` as the control.

**Acceptance criteria.**
- [ ] `policy.json` edited mid-run is picked up on the next request (hot-reload test exists).
- [ ] A benchmark report in `docs/benchmarks.md` with method, hardware, control endpoint, and
      p50/p99 at C=1/10/100 — or an explicit "not measured" note.

---

### P1-2 — Audit-log rotation + optional durable sink *(F9, F10)*

**Problem.** `AUDIT_LOG_PATH` is a single append-only file with no rotation (observed 15.5k
lines / 2.2 MB during a short benchmark). In Docker it lives inside the container and is lost on
recreate.

**Target.** Bounded disk, durable option, queryable.

**Steps.**
1. Add rotation: `AGENT_GUARDRAIL_AUDIT_MAX_BYTES` (default e.g. 10 MB) and keep `.1`, `.2` …
   Or use `logging.handlers.RotatingFileHandler` with a JSON formatter.
2. Add optional SQLite sink behind `AGENT_GUARDRAIL_AUDIT_SQLITE=/path.db`, schema
   `(ts, agent, user, resource, action, method, decision, reason)`, so the planned report/CI feature
   has something to query.
3. Add a `guardrail report` CLI (argparse, no new deps) that prints unauthorized attempts grouped
   by `(agent, resource, action)` and a coverage table of never-attempted policy entries. This is
   the seed of the roadmap's "GitHub Action fails a PR on unauthorized access."

**Acceptance criteria.**
- [ ] Rotation proven by a test that writes past the threshold and asserts multiple files exist.
- [ ] `guardrail report --audit audit.jsonl` prints a deterministic summary; snapshot-tested.

---

### P1-3 — Docker hardening *(F8, F9)*

**Problem.**

```dockerfile
CMD ["sh", "-c", "uvicorn policy_engine:app --host 0.0.0.0 --port ${AGENT_GUARDRAIL_PORT}"]
```

bound to all interfaces, running as root, no auth, app-level `allow_origins=["*"]`, no volume for
`audit.jsonl`, no healthcheck.

**Steps.**
1. Add a non-root user; `USER guardrail`.
2. Default host to `127.0.0.1`; require an explicit `AGENT_GUARDRAIL_HOST=0.0.0.0` to expose.
3. Declare `VOLUME /app/src/audit` (or `VOLUME /data`) and default
   `AGENT_GUARDRAIL_AUDIT=/data/audit.jsonl`.
4. Replace wildcard CORS with `AGENT_GUARDRAIL_CORS_ORIGINS` (comma-separated, default empty).
5. Add `HEALTHCHECK CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz').status==200 else 1)"`.
6. Pin the base image by digest.
7. Add `docker-compose.yml` publishing only `127.0.0.1:8080:8080` and mounting `./data`.

**Acceptance criteria.**
- [ ] `docker run` with no env vars exposes nothing beyond localhost and persists the audit log
      across `docker rm`/`run` via a named volume.
- [ ] `docker inspect` shows a non-root `User`.
- [ ] README Docker section matches reality; roadmap checkbox updated.

---

### P1-4 — Hygiene *(F11)*

- Remove `python-dotenv` from `requirements.txt` (never imported) — or actually use it for the env
  vars this brief introduces, and document it. Pick one.
- Add `tests/__init__.py` or a `pyproject.toml` with `[tool.pytest.ini_options]` so `tests/` imports
  don't rely on rootdir insertion.
- Add `pyproject.toml` with a `guardrail` console-script entry point for the P1-2 CLI.
- Add a GitHub Actions workflow: install `requirements-dev.txt`, `pytest -q`, plus a smoke job that
  boots the server and runs the four README curls.
- Fix stale docs: README roadmap `[ ] Docker image` → `[x]`; landing page "Docker upcoming" → shipped.
- Add `LICENSE` file matching the MIT claim, if missing.
- Add `.dockerignore` (`.venv`, `__pycache__`, `audit*.jsonl`).

---

### P2-1 — Benchmark honestly, then substantiate or delete the numbers

**Problem.** Public copy claims `<100ms p99` and `1,000+ requests/second`. This research could not
verify them because its own client saturated first.

**Steps.**
1. Use a real load generator (`hey -z 30s -c 1/10/100`, `vegeta`, or `k6`) from a separate process.
2. Always run the `/healthz` control. Report server-side attribution only when the control is
   materially faster than the policy route.
3. Publish `docs/benchmarks.md`: hardware, tool, versions, command lines, raw numbers.
4. Update the landing copy to the measured p99 at the stated concurrency, or remove the claims.

**Acceptance criteria.**
- [ ] Numbers in docs are reproducible from the pasted commands.
- [ ] No page advertises a latency/throughput figure without the concurrency and hardware it was
      measured at.

---

### P2-2 — Make the copy match the FAQ *(the core harm)*

**Problem.** The FAQ correctly says this "simulates permission enforcement" and "never sits in front
of real systems." The hero says "fail-closed" and "Stop guessing if your agent respects
permissions." The mismatch manufactures false confidence — the exact failure mode a safety tool
must not have.

**Steps.**
1. Retire "fail-closed" and "denying by default" as marketing until P0-1 is merged **and** a test
   proves every malformed-policy path denies. After that, keep it only with a link to the test.
2. Fix the hero demo's response body: the server returns
   `{"detail": "Access denied by sandbox policy"}`; the page shows a `{"decision","reason"}` schema
   the shipped code never emits. Show real output.
3. Rename the promise from *"does your agent respect permissions"* to what the code proves:
   *"which permission boundaries your agent attempts to cross — and whether your policy, as written,
   denies them."* The agent-behavior half is P2-3/P2-4.
4. Remove "RESTful by design — across GET/POST/PUT/DELETE/PATCH". That is F2; it is method-agnostic
   routing, which is the opposite of REST semantics. Say "method binding is declared per action."
5. Remove/soften "dense RBAC rules" — the model is a flat boolean matrix and cannot represent them.
6. Reword the pen-testing use case: you cannot probe bypasses through a client-side playground.

**Acceptance criteria.**
- [ ] Every claim on the page maps to a test or a command in the repo.
- [ ] The hero response body is copied from an actual `curl -i`.

---

### P2-3 — `instruction_provenance` as an authorization context attribute *(research spike)*

**Problem.** Every IAM-style system decides on `(principal, resource, action, context)`. Agents add a
context attribute no IAM system has: **was this request derived from the user's instruction, or from
untrusted content the agent read?** Without it, a prompt-injected agent using legitimately granted
authority is indistinguishable from a compliant one.

**Target.** A spike, not a product.

**Steps.**
1. Extend the request contract: require `X-Instruction-Provenance: trusted|untrusted|<id>` (header
   preferred over query param; unauthenticated values are advisory, say so).
2. Policy gains an optional per-action constraint: `{"require_provenance": "trusted"}`.
3. Decision: an action requiring trusted provenance with `untrusted`/absent provenance → `DENY`,
   `reason="UNTRUSTED_PROVENANCE"`, audited.
4. Write up (in `docs/`) why this is undecidable at the PDP without taint-tracking through the model,
   and that the mock can only *check a label the caller supplies* — it cannot verify the label.
   That limitation is the finding, and it's the interesting one.

**Acceptance criteria.**
- [ ] Tests for trusted / untrusted / missing provenance.
- [ ] A doc that states clearly this is a *label check*, not enforcement of real taint tracking, and
      what would be required to make it sound.

---

### P2-4 — Attenuated capability-token mode *(structural fix)*

**Problem.** `(agent, user, resource, action) → ALLOW/DENY` is *ambient authority*: the agent can
name any resource and a global policy vetoes. This is why the fail-open class of bug (F1) is
possible at all — there is always a "denied" decision that must be computed correctly.

**Target.** A mode where the agent holds an unforgeable, pre-attenuated token scoped to exactly the
resources/actions it needs, so an unauthorized action is *unnameable* rather than *denied*.

**Steps.**
1. Add `POST /token` (dev-only, unauthenticated, **loudly documented as such**) that mints a signed
   scope token: `{sub, user, scope: [{resource, actions, methods}], exp}`.
2. Add an alternate route `POST /cap/{token}/{resource}/{action}` that verifies the signature, checks
   the action is inside scope, and never consults a global user matrix.
3. Implement attenuation: a token holder can derive a strictly narrower token (`scope' ⊆ scope`),
   never wider. HMAC with a server-generated dev key is enough for the spike; do not invent crypto.
4. Property test: for random policies and random request streams, `used ⊆ scope` holds, and no
   sequence of attenuations produces an action outside the original scope.

**Acceptance criteria.**
- [ ] Property test above passes.
- [ ] A token for `emails:read` cannot cause `emails:delete` under any request, including retries
      and method permutations — because the operation is not expressible, not because a table says no.
- [ ] Design note comparing this to macaroons/Biscuit (attenuation) and object-capability POLA.

---

## 5. Finding → work item traceability

| Finding | Fixed by | Regression test |
|---|---|---|
| F1 fail-open on non-bool | P0-1 | `test_F1_*` |
| F2 method/action decoupled | P0-1, P0-3 | `test_F2_method_must_match_action` |
| F3 unknown user unaudited | P0-1 | `test_F3_unknown_user_is_audited` |
| F4 malformed policy 500 | P0-1, P0-4 | `test_F4_*` |
| F5 unbounded `agent_id` | P0-1 | `test_F5_agent_id_is_bounded_and_header_supported` |
| F6 403/404 enumeration | P0-1 (document as accepted) | — |
| F7 bodies ignored | P2-3/P2-4 (scope of model) | — |
| F8 wildcard CORS / `0.0.0.0` | P0-1, P1-3 | docker smoke job |
| F9 Docker log not persisted | P1-2, P1-3 | volume test |
| F10 process-local lock / blocking I/O | P0-1, P1-1 | benchmark report |
| F11 stale deps/docs | P1-4 | CI green |

---

## 6. Explicit non-goals

Do **not** do these in this repo without a separate design discussion:

- Become a real enforcement proxy in front of production systems. It is a mock by design; keep it so.
- Add a general-purpose policy DSL / Cedar / Rego engine. P2-4 is a spike, not an adoption.
- Add authentication for the guardrail itself beyond the dev-token spike (production identity is
  L0 and belongs to the real system, not the fixture).
- Delete `RESEARCH.md`, the named `test_F*` tests, or the `reason` field on audit records — they are
  the traceability spine.
- Rewrite the engine in another language or framework.
- Optimize for the landing page's numbers before P1-1 is measured with a correct harness.

---

## 7. Definition of done for a PR

- [ ] One work item; commit message references the finding ID.
- [ ] `pytest -q` green; no test asserts known-buggy behavior.
- [ ] Verification protocol in §3 passes (record output in the PR).
- [ ] Four README curls return exactly the documented status + body.
- [ ] Every new code path that can deny writes an audit line with a `reason`.
- [ ] Every malformed-policy path returns `503`, never `500`, and is audited.
- [ ] Docs touched by the change are updated (README roadmap, Docker section, and — if applicable —
      the landing copy in P2-2).
- [ ] No new runtime dependency, or an explicit justification.
- [ ] If the PR is in P0/P1, `policy_engine_hardened.py` is either deleted or explicitly marked
      deprecated with a deletion date — no two divergent engines.
