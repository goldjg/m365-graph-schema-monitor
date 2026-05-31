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
Implement PR5 local watchlist evaluation over already-computed local schema diffs while preserving the existing offline parser/diff/fetch/inventory/report core and trust boundaries.
## Contract status
active
## Non-goals
- Do not add any database, scheduler, background service, or web UI.
- Do not add changelog correlation, documentation correlation, tenant access, authentication, MSAL, Graph SDK usage, or any new network behavior.
- Do not replace or broaden the existing parser, diff, fetch, snapshot inventory, sidecar, or report contracts.
- Do not remove or change current `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, `report diff`, or `report summary` behavior except by adding separate watchlist evaluation.
- Do not add AI summarization, observability dashboards, cross-tenant reporting, or bundled production watchlist packs.
- Do not introduce new runtime dependencies.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
- Reusable instruction-pack guidance may be synced from `coding-agent-baselines` when it improves AADLCv2 governance without erasing repository-specific state.
## Approved scope
- Add `src/graph_schema_monitor/watchlists.py` for deterministic local watchlist loading, validation, matching, summaries, and markdown/json rendering over `DiffChange` values.
- Extend `src/graph_schema_monitor/cli.py` with additive `watchlist check` support that uses `load_watchlist()` as the single watchlist parsing and validation entry point.
- Add or update deterministic tests for watchlist validation, matching semantics, markdown/json output, CLI behavior, and no-network guarantees.
- Update README documentation directly related to local watchlist workflow and file schema.
- Refresh this contract and related AADLC artifacts so PR5 scope, stop conditions, escalation triggers, trust-boundary handling, and acceptance criteria are explicitly anchored to watchlists.
## Intentional amendments
- This PR intentionally replaces the prior PR4 active contract with a feature-delivery contract for PR5.
- Historical PR1 through PR4 work remains evidence only; it is not active implementation scope unless restated here.
- The fixed Graph metadata endpoint boundary and standard-library-only runtime remain durable carry-forward constraints.
- Watchlist evaluation is intentionally separate from `report diff` in PR5.
- `tests/test_cli.py` may only receive additive watchlist CLI tests; existing CLI behavior and assertions must remain intact except for mechanical refactoring that preserves behavior.
## Forbidden scope
- Do not modify the Graph metadata fetch allowlist or permit arbitrary URLs.
- Do not add authentication, tenant access, secrets handling, or any privileged Microsoft 365 access path.
- Do not add persistence beyond existing local snapshot files, adjacent sidecars, and local watchlist JSON files.
- Do not remove or weaken deterministic ordering guarantees in parser, diff, filter, summary, watchlist matching, or output rendering.
- Do not change CI scope, add new toolchains, or introduce non-standard-library runtime packages.
- Do not expand parser coverage, add `NavigationProperty` diffing, or flatten inherited properties.
- Do not duplicate watchlist validation logic in `cli.py`.
## Architectural constraints
- Keep `src/graph_schema_monitor/parser.py` as the local CSDL parsing primitive.
- Keep `src/graph_schema_monitor/diff.py` as the deterministic change engine reused by reporting and watchlist surfaces.
- Keep `src/graph_schema_monitor/fetcher.py` as the only networked component and preserve its fixed-endpoint behavior.
- Keep `src/graph_schema_monitor/snapshots.py` as the local snapshot inventory and sidecar loading surface.
- Keep `src/graph_schema_monitor/report.py` and `src/graph_schema_monitor/report_filters.py` as existing report primitives; watchlists must compose over them rather than replacing them.
- Keep CLI output deterministic and file-based.
- Keep new functionality composable over already-computed local diffs rather than adding new online behavior.
## Security constraints
- No secrets, credentials, tokens, tenant data, or private customer data may be introduced.
- Do not weaken the fixed Graph metadata network boundary.
- Treat CLI paths, local XML, sidecar JSON, and watchlist JSON as untrusted inputs and validate them before rendering reports.
- Do not introduce any capability to fetch non-Graph endpoints or follow redirects.
- Watchlist loading must use JSON parsing plus explicit field validation only; no eval, dynamic imports, or file inclusion.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/memory.md`
- `.github/aadlc/trust-boundaries.md`
- `.github/aadlc/invariants.yml`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/watchlists.py`
- `tests/test_cli.py`
- `tests/test_watchlists.py`
- `tests/fixtures/watchlist_identity.json`
- `tests/fixtures/watchlist_empty_prefixes.json`
The following files may be reviewed to preserve existing contracts and invariants:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `src/graph_schema_monitor/snapshots.py`
## Contract assertions
- Invalid watchlist JSON exits with code `2` and a clear error, while valid watchlists load through `load_watchlist()`.
- Watchlist matching applies OR semantics within each filter list and AND semantics across filter classes.
- `watchlist check --format json` emits the approved top-level fields in stable order and includes all seven change types in `matches_by_change_type`.
- No-match watchlists succeed with exit code `0` and clearly report `No matching watchlist changes.` in markdown output.
- Watchlist evaluation introduces no new network behavior.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm existing `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, `report diff`, and `report summary` behavior still pass unchanged.
- Confirm watchlist validation rejects malformed structures, duplicate values, unexpected fields, and unknown change types.
- Confirm watchlist markdown/json output remains deterministic and preserves stable field/group ordering.
- Confirm `watchlist check` only uses local snapshots, optional adjacent sidecars, local watchlist JSON, and existing diff output.
## Stop conditions
- A requested change would introduce a database, scheduler, daemon, web UI, or any persistent service layer.
- A requested change would require authentication, tenant access, arbitrary URL fetching, or any network boundary expansion.
- A requested change would break or replace existing `fetch`, `inspect`, top-level `diff`, snapshot inventory, `report diff`, or `report summary` behavior instead of extending the CLI alongside it.
- A requested change would require a new runtime dependency or non-file-based storage surface.
- Watchlist schema or matching semantics become ambiguous beyond the approved exact-string/prefix PR5 scope.
## Escalation triggers
- Need to change parser or diff semantics to support watchlist matching.
- Need to support wildcard, regex, case-insensitive matching, severity scoring, or report formats beyond markdown/JSON.
- Need to add watchlist handling inside `report diff` instead of keeping a separate `watchlist check` command.
- Need to alter durable invariants or trust boundaries beyond explicitly recording the local watchlist JSON boundary.
- Need to expand scope into scheduling, persistence, UI, or any online correlation feature.
## Context reset notes
- Mark this contract complete after PR5 watchlist commands are merged.
- Future PRs should create a fresh active contract before adding scheduling, UI, persistence, broader matching semantics, or online correlation.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
- Completed PR constraints should be treated as historical evidence unless promoted to durable invariants.
## PR5 acceptance criteria
- `python -m graph_schema_monitor watchlist check --old <FILE> --new <FILE> --watchlist <FILE>` deterministically renders markdown output over local diff results.
- `python -m graph_schema_monitor watchlist check --old <FILE> --new <FILE> --watchlist <FILE> --format json` emits the approved stable JSON schema and field order.
- Invalid watchlists fail clearly with exit code `2`.
- No-match watchlists succeed with exit code `0` and clear empty-result output.
- Existing `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, `report diff`, and `report summary` behavior remains intact.
- No database, scheduler, web UI, changelog correlation, authentication, tenant access, new network behavior, or AI summarization is introduced.
