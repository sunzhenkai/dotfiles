# agents-unified-cli Specification

## Purpose
TBD - created by archiving change unify-agents. Update Purpose after archive.
## Requirements
### Requirement: Unified agents config module
The system SHALL expose a single primary config module named `agents` that synchronizes both shared skills/commands and agent environment MCP/profile configuration.

#### Scenario: User configures agents
- **WHEN** the user runs `dotf agents -c` or the equivalent config script entry
- **THEN** the system SHALL sync skills/commands for supported tools
- **THEN** the system SHALL sync MCP/profile configuration for tools that support it
- **THEN** the operation SHALL be idempotent when repeated with the same inputs

#### Scenario: Tool filter is provided
- **WHEN** the user requests sync for a specific tool such as `cursor`
- **THEN** skills and env/MCP sync SHALL be limited to that tool where applicable
- **THEN** unsupported combinations SHALL be reported as intentional skips rather than hard failures

### Requirement: Granular sync flags
The system SHALL allow users to restrict sync scope without abandoning the unified `agents` entry.

#### Scenario: Skills-only sync
- **WHEN** the user requests skills-only sync through the unified agents CLI
- **THEN** the system SHALL sync skills/commands
- **THEN** the system SHALL NOT modify MCP configuration

#### Scenario: Env-only sync
- **WHEN** the user requests env-only sync through the unified agents CLI
- **THEN** the system SHALL sync MCP/profile configuration
- **THEN** the system SHALL NOT rewrite skills/commands outputs

### Requirement: Per-tool installers use unified sync
The system SHALL route Claude/Cursor/OpenCode/Codex config flows through the unified agents sync helper rather than calling divergent skills-only and env-only entrypoints independently in a conflicting way.

#### Scenario: Cursor config runs
- **WHEN** the user runs `dotf cursor -c`
- **THEN** Cursor-specific settings/MCP installation MAY still run
- **THEN** shared skills and managed MCP sync SHALL go through the unified agents sync path
- **THEN** repeated runs SHALL remain idempotent

### Requirement: Scripts expose a single agents CLI surface
The system SHALL provide scripts under `scripts/agents/` as the single CLI surface for sync and doctor orchestration, implemented as one self-contained Python package with no reverse dependency on any other agent script directory. Sync entrypoints SHALL NOT accept a `--doctor` flag; diagnosis SHALL be invoked via the module doctor action (`dotf agents -d`) or by calling the doctor script directly.

#### Scenario: User invokes scripts directly
- **WHEN** the user runs `scripts/agents/sync.sh` without going through `dotf`
- **THEN** the command SHALL support the same core scopes as `dotf agents -c`
- **THEN** documentation SHALL present this path as equivalent to the config module

#### Scenario: Sync rejects doctor flag
- **WHEN** the user runs `scripts/agents/sync.sh --doctor` or `dotf agents -c --doctor`
- **THEN** the command SHALL fail with a non-zero exit
- **THEN** the error SHALL direct the user to `dotf agents -d` or `dotf agents -cd`

#### Scenario: No parallel agent script directory
- **WHEN** the sync/doctor logic is loaded
- **THEN** all core implementation modules SHALL reside under `scripts/agents/`
- **THEN** the code SHALL NOT import agent logic from a separate `scripts/agent-env/` directory

### Requirement: Agents dual capability via subject-first CLI
The `agents` module SHALL be registered with install, config, and doctor capabilities. Users SHALL be able to run `dotf agents -i`, `dotf agents -c`, `dotf agents -d`, and combinations such as `dotf agents -ic` and `dotf agents -cd` under the subject-first CLI.

#### Scenario: Install then config
- **WHEN** the user runs `dotf agents -ic`
- **THEN** the system SHALL run the agents install bundle first
- **THEN** only if install succeeds, the system SHALL run the unified agents config sync

#### Scenario: Config then doctor
- **WHEN** the user runs `dotf agents -cd`
- **THEN** the system SHALL run the unified agents config sync first
- **THEN** only if config succeeds, the system SHALL run agents doctor

#### Scenario: Doctor alone
- **WHEN** the user runs `dotf agents -d`
- **THEN** the system SHALL run agents doctor without requiring a preceding sync in the same invocation

