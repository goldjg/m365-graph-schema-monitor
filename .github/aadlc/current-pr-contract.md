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
Implement PR4 deterministic report filtering and summary/index output over already-computed local schema diffs while preserving the existing offline parser/diff/fetch/inventory core and trust boundaries.
## Contract status
active
## Non-goals
- Do not add any database, scheduler, background service, or web UI.
- Do not add changelog correlation, tenant access, authentication, MSAL, Graph SDK usage, or any new network behavior.
- Do not replace or broaden the existing parser, diff, fetch, snapshot inventory, or sidecar contracts.
- Do not remove or change current `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, or existing `report diff` behavior except by extending report filtering and summary output.
- Do not add AI summarization, observability dashboards, or cross-tenant reporting.
- Do not introduce new runtime dependencies.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
- Reusable instruction-pack guidance may be synced from `coding-agent-baselines` when it improves AADLCv2 governance without erasing repository-specific state.
## Approved scope
- Extend `src/graph_schema_monitor/report.py` with deterministic filtered diff rendering and unfiltered summary rendering over local diff output.
- Add `src/graph_schema_monitor/report_filters.py` for deterministic single-value filtering and summary aggregation over `DiffChange` values.
- Extend `src/graph_schema_monitor/cli.py` with `report diff` filter flags and a `report summary` subcommand.
- Add or update deterministic tests for filtering, limits, summaries, and CLI behavior.
- Update README documentation directly related to filtered reports and summary reports.
- Refresh this contract and related AADLC memory notes so PR4 scope, stop conditions, escalation triggers, and acceptance criteria are explicitly anchored to this work.
## Intentional amendments
- This PR intentionally replaces the prior PR3 active contract with a feature-delivery contract for PR4.
- Historical PR1 through PR3 work remains evidence only; it is not active implementation scope unless restated here.
- The fixed Graph metadata endpoint boundary and standard-library-only runtime remain durable carry-forward constraints.
- PR4 supports exactly one value per filter class: one `--change-type`, one `--type-prefix`, and one `--type-name`.
- PR4 summary output is intentionally unfiltered.
## Forbidden scope
- Do not modify the Graph metadata fetch allowlist or permit arbitrary URLs.
- Do not add authentication, tenant access, secrets handling, or any privileged Microsoft 365 access path.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in parser, diff, filter, summary, or output rendering.
- Do not change CI scope, add new toolchains, or introduce non-standard-library runtime packages.
- Do not expand parser coverage, add `NavigationProperty` diffing, or flatten inherited properties.
## Architectural constraints
- Keep `src/graph_schema_monitor/parser.py` as the local CSDL parsing primitive.
- Keep `src/graph_schema_monitor/diff.py` as the deterministic change engine reused by reporting surfaces.
- Keep `src/graph_schema_monitor/fetcher.py` as the only networked component and preserve its fixed-endpoint behavior.
- Keep `src/graph_schema_monitor/snapshots.py` as the local snapshot inventory and sidecar loading surface.
- Keep CLI output deterministic and file-based.
- Keep new functionality composable over already-computed local diffs rather than adding new online behavior.
## Security constraints
- No secrets, credentials, tokens, tenant data, or private customer data may be introduced.
- Do not weaken the fixed Graph metadata network boundary.
- Treat CLI paths, local XML, and sidecar JSON as untrusted inputs and validate them before rendering reports.
- Do not introduce any capability to fetch non-Graph endpoints or follow redirects.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `tests/test_cli.py`
- `tests/test_report.py`
- `tests/test_report_filters.py`
The following files may be reviewed to preserve existing contracts and invariants:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/snapshots.py`
- `.github/aadlc/memory.md`
- `.github/aadlc/trust-boundaries.md`
- `.github/aadlc/invariants.yml`
## Contract assertions
- PR3 `report diff --format json` top-level fields remain present and unchanged.
- `report diff --change-type` and `report diff --type-prefix` filter changes deterministically.
- `report diff --limit` applies after filtering while preserving stable change order.
- `report summary` counts by change type match the full unfiltered diff.
- PR4 report filtering and summary rendering introduce no new network behaviour.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm existing `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, and unfiltered `report diff` behavior still pass unchanged.
- Confirm filtered `report diff` output remains deterministic for markdown and JSON output.
- Confirm `report summary` renders deterministic unfiltered markdown and JSON output.
- Confirm report generation only uses local snapshots plus auto-resolved adjacent sidecars and does not add new network behavior.
## Stop conditions
- A requested change would introduce a database, scheduler, daemon, web UI, or any persistent service layer.
- A requested change would require authentication, tenant access, arbitrary URL fetching, or any network boundary expansion.
- A requested change would break or replace existing `fetch`, `inspect`, top-level `diff`, snapshot inventory, or unfiltered `report diff` behavior instead of extending the CLI alongside it.
- A requested change would require a new runtime dependency or non-file-based storage surface.
- The filter or summary contract needed for deterministic reporting is ambiguous beyond the approved single-value PR4 scope.
## Escalation triggers
- Need to change the sidecar schema, allowlisted fields, or fetch trust boundary.
- Need to support OR semantics, repeatable/comma-separated filters, property-name filtering, or filtered summaries within PR4.
- Need to support report formats beyond markdown/JSON or output behavior that conflicts with current deterministic diff output.
- Need to alter durable invariants in `.github/aadlc/memory.md`, `.github/aadlc/trust-boundaries.md`, or `.github/aadlc/invariants.yml`.
- Need to expand scope into scheduling, persistence, UI, or any online correlation feature.
## Context reset notes
- Mark this contract complete after PR4 filtered report and summary commands are merged.
- Future PRs should create a fresh active contract before adding scheduler, UI, persistence, online correlation, or broader filtering semantics.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
- Completed PR constraints should be treated as historical evidence unless promoted to durable invariants.
## PR4 acceptance criteria
- `python -m graph_schema_monitor report diff --old <FILE> --new <FILE> --change-type property_added` deterministically renders only matching change types.
- `python -m graph_schema_monitor report diff --old <FILE> --new <FILE> --type-prefix microsoft.graph.conditionalAccessPolicy` deterministically renders only matching type prefixes.
- `python -m graph_schema_monitor report diff --old <FILE> --new <FILE> --type-name microsoft.graph.conditionalAccessPolicy --limit 100 --format json` deterministically limits filtered JSON output.
- `python -m graph_schema_monitor report summary --old <FILE> --new <FILE> [--format markdown|json]` renders an unfiltered deterministic summary over the full diff.
- Existing `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, and existing unfiltered `report diff` behavior remains intact.
- No database, scheduler, web UI, changelog correlation, authentication, tenant access, new network behavior, or AI summarization is introduced.
