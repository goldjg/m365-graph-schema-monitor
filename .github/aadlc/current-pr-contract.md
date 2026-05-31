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
Synchronise reusable AADLCv2 governance guidance from `goldjg/coding-agent-baselines` into this repository while preserving `m365-graph-schema-monitor` project-specific memory, trust boundaries, invariants, and implementation history.
## Contract status
active
## Non-goals
- Do not overwrite project-specific AADLC memory with baseline template content.
- Do not remove the existing Graph metadata endpoint trust boundary.
- Do not remove the `network-boundary-fixed` invariant.
- Do not alter application code, parser behaviour, diff behaviour, fetch behaviour, CLI behaviour, tests, or CI unless explicitly approved.
- Do not introduce new dependencies, tools, workflows, or runtime behaviour.
- Do not change repository architecture or implementation scope.
- Do not treat completed PR1 or PR2 constraints as active scope unless explicitly promoted to durable invariants.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
- Reusable instruction-pack guidance may be synced from `coding-agent-baselines` when it improves AADLCv2 governance without erasing repository-specific state.
## Approved scope
- Add `.github/aadlc/plans/README.md` from `coding-agent-baselines`.
- Add `.github/aadlc/plans/plan-template.md` from `coding-agent-baselines`.
- Update `.github/copilot-instructions.md` with the latest reusable AADLCv2 guidance for:
  - prompt-as-code
  - tool-policy classification before writes
  - model fallback
  - correction-budget / prompt ping-pong control
- Update `.github/instructions/core/aadlc.instructions.md` to the latest reusable AADLCv2 guidance.
- Update `.github/instructions/core/pr-contract.instructions.md` to include completed-contract, carry-forward, intentional-amendment, stale-contract anchoring, and new trust-boundary guidance.
- Update `.github/instructions/core/cognition-governance.instructions.md` to include model availability, model fallback, and correction-budget guidance.
- Update `.github/aadlc/current-pr-contract.md` to the v1.1.0 contract lifecycle structure.
- Preserve repository-specific AADLC artefacts and only amend them where needed to align with the new lifecycle model.
## Intentional amendments
- This PR intentionally replaces the PR2 fetch-specific active contract with a governance-sync contract.
- The completed PR2 contract is no longer active implementation scope.
- The PR2 network-boundary facts remain durable where already promoted into:
  - `.github/aadlc/memory.md`
  - `.github/aadlc/trust-boundaries.md`
  - `.github/aadlc/invariants.yml`
- This PR introduces prompt-as-code as a reusable AADLCv2 workflow pattern via `.github/aadlc/plans/`.
- This PR formalises the correction-budget rule:
  - one corrective prompt is acceptable
  - two corrective prompts means reset the session
  - three means abandon the session/model and restart with a clearer plan
- This PR formalises model fallback as an expected AADLCv2 operational path when a model is unavailable or repeatedly misinterprets scope.
- This PR formalises the rule that completed PR constraints are historical evidence unless explicitly promoted to durable invariants.
## Forbidden scope
- Do not replace `.github/aadlc/memory.md` with the baseline template.
- Do not replace `.github/aadlc/trust-boundaries.md` with the baseline template.
- Do not replace `.github/aadlc/invariants.yml` with the baseline template.
- Do not remove schema-monitor-specific facts, trust boundaries, invariants, or open questions.
- Do not modify `src/`, `tests/`, `pyproject.toml`, or `.github/workflows/ci.yml` unless explicitly approved.
- Do not add new runtime behaviour.
- Do not add new dependencies.
- Do not alter application acceptance criteria from prior merged PRs.
- Do not introduce live-network tests, new Graph behaviour, authentication, tenant access, or additional network boundaries.
## Architectural constraints
- Keep `.github/copilot-instructions.md` as the root Copilot operating model.
- Keep reusable instruction packs under `.github/instructions/`.
- Keep durable AADLC governance artefacts under `.github/aadlc/`.
- Store substantial, long, nested, trust-boundary-changing, or UI-fragile task contracts under `.github/aadlc/plans/`.
- Treat root-level `PLAN.md` as temporary feature-branch scaffolding only; remove it or move it into `.github/aadlc/plans/` before merge.
- Preserve the distinction between:
  - durable invariants
  - active PR scope
  - completed PR constraints
  - intentional contract amendments
  - historical implementation evidence
## Security constraints
- No secrets, credentials, tokens, tenant data, or private customer data may be added to AADLC plan files or instruction files.
- Do not weaken existing security, dependency, identity, trust-boundary, or CI/CD guidance.
- Do not remove explicit validation requirements for the fixed Graph metadata endpoint boundary.
- Do not remove guidance requiring user approval for new trust boundaries.
- Do not introduce any instruction that permits arbitrary URL fetching, authentication flows, tenant access, or broad network expansion without an explicit PR contract amendment.
## Files expected to change
- `.github/copilot-instructions.md`
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/plans/README.md`
- `.github/aadlc/plans/plan-template.md`
- `.github/instructions/core/aadlc.instructions.md`
- `.github/instructions/core/pr-contract.instructions.md`
- `.github/instructions/core/cognition-governance.instructions.md`
The following files may be reviewed but should not be overwritten with baseline templates:
- `.github/aadlc/memory.md`
- `.github/aadlc/trust-boundaries.md`
- `.github/aadlc/invariants.yml`
- `.github/aadlc/tool-policy.yml`
- `.github/aadlc/repo-map.example.json`
## Tests / validation
- Review the `.github` diff against `goldjg/coding-agent-baselines`.
- Confirm reusable guidance from the baseline has been synced where intended.
- Confirm project-specific AADLC state has not been overwritten.
- Confirm `.github/aadlc/plans/README.md` and `.github/aadlc/plans/plan-template.md` are present.
- Confirm `current-pr-contract.md` uses the v1.1.0 lifecycle structure.
- Confirm no application code, tests, CI, runtime dependencies, or fetch/parser/diff behaviour changed.
- If application files were unexpectedly changed, stop and revert or request approval.
## Stop conditions
- A change would overwrite project-specific memory, trust boundaries, or invariants with generic baseline template content.
- A change would remove the Graph metadata endpoint trust boundary or `network-boundary-fixed` invariant.
- A change would modify application code, tests, dependencies, CI, or runtime behaviour without explicit approval.
- A change would blur the distinction between completed PR contracts and durable invariants.
- A change would make completed PR1/PR2 constraints active again without explicit contract amendment.
- A change would introduce new trust boundaries or implementation scope.
## Escalation triggers
- Need to decide whether to archive prior PR plans/contracts permanently under `.github/aadlc/plans/`.
- Need to modify `.github/aadlc/memory.md` beyond minor lifecycle wording.
- Need to modify `.github/aadlc/trust-boundaries.md` beyond preserving existing project-specific boundaries.
- Need to modify `.github/aadlc/invariants.yml` beyond preserving existing project-specific invariants.
- Need to touch application code, tests, CI, or dependencies.
- Need to resolve a conflict between baseline reusable guidance and repository-specific project truth.
## Context reset notes
- Mark this contract complete after the reusable AADLCv2 governance sync is merged.
- After merge, future PRs should create or update a fresh active PR contract before implementation.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
- Completed PR constraints should be treated as historical evidence unless promoted to durable invariants.