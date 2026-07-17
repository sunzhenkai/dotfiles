# agents-unified-cli Specification

## Purpose
TBD - created by archiving change unify-agents. Update Purpose after archive.
## Requirements
### Requirement: Unified agents config module
The system SHALL expose a single primary config module named `agents` that synchronizes both shared skills/commands and agent environment MCP/profile configuration.

#### Scenario: User configures agents
- **WHEN** the user runs `dotf -c agents` or the equivalent config script entry
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

### Requirement: Compatibility alias for agent-env
The system SHALL keep `agent-env` as a compatibility alias that delegates to the unified `agents` implementation.

#### Scenario: Legacy agent-env config is invoked
- **WHEN** the user runs `dotf -c agent-env`
- **THEN** the system SHALL delegate to the unified agents env/MCP sync path
- **THEN** the system SHALL emit a deprecation or migration hint recommending `agents`

### Requirement: Per-tool installers use unified sync
The system SHALL route Claude/Cursor/OpenCode/Codex config flows through the unified agents sync helper rather than calling divergent skills-only and env-only entrypoints independently in a conflicting way.

#### Scenario: Cursor config runs
- **WHEN** the user runs `dotf -c cursor`
- **THEN** Cursor-specific settings/MCP installation MAY still run
- **THEN** shared skills and managed MCP sync SHALL go through the unified agents sync path
- **THEN** repeated runs SHALL remain idempotent

### Requirement: Scripts expose a single agents CLI surface
The system SHALL provide scripts under `scripts/agents/` as the preferred direct CLI for sync and doctor orchestration.

#### Scenario: User invokes scripts directly
- **WHEN** the user runs `scripts/agents/sync.sh` without going through `dotf`
- **THEN** the command SHALL support the same core scopes as `dotf -c agents`
- **THEN** documentation SHALL present this path as equivalent to the config module

