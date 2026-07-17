# agents-doctor-report Specification

## Purpose
TBD - created by archiving change unify-agents. Update Purpose after archive.
## Requirements
### Requirement: Unified doctor command
The system SHALL provide a unified agents doctor command that diagnoses skills sync, MCP/env configuration, tools, browser, security, and related agent readiness.

#### Scenario: Doctor runs with defaults
- **WHEN** the user runs agents doctor without extra flags
- **THEN** it SHALL evaluate the selected default profile
- **THEN** it SHALL report grouped results covering at least env, tools, mcp, skills/agents sync, browser (if in scope), and security

#### Scenario: Doctor is requested after config
- **WHEN** the user runs `dotf -c agents` with a doctor-enabled option
- **THEN** sync SHALL complete first according to the selected scope
- **THEN** doctor SHALL print a summary of current status and outstanding problems

### Requirement: Detailed status and problem report
The doctor command SHALL produce a structured report that distinguishes overall status, individual check results, and actionable problems.

#### Scenario: Text report is shown
- **WHEN** doctor runs in text mode
- **THEN** it SHALL print a summary with counts by status (`pass`, `warn`, `fail`, `skip`)
- **THEN** it SHALL list problems (`warn`/`fail`) with identifiers and human-readable messages
- **THEN** it SHALL include remediation hints or related commands when available

#### Scenario: JSON report is requested
- **WHEN** the user requests JSON output
- **THEN** doctor SHALL emit valid JSON containing summary, problems, checks, and next_steps
- **THEN** secret values SHALL remain omitted or redacted

### Requirement: Normalized check statuses
Each doctor check SHALL use one of `pass`, `warn`, `fail`, or `skip`.

#### Scenario: Required check fails
- **WHEN** a required check fails
- **THEN** doctor SHALL mark it `fail`
- **THEN** the process exit code SHALL be non-zero

#### Scenario: Optional gap is found
- **WHEN** an optional dependency or configuration is missing
- **THEN** doctor SHALL mark it `warn` or `skip`
- **THEN** other checks SHALL continue

#### Scenario: Unsupported capability is intentional
- **WHEN** a target tool intentionally lacks a capability such as Codex MCP
- **THEN** doctor SHALL mark it `skip`
- **THEN** that skip alone SHALL NOT cause failure

### Requirement: Skills drift is reported clearly
The doctor command SHALL detect and report drift between shared `agents/` sources and generated per-tool skills/commands outputs.

#### Scenario: Skills output is stale
- **WHEN** generated skills or commands differ from the shared source for a selected tool
- **THEN** doctor SHALL report a problem identifying the tool and drift
- **THEN** remediation SHALL recommend the unified agents sync command for that tool

#### Scenario: Skills are in sync
- **WHEN** checked generated outputs match the shared source expectations
- **THEN** doctor SHALL report `pass` for that skills check

### Requirement: Problems include remediation next steps
The doctor report SHALL aggregate remediation into deduplicated next steps where possible.

#### Scenario: Multiple MCP drift issues share one fix
- **WHEN** several managed MCP drift checks fail for the same tool
- **THEN** next_steps MAY collapse to a single sync command for that tool
- **THEN** the detailed checks list SHALL still retain per-server or per-id detail

### Requirement: Deep mode remains explicit
Network reachability and expensive browser launch checks SHALL remain opt-in via a deep mode flag.

#### Scenario: Deep mode disabled
- **WHEN** doctor runs without deep mode
- **THEN** it SHALL avoid remote reachability probes and heavy browser launch attempts by default
- **THEN** it SHALL still report local readiness and configuration problems

