# task-workflow-correctness Specification

## Purpose
定义 checkout 连续性、依赖安全调度、验证新鲜度、索引一致性、可见 rollback 与两阶段归档的 fail-closed 契约，作为 `task-workflow-orchestration` 之上的正确性增量。
## Requirements

### Requirement: Delivery checkout must be explicitly prepared and continuous
The workflow SHALL use a persisted checkout binding for every required delivery repository. Apply and archive MUST fail closed when the binding is absent, the checkout is missing or belongs to another repository, or its current branch differs from the recorded task branch; they MUST NOT silently fall back to the canonical checkout.

#### Scenario: Required repository has no binding
- **WHEN** a task targets a repository classified as required delivery and no work-context checkout is recorded
- **THEN** `execution-context`, `advance`, and archive report `checkout_not_prepared`
- **THEN** none of them uses the canonical repository as an implicit substitute

#### Scenario: Recorded checkout branch changed
- **WHEN** a recorded checkout is valid and clean but its current branch is detached or differs from the recorded task branch
- **THEN** apply and archive block with the expected and actual branch
- **THEN** dirty or force-merge overrides cannot bypass the mismatch

#### Scenario: Dirty required repository is not on the task branch
- **WHEN** branch preparation finds a dirty required repository on another branch
- **THEN** it returns a blocked repository rather than a successful checkout binding
- **THEN** no `skipped_dirty` binding is persisted

### Requirement: Apply control outcomes are unambiguous
`advance` SHALL return a control outcome whose precedence is determined first by the requested phase and then by schedule state. The supported outcomes MUST distinguish `blocked`, `next`, `deferred_only`, `validation_required`, `validation_recorded`, and `done`; `done` MUST mean the final done transition, not merely that checkbox work is exhausted.

#### Scenario: Global blocker overrides candidates
- **WHEN** `advance --phase blocked` records a global blocker while unchecked candidates remain
- **THEN** it returns `blocked` with `next=null`
- **THEN** candidates may remain visible for later recovery but MUST NOT instruct the caller to continue

#### Scenario: Implementation exhausts checkboxes
- **WHEN** `advance --phase implementing` observes no remaining OpenSpec checkbox
- **THEN** it returns `validation_required`
- **THEN** it does not return `done`

#### Scenario: Testing and final completion are separate
- **WHEN** all checkboxes are complete and fresh verification is recorded with `--phase testing`
- **THEN** `advance` returns `validation_recorded`
- **WHEN** a subsequent `--phase done` passes the freshness checks
- **THEN** it returns `done`

### Requirement: Deferred work preserves independent progress without guessing dependencies
The workflow SHALL keep an unavailable checkbox unchecked and deferred with a non-empty reason. Before executing a returned candidate, the Agent MUST determine whether it directly or transitively depends on a deferred item; dependent candidates MUST also be deferred with the blocker identity, while independent candidates continue. The CLI MUST describe unchecked non-deferred items as candidates unless dependency satisfaction is explicitly known.

#### Scenario: Independent item follows unavailable verification
- **WHEN** a manual or environmental verification item is deferred and another remaining item is independent
- **THEN** the independent item remains a candidate and apply continues in the same run

#### Scenario: Candidate depends on deferred work
- **WHEN** the next textual checkbox depends on a deferred checkbox
- **THEN** the Agent does not implement it
- **THEN** it is deferred with a reason that identifies the blocking checkbox before another candidate is selected

#### Scenario: No independent work remains
- **WHEN** every remaining checkbox is explicitly deferred or transitively blocked by deferred work
- **THEN** `advance` returns `deferred_only` and no next candidate

### Requirement: Final verification evidence is fresh
Verification used by final completion and archive SHALL be recorded after the last implementation transition and tied to the current delivery checkout branch and commit snapshot. Returning to implementation or changing the recorded delivery snapshot MUST invalidate prior final verification evidence. Provisional evidence from a dirty checkout MAY be displayed but MUST NOT satisfy final archive readiness.

#### Scenario: Implementation resumes after testing
- **WHEN** fresh verification has been recorded and a later `advance --phase implementing` occurs
- **THEN** the prior final-verification marker is invalidated
- **THEN** `--phase done` and archive require new verification

#### Scenario: Delivery commit changes after verification
- **WHEN** the current delivery branch or HEAD differs from the clean snapshot recorded with final verification
- **THEN** archive reports stale verification and blocks

#### Scenario: Final verification matches delivery snapshots
- **WHEN** verification is recorded on clean delivery checkouts and their branch and HEAD remain unchanged
- **THEN** final done and archive accept the evidence

### Requirement: Task catalog and operational Markdown fail closed
README task directories SHALL remain the task identity source and INDEX SHALL be a reconciled locator/allocation index. Before mutation, the workflow MUST detect duplicate IDs, active/archive conflicts, missing indexed paths, README/path identity mismatch, malformed operational tables, unknown scope roles, and unsupported non-empty store bindings. Unknown scope roles MUST NOT default to required delivery.

#### Scenario: Existing INDEX omits a task
- **WHEN** a task directory exists but an existing INDEX omits it
- **THEN** allocation accounts for the directory ID and does not reuse it
- **THEN** a conflict-free reconciliation may restore the derived INDEX row

#### Scenario: Catalog identity conflicts
- **WHEN** two directories claim one task ID or active and archive entries conflict
- **THEN** mutating commands fail with all conflicting paths
- **THEN** no INDEX or task directory is changed

#### Scenario: Scope role is unknown
- **WHEN** an operational scope row contains a role other than required, suggested, or excluded aliases
- **THEN** parsing returns a format error
- **THEN** the repository is not promoted to required delivery

#### Scenario: Acceptance structure is missing
- **WHEN** final archive cannot find a valid acceptance section and its checkbox structure
- **THEN** archive blocks instead of treating the missing section as zero unchecked items

#### Scenario: Standalone store is recorded but unsupported
- **WHEN** an OpenSpec binding contains a non-empty store ID that this change does not resolve
- **THEN** execution context fails with an explicit unsupported-store diagnostic
- **THEN** it does not ignore the store and infer a repo-local planning root

### Requirement: Mutation rollback failures are visible
Every task-store mutation SHALL snapshot all affected task files and INDEX state before writing. If the primary mutation fails, rollback MUST attempt every restoration step, collect every rollback failure, and return the primary error, rollback errors, affected paths, and a manual recovery hint. A command MUST NOT report success or hide rollback failure with exception suppression.

#### Scenario: Advance rollback also fails
- **WHEN** advance cannot update INDEX and restoring progress or apply state also fails
- **THEN** it reports `rollback_failed` with both the primary and restoration errors

#### Scenario: New or archive rollback also fails
- **WHEN** new or archive partially changes a directory and its cleanup or move-back fails
- **THEN** it reports the surviving source/destination paths and required manual inspection

#### Scenario: Rollback succeeds
- **WHEN** a mutation fails and every snapshot is restored
- **THEN** the command returns the primary error
- **THEN** README, INDEX, apply state, progress, audit files, and directory location match the pre-call state

### Requirement: Archive uses preflight before external mutation and remains resumable
Archive SHALL perform an initial read-only preflight of task identity, OpenSpec targets, checkout bindings, branches, repository status, acceptance structure, remaining work, and requested overrides before archiving OpenSpec changes or promoting design files. It SHALL perform a second final preflight immediately before moving the task. Because external archives are not globally atomic, reruns MUST recognize already archived targets and report partial progress without treating it as missing.

#### Scenario: Initial preflight fails
- **WHEN** a delivery checkout is missing, on the wrong branch, or cannot be inspected
- **THEN** no OpenSpec change is archived and no design file is promoted

#### Scenario: One of multiple target archives fails
- **WHEN** one target has archived successfully and a later target fails
- **THEN** the task remains active and the completed target is reported
- **THEN** a retry skips or validates the completed target and continues from the failed target

#### Scenario: Final preflight detects new dirty state
- **WHEN** external archive or design promotion leaves a delivery checkout dirty without an exact override
- **THEN** finalization stops before moving the task
- **THEN** the task remains resumable with the external results intact

### Requirement: Archive overrides are exact, confirmable, and audited
The workflow SHALL expose only narrowly scoped overrides for user-judgment conditions. Remaining known checkbox work, unchecked acceptance, missing final verification, and a named dirty delivery checkout MUST each require explicit confirmation and write an audit entry. Missing or ambiguous change identity, missing/invalid checkout, unavailable status, branch mismatch, malformed operational data, and missing `changes.md` during finalization MUST NOT be overrideable.

#### Scenario: User-judgment override is requested
- **WHEN** archive encounters an overrideable condition without prior exact authorization
- **THEN** it returns exit code 2 with the condition, affected item, and exact user action
- **THEN** no mutation occurs

#### Scenario: Exact override is finalized
- **WHEN** the user authorizes one remaining-work, acceptance, verification, or dirty-repository condition
- **THEN** only that condition is bypassed
- **THEN** `changes.md` records the condition and authorization before task movement

#### Scenario: Structural failure cannot be forced
- **WHEN** a recorded change is missing or ambiguous, a checkout is invalid, status is unavailable, or the branch mismatches
- **THEN** `--force-merge` and dirty overrides do not permit archive
