# task-workflow-orchestration Specification

## Purpose
定义 task 工作流的指令面与命令面：一个根 skill 加四份 reference、九条 taskctl 命令、六个阶段的路由，以及「OpenSpec checkbox 是唯一进度真相」这一核心约束。正确性门禁见 `task-workflow-correctness`。

## Requirements

### Requirement: Workflow structure has a bounded instruction surface
The task workflow SHALL use one root skill and exactly four workflow references named `planning.md`, `apply.md`, `archive.md`, and `safety.md`. The combined line count of the root skill and its references MUST stay under 320 lines. The root skill MUST route phases without embedding complete per-command procedures, and command shells MUST pass phase identity and user input without copying gate algorithms.

#### Scenario: Planning command loads bounded context
- **WHEN** an Agent executes `task-new`, `task-explore`, `task-design`, or `task-propose`
- **THEN** it loads the root contract, `planning.md`, and `safety.md`
- **THEN** it does not load apply or archive procedures

#### Scenario: Apply and archive load their own procedures
- **WHEN** an Agent executes `task-apply` or `task-archive`
- **THEN** it loads the root contract, the matching phase reference, and `safety.md`
- **THEN** no second copy of the phase algorithm exists in the command shell

#### Scenario: Safety rules are defined once
- **WHEN** the reference set is inspected
- **THEN** only `safety.md` contains the normative rule table
- **THEN** phase references cite rule IDs instead of restating the rules

#### Scenario: Task-new retains the proven input boundary
- **WHEN** the `task-new` command is rendered with appended user text
- **THEN** `[TASK_NEW_INPUT_START]` still separates the command contract from user input
- **THEN** natural-language summarization remains an Agent responsibility rather than a CLI parser feature

### Requirement: Public command surface is small and free of parallel paths
The supported taskctl command set SHALL be exactly `new`, `list`, `resolve`, `status`, `set-status`, `prepare-branches`, `archive`, `restore`, `notes`, and the maintenance command `sync-index`. The workflow MUST NOT add aliases, legacy wrappers, compatibility façades, duplicate schedulers, or a second apply path.

#### Scenario: Public command surface is converged
- **WHEN** taskctl public subcommands are enumerated
- **THEN** the supported set is exactly the ten documented commands
- **THEN** the skill documentation lists the same set

#### Scenario: Scheduler commands are absent
- **WHEN** taskctl help, parser definitions, and workflow instructions are inspected
- **THEN** `advance`, `execution-context`, `checkpoint`, `apply-next`, `repo-roots`, `scope-repos`, and `git-summary` are not public subcommands or hidden aliases
- **THEN** no runtime switch selects between an old and a new progress path

#### Scenario: CLI reports machine-readable results
- **WHEN** any command completes
- **THEN** stdout contains only JSON and stderr contains a one-line summary
- **THEN** exit code 0 means success, 1 means hard failure including argument misuse, and 2 means user confirmation is required

#### Scenario: Root can be given on either side of the subcommand
- **WHEN** `--root` is passed before the subcommand, after it, or both with identical values
- **THEN** the workspace resolves to that root
- **WHEN** both positions are given with different values
- **THEN** the command fails with a usage error

### Requirement: OpenSpec checkboxes are the only progress truth
Implementation progress SHALL be derived exclusively from the checkbox state of each change's `tasks.md` under its canonical planning root. The workflow MUST NOT persist a second record of completion, deferred work, or checkout identity.

#### Scenario: Progress is read from checkboxes
- **WHEN** `status` runs for a task with associated OpenSpec changes
- **THEN** it reports per-change `complete`, `total`, and the remaining checkbox texts
- **THEN** it performs no git operation and requires no prepared checkout

#### Scenario: No parallel progress files are produced
- **WHEN** a task completes its full lifecycle from `new` through `archive`
- **THEN** no `progress.md` or `.task-apply-state.json` is created
- **THEN** deferred work and blockers are recorded as prose in the task README

#### Scenario: Resuming apply needs no dedicated command
- **WHEN** apply is interrupted and later resumed
- **THEN** the Agent reads `status` and treats unchecked checkboxes as the remaining work
- **THEN** no resume-state command is required

### Requirement: Task identity and index are derived from the directory tree
Task IDs SHALL be `T` plus four digits, allocated by scanning `tasks/`, and MUST NOT be reused after archival. Active tasks live at `tasks/YYYY-MM-DD/TNNNN-<slug>/` and archived tasks at `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`. `tasks/INDEX.md` SHALL be a derived locator regenerated from the directory tree and MUST NOT store allocation or status state.

#### Scenario: Identifiers are not recycled
- **WHEN** a task is archived and a new task is created
- **THEN** the new task receives an unused higher identifier

#### Scenario: Index is rebuilt from disk
- **WHEN** `INDEX.md` is edited by hand or deleted
- **THEN** `sync-index` regenerates it from the actual task directories
- **THEN** the regenerated index contains no `next_id` frontmatter

#### Scenario: Duplicate identity on disk fails closed
- **WHEN** two task directories claim the same identifier
- **THEN** commands fail with the conflicting paths rather than guessing

### Requirement: Repository roles drive branch preparation
The task README SHALL classify every listed repository as exactly one of `必须`, `建议`, or `排除`. Only `必须` repositories are delivery repositories eligible for branch preparation. Planning roots hosting `openspec/` are read and written as artifacts but never switched.

#### Scenario: Only required repositories are switched
- **WHEN** `prepare-branches` runs for a task whose scope lists required, suggested, and excluded repositories
- **THEN** only the required repositories are switched to the task branch
- **THEN** the working directory, suggested, and excluded repositories are left untouched

#### Scenario: Work context records the real execution environment
- **WHEN** branch preparation succeeds for at least one repository
- **THEN** the task README work-context table records repository, branch, and base for those repositories
- **THEN** repeated runs update the same rows without duplicating them or accumulating blank lines

#### Scenario: Planning phases never touch delivery branches
- **WHEN** `task-new`, `task-explore`, `task-design`, or `task-propose` runs
- **THEN** no fetch or checkout is performed for the task branch
- **THEN** the work-context section remains in its unprepared placeholder state
