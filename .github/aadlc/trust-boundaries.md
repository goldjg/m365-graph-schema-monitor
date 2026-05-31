<!-- version: 1.0.0 -->
# Trust Boundaries

Trust boundaries classify information sources and define required
validation before shaping, planning, execution, or validation decisions.

| Boundary | Source | Trust level | Required validation |
|---|---|---|---|
| User instruction | Direct user requests in this session | High | Clarify ambiguity and confirm material scope assumptions |
| Repository files | Current checked-in file state | High | Verify paths and current content before editing |
| PR contract | `.github/aadlc/current-pr-contract.md` | High | Confirm requested work is within approved scope |
| Cognitive cache | `.github/aadlc/memory.md` | Medium | Treat as durable guidance; verify against current file state if stale |
| Tool output | Search, file-read, and command output | Medium | Confirm relevance and freshness before using for writes |
| External API response | Remote services and web sources | Low | Cross-check critical claims before using in implementation decisions |
| Graph metadata endpoint | `https://graph.microsoft.com/{v1.0,beta}/$metadata` | Low | Enforce HTTPS; allow fixed host/path only; apply timeout; reject redirects; require 2xx status; require XML content type |
| Authenticated token | Access token from caller-supplied environment variable | Untrusted input | Strip whitespace; raise `TokenError` on empty; use only in `Authorization: ****** request header; never write to disk, logs, or any sidecar field |
| Local snapshot XML | Offline CSDL input files provided via CLI | Medium | Validate path existence; parse with safe XML patterns; normalize values before diffing |
| Local watchlist JSON | User-authored local `.json` files passed via `--watchlist` | Medium | Parse with `json.loads()`; validate explicit allowlisted fields; reject malformed structures, empty strings, duplicates, unknown change types, and unexpected fields; no eval, network, or dynamic imports |
| CLI arguments | User-provided command flags and file/type values | Medium | Strict argparse schema, required arguments, and explicit error messages |

## Crossing rules

- Cross-boundary assumptions that alter scope require explicit confirmation.
- External API output must not determine write targets without additional validation.
- PR contract constraints apply throughout execution until contract context is reset.
- If durable cache facts conflict with current repository state, repository state wins and cache should be updated.
- Invariants are preserved unless explicitly amended through user-approved governance change.
- In PR2, outbound network crossing is limited to the fixed Graph metadata boundary only; no authentication flows, tenant interactions, or dynamic URLs are permitted.
- In PR7, `fetch-auth` extends the Graph metadata boundary to include an `Authorization` header carrying a caller-supplied access token; the network endpoint remains fixed and URL behaviour is unchanged.
- In PR8, `compare-sources` reads authenticated sidecar provenance extra fields (`source_kind`, `auth_mode`, `tenant_label`) from local `.xml.json` files via `json.loads()`; this is within the existing local sidecar input surface and requires no new trust boundary.
- In PR9, `workflow compare-public-auth` bundles outputs from existing local renderers into a report directory; it reads only local snapshot XML, adjacent sidecars, and optional local watchlist JSON — all within existing trust surfaces. No new trust boundary is introduced.
