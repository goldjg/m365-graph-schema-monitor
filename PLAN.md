You are a disciplined engineering agent operating under AADLCv2 governance.

OPERATING MODE: Plan-only.
Do NOT apply code changes, do NOT run tests, do NOT create files.
Report “No code changes proposed (Plan-only mode)” and “Not run (Plan-only mode)” under the required final headings.
Only proceed to implementation if Graham explicitly approves the plan with words such as “implement”, “proceed”, or “approved”.

⸻

Step 0 – Read before planning

Before producing any plan, read the following files from the current state of main in full:

1. .github/copilot-instructions.md
2. .github/aadlc/memory.md
3. .github/aadlc/current-pr-contract.md
4. .github/aadlc/trust-boundaries.md
5. .github/aadlc/invariants.yml
6. src/graph_schema_monitor/cli.py
7. src/graph_schema_monitor/parser.py
8. src/graph_schema_monitor/diff.py
9. pyproject.toml
10. README.md

If any file cannot be read, stop and report the missing file before continuing.

Confirm you have read all ten files before producing your plan. Do not plan against a stale or assumed state.

⸻

Step 1 – PR2 task summary

PR1 delivered an offline, deterministic CLI (inspect, diff) for parsing and diffing local CSDL/XML snapshots. It has no network access.

PR2 adds one new capability: a controlled, unauthenticated snapshot acquisition workflow that fetches Microsoft Graph $metadata from fixed, allowlisted public endpoints and writes the result to a local file, ready for the existing parser/diff pipeline.

PR2 introduces exactly one new trust boundary: outbound HTTPS to fixed Graph metadata URLs.
PR2 must not expand further than this.

⸻

Step 2 – Produce the PR2 implementation plan

Produce a complete, structured plan covering the sections below. Be concrete and specific. Do not use vague “best practice” language unless tied to a named action.

2a. PR contract

Write the PR2 contract covering:

* Goal: one sentence.
* Scope: what is included.
* Non-goals: explicit list of what is forbidden.
* Constraints: security, dependency, design.
* Risks: enumerate risks specific to introducing network access.
* Validation plan: how correctness will be verified.
* Stop conditions: when to stop and escalate rather than proceed.
* Escalation triggers: what changes to scope require Graham’s approval.

The non-goals section must explicitly list:

* No authentication, OAuth, MSAL, or Graph SDK.
* No tenant access or permissions.
* No arbitrary URL fetching.
* No local file URL support.
* No redirects to non-HTTPS or non-graph.microsoft.com hosts.
* No scheduler, database, web UI.
* No changelog/docs correlation.
* No canary tenant logic.
* No AI summarisation.
* No raw request or response header dumps.
* No custom URL argument.

2b. Proposed file tree

List every file that will be created or modified. For each entry, state whether it is new or modified, and give a one-line description of its role.

Minimum expected new files:

* src/graph_schema_monitor/fetcher.py – snapshot acquisition module
* tests/test_fetcher.py – unit and CLI tests for fetcher
* Updated AADLC artefacts, listing each modified file explicitly
* Updated README.md

Whether to update pyproject.toml or add test fixtures is your decision; justify it in the plan.

2c. fetcher.py design

Specify:

1. Profile-to-URL mapping. Allowed profiles for PR2: v1.0 and beta only. Map:
    * v1.0 → https://graph.microsoft.com/v1.0/$metadata
    * beta  → https://graph.microsoft.com/beta/$metadata
    No other profiles or URLs are accepted in PR2.
2. Whether to use urllib.request from the Python standard library or requests. Justify your choice. Default assumption: stdlib is sufficient for PR2.
3. Enforcement of HTTPS. Explain how you will reject or refuse non-HTTPS at the code level, not just by convention.
4. Timeout policy. State the timeout value and how it is applied.
5. Redirect handling. State whether redirects are followed. If redirects are followed, specify how the implementation ensures the redirect target remains HTTPS and within graph.microsoft.com. If redirects are not followed, specify how redirect responses are handled.
6. Error handling. Specify non-zero exit codes and clear error messages for:
    * Unknown profile.
    * HTTP non-2xx response.
    * Connection timeout or network error.
    * Output path already exists and --overwrite not set.
    * Write failure.
    * Non-XML or unexpected content type.
7. Parent directory creation. State whether fetcher.py creates missing parent directories automatically or fails clearly. Justify your decision.
8. Return type. The fetch function should return a structured result object or named tuple, not just raw bytes/string. Specify the shape.
9. Sidecar metadata file. For every output file <name>.xml, write a sidecar <name>.xml.json containing exactly:
    * profile (string)
    * source_url (string)
    * fetched_at_utc (ISO 8601 string)
    * status_code (int)
    * content_type (string or null)
    * etag (string or null)
    * last_modified (string or null)
    * sha256 (hex string of snapshot content)
    * x_ms_schema_version (string or null; set only from an explicit allowlisted x-ms-schemaVersion response header if present, otherwise null)
    No other headers. No request headers. No secrets.

2d. CLI design

Specify the fetch subcommand:

* --profile (required): v1.0 or beta.
* --out (required): output path for the XML snapshot.
* --overwrite (optional flag): if not set, refuse to overwrite an existing output file with a clear error.
* Do not modify the inspect or diff subcommands.
* Show how fetch will be wired into cli.py and _build_parser().

2e. Test plan

List every test case. For each, state:

* test name or description
* what it tests
* how the network is mocked
* expected outcome

Required test coverage:

1. Profile mapping – valid profiles return expected URLs.
2. Profile mapping – unknown profile raises a clear error and is not treated as a URL.
3. Fetch success – mocked HTTP 200 with XML body writes snapshot and sidecar correctly.
4. Fetch HTTP error – mocked HTTP 404 returns non-zero exit / raises.
5. Fetch HTTP error – mocked HTTP 503 returns non-zero exit / raises.
6. Timeout – mocked timeout raises/returns correct error.
7. Sidecar shape – verify all required keys present, no extra keys, and sha256 matches content.
8. Overwrite guard – existing file without --overwrite returns non-zero exit.
9. Overwrite flag – existing file with --overwrite succeeds.
10. CLI integration – fetch --profile v1.0 --out <tmpfile> with mocked network completes successfully.
11. No arbitrary URL – confirm there is no code path that accepts a raw URL from the user in PR2.
12. Redirect handling – verify redirects are either rejected or validated according to the chosen design.
13. Content type handling – verify non-XML / unexpected content type is rejected clearly.

All tests must be deterministic.
No test may make a live network call by default.
State how this will be enforced, for example with unittest.mock, monkeypatching, or a fixture that fails the test if real network code is reached.

2f. Optional live integration test

Decide: include a live integration test in PR2, or defer?

If included:

* It must be skipped by default.
* It must be gated behind GRAPH_SCHEMA_MONITOR_LIVE_TESTS=1.
* It must not run in normal CI.
* It must not require authentication.
* It must assert only HTTP 200 and XML parseability, not volatile content.
* Add a conftest.py fixture or pytest marker to enforce the skip.

If deferred:

* State the reason.
* Note it as an open question in memory.md.
* Ensure PR2 acceptance does not depend on live network success.

2g. AADLC artefact updates

State precisely what changes you will make to each artefact:

1. memory.md – add:
    * PR2 introduced a constrained outbound network boundary.
    * Only v1.0 and beta Graph $metadata endpoints are allowed.
    * No auth/tenant/OAuth/Graph permissions introduced in PR2.
    * Network tests must be mocked by default.
    * Optional live integration, if ever added, is opt-in via env var and skipped by default.
    * Update “Open questions” and “Last updated”.
2. current-pr-contract.md – replace PR1 contract with PR2 contract as specified in §2a.
3. trust-boundaries.md – add a new row for:
    * Boundary: Graph metadata endpoint
    * Source: https://graph.microsoft.com/{v1.0,beta}/$metadata
    * Trust level: Low
    * Required validation: HTTPS enforced; fixed allowlist only; timeout applied; status checked; content-type checked; no redirect to non-Graph hosts
4. invariants.yml – add:
    * id: network-boundary-fixed
    * Rule: outbound network calls are limited to the allowlisted Graph metadata endpoints; no dynamic or user-supplied URLs are permitted.

2h. README update

Specify the sections to add or revise:

* Installation / setup section if missing.
* Workflow example: fetch → inspect → diff.
* Explicit network boundary statement:
    * fixed Graph endpoints only
    * no auth
    * no tenant data
    * no arbitrary URLs
* CLI usage examples for:
    * fetch
    * inspect
    * diff
* Limitations section: list what PR2 does not do.

2i. Implementation phases

Break the work into small, logical commits or phases in the order Codex should implement them when approved. Each phase should be independently reviewable.

Suggested structure, but adjust if a better ordering is justified:

1. AADLC artefact updates.
2. fetcher.py core: profile map, fetch, sidecar, redirect policy, timeout, and error handling.
3. cli.py: wire fetch subcommand.
4. tests/test_fetcher.py: all unit tests with mocked network.
5. Optional live integration test, only if included and skipped by default.
6. README.md update.
7. Final validation pass: run python -m pytest tests/ and confirm all tests pass offline.

2j. Security requirements

Enumerate the security requirements that apply specifically to PR2:

1. No secrets, credentials, or tokens in any committed file.
2. HTTPS enforced at the code level; no HTTP URLs permitted.
3. Profile allowlist enforced at the code level; no dynamic URL construction from user input.
4. No local file URL (file://) support.
5. Redirects must be rejected or validated: if followed, only follow redirects that stay on HTTPS and within graph.microsoft.com.
6. Timeout enforced on all network calls.
7. Sidecar contains only an explicit header allowlist; no raw header dump.
8. No eval, exec, or dynamic imports in new code.
9. XML in the HTTP response is written to disk as-is; it is not executed or interpreted in the fetch layer. Parsing is deferred to the existing parser.py pipeline.
10. sha256 of snapshot content recorded in sidecar for integrity verification.
11. Live network tests, if present, are skipped by default and never required for merge readiness.

2k. Acceptance criteria

List the conditions that define PR2 as complete and ready to merge:

1. python -m pytest tests/ passes with no live network calls.
2. A mocked CLI test proves fetch --profile v1.0 --out <tmpfile> writes a valid XML file and a <tmpfile>.json sidecar.
3. python -m graph_schema_monitor fetch --profile invalid --out <tmpfile> exits non-zero with a clear error message.
4. A fetched or mocked metadata snapshot can be parsed by the existing parser for at least one known EntityType present in the test fixture or optional live smoke path.
5. inspect and diff still work with local XML snapshots after PR2 changes.
6. All four AADLC artefacts updated as specified.
7. README documents fetch, inspect, diff workflow and states network boundary clearly.
8. No new runtime dependencies added; stdlib only.
9. No authentication, tenant access, OAuth, MSAL, or Graph SDK introduced.
10. No arbitrary URL argument present in CLI or fetcher.
11. No raw header dump in sidecar metadata.
12. Redirect behaviour is explicitly tested.
13. Live integration test, if present, is skipped by default in CI and is not required for PR2 acceptance.

⸻

Step 3 – Explicit overbuild guards

These are hard constraints. If your plan violates any of them, revise until it does not:

* Do NOT add authentication, OAuth, MSAL, or Graph SDK.
* Do NOT add tenant access or permission handling.
* Do NOT add a scheduler, cron job, or background process.
* Do NOT add a database, storage abstraction, or persistence layer beyond local files.
* Do NOT add a web UI or reporting framework.
* Do NOT add changelog correlation or docs repo monitoring.
* Do NOT add canary tenant logic.
* Do NOT add AI or LLM summarisation.
* Do NOT add a --url argument or any mechanism for user-supplied arbitrary URLs.
* Do NOT add NavigationProperty diffing.
* Do NOT flatten inherited properties.
* Do NOT expand parser scope beyond what is needed for fetched Graph $metadata to parse correctly with parser.py.
* Do NOT add runtime dependencies unless stdlib cannot accomplish the task; if you believe a dependency is necessary, flag it explicitly and wait for approval.
* Tests MUST NOT make live network calls by default.

⸻

Required final headings

Always conclude with:

Summary

[your summary]

Changes

No code changes proposed (Plan-only mode).

Tests run/not run

Not run (Plan-only mode).

Risks

[your risk assessment]
