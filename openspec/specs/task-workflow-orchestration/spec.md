# task-workflow-orchestration Specification

## Purpose
定义低上下文、单路径、可恢复并保留关键安全门禁的 task 工作流：根 skill 加四份 reference、`advance` 作为唯一进度转换，以及 checkout/archive 的 fail-closed 契约。
## Requirements

### Requirement: Workflow structure has a bounded instruction surface
The task workflow SHALL use one root skill and exactly four workflow references named `planning.md`, `apply.md`, `archive.md`, and `safety.md`. The root skill MUST route phases without embedding complete per-command procedures, and command shells MUST pass phase identity and user input without copying gate algorithms.

#### Scenario: Planning command loads bounded context
- **WHEN** an Agent executes `task-new`, `task-explore`, `task-design`, or `task-propose`
- **THEN** it loads the root contract, `planning.md`, and only the safety rules referenced by that phase
- **THEN** it does not load complete apply or archive procedures

#### Scenario: Apply and archive load their own procedures
- **WHEN** an Agent executes `task-apply` or `task-archive`
- **THEN** it loads the root contract, the matching phase reference, and referenced safety rules
- **THEN** no second copy of the phase algorithm exists in the command shell

#### Scenario: Task-new retains the proven input boundary
- **WHEN** the `task-new` command is rendered with appended user text
- **THEN** `[TASK_NEW_INPUT_START]` still separates the command contract from user input
- **THEN** natural-language summarization remains an Agent responsibility rather than a CLI parser feature

### Requirement: Complexity decreases without parallel paths
The completed change MUST reduce the public taskctl command count, repeated normative instruction blocks, and Agent tool calls for apply progress. It MUST NOT add aliases, legacy wrappers, compatibility façades, duplicate schedulers, schema migration code, or package structure whose only purpose is preserving removed interfaces.

#### Scenario: Removed commands are absent
- **WHEN** taskctl help and parser definitions are inspected after cutover
- **THEN** `checkpoint`, `apply-next`, `repo-roots`, `scope-repos`, and `git-summary` are not public subcommands or hidden aliases

#### Scenario: Public command surface is converged
- **WHEN** taskctl public subcommands are enumerated
- **THEN** the supported set is `list`, `resolve`, `set-status`, `new`, `archive`, `restore`, `prepare-branches`, `execution-context`, `advance`, and `notes`

#### Scenario: No compatibility implementation remains
- **WHEN** repository code and task workflow instructions are searched
- **THEN** no wrapper dispatches a removed command to the new implementation
- **THEN** no runtime switch selects between old and new progress paths

### Requirement: Case-derived safety rules remain testable
The workflow SHALL keep a concise safety contract whose rules map to regression tests for task resolution, checkout continuity, apply durability, archive repository roles, and mutation rollback. Removing duplicated prose MUST NOT remove the tested behavior behind a real failure case.

#### Scenario: Explicit task focus is used
- **WHEN** the current message or unique session focus identifies a `TNNNN`
- **THEN** Resolution uses that explicit query rather than discarding it and selecting by heuristic

#### Scenario: Heuristic resolution requires confirmation
- **WHEN** only status or recency heuristics identify candidates
- **THEN** no task mutation occurs before user confirmation

#### Scenario: Safety rule has a regression case
- **WHEN** `safety.md` lists a fail-closed or rollback rule
- **THEN** it names at least one test that exercises the triggering condition and expected outcome

### Requirement: Planning and delivery remain isolated
Checkout Gate MUST run only during `task-apply` and only for repositories classified as required delivery repositories. Planning phases MUST NOT inspect or mutate target Git state solely to prepare task branches.

#### Scenario: Planning does not prepare Git
- **WHEN** a task is created, explored, designed, or proposed
- **THEN** no target fetch, status, checkout, branch creation, or worktree preparation occurs for Checkout Gate

#### Scenario: Only required repositories are prepared
- **WHEN** scope contains required, suggested, and excluded repositories
- **THEN** branch preparation targets only required repositories
- **THEN** cwd or workspace `.` is not added implicitly

#### Scenario: No delivery repository exists
- **WHEN** the required repository set is empty
- **THEN** preparation returns a successful no-target result without switching the workspace repository

### Requirement: Real checkout continuity fails closed
Apply SHALL persist and reuse the real checkout for each delivery repository and SHALL stop when a safe checkout or current baseline cannot be established.

#### Scenario: Recorded worktree is reused
- **WHEN** a task records a valid linked worktree that owns the task branch
- **THEN** apply and archive operate on that checkout rather than current cwd or the canonical worktree

#### Scenario: Configured origin fetch fails
- **WHEN** a delivery repository has an `origin` and refresh fails
- **THEN** branch preparation stops instead of continuing from a stale local baseline

#### Scenario: Dirty checkout is on another branch
- **WHEN** a delivery checkout is dirty and not on the task branch
- **THEN** preparation stops for user confirmation without automatic stash, reset, or force checkout

#### Scenario: Dirty checkout is already on the task branch
- **WHEN** the recorded checkout is already on the task branch with in-progress changes
- **THEN** apply resumes without discarding or relocating those changes

### Requirement: Advance is the single progress transition
The CLI SHALL provide `advance` as the only command that changes apply checkpoint state. One invocation MUST persist the phase/current item/evidence/deferred state, recalculate the OpenSpec schedule, and return `next`, `done`, or `deferred_only` atomically.

#### Scenario: Completed item returns next runnable item
- **WHEN** an OpenSpec checkbox has been completed and `advance` records the checkpoint
- **THEN** it returns the next non-deferred checkbox in the same JSON response
- **THEN** no second scheduling command is required

#### Scenario: Deferred item does not block independent work
- **WHEN** the exact current remaining checkbox is deferred with a non-empty reason and another runnable item exists
- **THEN** the deferred checkbox remains unchecked
- **THEN** `advance` returns the next runnable item

#### Scenario: Only deferred work remains
- **WHEN** every remaining checkbox is deferred
- **THEN** `advance` returns `deferred_only` and no next item

#### Scenario: All work is complete
- **WHEN** no OpenSpec checkbox remains
- **THEN** `advance` returns `done`

#### Scenario: Progress write fails
- **WHEN** writing README, INDEX, apply state, or progress fails
- **THEN** all partial mutations are rolled back
- **THEN** no successful next item is reported

### Requirement: Internal query capabilities are returned by owner commands
Repository-root resolution, scope classification, and delivery Git summaries SHALL remain internal implementation capabilities. Their results MUST be exposed through the owner commands that act on them rather than through separate public utility subcommands.

#### Scenario: Execution context returns scope
- **WHEN** `execution-context` is requested for a task
- **THEN** its JSON includes required, suggested, excluded, and checkout scope used by apply

#### Scenario: Prepare resolves real repositories internally
- **WHEN** `prepare-branches` receives task scope or an explicit repository
- **THEN** it resolves canonical roots and linked worktrees without invoking a public `repo-roots` command

#### Scenario: Archive dry-run returns delivery summaries
- **WHEN** `archive --dry-run` evaluates delivery repositories
- **THEN** `archive_gate.delivery_summaries` contains the commit and working-tree summary needed for `changes.md`
- **THEN** no public `git-summary` command is required

### Requirement: Existing state has one owner and no new mirror
The workflow MUST keep task identity/status/scope/work context in README, allocation and lookup in INDEX, completion in OpenSpec checkboxes, deferred reasons in apply state, checkpoint/evidence presentation in `progress.md`, and checkout facts in Git. The change MUST NOT add a new state file, schema-version branch, dual-write field, or alternate index.

#### Scenario: Schedule uses canonical facts
- **WHEN** `advance` or `execution-context` computes a schedule
- **THEN** completion comes from OpenSpec checkboxes and deferred membership comes from apply state
- **THEN** copied text in `progress.md` cannot override either fact

#### Scenario: Index mutation fails
- **WHEN** a status, advance, archive, or restore operation cannot update INDEX
- **THEN** related README state, directory movement, apply state, progress, and generated audit changes return to their prior consistent state
- **THEN** a rollback failure is reported explicitly

### Requirement: Archive preserves repository roles and user judgment
Archive SHALL distinguish delivery, planning, task-store, and reference roles. Delivery failures MUST block by default, non-delivery dirty state MUST be diagnostic only, and remaining OpenSpec text MUST be returned verbatim for Agent explanation and user judgment.

#### Scenario: Dirty or unavailable delivery blocks
- **WHEN** a delivery checkout is dirty without exact override or its status cannot be obtained
- **THEN** archive fails closed with the repository in `archive_gate.blocking`

#### Scenario: Recorded delivery checkout is invalid
- **WHEN** a recorded delivery checkout is missing, invalid, or not from the canonical repository
- **THEN** archive fails even when a dirty override is supplied

#### Scenario: Non-delivery store is dirty
- **WHEN** a repository is dirty only in planning or task-store roles
- **THEN** archive reports it as non-blocking and continues

#### Scenario: Delivery role takes priority
- **WHEN** one repository has both delivery and non-delivery roles
- **THEN** delivery clean requirements take precedence

#### Scenario: OpenSpec work remains
- **WHEN** any associated OpenSpec checkbox remains unchecked
- **THEN** archive returns each remaining item verbatim and requires user confirmation before force merge
- **THEN** the CLI does not classify wording such as `test` or `healthcheck` as verification or implementation
