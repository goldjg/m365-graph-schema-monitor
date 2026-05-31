<!-- version: 1.1.0 -->
# Current PR Contract
This contract constrains implementation scope for the active PR. Update
it when scope is explicitly amended. If a requested action falls outside
approved scope, stop and escalate before proceeding.
Use this contract to distinguish active PR constraints, completed PR
constraints, durable invariants, and intentional amendments. Completed
PR constraints are historical evidence unless they are explicitly
promoted to durable invariants.
## Goal
Add a `fetch-auth` CLI command that fetches Microsoft Graph `$metadata` using an access token
supplied by the caller via an environment variable. The token must not be stored, logged, or
written to any persisted artefact. All existing public fetch behaviour must be preserved
unchanged.
## Contract status
active
## Non-goals
- Do not add any database, scheduler, background service, or web UI.
- Do not acquire, refresh, cache, or store tokens; the caller is responsible for supplying a valid token.
- Do not add MSAL, Graph SDK, or any new runtime dependency.
- Do not replace or broaden the existing `fetch`, `inspect`, `diff`, `snapshots list`, `snapshots validate`, `report diff`, `report summary`, `watchlist check`, or `version compare` contracts.
- Do not make endpoint URLs dynamic or user-supplied.
- Do not add multi-tenant batch acquisition.
- Do not add signed-in-user context, delegated permission flows, or on-behalf-of flows.
- Do not log, hash, or persist the token value in any form.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
## Approved scope
- Extend `src/graph_schema_monitor/fetcher.py` with `fetch_authenticated_snapshot()`, `AuthFetchResult`, `TokenError`, and `_render_authenticated_sidecar_json()`.
- Extend `src/graph_schema_monitor/cli.py` additively with `fetch-auth` subcommand.
- Extend `tests/test_fetcher.py` with authenticated fetch tests covering all contract assertions CA-1 through CA-5.
- Update `README.md` with an "Authenticated metadata fetch" section.
- Refresh this contract and all AADLC artefacts for PR7 scope.
## Intentional amendments
- This PR intentionally replaces the prior PR6 active contract; version comparison work is completed history.
- The `network-boundary-fixed` invariant is amended to allow `Authorization` request headers while keeping endpoint URLs fixed.
- A new `auth-token-not-persisted` invariant is added to `invariants.yml`.
- A new `Authenticated token` trust-boundary row is added to `trust-boundaries.md`.
- Historical PR1 through PR6 work remains evidence only; it is not active implementation scope unless restated here.
## Forbidden scope
- Do not modify the Graph metadata fetch allowlist or permit arbitrary URLs.
- Do not add any new runtime dependencies (standard library only).
- Do not delete or weaken existing tests.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in any existing module.
- Do not change CI scope or add new toolchains.
- Do not write the token value, token hash, or any token-derived value to disk, stdout, stderr, or any sidecar field.
## Architectural constraints
- Keep `src/graph_schema_monitor/parser.py` as the local CSDL parsing primitive.
- Keep `src/graph_schema_monitor/diff.py` as the deterministic change engine.
- Keep `src/graph_schema_monitor/fetcher.py` as the only networked component.
- Keep `src/graph_schema_monitor/snapshots.py` as the local snapshot and sidecar loading surface.
- `fetch_authenticated_snapshot()` is the new authenticated acquisition entry point.
- CLI output is deterministic and file-based.
## Security constraints
- Token must only flow from env var → memory → `Authorization` header in the HTTP request. No other path.
- Token must not be written to disk, logs, stdout, stderr, or any sidecar field.
- Whitespace-only tokens must raise `TokenError` (exit 2) before any network call.
- Unknown profiles must raise `InvalidProfileError` before any env var is read.
- Sidecar fields `source_kind`, `auth_mode`, and `tenant_label` contain only provenance strings — never token data.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/memory.md`
- `.github/aadlc/invariants.yml`
- `.github/aadlc/trust-boundaries.md`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/fetcher.py`
- `tests/test_fetcher.py`
The following files must not change:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `src/graph_schema_monitor/snapshots.py`
- `src/graph_schema_monitor/versioning.py`
- `src/graph_schema_monitor/watchlists.py`
## Contract assertions
- CA-1: `fetch_authenticated_snapshot()` builds an `Authorization: ****** header from the stripped env var value — the token flows directly from memory to the request header and is never persisted.
- CA-2: Unknown profile raises `InvalidProfileError` before any env var is read.
- CA-3: Empty/whitespace-only token raises `TokenError` (exit 2) before any network call.
- CA-4: Token value does not appear in the sidecar JSON file.
- CA-5: `fetch_authenticated_snapshot()` opens exactly one HTTPS socket to the fixed profile URL.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm all existing tests pass unchanged.
- Confirm CA-1 through CA-5 are each covered by direct unit tests.
## Stop conditions
- Authenticated acquisition requires dynamic URL selection.
- Token persistence in any form is required.
- A new runtime dependency is needed.
- Existing tests cannot be preserved.
- CLI compatibility (existing commands) cannot be preserved.
## Acceptance criteria
- AC-1: `python -m pytest tests/` passes with no failures, no deleted tests.
- AC-2: `fetch-auth` exits 0, writes XML and sidecar files.
- AC-3: Sidecar contains `source_kind`, `auth_mode`, `tenant_label` plus the standard nine fields.
- AC-4: Empty token exits 2 with a clear error.
- AC-5: Unknown profile exits 1 before env var is read.
- AC-6: Authorization header value equals `****** — verified by `FakeCapturingOpener` in tests.
- AC-7: Token value absent from sidecar JSON.
- AC-8: All existing PR1–PR6 CLI behaviours intact.
- AC-9: README documents authenticated fetch workflow.
- AC-10: AADLC artefacts reflect PR7; no prior durable state removed.
- AC-11: No new runtime dependencies.
## Context reset notes
- Mark this contract complete after PR7 `fetch-auth` command is merged.
- Future PRs should create a fresh active contract before adding scheduling, UI, persistence, or any additional acquisition surfaces.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
