<!-- version: 1.0.0 -->
# Current PR Contract

This contract constrains implementation scope for the active PR. Update
it when scope is explicitly amended. If a requested action falls outside
approved scope, stop and escalate before proceeding.

## Goal
Deliver an offline, deterministic Python CLI that parses local Microsoft Graph-like CSDL snapshots and reports schema property diffs, with fixtures, tests, and project governance docs populated.

## Non-goals
- Live Microsoft Graph fetch or any network behavior.
- Authentication, authorization, tenant access, or cloud integration.
- Scheduler/cron, database, web UI, changelog correlation, canary logic, or AI summarization.

## Approved scope
- Populate project-specific `.github/aadlc` governance artefacts.
- Add Python package skeleton under `src/graph_schema_monitor`.
- Implement local CSDL parser and deterministic diff engine.
- Add local XML fixtures and offline pytest coverage.
- Add README usage and optional minimal CI workflow.

## Forbidden scope
- Any feature requiring network calls, tenant credentials, OAuth tokens, or Graph permissions.
- Any persistence layer beyond local files.
- Any runtime dependency addition not justified by a concrete blocker.

## Architectural constraints
- Maintain parser, diff, and CLI as separate modules.
- Use deterministic ordering and stable output schemas.
- Treat property identity as `fully-qualified-type-name + property-name`, declared-only.
- Keep PR1 implementation narrow and reversible.

## Security constraints
- No secrets or credentials in repository files.
- No unsafe execution features (`eval`, `exec`, dynamic imports from user input).
- Parse XML via safe stdlib usage only; no external entity resolution behavior.
- Avoid logging sensitive payloads (none expected for PR1 fixtures).

## Files expected to change
- `.github/aadlc/memory.md`
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/trust-boundaries.md`
- `README.md`
- `pyproject.toml`
- `src/graph_schema_monitor/*`
- `tests/fixtures/*`
- `tests/test_*.py`
- `.github/workflows/ci.yml` (optional)

## Tests / validation
- `python -m pytest tests/`
- `python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --format json`

## Stop conditions
- Requested change expands into forbidden scope areas.
- Existing repository constraints conflict with offline-only architecture.
- Deterministic output cannot be guaranteed with current data model.

## Escalation triggers
- Need to include additional OData surfaces beyond declared properties.
- Need to add non-stdlib runtime dependencies.
- Need to change non-goals for PR1.

## Context reset notes
- Mark this contract complete after parser/diff CLI, fixtures, tests, and docs are merged.
- Move future online acquisition concerns into a new PR contract.
