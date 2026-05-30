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
| Local snapshot XML | Offline CSDL input files provided via CLI | Medium | Validate path existence; parse with safe XML patterns; normalize values before diffing |
| CLI arguments | User-provided command flags and file/type values | Medium | Strict argparse schema, required arguments, and explicit error messages |

## Crossing rules

- Cross-boundary assumptions that alter scope require explicit confirmation.
- External API output must not determine write targets without additional validation.
- PR contract constraints apply throughout execution until contract context is reset.
- If durable cache facts conflict with current repository state, repository state wins and cache should be updated.
- Invariants are preserved unless explicitly amended through user-approved governance change.
- In PR2, outbound network crossing is limited to the fixed Graph metadata boundary only; no authentication flows, tenant interactions, or dynamic URLs are permitted.
