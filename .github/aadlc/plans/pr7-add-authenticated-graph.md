You are Claude Sonnet 4.6 acting as the implementation agent in Graham’s AADLCv2 workflow.

Repository:

https://github.com/goldjg/m365-graph-schema-monitor

This is PR7.

OPERATING MODE: Plan first.

First produce the implementation plan. Do not edit files until Graham explicitly replies with “approved”, “implement”, or “proceed”.

After approval, implement exactly the approved plan. Do not broaden scope.

────────────────────────────────────────
PR7 GOAL
────────────────────────────────────────

Add controlled authenticated Microsoft Graph $metadata acquisition using an externally supplied access token from an environment variable.

PR7 is the first authenticated acquisition step, but it must stay narrow.

It should answer:

Can this tool fetch authenticated Graph $metadata, preserve the same provenance model, capture x_ms_schema_version, and avoid storing or leaking tokens?

PR7 builds on:

* PR1: offline CSDL/XML parser and deterministic diff foundation.
* PR2: public unauthenticated Graph $metadata fetch + sidecar.
* PR3: local snapshot inventory and deterministic reports.
* PR4: deterministic report filtering and summaries.
* PR5: local schema watchlists.
* PR6: version/content/semantic movement comparison.

Strategic direction:

The project is moving toward distinguishing:

* version movement
* content movement
* semantic movement
* watched movement
* later: public-observed vs tenant-authenticated-observed movement

PR7 only adds authenticated acquisition. It does not add public-vs-authenticated comparison yet.

────────────────────────────────────────
HARD BOUNDARIES
────────────────────────────────────────

Allowed in PR7:

* Fetch authenticated Graph $metadata from the same fixed allowlisted public Graph metadata URLs:
    * https://graph.microsoft.com/v1.0/$metadata
    * https://graph.microsoft.com/beta/$metadata
* Use an access token supplied via environment variable.
* Send the token only as an Authorization: Bearer <token> request header.
* Reuse the existing fixed profile allowlist.
* Reuse the existing HTTPS/content-type/timeout/redirect rules.
* Write XML snapshot and adjacent JSON sidecar.
* Capture sanitized provenance in sidecar.
* Add tests with mocked network calls only.
* Update README and AADLC artefacts.

Forbidden in PR7:

* No MSAL.
* No device code flow.
* No browser login.
* No client secret support.
* No certificate credential support.
* No token acquisition.
* No refresh tokens.
* No token cache.
* No token persistence.
* No writing access tokens, token env var values, request headers, or Authorization headers to sidecars, logs, stdout, stderr, test fixtures, or docs.
* No tenant discovery.
* No Graph SDK.
* No permissions/scopes handling beyond documenting that the supplied token must be valid for Graph.
* No arbitrary URL fetching.
* No sovereign cloud support.
* No source comparison.
* No public-vs-authenticated comparison.
* No scheduler.
* No database.
* No web UI.
* No changelog/docs correlation.
* No AI summarisation.
* No new runtime dependencies.
* No parser expansion.
* No NavigationProperty diffing.
* No inherited-property flattening.

Python standard library only.

────────────────────────────────────────
STEP 0 — READ BEFORE PLANNING
────────────────────────────────────────

Before planning, read these files in full and record current-state observations:

.github/copilot-instructions.md
.github/aadlc/current-pr-contract.md
.github/aadlc/memory.md
.github/aadlc/trust-boundaries.md
.github/aadlc/invariants.yml
.github/aadlc/plans/plan-template.md
README.md

src/graph_schema_monitor/fetcher.py
src/graph_schema_monitor/snapshots.py
src/graph_schema_monitor/versioning.py
src/graph_schema_monitor/cli.py
src/graph_schema_monitor/parser.py
src/graph_schema_monitor/diff.py
src/graph_schema_monitor/report.py
src/graph_schema_monitor/report_filters.py
src/graph_schema_monitor/watchlists.py

tests/test_fetcher.py
tests/test_snapshots.py
tests/test_versioning.py
tests/test_cli.py
tests/test_report.py
tests/test_watchlists.py
tests/fixtures/

Record especially:

* Current fetcher profile allowlist and URL validation.
* Current fetcher redirect policy.
* Current fetcher timeout policy.
* Current FetchResult shape.
* Current sidecar fields and strictness.
* How snapshots.py validates sidecars and whether unknown sidecar fields are allowed, rejected, warned, or ignored.
* Existing sidecar hash validation behaviour.
* Existing CLI fetch command shape.
* Existing tests for fetch, sidecar exactness, and no-network behaviour.
* Current invariants and trust-boundaries relating to network and sidecars.

If any assumption in this prompt conflicts with current repo state, stop and report the conflict before planning implementation.

────────────────────────────────────────
PR7 DESIGN INTENT
────────────────────────────────────────

PR7 should preferably extend the existing fetcher surface rather than create a second unrelated network module.

Default design preference:

* Keep fetcher.py as the only network acquisition module.
* Add a new authenticated fetch entry point there, or refactor the existing fetch implementation so public and authenticated fetch share the same allowlist, timeout, redirect rejection, content-type validation, hash, and sidecar writing logic.
* Extend cli.py with a separate command to avoid changing existing fetch behaviour.

Preferred CLI:

python -m graph_schema_monitor fetch-auth \
  --profile beta \
  --out snapshots/lab/graph-beta-auth.xml \
  --token-env GRAPH_METADATA_TOKEN \
  --tenant-label lab \
  [--overwrite]

Arguments:

* --profile: required; v1.0 or beta
* --out: required XML output path
* --token-env: required name of environment variable containing the access token
* --tenant-label: optional user-supplied local label for provenance; must not be interpreted as tenant identity
* --overwrite: optional, same semantics as public fetch

If Codex proposes a different CLI shape, justify it and preserve existing public fetch behaviour exactly.

Existing public fetch command must remain unchanged:

python -m graph_schema_monitor fetch --profile beta --out graph-beta.xml

────────────────────────────────────────
SIDEcar / PROVENANCE MODEL
────────────────────────────────────────

Current PR2 sidecar fields are the baseline:

* profile
* source_url
* fetched_at_utc
* status_code
* content_type
* etag
* last_modified
* sha256
* x_ms_schema_version

PR7 should add source provenance fields only if they can be made compatible with existing sidecar validation and tests.

Preferred new optional sidecar fields:

* source_kind
    * "public_graph_metadata" for public fetches, if added to public sidecars
    * "authenticated_graph_metadata" for authenticated fetches
* auth_mode
    * "none" for public fetches, if added to public sidecars
    * "env_token" for authenticated fetches
* tenant_label
    * string or null
    * user-supplied display label only
    * no tenant ID lookup
    * no tenant ID storage
    * no hashing tenant ID in PR7

Important compatibility requirement:

If adding these fields to sidecars would break existing sidecar validation, inventory, report, watchlist, version compare, or tests, Codex must explicitly plan the necessary central sidecar-schema update.

Do not silently create sidecars that existing commands cannot load.

Do not add raw request headers, raw response headers, Authorization header, token value, token hash, token env var value, scopes, claims, tenant ID, user ID, app ID, or account identity to sidecars.

It is acceptable to store the token environment variable name only if justified, but the default preference is do not store token_env in the sidecar.

────────────────────────────────────────
AUTHENTICATED FETCH BEHAVIOUR
────────────────────────────────────────

Authenticated fetch must:

* Resolve --profile through the same fixed profile map as public fetch.
* Reject unknown profiles before reading the token or making network calls.
* Read the access token from the environment variable named by --token-env.
* Fail clearly if:
    * --token-env is missing
    * environment variable is absent
    * environment variable value is empty or whitespace
* Strip surrounding whitespace from the token for use in the Authorization header.
* Never print the token.
* Never include the token in exception messages.
* Never write the token to sidecar.
* Send:
    * Authorization: Bearer <token>
* Use HTTPS only.
* Reject redirects, same as public fetch.
* Apply the same timeout as public fetch.
* Require HTTP 2xx.
* Require XML-compatible content type.
* Write snapshot bytes as-is.
* Compute SHA-256 over snapshot bytes.
* Write adjacent sidecar after successful XML write.
* Respect --overwrite.
* Reuse the existing atomic/safe write pattern if available.
* Return a structured result object that does not contain raw content bytes or token data.

Do not validate JWT structure. Do not decode JWT. Do not infer tenant identity from token claims.

────────────────────────────────────────
OUTPUT / CLI SUCCESS MESSAGE
────────────────────────────────────────

On success, CLI should mirror public fetch style, for example:

Fetched authenticated https://graph.microsoft.com/beta/$metadata -> snapshots/lab/graph-beta-auth.xml
Sidecar: snapshots/lab/graph-beta-auth.xml.json

Do not print token env var value.

If printing the token env var name, ensure it is clearly just the name. Prefer not printing it.

Error examples should be clear but non-sensitive:

Token environment variable is required: --token-env
Token environment variable is not set: GRAPH_METADATA_TOKEN
Token environment variable is empty: GRAPH_METADATA_TOKEN
Authenticated metadata fetch failed with HTTP 401

Do not print response body on HTTP errors.

────────────────────────────────────────
AADLC UPDATES
────────────────────────────────────────

Update:

* .github/aadlc/current-pr-contract.md
* .github/aadlc/memory.md
* .github/aadlc/trust-boundaries.md
* .github/aadlc/invariants.yml
* README.md

Preserve prior durable state.

Current durable invariants likely include:

* network-boundary-fixed
* watchlists-local-only
* version-comparison-local-only

PR7 must amend the network boundary carefully.

The old invariant “outbound network calls are limited to allowlisted Graph metadata endpoints; no dynamic or user-supplied URLs” remains true.

But PR7 adds authenticated requests to the same allowlisted endpoints.

Consider whether to update/add invariants such as:

- id: graph-metadata-network-boundary-fixed
  name: Graph metadata network boundary fixed
  rule: Outbound metadata acquisition is limited to the allowlisted Graph `$metadata` endpoints for v1.0 and beta. Authentication mode may change request headers but must not make URLs dynamic or user-supplied.
  severity: critical

And:

- id: auth-token-not-persisted
  name: Auth tokens are never persisted
  rule: Authenticated metadata acquisition must never write access tokens, Authorization headers, token claims, or raw request headers to files, logs, stdout, stderr, or sidecars.
  severity: critical

Codex should inspect existing invariant style and propose the smallest safe change.

Trust-boundary updates must include an authenticated token boundary:

Suggested row:

| Access token environment variable | User-specified env var name via `--token-env`; token value read from process environment | Low | Required; non-empty; used only as Authorization bearer token; never logged, persisted, decoded, or written to sidecars |

Also update the Graph metadata endpoint boundary to mention both unauthenticated and authenticated requests to the same fixed endpoints.

Current PR contract must be replaced with PR7 active contract.

────────────────────────────────────────
CONTRACT ASSERTIONS
────────────────────────────────────────

The plan must include 5 contract assertions that tests directly assert.

At minimum:

CA-1 — Existing public fetch behaviour remains unchanged.

* fetch --profile ... --out ... still writes the existing public snapshot and sidecar as expected.

CA-2 — Authenticated fetch uses fixed allowlisted Graph metadata URLs only.

* Unknown profile fails before token read/network.
* No raw URL argument exists.
* Redirects remain rejected.

CA-3 — Token handling is non-persistent and non-observable.

* Authenticated fetch sends Authorization header in the mocked request.
* Token value does not appear in result object, stdout, stderr, sidecar JSON, or exception messages.

CA-4 — Authenticated sidecar provenance is compatible.

* Authenticated fetch writes a sidecar that existing load_snapshot_bundle(), snapshots validate, report diff, version compare, and watchlist check can consume.
* Required PR2 fields remain present.
* New provenance fields, if added, are explicit and tested.

CA-5 — No new network surface.

* Tests mock network calls.
* Authenticated fetch reaches only the allowlisted Graph metadata URL for the selected profile.
* No test performs live network access.

────────────────────────────────────────
TEST PLAN REQUIREMENTS
────────────────────────────────────────

Add or update tests for:

Public fetch regression:

* Existing public fetch tests still pass unchanged.
* Public fetch sidecar remains loadable by snapshot inventory and version comparison.

Authenticated fetch success:

* Mocked HTTP 200 XML response.
* Env var token set.
* Authorization header is present and correct in the mocked request.
* XML and sidecar are written.
* SHA-256 matches content.
* x_ms_schema_version captured from response header.
* Result object contains no token value.
* Sidecar contains no token value.

Token failures:

* Missing --token-env fails through argparse or clear validation.
* Env var absent fails clearly.
* Env var empty/whitespace fails clearly.
* Token value does not appear in error messages.

Profile / URL controls:

* Unknown profile fails before env var read and before network call.
* No --url argument exists.
* Redirects rejected.
* Non-XML content type rejected.
* HTTP 401/403/500 fail without response body leakage.

Overwrite/file behaviour:

* Existing output without --overwrite fails before network call.
* Existing output with --overwrite succeeds.
* Sidecar overwrite semantics match public fetch.

Sidecar compatibility:

* Authenticated sidecar loads with load_snapshot_bundle().
* snapshots validate accepts authenticated sidecar.
* version compare can compare an authenticated snapshot with another snapshot if required provenance exists.
* If sidecar schema is extended, tests assert older sidecars still load.

CLI:

* fetch-auth success path.
* fetch-auth --out writes expected files.
* CLI success output does not leak token.
* CLI failure output does not leak token.

No live network:

* Existing no-network test guard remains effective.
* New tests monkeypatch network/openers; no live HTTP.

Security:

* Grep-style assertion in tests: token literal is absent from sidecar, stdout, stderr, and result repr if result is printable.

────────────────────────────────────────
IMPLEMENTATION CONSTRAINTS
────────────────────────────────────────

Prefer minimal implementation.

Likely file changes:

* src/graph_schema_monitor/fetcher.py
* src/graph_schema_monitor/cli.py
* src/graph_schema_monitor/snapshots.py only if sidecar schema must be centrally updated
* tests/test_fetcher.py
* tests/test_cli.py
* maybe tests/test_snapshots.py
* maybe tests/test_versioning.py only for compatibility test
* .github/aadlc/current-pr-contract.md
* .github/aadlc/memory.md
* .github/aadlc/trust-boundaries.md
* .github/aadlc/invariants.yml
* README.md

Files that should not change unless strictly necessary:

* parser.py
* diff.py
* report.py
* report_filters.py
* watchlists.py
* existing fixtures, unless adding new fixtures only

Do not add new dependencies.

Do not broaden parser/diff/report/watchlist semantics.

────────────────────────────────────────
README UPDATE
────────────────────────────────────────

Add an “Authenticated metadata fetch” section.

Document:

* It uses an access token supplied via environment variable.
* The tool does not acquire tokens.
* The tool does not store tokens.
* Example:

export GRAPH_METADATA_TOKEN="<access-token>"
python -m graph_schema_monitor fetch-auth \
  --profile beta \
  --out snapshots/lab/graph-beta-auth.xml \
  --token-env GRAPH_METADATA_TOKEN \
  --tenant-label lab

* The token must be valid for Microsoft Graph.
* The command still only talks to fixed Graph $metadata endpoints.
* No arbitrary URL support.
* Sidecar provenance fields.
* Security caveats:
    * do not commit tokens
    * do not include tokens in bug reports
    * sidecars are safe to inspect but may contain local labels and snapshot provenance

Do not document MSAL/device-code flow in PR7.

────────────────────────────────────────
STOP CONDITIONS
────────────────────────────────────────

Stop and ask Graham before proceeding if:

* Existing sidecar validation cannot safely support authenticated provenance fields.
* Implementing authenticated fetch requires MSAL or any dependency.
* Token acquisition, refresh, or caching becomes necessary.
* A raw URL input seems necessary.
* Sovereign cloud support is needed.
* Tenant identity extraction is suggested.
* Existing public fetch behaviour would need to change.
* Existing report/version/watchlist behaviour would need to weaken.
* Any token value would be written to disk, logs, stdout, stderr, or sidecars.
* Tests would need live network access.
* Correction budget is exceeded.

────────────────────────────────────────
ESCALATION TRIGGERS
────────────────────────────────────────

Ask Graham before proceeding if proposing:

* Device code auth.
* Azure CLI token acquisition.
* MSAL.
* Client credentials.
* Certificate credentials.
* Managed identity.
* Token introspection/claim decoding.
* Tenant ID capture.
* Tenant label requirements beyond optional user-supplied string.
* Source comparison.
* Public-vs-authenticated comparison.
* Multiple clouds.
* New dependencies.
* New report formats.
* Changes to parser/diff semantics.

────────────────────────────────────────
ACCEPTANCE CRITERIA
────────────────────────────────────────

The PR is ready when:

* python -m pytest tests/ passes.
* Existing public fetch behaviour is unchanged.
* New fetch-auth command fetches mocked authenticated metadata using env-token mode.
* Authenticated fetch sends Authorization header in tests.
* Authenticated fetch never persists or prints token values.
* Authenticated sidecar contains required PR2 fields and approved provenance fields only.
* Authenticated sidecar is compatible with existing snapshot inventory/report/version/watchlist workflows.
* Unknown profile fails before token read/network.
* Existing output without --overwrite fails before token read/network.
* No live network calls occur in tests.
* No new runtime dependencies.
* README documents authenticated fetch accurately.
* AADLC artefacts reflect the authenticated token trust boundary and PR7 scope without removing prior durable state.

────────────────────────────────────────
FINAL RESPONSE FORMAT FOR PLAN
────────────────────────────────────────

When producing the plan, include these headings:

Summary

Current-state observations

Proposed file changes

PR contract updates

Sidecar compatibility plan

Fetcher design

CLI design

Token handling and security model

Test plan

README updates

AADLC updates

Stop conditions

Escalation triggers

Acceptance criteria

Risks

Changes

No code changes proposed (Plan-only mode).

Tests run / not run

Not run (Plan-only mode).

After Graham approves the plan, implement exactly that plan.
