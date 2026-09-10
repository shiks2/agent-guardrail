# Deep Research: `agent-guardrail`

**Subject:** https://github.com/shiks2/agent-guardrail @ `33ab1fd` (main)
**Author:** Sachin Rathod (`shiks2`) · MIT · 9 commits, 2026-08-31 → 2026-09-01
**Method:** static read of all 6 tracked files; live execution of the server; 40+ adversarial probes
against two independent environments — a current venv (FastAPI 0.141.1) and a clean venv built
strictly from `requirements.txt` (FastAPI 0.115.0, Pydantic 2.7.0). **Every finding below was
reproduced on the pinned/README stack.**
**Assumption:** "deep research with an agenda" = an evidence-backed evaluation of what this project
actually guarantees, where those guarantees break, and what to do next. If the agenda was something
else (e.g. "should I adopt it", "should I fork it", "give me a project idea"), see §9.

---

## 1. Executive summary

`agent-guardrail` is a ~120-line FastAPI mock that stands in for a real backend. You declare
`synthetic_users → resource → action → bool` in `policy.json`; an agent calling
`/api/{resource}/{user_id}/{action}` gets `200` or `403`, and every decision is appended to
`audit.jsonl`.

The core idea is sound and the happy path works exactly as advertised — I verified all four README
curl examples and the fail-closed behavior for unknown resource/action/user. The
generic path-parameter design is a genuine improvement over the prior per-endpoint version
(`git show ba3b484`), since new API shapes need only a JSON edit.

**But the central safety claim is false in a way that matters.** The README says *"Anything not
explicitly allowed is denied."* In practice the engine coerces the policy value with Python
truthiness, so a permission written as the **string** `"false"` — the single most common
copy-paste error, and exactly what you get from YAML/env-derived config — **grants access**. A
tool whose entire value proposition is "fail closed" fails **open** on a typo. That is worse than
having no tool, because it manufactures false confidence in exactly the moment someone is relying
on it to catch a permission boundary violation.

Two more structural gaps undercut the two things the project sells:

| Promise | Reality |
|---|---|
| "Anything not explicitly allowed is denied" | Non-boolean values fail **open**; malformed policy `500`s |
| "Every call is logged" | Unknown-user requests are **not logged** (404 raised before logging) |
| It tests whether an agent *respects* boundaries | It only returns a status code; it never observes whether the agent *honored* a 403, and the HTTP method is ignored entirely |

Verdict: **good prototype, not yet safe to trust as a safety gate.** The fix is small and mostly
mechanical (strict schema validation + method/action binding + audit the deny path). All three are
implemented in the accompanying patch and tests.

---

## 2. What it actually is (verified)

```
agent-guardrail/
├── src/policy_engine.py     # 116 lines — all logic
├── src/policy.json          # 2 users × 3 resources × 2 actions
├── src/__init__.py          # empty, unused when run as README says
├── requirements.txt         # fastapi 0.115.0, uvicorn 0.30.0, pydantic 2.7.0, python-dotenv 1.0.1
├── Dockerfile               # python:3.12-slim, binds 0.0.0.0:8080
└── README.md
```

**Runtime shape**

- One catch-all route: `@app.api_route("/api/{resource}/{user_id}/{action}", methods=[GET,POST,PUT,DELETE,PATCH])`.
- `check_permission()` reloads `policy.json` **on every request** — intentional (`"so edits take
  effect without a restart"`), so there is no restart-based TOCTOU and the live-edit workflow is real.
- `user_policy = policy["synthetic_users"].get(user_id)` → `None` means unknown user → `404`.
- `allowed = resource_policy.get(action, False)` → unknown resource/action default to `False` → `403`.
- Decision appended to `audit.jsonl` under a `threading.Lock`, then printed with an emoji.
- Non-positive outcomes raise `HTTPException`; only the positive path returns the
  `{"status": "simulated success"}` body.

**Data flow**

```
agent → GET /api/emails/alice/read?agent_id=bot
        → load policy.json (every request)
        → look up user → look up resource → look up action → bool
        → append {timestamp, agent, user, resource, action, decision} to audit.jsonl
        → 200 {"status":"simulated success"}  |  403  |  404
```

Note there is **no dependency on the HTTP method** anywhere in the decision. `resource`, `user_id`,
and `action` all come from the *path*; `agent_id` is an *unauthenticated query param*.

---

## 3. Verified behavior matrix

Runtime: README stack (FastAPI 0.115.0) on `127.0.0.1:8097`. ✅ = matches README.

| Probe | Result | Note |
|---|---|---|
| `GET /api/emails/alice/read` | `200` ✅ | README example |
| `GET /api/emails/bob/read` | `403` ✅ | README example |
| `DELETE /api/records/alice/delete` | `403` ✅ | README example |
| `GET /api/calendar/bob/read` | `200` ✅ | README example |
| `GET /api/emails/charlie/read` (unknown user) | `404` | README says "fail closed" — 404 is arguably weaker than 403 but acceptable |
| `GET /api/nuclear/alice/launch` (unknown resource) | `403` ✅ | fail-closed |
| `GET /api/emails/alice/launch` (unknown action) | `403` ✅ | fail-closed |
| `GET /api/emails/alice/READ` (case) | `403` ✅ | case-sensitive, safe |
| `GET /api/emails/ALICE/read` (case) | `404` ✅ | case-sensitive, safe |
| `POST /api/emails/alice/read` | **`200`** ⚠️ | method ignored |
| `DELETE /api/emails/alice/read` | **`200`** ⚠️ | **a delete-shaped request authorized as "read"** |
| `GET /api/emails/alice/read/` | `307` redirect | fine |
| `HEAD/OPTIONS/TRACE /api/...` | `405` | fine |
| `GET /api/%65mails/alice/read` | `200` | URL-decoded, fine |
| `GET /api/..%2f..%2fetc/alice/read` | `404` | no traversal (resource never touches the FS) |
| policy `"read": "false"` | **`200`** 🔴 | **fail-OPEN** |
| policy `"read": 1` / `["x"]` / `{"x":1}` | **`200`** 🔴 | same class |
| policy `"read": 0` / `None` / `False` / `[]` | `403` | truthy/falsy coincidence, not validation |
| policy `resource: null` | **`500`** 🔴 | `None.get(...)` AttributeError |
| policy missing `synthetic_users` | **`500`** 🔴 | `KeyError` |
| `agent_id` with `\n{...}` | escaped in JSON | no log injection ✅ |
| 300 parallel requests, 1 worker | 300/300 intact lines | ✅ |
| 300 parallel requests, `--workers 4` | 300/300 intact lines | small `O_APPEND` writes are atomic; not a guarantee for large lines |

---

## 4. Findings

### F1 — 🔴 HIGH · Fail-open on non-boolean policy values
`src/policy_engine.py:92`
```python
resource_policy = user_policy.get(resource, {})
allowed = resource_policy.get(action, False)   # "false" is a truthy str
```
`allowed` is used directly as a boolean. Any non-empty string, non-empty list, non-empty dict, or
non-zero int is truthy. The most dangerous instance is `"read": "false"` — quoted booleans are the
canonical YAML/env/JSON copy-paste error, and `policy.json` is explicitly marketed as the
user-editable surface. The engine has no schema validation at load time.

**PoC** (reproduced on FastAPI 0.115.0):
```
policy.json: {"synthetic_users":{"alice":{"emails":{"read":"false"}}}}
GET /api/emails/alice/read   →  200 {"status":"simulated success"}
```
**Impact:** the project's headline guarantee ("anything not explicitly allowed is denied") is
violated silently on a realistic input error. A human reading `policy.json` sees `"false"` and
believes the boundary is denied; the tool says allowed. For a safety/assurance tool this is the
worst failure mode: it converts a config typo into a false "your agent is well-behaved" signal.
**Fix:** validate every leaf is `isinstance(v, bool)` (reject `bool` subclasses only when you must,
but here plain `bool`), and fail loudly at load rather than coercing.

### F2 — 🔴 HIGH · HTTP method is decoupled from the action
The route accepts five methods and never compares `request.method` to the path `action`.
```
DELETE /api/emails/alice/read?agent_id=x   → 200
audit.jsonl: {"action":"read","decision":"ALLOW", ...}
```
Two consequences:
1. **Non-transferable verdicts.** Real APIs route by method (`DELETE /records`). An agent wired to
   send `DELETE` to what the mock labels `read` is authorized, so the mock's pass/fail does not
   predict the real API's behavior — the exact thing the tool is used to predict.
2. **Audit misattribution.** The log records the *path label*, not the operation the client
   intended. An agent that attempts a destructive action via the wrong method is logged as having
   performed a benign read. The audit trail — the tool's real product — can be wrong.

**Fix:** bind method→action explicitly (in `policy.json`, so the "no code changes" promise holds),
deny mismatches, and log `decision=DENY, reason=METHOD_MISMATCH`.

### F3 — 🟠 MEDIUM · Unknown-user denials are never audited
`src/policy_engine.py:104-108` raises `404` **before** `log_decision()`. Confirmed: a probe for
`/api/emails/ghost/read?agent_id=PROBE` produced a 404 and **zero** audit lines.
**Impact:** the class of request an attacker probes with most (does user X exist? are there users I
haven't been given?) is invisible. The roadmap's planned GitHub Action ("fail a PR if an agent
attempts unauthorized access") will miss every unknown-user attempt.
**Fix:** log the decision with `decision=DENY, reason=UNKNOWN_USER` before raising.

### F4 — 🟠 MEDIUM · Malformed policy `500`s instead of failing closed/loudly
No validation. `synthetic_users` absent → `KeyError`; a user or resource set to `null` → `.get`
on `None` → `AttributeError`. Observed `500 Internal Server Error` for both.
**Impact:** a one-character typo turns the guardrail into a broken endpoint that returns no
decision and writes no audit line. For a CI gate, "couldn't evaluate" silently looks like a crash,
which is at least visible — but a partial/`null` policy that only 500s on *some* routes could hide.
**Fix:** validate the whole document at load; on invalid, deny all with a clear `503` + a startup
error, and never fall through to a default-allow.

### F5 — 🟡 LOW-MEDIUM · Unauthenticated, unbounded `agent_id` attribution
`agent_id` is a free query param, defaults to `"unknown"`, has no length limit. Observed a **5,140
byte** audit line from a 5 KB `agent_id`. Newlines are JSON-escaped, so there is no log injection,
but: (a) the audit trail's actor field is entirely caller-controlled and unverifiable; (b) the log
can be inflated/DoS'd by any client; (c) two agents can trivially impersonate each other, so the
log cannot answer "which agent did this" with any confidence.
**Fix:** cap at a sane length (e.g. 128), prefer a header or a required field, and document that
attribution is advisory, not authenticated.

### F6 — 🟡 LOW · `403` vs `404` enables synthetic-user enumeration
Unknown user → 404, known-but-denied → 403. Any client can enumerate the synthetic user directory.
Low impact for a local mock, but the roadmap targets CI/shared use.

### F7 — 🟡 LOW · Request bodies are ignored entirely
`POST /api/emails/alice/read` with body `{"wipe":"all","to":"attacker@evil.com"}` → `200`. The
model is strictly `(user, resource, action)`; parameter-level and payload-level permissions (e.g.
"can read only own records", "can send to internal domains only") are unrepresentable. Fine as a
scoped MVP, but worth stating so users don't assume more.

### F8 — ⚪ INFO · Docker defaults to an unauthenticated, wildcard-CORS service on `0.0.0.0`
`Dockerfile` runs `uvicorn --host 0.0.0.0`; the app sets `allow_origins=["*"]` and has no auth.
The code comments correctly call the local-dev CORS posture out — but the Dockerfile turns that
local posture into a network-exposed one. Any browser page reachable to the host can drive the
guardrail and write audit entries.
**Fix:** default the container to `127.0.0.1` (or require an explicit env/flag + shared token),
and make CORS origin allow-list configurable.

### F9 — ⚪ INFO · Docker audit log is not persisted
`AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"` → `/app/src/audit.jsonl` inside the
container, no `VOLUME`. Every container restart/replacement loses the audit trail, contradicting
"you get ... every decision logged" for the Docker path.

### F10 — ⚪ INFO · Lock is process-local only
`threading.Lock` does not coordinate across `--workers`. In practice 4 workers × 300 requests was
lossless because `O_APPEND` writes of short lines are atomic on Linux, but that is an OS
coincidence, not a design. Long `agent_id` values (F5) near/over `PIPE_BUF` could interleave.
A per-line length cap + `O_APPEND` single `write()` (or JSONL → SQLite) removes the assumption.

### F11 — ⚪ INFO · Repo hygiene
- `requirements.txt` pins are old but **verified installable and functional** on Python 3.12.
- No tests exist, despite `pytest` being installed in the working venv.
- README roadmap shows `[ ] Docker image` unchecked even though `Dockerfile` exists and
  commit `33ab1fd` is titled "Added: Docker support" — README is stale.
- `python-dotenv` is a dependency but never imported.
- The refactor from per-endpoint (`can_read_emails`) to generic path routing (`git diff 8633219 cfc7233`)
  is what introduced F1/F2; the original flat-boolean design had the same truthiness coercion but
  the method coupling couldn't arise.

---

## 5. Claim-vs-reality audit (README)

| README claim | Verdict |
|---|---|
| "these are real, verified responses from a running instance" | ✅ all four reproduce exactly |
| "Anything not explicitly allowed is denied — unknown resources, unknown actions, and unknown users all fail closed." | ⚠️ **partly false**: unknown resource/action/user yes; **non-boolean values fail open** (F1); malformed policy 500s (F4) |
| "Every call above is logged to `audit.jsonl`" | ⚠️ the four examples yes; **unknown-user calls are not** (F3); Docker log not persisted (F9) |
| "The server checks the policy and responds accordingly" | ✅ but the HTTP **method is not part of the check** (F2) |
| "Test whether your AI agent respects permission boundaries" | ⚠️ it tests whether the *backend* would authorize; it never observes whether the agent *respects* a denial |
| Roadmap `[x] Fail-closed on unknown resource/action/user` | ✅ true for *absence*; undermined by F1/F4 |
| Roadmap `[ ] Docker image` | ❌ stale — it exists |

---

## 6. Threat model: what this tool can and cannot prove

**Can prove**
- Which `(user, resource, action)` tuples your agent attempts, *provided every call is routed
  through the mock* and *provided the attempt is audited* (fails for unknown users, F3).
- That a configured policy is applied as written (once F1/F4 are fixed).

**Cannot prove (important, and currently unstated)**
- **That the agent honors a 403.** The tool returns 403 and moves on. An agent that retries, ignores
  the status code, or routes around the check still "passes". The tool's value is the audit log +
  the *agent's* reaction, which it doesn't capture.
- **Coverage.** "No unauthorized attempts in the log" is indistinguishable from "the agent never
  ran that code path." There is no notion of expected/required attempts.
- **Method correctness** (F2) — the verdicts don't transfer to method-routed APIs.
- **Scope of *allowed* actions** — an ALLOW for `read` doesn't constrain what the agent does with
  the data.
- **Real side effects.** It is a mock, not a sandbox. It has no ability to stop anything; it can
  only fail to authorize a call the agent chose to send it.
- **Identity.** `agent_id` is self-declared (F5).

**The sharpest framing:** this is a *policy conformance fixture*, closer to a JSON-schema test
server than to a guardrail. The name and framing promise enforcement; the implementation delivers
observation. That's a legitimate and useful thing — it just needs to be named and documented as
such, or the mismatch itself becomes the safety hazard.

---

## 7. Engineering assessment

| Dimension | Assessment |
|---|---|
| Idea / positioning | Strong. Permission-boundary testing for agents is a real, underserved need. |
| Scope discipline | Good. ~120 LOC, one dependency surface, one config file. |
| Design | Clean separation (`load_policy` / `check_permission` / `log_decision`), live reload, fail-closed defaults for *absence*. The generic route is the right call. |
| Correctness | Weak at the boundary that matters: **policy value validation is absent** (F1/F4). |
| Security posture | Prototype-grade: no auth, wildcard CORS, unbounded input, `0.0.0.0` container. Acceptable for "local dev", not for the CI/team use the roadmap targets. |
| Observability | Audit log is the right primitive; the deny path is incompletely logged (F3). |
| Testing | None in-repo. The README's "verified responses" were manual. |
| Docs | Clear and honest in tone; overstates fail-closed and is stale on Docker. |
| Dependency hygiene | Pins are old but verified working; one unused dep. |
| Commit history | Sincere solo-dev log, no secrets, no binaries, no generated noise. |

---

## 8. Hardening patch (included)

`src/policy_engine_hardened.py` + `src/policy.hardened.json` implement the minimal fixes:

1. **Strict schema validation** — every leaf must be a JSON boolean; `synthetic_users` and nested
   maps must be objects. Invalid policy → every request returns **`503`** with a clear reason and
   an audit line, never a default-allow and never a bare 500. (fixes F1, F4)
2. **Method ↔ action binding** — `action_methods` lives in `policy.json`, so the "add a resource
   without code changes" promise is preserved. A method mismatch is `403` + audited
   `reason=METHOD_MISMATCH`. (fixes F2)
3. **Audit the deny path** — unknown users are logged as `ALLOW`/`DENY` with a `reason` before the
   404/403 is raised. (fixes F3)
4. **Bounded, explicit attribution** — `agent_id` capped at 128 chars, `X-Agent-Id` header
   supported, `reason` added to every audit record. (fixes F5/F10 line-length concern)
5. **Safe container defaults** — host/port/CORS from env, `127.0.0.1` default, CORS allow-list
   instead of `*`. (fixes F8)

`tests/test_guardrail_research.py` encodes **both** the observed current behavior and the desired
hardened behavior (the latter as `xfail`, so the suite is green today and flips to XPASS as fixes
land). Run with `./.venv/bin/pytest -v`.

> These are *proposed* changes in a separate module. `src/policy_engine.py` is left byte-identical
> so the findings above stay reproducible.

---

## 9. Agenda: where to take this

The project is one honest refactor away from being genuinely useful. Ranked options:

**A. Ship the hardening, rename the promise.** Keep "guardrail" for the mock, but document it as
*policy conformance + attempt auditing*, not enforcement. This is the highest-value/lowest-effort
move and directly fixes the false-confidence problem.

**B. Add the missing half: agent-side assertions.** The tool returns 403 but never checks the agent
reacted correctly. A thin wrapper — `guardrail.expect_denied(agent, ...)` that asserts the agent
surfaced the denial and did **not** retry or route around it — turns a status-code mock into an
actual behavioral test. This is the real product gap.

**C. Make the audit log queryable and diffable.** `audit.jsonl` is the product; give it
`guardrail report` (unauthorized attempts grouped by agent, coverage gaps by resource/action) and
the README's promised GitHub Action (`--fail-on DENY`) follows naturally.

**D. Coverage contracts.** Let `policy.json` declare *expected* attempts, so "agent never touched
`records/delete`" becomes a visible gap rather than a silent pass.

**E. Adopt existing standards instead of a bespoke policy file.** Cedar / OPA-Rego / Casbin are
where teams already express authorization. A loader for one of them would make the fixture
credible to security reviewers and give you F1's validation for free.

**F. Fuzz/property tests for the engine itself.** Fixed cases (unknown resource/action/user, case
sensitivity, method mismatch, every non-boolean leaf type) as the repo's first test suite.

If the agenda was instead *"find a project/startup in this space"*: the defensible wedge is **B+C**
— behavioral conformance testing of agent permission handling with a signed, reviewable audit
trail — not the mock itself, which is a weekend of work.

---

### Reproduction

```bash
cd agent-guardrail
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt httpx pytest
.venv/bin/pytest tests/ -v                      # 20+ assertions, incl. xfail'd desired behavior

# manual PoC for F1/F2 (README stack):
cd src
sed -i 's/"read": true, "delete"/"read": "false", "delete"/' policy.json   # or edit by hand
uvicorn policy_engine:app --port 8099 &
curl -s "http://127.0.0.1:8099/api/emails/alice/read"                      # → 200 (should be 403)
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE \
     "http://127.0.0.1:8099/api/emails/alice/read"                         # → 200 (method ignored)
```
