<!-- version: 1.0.0 -->
# Current PR Contract

This contract constrains implementation scope for the active PR. Update
it when scope is explicitly amended. If a requested action falls outside
approved scope, stop and escalate before proceeding.

## Goal
Add a tightly constrained `fetch` workflow that downloads Microsoft Graph `$metadata` from one of two fixed public endpoints and saves a local XML snapshot plus sidecar metadata for the existing offline parser/diff flow.

## Non-goals
- Authentication, OAuth, MSAL, Graph SDK, tenant access, or permissions.
- Arbitrary URL fetching, custom URL arguments, or local file URL support.
- Redirects to non-HTTPS or non-`graph.microsoft.com` hosts.
- Scheduler/cron, database, web UI, changelog correlation, canary logic, or AI summarization.
- NavigationProperty diffing, inherited-property flattening, or parser expansion beyond fetched metadata parseability.

## Approved scope
- Update `.github/aadlc` governance artefacts for PR2 trust boundaries and constraints.
- Add a stdlib-only `src/graph_schema_monitor/fetcher.py` with fixed profile allowlist, timeout, redirect rejection, content-type validation, hashing, and sidecar writing.
- Extend `src/graph_schema_monitor/cli.py` with `fetch --profile --out [--overwrite]`.
- Add deterministic offline pytest coverage for fetcher and CLI with mocked network behavior.
- Update `README.md` for the `fetch -> inspect -> diff` workflow and explicit network boundary.

## Forbidden scope
- Any authentication, tenant credentials, OAuth tokens, Graph permissions, or SDK integration.
- Any dynamic/user-supplied URLs, persistence layer beyond local files, or background scheduling.
- Any runtime dependency addition not justified by a concrete blocker and explicit approval.

## Architectural constraints
- Maintain parser, diff, fetcher, and CLI as separate modules.
- Use deterministic ordering and stable output schemas.
- Treat property identity as `fully-qualified-type-name + property-name`, declared-only.
- Keep outbound network behavior limited to allowlisted Graph metadata endpoints.
- Keep PR2 implementation narrow, reversible, and stdlib-only.

## Security constraints
- No secrets or credentials in repository files.
- No unsafe execution features (`eval`, `exec`, dynamic imports from user input).
- Parse XML via safe stdlib usage only; no external entity resolution behavior.
- Enforce HTTPS and fixed profile allowlist in code; no user-supplied URL construction.
- Reject redirects rather than expanding the trust boundary.
- Capture only allowlisted response metadata in sidecar files; no raw header dumps.

## Files expected to change
- `.github/aadlc/memory.md`
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/trust-boundaries.md`
- `.github/aadlc/invariants.yml`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/fetcher.py`
- `tests/conftest.py`
- `tests/test_fetcher.py`

## Tests / validation
- `python -m pytest tests/`
- `python -m graph_schema_monitor fetch --profile invalid --out /tmp/graph-metadata.xml`
- `python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --format json`

## Stop conditions
- Requested change expands into forbidden scope areas.
- A safe stdlib-only implementation cannot enforce the fixed outbound network boundary.
- Merge readiness depends on live network success.

## Escalation triggers
- Need to add profiles beyond `v1.0` and `beta`.
- Need to follow redirects rather than reject them.
- Need to add non-stdlib runtime dependencies.
- Need to change PR2 non-goals or broaden parser scope beyond declared properties.

## Context reset notes
- Mark this contract complete after fetcher, CLI, tests, docs, and governance updates are merged.
- Future live-network experimentation, if any, stays opt-in and outside PR2 acceptance.
