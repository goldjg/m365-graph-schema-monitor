# m365-graph-schema-monitor

`m365-graph-schema-monitor` is an offline-first tool for acquiring Microsoft Graph metadata snapshots, inspecting CSDL types, diffing schema changes, and rendering deterministic local reports over fetched snapshots.

## Why this exists

Microsoft Graph schema changes can affect governance, drift detection, and identity/security tooling before those changes are easy to spot in downstream documentation. This project uses deterministic local parsing and diffing, with a tightly constrained snapshot fetch step for public Graph metadata.

## Installation / setup

From repository root:

```bash
python -m pip install -e ".[dev]"
```

## Workflow

Fetch local snapshots, inspect one type, diff snapshots, inventory a snapshot directory, then render filtered reports or a compact summary:

```bash
python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-v1.xml --overwrite
python -m graph_schema_monitor fetch --profile beta --out /tmp/graph-beta.xml --overwrite
python -m graph_schema_monitor inspect --snapshot /tmp/graph-v1.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor snapshots list --dir /tmp
python -m graph_schema_monitor snapshots validate --dir /tmp
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --change-type property_added --type-prefix microsoft.graph.conditionalAccessPolicy --out /tmp/graph-report.md
python -m graph_schema_monitor report summary --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --out /tmp/graph-summary.md
```

## Network boundary

`fetch` is intentionally constrained:

- Fixed Graph endpoints only:
  - `https://graph.microsoft.com/v1.0/$metadata`
  - `https://graph.microsoft.com/beta/$metadata`
- No authentication
- No tenant data or permissions
- No arbitrary URLs
- No redirect following
- Sidecar metadata includes only the explicit allowlisted fields

## Authenticated metadata fetch

`fetch-auth` fetches the same fixed Graph `$metadata` endpoints using an access token supplied via environment variable. The tool does **not** acquire, refresh, store, or cache tokens — the caller must supply a valid token.

```bash
export GRAPH_METADATA_TOKEN="<access-token>"
python -m graph_schema_monitor fetch-auth \
  --profile beta \
  --out snapshots/lab/graph-beta-auth.xml \
  --token-env GRAPH_METADATA_TOKEN \
  --tenant-label lab
```

Arguments:

| Argument | Required | Description |
|---|---|---|
| `--profile` | yes | `v1.0` or `beta` |
| `--out` | yes | Output path for the XML snapshot |
| `--token-env` | yes | Name of the environment variable containing the access token |
| `--tenant-label` | no | Optional local display label stored in the sidecar for provenance (not a tenant ID) |
| `--overwrite` | no | Overwrite existing output files |

The token must be valid for Microsoft Graph (`https://graph.microsoft.com`). The command only talks to the same fixed `$metadata` endpoints as `fetch` — no arbitrary URL support.

Authenticated sidecars include the same nine required fields as public sidecars, plus three additional optional provenance fields:

| Field | Value |
|---|---|
| `source_kind` | `"authenticated_graph_metadata"` |
| `auth_mode` | `"env_token"` |
| `tenant_label` | User-supplied label string, or `null` |

These extra fields are ignored by `snapshots validate`, `snapshots list`, `report diff`, `version compare`, and `watchlist check` — authenticated snapshots are fully compatible with all existing commands.

**Security notes:**

- Do not commit access tokens to source control.
- Do not include access tokens in bug reports or issue descriptions.
- Sidecars are safe to inspect and commit — they contain only provenance metadata and no token data.
- The tool never writes the token value, Authorization header, token hash, or any token-derived data to disk, logs, stdout, or stderr.

## CLI usage

```bash
python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-v1.xml --overwrite
python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --format json
python -m graph_schema_monitor snapshots list --dir /tmp
python -m graph_schema_monitor snapshots validate --dir /tmp
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --format json
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --change-type property_added
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --type-prefix microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --type-name microsoft.graph.conditionalAccessPolicy --limit 100 --format json
python -m graph_schema_monitor report summary --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml
python -m graph_schema_monitor report summary --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --format json
```

`report diff` automatically resolves sidecars as `<snapshot-path>.json`, defaults to markdown output, and also supports deterministic JSON output via `--format json`. The JSON report uses the approved top-level schema: `report_type`, `old_snapshot`, `new_snapshot`, `old_profile`, `new_profile`, `old_fetched_at_utc`, `new_fetched_at_utc`, `old_sha256`, `new_sha256`, `total_changes`, and `changes`. Use `--change-type`, `--type-prefix`, `--type-name`, and `--limit` to deterministically narrow large reports; each filter accepts a single value in PR4. Use `--out` to write the rendered report to a file atomically; otherwise it prints to stdout. Missing sidecars are allowed for reports and render unknown metadata fields, while malformed or incomplete sidecars still fail validation.

`report summary` renders an unfiltered deterministic summary over the full local diff and supports markdown or JSON output.

## Watchlists

`watchlist check` evaluates an existing local diff against a local JSON watchlist and renders deterministic markdown or JSON output. Watchlist evaluation is local-only and reuses adjacent sidecar metadata when available.

```bash
python -m graph_schema_monitor watchlist check --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --watchlist tests/fixtures/watchlist_identity.json
python -m graph_schema_monitor watchlist check --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --watchlist tests/fixtures/watchlist_identity.json --format json --out /tmp/graph-watchlist.json
```

Watchlist JSON fields:

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | yes | string | Non-empty |
| `description` | no | string | Optional descriptive text |
| `type_prefixes` | yes* | list[string] | Non-empty strings; OR semantics within the list |
| `type_names` | yes* | list[string] | Exact fully-qualified type names; OR semantics within the list |
| `change_types` | no | list[string] | Values must be known change types |
| `property_names` | no | list[string] | Exact property names only |

\* At least one of `type_prefixes` or `type_names` must be present.

Matching uses OR within each list and AND across filter classes. If `change_types` is omitted, all change types are eligible. If `property_names` is omitted, all property names are eligible. Type-level changes with `property_name = null` do not match a non-empty `property_names` filter.

Example watchlist:

```json
{
  "name": "identity-critical",
  "description": "Schema areas relevant to Entra and Conditional Access.",
  "type_prefixes": [
    "microsoft.graph.conditionalAccess",
    "microsoft.graph.identityGovernance"
  ],
  "change_types": [
    "type_added",
    "property_added",
    "property_removed",
    "property_type_changed",
    "property_nullability_changed",
    "property_collection_shape_changed"
  ]
}
```

`watchlist check` exits `0` on success, including when no changes match. Invalid CLI input, unreadable watchlists, malformed watchlist JSON, and invalid watchlist schema exit `2`.

`snapshots list` writes the inventory table to stdout and emits warning diagnostics to stderr. Missing sidecars are warnings in list mode, while `snapshots validate` treats them as errors and exits non-zero for invalid inventory.

## Testing

```bash
python -m pytest tests/
```

## Known limitations

- Parser scope is intentionally limited to `EntityType` and `ComplexType` declared properties.
- Diff identity is `fully-qualified-type-name + property-name` (declared-only, no inheritance flattening).
- `fetch` only supports the `v1.0` and `beta` public Graph `$metadata` endpoints.
- `report diff` renders unknown metadata when an adjacent sidecar is missing, but malformed or incomplete sidecars still fail.
- `report summary` is intentionally unfiltered in PR4.
- `watchlist check` is intentionally local-only in PR5 and does not add scheduling, persistence, or online correlation.
- No authentication, tenant access, OAuth, MSAL, or Graph SDK integration.
- No arbitrary URL input, scheduler, database, web UI, changelog correlation, canary tenant logic, or AI summarization.

## Roadmap

- Expand parser coverage for additional OData surfaces if needed.
- Add richer output/reporting surfaces while preserving deterministic core behavior.

## Version comparison

`version compare` answers three questions simultaneously over two local snapshots and their adjacent validated sidecars: did the `x_ms_schema_version` header change, did the raw payload hash change, and did parsed schema content change? All three dimensions are evaluated and combined into a single deterministic classification string.

Both snapshots must have adjacent sidecars (written by `fetch`) that include a non-null `x_ms_schema_version` field. If a sidecar is missing, the sha256 does not match, or `x_ms_schema_version` is absent or null, the command exits with code 2 and a clear error message.

```bash
# Markdown output to stdout (default)
python -m graph_schema_monitor version compare \
  --old /tmp/graph-v1-2026-05-01.xml \
  --new /tmp/graph-v1-2026-05-30.xml

# JSON output written atomically to a file
python -m graph_schema_monitor version compare \
  --old /tmp/graph-v1-2026-05-01.xml \
  --new /tmp/graph-v1-2026-05-30.xml \
  --format json \
  --out /tmp/graph-version-comparison.json
```

### Classification values

The eight possible classification strings encode the three boolean dimensions (schema version changed / content SHA-256 changed / semantic diff present):

| Classification | schema_version_changed | sha256_changed | semantic_changes_present | Meaning |
|---|---|---|---|---|
| `version_same_content_same_semantics_same` | no | no | no | Identical in all respects; confirm the fetch recorded the same snapshot. |
| `version_same_content_same_semantics_changed` | no | no | yes | Parser sees changes but bytes are identical; unusual edge case. |
| `version_same_content_changed_semantics_same` | no | yes | no | Payload bytes differ but parsed schema meaning is identical; likely whitespace or XML formatting. |
| `version_same_content_changed_semantics_changed` | no | yes | yes | Content and semantics changed; version header was not bumped. |
| `version_changed_content_same_semantics_same` | yes | no | no | Version header advanced but no content or semantic change detected; possible cosmetic bump. |
| `version_changed_content_same_semantics_changed` | yes | no | yes | Version bumped and semantic changes present, but byte hash unchanged. |
| `version_changed_content_changed_semantics_same` | yes | yes | no | Version bumped and payload changed, but parsed schema meaning is identical. |
| `version_changed_content_changed_semantics_changed` | yes | yes | yes | Typical schema release; all three signals fire. |

The JSON report uses `report_type: "version_comparison"` and includes the stable field set: `report_type`, `old_snapshot`, `new_snapshot`, `old_profile`, `new_profile`, `old_fetched_at_utc`, `new_fetched_at_utc`, `old_sha256`, `new_sha256`, `old_x_ms_schema_version`, `new_x_ms_schema_version`, `schema_version_changed`, `sha256_changed`, `semantic_change_count`, `semantic_changes_present`, `classification`.
