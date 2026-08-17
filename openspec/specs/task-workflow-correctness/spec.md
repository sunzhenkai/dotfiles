# task-workflow-correctness Specification

## Purpose
定义 task 工作流的 fail-closed 契约：唯一任务解析、分支准备的用户数据安全、归档门禁与覆盖审计、操作数据的具名失败，以及委托 `openspec-*` 的绑定要求。指令面与命令面见 `task-workflow-orchestration`。

## Requirements

### Requirement: Task resolution is unique before any write
Every command except task creation SHALL resolve exactly one task before writing. When the request or session already names a unique task, that identity MUST be passed explicitly rather than re-derived heuristically. When resolution is not unique, the workflow MUST return exit code 2 with the candidates and perform no write.

#### Scenario: Explicit identifier wins
- **WHEN** a task identifier is present in the request or established in the session
- **THEN** it is passed to `resolve` directly
- **THEN** heuristic inference is not used as a substitute

#### Scenario: Heuristic candidates are not unique
- **WHEN** only keyword or status heuristics are available and they match more than one task
- **THEN** `resolve` returns exit code 2 with every candidate
- **THEN** no task is modified before the user chooses

#### Scenario: No query is supplied
- **WHEN** `resolve` runs without an identifier or hint
- **THEN** it returns exit code 2 listing the active tasks

#### Scenario: Resolution lands on an archived task
- **WHEN** the resolved task is archived
- **THEN** `resolve` returns exit code 2 naming the restore action
- **THEN** the task is not silently reactivated

### Requirement: Branch preparation never destroys user work
Branch preparation SHALL fail closed for any required repository it cannot safely switch. It MUST NOT stash, reset, force-checkout, or otherwise discard uncommitted changes. Repositories already prepared MUST retain their recorded binding so a retry resumes rather than restarts.

#### Scenario: Required repository is dirty on another branch
- **WHEN** a required repository has uncommitted changes and is not on the task branch
- **THEN** preparation reports it as blocked with the dirty entries and exit code 2
- **THEN** its branch and uncommitted changes are unchanged

#### Scenario: Remote is unreachable
- **WHEN** fetching `origin` fails for a required repository
- **THEN** preparation reports it as blocked with the git error
- **THEN** no branch is created from a stale or guessed base

#### Scenario: One repository blocks while another succeeds
- **WHEN** preparation succeeds for one required repository and blocks on another
- **THEN** the successful repository stays on the task branch and is recorded in the work context
- **THEN** rerunning the same command after the user resolves the blocker completes the preparation

#### Scenario: Continuing on the task branch tolerates work in progress
- **WHEN** a required repository is already on the task branch with uncommitted changes
- **THEN** preparation reuses it without touching the working tree

#### Scenario: Path is not a repository root
- **WHEN** a required scope path is missing or is not a git repository root
- **THEN** preparation reports it as blocked naming the path

### Requirement: Archive gates are exact, confirmable, and audited
Archive SHALL run a read-only preflight before any external mutation. Remaining checkbox work, unchecked acceptance criteria, and a named dirty delivery repository MUST each require explicit confirmation via its own exact flag, and every authorization used MUST be recorded in `changes.md`. Missing change identity, malformed operational data, and changes that are still active MUST NOT be overrideable.

#### Scenario: Overrideable condition is requested
- **WHEN** preflight finds remaining checkboxes, unchecked acceptance, or a dirty delivery repository without prior authorization
- **THEN** it returns exit code 2 with the affected items and the exact flag for each condition
- **THEN** no mutation occurs

#### Scenario: Authorization is narrowly scoped
- **WHEN** the user authorizes one condition
- **THEN** only that condition is bypassed and the others still require confirmation
- **THEN** the authorization is written to `changes.md` before the task is moved

#### Scenario: Structural failure cannot be forced
- **WHEN** a recorded change cannot be found under its planning root
- **THEN** archive fails with a hard error naming the change
- **THEN** no override flag permits it to proceed

#### Scenario: Changes must be archived before the task
- **WHEN** finalization runs while any associated OpenSpec change is still active
- **THEN** archive fails naming those changes and the task remains active and resolvable

#### Scenario: Archive recognition tolerates similar names
- **WHEN** a change has been archived and another archived directory shares its name as a prefix
- **THEN** recognition matches only the exact `YYYY-MM-DD-<change>` directory

#### Scenario: Finalization leaves a coherent record
- **WHEN** archive completes
- **THEN** the task README status is `archived`, `changes.md` records delivery repositories, branches, and change states, the task directory moves under `tasks/archive/`, emptied date directories are pruned, and the index is regenerated

### Requirement: Operational data fails closed instead of defaulting
Scope, OpenSpec, work-context, and acceptance tables SHALL be parsed by header name so existing documents remain readable as columns evolve. Unknown repository roles and malformed tables MUST produce a named failure. An unknown role MUST NOT default to required delivery.

#### Scenario: Repository role is unknown
- **WHEN** a scope row carries a role other than the three permitted values
- **THEN** parsing fails naming the offending row
- **THEN** the repository is not promoted to required delivery

#### Scenario: Existing table layouts remain readable
- **WHEN** a task README uses an older table layout with extra or missing columns
- **THEN** values are read by header name and the recognized fields are extracted
- **THEN** no migration step is required to read the document

#### Scenario: Placeholder rows are not data
- **WHEN** a table still holds the scaffold placeholder rows
- **THEN** parsing yields no entries rather than a repository or change named after the placeholder

#### Scenario: Recorded change is absent
- **WHEN** a change recorded in the README exists neither under `openspec/changes/` nor its archive
- **THEN** the change is reported as missing rather than assumed complete

### Requirement: Delegating openspec-* requires an explicit binding
Before delegating any `openspec-*` skill, the workflow SHALL execute inside that change's canonical planning root and pass the change name explicitly. Missing either binding MUST stop the delegation. Proposal completion and archive external actions MUST run `openspec validate --strict --change <name>` first.

#### Scenario: Binding is incomplete
- **WHEN** the planning root or the change name cannot be determined for a target
- **THEN** delegation stops and the target is reported
- **THEN** no `openspec-*` skill is invoked from an unrelated working directory

#### Scenario: Validation precedes external archive
- **WHEN** archive is about to archive a change externally
- **THEN** `openspec validate --strict --change <name>` runs in that planning root first
- **THEN** a validation failure stops the archive and the task remains active

#### Scenario: Change artifacts stay in the planning root
- **WHEN** apply implements checkbox work
- **THEN** the checkbox is ticked in the canonical planning root's `tasks.md`
- **THEN** the change is not copied into or read from a delivery branch
