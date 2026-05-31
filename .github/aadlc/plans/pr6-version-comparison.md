Clarification before implementation:

- The approved JSON report_type for PR6 is "version_comparison". Do not use "schema_version_comparison".
- Missing or empty sha256 may fail through existing SnapshotSidecar/hash validation. That is acceptable if the failure is clear and exits with code 2.

You are Codex acting as the implementation-planning model in Graham's AADLCv2 workflow.

OPERATING MODE: Plan-only unless Graham explicitly says "implement", "proceed", or "approved".
In Plan-only mode: produce the plan below, report "No code changes proposed (Plan-only mode)" and
"Not run (Plan-only mode)" under the required final headings.

─────────────────────────────────────────────────────────────────────────
BEFORE PLANNING — READ THESE FILES IN FULL
─────────────────────────────────────────────────────────────────────────
Read every file listed here before producing a single planning word.
Do not skip any file. Note the exact public API signatures you will reuse.

  .github/copilot-instructions.md
  .github/aadlc/current-pr-contract.md        ← currently PR5 active; PR6 will replace it
  .github/aadlc/memory.md
  .github/aadlc/trust-boundaries.md
  .github/aadlc/invariants.yml
  .github/aadlc/plans/plan-template.md
  README.md

  src/graph_schema_monitor/parser.py
  src/graph_schema_monitor/diff.py             ← note: diff_snapshots() signature
  src/graph_schema_monitor/fetcher.py          ← note: ALLOWED_SIDECAR_FIELDS tuple
  src/graph_schema_monitor/snapshots.py        ← note: load_snapshot_bundle(), SnapshotBundle,
                                                        SnapshotSidecar, SnapshotValidationError
  src/graph_schema_monitor/report.py           ← note: JSON_DIFF_REPORT_FIELDS, _write_output_file
  src/graph_schema_monitor/report_filters.py
  src/graph_schema_monitor/watchlists.py       ← note: JSON_WATCHLIST_REPORT_FIELDS pattern
  src/graph_schema_monitor/cli.py              ← note: _build_parser(), _write_output_file(),
                                                        existing subcommand shape

  tests/test_cli.py                            ← note: _write_snapshot_with_sidecar() helper
  tests/test_report.py
  tests/test_report_filters.py
  tests/test_snapshots.py
  tests/test_watchlists.py
  tests/test_diff.py
  tests/test_fetcher.py
  tests/test_parser.py
  tests/fixtures/                              ← list all files; you will reuse these fixtures

─────────────────────────────────────────────────────────────────────────
THIS IS PR6
─────────────────────────────────────────────────────────────────────────

PR6 adds deterministic schema version comparison over existing local snapshots and their
adjacent validated sidecars. It answers three questions simultaneously:

  1. Did x_ms_schema_version change?       (schema_version_changed)
  2. Did the raw payload hash change?      (sha256_changed)
  3. Did parsed schema content change?     (semantic_changes_present)

PR6 is local-first, file-based, standard-library-only, and fail-closed on missing provenance.
PR6 must not add any authentication, network behaviour, database, scheduler, web UI, or
changelog correlation.

─────────────────────────────────────────────────────────────────────────
TASK: PRODUCE A SCOPED IMPLEMENTATION PLAN
─────────────────────────────────────────────────────────────────────────

Use the plan-template.md structure. Cover all numbered sections below.
Do not write code — write the plan only.

══════════════════════════════════════════════════════════════════════════
SECTION 1 — SUMMARY
══════════════════════════════════════════════════════════════════════════

One paragraph. State what PR6 adds, what it reuses, and what remains
unchanged.

══════════════════════════════════════════════════════════════════════════
SECTION 2 — PR CONTRACT (replace the current PR5 contract)
══════════════════════════════════════════════════════════════════════════

Write the full replacement for .github/aadlc/current-pr-contract.md
using the PR5 contract as a structural template. Preserve all required
headings. Record:

  Goal: Add deterministic version/hash/semantic comparison over local
  snapshots.
  Contract status: active
  Non-goals: (list all forbidden items from the hard-constraints section)
  Carry-forward rules: (same as PR5)
  Approved scope: (see SECTION 6)
  Intentional amendments: replace PR5 active contract; watchlist work
    is completed history; watchlists-local-only invariant carries forward.
  Forbidden scope: (derived from hard-constraints)
  Architectural constraints: (same module separation; add versioning.py)
  Security constraints: (same plus: sidecar fields are untrusted; fail
    closed; no sha256 guessing)
  Files expected to change: (list exactly; see SECTION 8–9)
  Contract assertions: (see SECTION 13)
  Tests / validation: (see SECTION 15)
  Stop conditions: (see SECTION 19)
  Escalation triggers: (see SECTION 20)
  Acceptance criteria: (see SECTION 21)

══════════════════════════════════════════════════════════════════════════
SECTION 3 — CONTRACT ASSERTIONS (5 items)
══════════════════════════════════════════════════════════════════════════

State exactly five behaviours that tests must assert against the contract,
not the implementation. Number them CA-1 through CA-5.

  CA-1  PROVENANCE REQUIREMENT
        build_version_comparison() raises SnapshotValidationError (exit
        code 2) in each of these cases independently:
          • old sidecar file is absent
          • new sidecar file is absent
          • old sidecar sha256 field is missing or empty
          • new sidecar sha256 field is missing or empty
          • old sidecar x_ms_schema_version field is missing (null or absent)
          • new sidecar x_ms_schema_version field is missing (null or absent)
        Tests must exercise each sub-case individually.

  CA-2  CLASSIFICATION CORRECTNESS
        classify_version_comparison() maps all eight input combinations of
        (schema_version_changed, sha256_changed, semantic_changes_present)
        to the exact deterministic classification strings below, with no
        other outputs possible:

          (F,F,F) → version_same_content_same_semantics_same
          (F,F,T) → version_same_content_same_semantics_changed
          (F,T,F) → version_same_content_changed_semantics_same
          (F,T,T) → version_same_content_changed_semantics_changed
          (T,F,F) → version_changed_content_same_semantics_same
          (T,F,T) → version_changed_content_same_semantics_changed
          (T,T,F) → version_changed_content_changed_semantics_same
          (T,T,T) → version_changed_content_changed_semantics_changed

        These eight tests must call classify_version_comparison() directly.

  CA-3  JSON REPORT SCHEMA
        render_version_comparison_json() (and CLI --format json) produces a
        JSON object whose top-level keys, in iteration order, are exactly:

          report_type, old_snapshot, new_snapshot,
          old_profile, new_profile,
          old_fetched_at_utc, new_fetched_at_utc,
          old_sha256, new_sha256,
          old_x_ms_schema_version, new_x_ms_schema_version,
          schema_version_changed, sha256_changed,
          semantic_change_count, semantic_changes_present,
          classification

        (Codex may propose minor field-order adjustments here, but must
        justify any deviation and list the final approved order in the plan.
        The order must be stable across Python versions.)

  CA-4  LOCAL-ONLY BEHAVIOUR
        version compare must not open any network sockets. Tests must use
        socket.setdefaulttimeout(0) or monkeypatching to assert no network
        calls are introduced. Pattern: mirror the existing no-network test
        in tests/test_cli.py.

  CA-5  EXISTING BEHAVIOUR PRESERVATION
        All existing tests in test_cli.py, test_report.py,
        test_report_filters.py, test_snapshots.py, test_watchlists.py,
        test_diff.py, test_fetcher.py, and test_parser.py must continue to
        pass without modification.

══════════════════════════════════════════════════════════════════════════
SECTION 4 — CURRENT-STATE OBSERVATIONS
══════════════════════════════════════════════════════════════════════════

After reading the repository, record what is already present that PR6
can reuse. Address each item:

  4a. load_snapshot_bundle() signature and allow_missing_sidecar flag.
      PR6 must call it with allow_missing_sidecar=False (default).
      Confirm the default is False by reading the source.

  4b. SnapshotSidecar fields. Confirm x_ms_schema_version is str | None
      and sha256 is str (never None). Record what happens when
      x_ms_schema_version is None — that is a valid sidecar but fails the
      PR6 provenance requirement.

  4c. SnapshotValidationError.exit_code = 2. PR6 must reuse this for all
      provenance failures.

  4d. diff_snapshots() signature: (old: SchemaSnapshot, new: SchemaSnapshot,
      type_name: str | None = None) -> list[DiffChange]. PR6 calls it with
      no type_name filter.

  4e. _write_output_file() in cli.py — atomic write helper; PR6 must reuse
      it rather than reimplementing.

  4f. JSON_DIFF_REPORT_FIELDS and JSON_WATCHLIST_REPORT_FIELDS — patterns
      PR6 should follow for JSON_VERSION_COMPARISON_REPORT_FIELDS.

  4g. Existing _write_snapshot_with_sidecar() helper in test_cli.py and
      test_watchlists.py. PR6 tests should reuse or copy this pattern.

  4h. tests/fixtures/ — schema_old.xml and schema_new.xml are the existing
      fixture pair. PR6 tests may use them.

  4i. Current-pr-contract.md is still the PR5 contract. PR6 replaces it.

  4j. invariants.yml — record the existing watchlists-local-only invariant
      which PR6 will be joined by version-comparison-local-only.

══════════════════════════════════════════════════════════════════════════
SECTION 5 — PROPOSED CLI SHAPE
══════════════════════════════════════════════════════════════════════════

New command:

  python -m graph_schema_monitor version compare \
    --old <PATH>       required, path to old XML snapshot
    --new <PATH>       required, path to new XML snapshot
    --format <FMT>     optional, choices: markdown (default), json
    --out <PATH>       optional, output file; stdout if omitted

Subcommand nesting: add "version" as a new top-level subcommand in
_build_parser(), with "compare" as its required sub-subcommand — exactly
mirroring the "snapshots" and "report" nesting pattern already in cli.py.

Existing commands that must remain unchanged:
  fetch, inspect, diff, snapshots list, snapshots validate,
  report diff, report summary, watchlist check

Exit codes:
  0 — success
  2 — invalid CLI input, missing sidecar, missing required provenance
      (x_ms_schema_version or sha256), malformed sidecar, unreadable files

The handler must call _write_output_file() from cli.py for --out writes.
The handler must not inline its own file-write logic.

══════════════════════════════════════════════════════════════════════════
SECTION 6 — PROPOSED FILE TREE
══════════════════════════════════════════════════════════════════════════

  NEW:
    src/graph_schema_monitor/versioning.py
    tests/test_versioning.py

  MODIFIED:
    src/graph_schema_monitor/cli.py       (additive: new subcommand only)
    .github/aadlc/current-pr-contract.md (replace PR5 with PR6 contract)
    .github/aadlc/memory.md              (append PR6 durable facts)
    .github/aadlc/invariants.yml         (append version-comparison-local-only)
    README.md                            (append version comparison workflow)

  UNCHANGED (must not be modified):
    src/graph_schema_monitor/parser.py
    src/graph_schema_monitor/diff.py
    src/graph_schema_monitor/fetcher.py
    src/graph_schema_monitor/snapshots.py
    src/graph_schema_monitor/report.py
    src/graph_schema_monitor/report_filters.py
    src/graph_schema_monitor/watchlists.py
    tests/test_cli.py          (no deletions; only additive version tests allowed)
    tests/test_diff.py
    tests/test_fetcher.py
    tests/test_parser.py
    tests/test_report.py
    tests/test_report_filters.py
    tests/test_snapshots.py
    tests/test_watchlists.py
    tests/conftest.py
    tests/fixtures/schema_old.xml
    tests/fixtures/schema_new.xml
    tests/fixtures/watchlist_identity.json
    tests/fixtures/watchlist_empty_prefixes.json

  Note: .github/aadlc/trust-boundaries.md should be reviewed. If Codex
  determines a new row is needed for the local sidecar version/hash
  provenance surface, add it. If the existing "Local snapshot XML" and
  "Local watchlist JSON" rows already cover this surface, note that
  explicitly and leave the file unchanged.

══════════════════════════════════════════════════════════════════════════
SECTION 7 — EXACT FILES TO ADD
══════════════════════════════════════════════════════════════════════════

7a. src/graph_schema_monitor/versioning.py

    Required public symbols (exact names; Codex may not rename them):

      JSON_VERSION_COMPARISON_REPORT_FIELDS: tuple[str, ...]
        — the stable field-order tuple for JSON output; mirrors
          JSON_DIFF_REPORT_FIELDS and JSON_WATCHLIST_REPORT_FIELDS patterns

      @dataclass(frozen=True)
      class VersionComparison:
          old_snapshot: Path
          new_snapshot: Path
          old_profile: str | None
          new_profile: str | None
          old_fetched_at_utc: str | None
          new_fetched_at_utc: str | None
          old_sha256: str
          new_sha256: str
          old_x_ms_schema_version: str
          new_x_ms_schema_version: str
          schema_version_changed: bool
          sha256_changed: bool
          semantic_change_count: int
          semantic_changes_present: bool
          classification: str

      def build_version_comparison(
          old_snapshot_path: str | Path,
          new_snapshot_path: str | Path,
      ) -> VersionComparison:
          """
          Load two local snapshot bundles (sidecars required), validate
          provenance, compute semantic diff, and return a frozen
          VersionComparison. Raises SnapshotValidationError for any
          missing or invalid provenance.
          """

      def classify_version_comparison(
          *,
          schema_version_changed: bool,
          sha256_changed: bool,
          semantic_changes_present: bool,
      ) -> str:
          """Return deterministic classification string. No side effects."""

      def render_version_comparison_markdown(comparison: VersionComparison) -> str:
          """Return deterministic Markdown string. No I/O."""

      def render_version_comparison_json(comparison: VersionComparison) -> str:
          """Return deterministic JSON string. No I/O."""

    Required behaviour:

      build_version_comparison() must:
        • call load_snapshot_bundle(path, allow_missing_sidecar=False) for both paths
        • after loading, assert bundle.sidecar is not None (defensive; load_snapshot_bundle
          with allow_missing_sidecar=False already raises if absent)
        • assert bundle.sidecar.sha256 is non-empty (it is always non-empty per SnapshotSidecar
          — but explicitly fail if somehow empty)
        • assert bundle.sidecar.x_ms_schema_version is not None and not empty — if it is None
          or empty, raise SnapshotValidationError with message:
          "sidecar x_ms_schema_version is required for version comparison: <path>"
        • call diff_snapshots(old_bundle.snapshot, new_bundle.snapshot) with no type_name filter
        • compute semantic_change_count = len(changes)
        • compute semantic_changes_present = semantic_change_count > 0
        • compute schema_version_changed = (old_xmsv != new_xmsv)
        • compute sha256_changed = (old_sha256 != new_sha256)
        • call classify_version_comparison(...) for the classification field
        • set old_profile and new_profile from sidecar.profile (str, never None per SnapshotSidecar)
        • set old_fetched_at_utc and new_fetched_at_utc from sidecar.fetched_at_utc

      classify_version_comparison() must:
        • be a pure function with no imports beyond builtins
        • cover all eight (bool, bool, bool) combinations exactly
        • raise ValueError for any unexpected combination (defensive; should be unreachable)

      render_version_comparison_markdown() must:
        • not read files, make network calls, or inspect wall-clock time
        • produce output matching the required Markdown structure below
        • be deterministic given the same VersionComparison input

      render_version_comparison_json() must:
        • serialise fields in JSON_VERSION_COMPARISON_REPORT_FIELDS order
        • use json.dumps with indent=2 and no sort_keys (order is explicit)
        • be deterministic given the same VersionComparison input
        • not include wall-clock timestamps beyond those already in sidecar fields

7b. tests/test_versioning.py

    See SECTION 15 for the full test plan.

══════════════════════════════════════════════════════════════════════════
SECTION 8 — EXACT FILES TO MODIFY
══════════════════════════════════════════════════════════════════════════

8a. src/graph_schema_monitor/cli.py

    Changes: additive only.

    • Import from versioning: build_version_comparison, render_version_comparison_markdown,
      render_version_comparison_json.
    • In _build_parser(), add:
        version_parser = subparsers.add_parser("version", ...)
        version_subparsers = version_parser.add_subparsers(dest="version_command", required=True)
        version_compare_parser = version_subparsers.add_parser("compare", ...)
        version_compare_parser.add_argument("--old", required=True, ...)
        version_compare_parser.add_argument("--new", required=True, ...)
        version_compare_parser.add_argument("--format", choices=["markdown","json"], default="markdown", ...)
        version_compare_parser.add_argument("--out", ...)
        version_compare_parser.set_defaults(handler=_version_compare)
    • Add _version_compare(args) handler:
        call build_version_comparison(args.old_snapshot, args.new_snapshot)
        catch SnapshotValidationError and return exit_code 2
        dispatch to render_version_comparison_markdown or render_version_comparison_json
        use _write_output_file() for --out; print() for stdout
    • Do not touch any other existing function in cli.py.

8b. .github/aadlc/current-pr-contract.md — replace with PR6 contract (see SECTION 2).

8c. .github/aadlc/memory.md — append PR6 durable facts:
    • versioning.py is the new local-only version/hash/semantic comparison module
    • VersionComparison dataclass fields and their provenance sources
    • version-comparison-local-only invariant added

8d. .github/aadlc/invariants.yml — append:
      - id: version-comparison-local-only
        name: Version comparison is local-only
        rule: >
          Version comparison must use only local snapshots, adjacent validated sidecars,
          and existing diff output. It must not introduce network calls, authentication,
          tenant access, or external correlation.
        severity: high

8e. README.md — append a new section "Version comparison workflow":
    • Explain the three-dimension comparison model (version / content / semantic)
    • Show both example CLI invocations (markdown stdout, json --out)
    • Describe the eight classification values
    • State that sidecars with x_ms_schema_version are required
    • Keep existing sections intact

══════════════════════════════════════════════════════════════════════════
SECTION 9 — FILES THAT MUST REMAIN UNCHANGED
══════════════════════════════════════════════════════════════════════════

  parser.py, diff.py, fetcher.py, snapshots.py, report.py,
  report_filters.py, watchlists.py — no changes permitted.

  All existing test files — no deletions or modifications to existing
  test functions. Only new test functions may be added to test_cli.py if
  Codex adds version compare CLI tests there; all new versioning tests
  must go in tests/test_versioning.py.

  All fixture files — no modifications to existing fixtures.

══════════════════════════════════════════════════════════════════════════
SECTION 10 — VERSION COMPARISON DATA MODEL
══════════════════════════════════════════════════════════════════════════

Use the VersionComparison dataclass exactly as specified in SECTION 7a.

Rationale for field types:
  • old_sha256, new_sha256 — str (SnapshotSidecar.sha256 is always str)
  • old_x_ms_schema_version, new_x_ms_schema_version — str (validated
    non-None before dataclass construction; fail-closed before reaching here)
  • old_profile, new_profile — str | None (SnapshotSidecar.profile is str,
    so these will always be str in practice, but the dataclass accepts None
    for forward compatibility; Codex must confirm after reading snapshots.py)
  • old_fetched_at_utc, new_fetched_at_utc — str | None (same reasoning)

VersionComparison is frozen and immutable. It must not contain mutable
collections. All Path values are the resolved input paths.

══════════════════════════════════════════════════════════════════════════
SECTION 11 — CLASSIFICATION SEMANTICS
══════════════════════════════════════════════════════════════════════════

All eight classification strings, enforced by CA-2:

  version_same_content_same_semantics_same
  version_same_content_same_semantics_changed
  version_same_content_changed_semantics_same
  version_same_content_changed_semantics_changed
  version_changed_content_same_semantics_same
  version_changed_content_same_semantics_changed
  version_changed_content_changed_semantics_same
  version_changed_content_changed_semantics_changed

These strings encode the three boolean dimensions in a stable,
human-readable, grep-friendly format. They must be the only possible
return values from classify_version_comparison().

Operational significance (record in plan, not necessarily in code):
  • version_same_content_same_semantics_same — identical in all respects;
    confirm the fetch recorded the same snapshot.
  • version_changed_content_same_semantics_same — version header advanced
    but no content or semantic change detected; possible cosmetic bump.
  • version_same_content_changed_semantics_same — payload bytes differ but
    parsed schema meaning is identical; likely whitespace or XML formatting.
  • version_changed_content_changed_semantics_changed — typical schema
    release; all three signals fire.

══════════════════════════════════════════════════════════════════════════
SECTION 12 — REQUIRED PROVENANCE VALIDATION
══════════════════════════════════════════════════════════════════════════

build_version_comparison() validation sequence (order matters for error
message clarity):

  1. Call load_snapshot_bundle(old_path, allow_missing_sidecar=False).
     If sidecar is missing: SnapshotValidationError propagates with
     message "Missing sidecar for snapshot: <path>" (from snapshots.py).

  2. Call load_snapshot_bundle(new_path, allow_missing_sidecar=False).
     Same behaviour.

  3. For old bundle: assert bundle.sidecar.x_ms_schema_version is not None
     and not empty. If violated: raise SnapshotValidationError(
     "sidecar x_ms_schema_version is required for version comparison: <path>").

  4. For new bundle: same as step 3.

  5. (sha256 validation is already enforced by load_snapshot_bundle /
     _load_snapshot_sidecar_result via hash comparison — see snapshots.py
     lines ~287–291. No additional sha256 check needed in PR6.)

  Fail-closed rule: if any provenance check fails, raise immediately.
  Do not fall back to partial data. Do not guess.

══════════════════════════════════════════════════════════════════════════
SECTION 13 — MARKDOWN OUTPUT DESIGN
══════════════════════════════════════════════════════════════════════════

Required Markdown structure (render_version_comparison_markdown must
produce output containing at least these sections in this order):

  # Graph Schema Version Comparison

  ## Snapshots

  - Old snapshot: <old_snapshot path>
  - New snapshot: <new_snapshot path>
  - Old profile: <old_profile>
  - New profile: <new_profile>
  - Old fetched at (UTC): <old_fetched_at_utc>
  - New fetched at (UTC): <new_fetched_at_utc>

  ## Provenance

  | Field | Old | New |
  |---|---|---|
  | x-ms-schemaVersion | <old_x_ms_schema_version> | <new_x_ms_schema_version> |
  | SHA-256 | <old_sha256> | <new_sha256> |

  ## Change Detection

  | Dimension | Changed |
  |---|---|
  | Schema version | <yes/no> |
  | Content (SHA-256) | <yes/no> |
  | Semantic (parsed diff) | <yes/no> |

  Semantic changes detected: <N>

  ## Classification

  `<classification>`

Rules:
  • No wall-clock timestamps in output.
  • Output is deterministic given the same VersionComparison input.
  • Codex may propose minor formatting improvements but must preserve all
    section headings and the table structures above.

══════════════════════════════════════════════════════════════════════════
SECTION 14 — JSON OUTPUT DESIGN
══════════════════════════════════════════════════════════════════════════

Approved top-level fields in stable iteration order (CA-3):

  report_type              — always "version_comparison"
  old_snapshot             — str(comparison.old_snapshot)
  new_snapshot             — str(comparison.new_snapshot)
  old_profile              — comparison.old_profile
  new_profile              — comparison.new_profile
  old_fetched_at_utc       — comparison.old_fetched_at_utc
  new_fetched_at_utc       — comparison.new_fetched_at_utc
  old_sha256               — comparison.old_sha256
  new_sha256               — comparison.new_sha256
  old_x_ms_schema_version  — comparison.old_x_ms_schema_version
  new_x_ms_schema_version  — comparison.new_x_ms_schema_version
  schema_version_changed   — comparison.schema_version_changed
  sha256_changed           — comparison.sha256_changed
  semantic_change_count    — comparison.semantic_change_count
  semantic_changes_present — comparison.semantic_changes_present
  classification           — comparison.classification

Implementation: build a dict in field-insertion order using
JSON_VERSION_COMPARISON_REPORT_FIELDS as the key sequence; use
json.dumps(d, indent=2) (no sort_keys). This mirrors the
JSON_DIFF_REPORT_FIELDS / JSON_WATCHLIST_REPORT_FIELDS pattern.

══════════════════════════════════════════════════════════════════════════
SECTION 15 — TEST PLAN
══════════════════════════════════════════════════════════════════════════

All new tests go in tests/test_versioning.py unless otherwise noted.
Existing tests must not be modified or deleted.

Group 1 — classify_version_comparison() (CA-2)
  • test_classify_all_false
  • test_classify_semantic_only
  • test_classify_content_only
  • test_classify_content_and_semantic
  • test_classify_version_only
  • test_classify_version_and_semantic
  • test_classify_version_and_content
  • test_classify_all_true
  (8 tests, one per combination)

Group 2 — build_version_comparison() provenance failures (CA-1)
  • test_missing_old_sidecar_raises
  • test_missing_new_sidecar_raises
  • test_missing_old_x_ms_schema_version_raises
  • test_missing_new_x_ms_schema_version_raises
  • test_null_old_x_ms_schema_version_raises
  • test_null_new_x_ms_schema_version_raises
  (All must assert SnapshotValidationError is raised)

Group 3 — build_version_comparison() success cases
  • test_no_changes_all_same: use two identical snapshot copies with
    same sha256 and same x_ms_schema_version → all three booleans False
  • test_all_changes: use schema_old.xml / schema_new.xml with different
    sha256 and different x_ms_schema_version → verify all three booleans
    True and semantic_change_count > 0

Group 4 — render_version_comparison_markdown() (CA-3 partial)
  • test_markdown_contains_required_sections: assert "# Graph Schema
    Version Comparison", "## Snapshots", "## Provenance",
    "## Change Detection", "## Classification" all appear
  • test_markdown_contains_classification_string: assert classification
    value appears in output

Group 5 — render_version_comparison_json() (CA-3)
  • test_json_top_level_fields_in_order: parse output; assert list(d.keys())
    == list(JSON_VERSION_COMPARISON_REPORT_FIELDS)
  • test_json_report_type_field: assert d["report_type"] == "version_comparison"

Group 6 — CLI tests (may live in test_cli.py as additive tests)
  • test_cli_version_compare_markdown: run CLI, assert exit 0, stdout
    contains "# Graph Schema Version Comparison"
  • test_cli_version_compare_json: run CLI --format json, assert exit 0,
    parse stdout JSON, assert top-level keys match approved field order
  • test_cli_version_compare_out: run CLI --out <tmp>, assert exit 0,
    file created, contains expected content
  • test_cli_version_compare_missing_sidecar_exits_2: remove one sidecar,
    assert exit code == 2

Group 7 — no-network assertion (CA-4)
  • test_version_compare_no_network: set socket.setdefaulttimeout(0),
    call build_version_comparison() with valid local fixtures, assert no
    ConnectionError or socket.timeout is raised (and if either is raised,
    that is a test failure indicating network access was attempted)
  Alternatively: monkeypatch socket.socket to raise if instantiated;
  confirm no socket is opened during comparison.

Group 8 — existing tests still pass (CA-5)
  • No new action needed; running pytest tests/ covers this. Explicitly
    note in the plan that CI must pass all existing tests unmodified.

══════════════════════════════════════════════════════════════════════════
SECTION 16 — README UPDATES
══════════════════════════════════════════════════════════════════════════

Append a new top-level section after the existing Watchlists section.
Title: "Version comparison"

Content must include:
  • One-paragraph explanation of the three-dimension model
  • Example: python -m graph_schema_monitor version compare --old ... --new ...
  • Example with --format json --out
  • Table or bullet list of the eight classification values with brief meaning
  • Note that both snapshots must have adjacent sidecars with x_ms_schema_version

Do not modify or remove existing README sections.

══════════════════════════════════════════════════════════════════════════
SECTION 17 — AADLC ARTEFACT UPDATES
══════════════════════════════════════════════════════════════════════════

17a. current-pr-contract.md — replace PR5 contract with PR6 contract
     (full content defined in SECTION 2).

17b. memory.md — append under "Architecture summary":
       - versioning.py performs local-only version/hash/semantic comparison
         over validated snapshot bundles; it uses load_snapshot_bundle(),
         diff_snapshots(), and SnapshotValidationError without modifying them.
     Append under "Core invariants":
       - version-comparison-local-only: see invariants.yml

17c. invariants.yml — append version-comparison-local-only as described
     in SECTION 8d. Preserve all existing invariants exactly.

17d. trust-boundaries.md — evaluate whether a new row is needed.
     Expected answer: No new row is needed. The "Local snapshot XML"
     boundary already covers the XML input surface. The "CLI arguments"
     boundary covers the --old and --new paths. The sidecar fields
     (sha256, x_ms_schema_version) are already inside the validated
     sidecar trust boundary implicitly covered by "Local snapshot XML"
     and the existing sidecar validation path in snapshots.py.
     If Codex disagrees after reading the file, it must explain why and
     propose a specific new row with justification.

══════════════════════════════════════════════════════════════════════════
SECTION 18 — SECURITY AND TRUST-BOUNDARY CONSIDERATIONS
══════════════════════════════════════════════════════════════════════════

  • PR6 introduces no new network surface.
  • PR6 introduces no authentication, token handling, or tenant access.
  • Sidecar fields sha256 and x_ms_schema_version are string values
    extracted from already-validated JSON by snapshots.py. They are used
    only for equality comparison and string rendering — no execution,
    no dynamic import, no eval.
  • Path inputs (--old, --new) are untrusted CLI inputs. They are passed
    to load_snapshot_bundle(), which validates file existence and parses
    through safe XML patterns already present in parser.py.
  • JSON output uses json.dumps() with no dynamic field injection.
  • Markdown output uses string formatting; no template engine or dynamic
    evaluation.
  • sha256 values are rendered as-is in output — they were validated
    against actual file content by snapshots.py before reaching versioning.py.
  • No new secret handling surface is introduced.

══════════════════════════════════════════════════════════════════════════
SECTION 19 — STOP CONDITIONS
══════════════════════════════════════════════════════════════════════════

Stop and escalate to Graham if any of the following arise:

  • Version comparison requires changing parser or diff semantics.
  • Sidecar validation needs weakening (e.g. allowing None sha256).
  • JSON schema compatibility with existing report outputs cannot be
    preserved.
  • Any new runtime dependency appears necessary.
  • Any new network behaviour is introduced.
  • Authentication, token handling, or tenant access is requested.
  • Existing tests would need to be weakened or deleted.
  • CLI compatibility (existing commands) cannot be preserved.
  • Contract assertions CA-1 through CA-5 cannot be mapped to direct tests.
  • Corrective prompt budget is exceeded (one corrective prompt acceptable;
    two means reset session; three means abandon model).

══════════════════════════════════════════════════════════════════════════
SECTION 20 — ESCALATION TRIGGERS
══════════════════════════════════════════════════════════════════════════

Ask Graham before proceeding if:

  • You propose authenticated $metadata acquisition.
  • You propose merging version compare output into report diff instead
    of keeping it separate.
  • You propose best-effort behaviour when sidecar provenance is missing
    (e.g. silently treating missing x_ms_schema_version as "unknown").
  • You propose source labels, tenant labels, or public-vs-authenticated
    comparison in PR6.
  • You propose report formats beyond Markdown and JSON.
  • You propose adding any dependency not already in pyproject.toml.
  • You need to alter any existing durable invariant.
  • You need to add a new trust-boundary row beyond what is described in
    SECTION 17d.
  • You propose NavigationProperty diffing or inherited-property flattening.
  • You propose expanding parser coverage.

══════════════════════════════════════════════════════════════════════════
SECTION 21 — ACCEPTANCE CRITERIA
══════════════════════════════════════════════════════════════════════════

The PR is ready to merge when all of the following hold:

  AC-1  python -m pytest tests/ passes with no failures, no deleted tests,
        and no weakened assertions.

  AC-2  python -m graph_schema_monitor version compare --old <FILE> --new <FILE>
        exits 0 and prints a Markdown report containing all required sections.

  AC-3  python -m graph_schema_monitor version compare --old <FILE> --new <FILE>
        --format json exits 0 and prints a JSON object whose keys match
        JSON_VERSION_COMPARISON_REPORT_FIELDS in order.

  AC-4  python -m graph_schema_monitor version compare --old <FILE> --new <FILE>
        --format json --out <FILE> exits 0 and writes the JSON report atomically.

  AC-5  Running with a missing sidecar, missing x_ms_schema_version, or
        malformed sidecar exits with code 2 and a clear error message.

  AC-6  All eight classification strings are exercised by direct unit tests.

  AC-7  No network calls are introduced (socket test passes).

  AC-8  All existing PR1–PR5 CLI behaviours remain intact
        (fetch, inspect, diff, snapshots list, snapshots validate,
        report diff, report summary, watchlist check).

  AC-9  README documents the version comparison workflow.

  AC-10 AADLC artefacts reflect PR6 scope; no prior durable state is
        removed or overwritten with baseline templates.

  AC-11 No new runtime dependencies in pyproject.toml or any import.

  AC-12 No modifications to parser.py, diff.py, fetcher.py, snapshots.py,
        report.py, report_filters.py, or watchlists.py.

══════════════════════════════════════════════════════════════════════════
SECTION 22 — RISKS
══════════════════════════════════════════════════════════════════════════

  R-1  x_ms_schema_version is null in early snapshots captured before PR2
       added the field. Mitigation: PR6 fails closed with a clear error.
       Users who need version comparison must re-fetch snapshots via
       `fetch` which now writes x_ms_schema_version.

  R-2  Two snapshots could compare the same underlying Graph response
       (version_same_content_same_semantics_same). This is valid output,
       not an error. Mitigation: the classification string makes it explicit.

  R-3  sha256 mismatch between sidecar and file content (file has been
       modified since fetch). This is already caught by load_snapshot_bundle()
       via snapshots.py hash validation and raises SnapshotValidationError
       before PR6 code runs. Mitigation: no additional work needed in PR6.

  R-4  CLI subcommand nesting ("version compare") follows the existing
       "snapshots list" and "report diff" pattern. If argparse requires
       a dest disambiguation between top-level "version" and the nested
       "compare", Codex must mirror the "snapshots_command" / "report_command"
       pattern exactly.

  R-5  JSON field order stability: json.dumps without sort_keys relies on
       dict insertion order (Python 3.7+). The project already uses this
       pattern (JSON_DIFF_REPORT_FIELDS, JSON_WATCHLIST_REPORT_FIELDS).
       Confirm Python version in pyproject.toml supports this guarantee
       (expected: >=3.11).

─────────────────────────────────────────────────────────────────────────
FINAL RESPONSE EXPECTATIONS (required headings in Plan-only mode)
─────────────────────────────────────────────────────────────────────────

## Summary
<one paragraph>

## Changes
No code changes proposed (Plan-only mode).

## Tests run / not run
Not run (Plan-only mode).

## Risks
<from SECTION 22>
