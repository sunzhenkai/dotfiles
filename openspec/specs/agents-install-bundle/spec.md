# agents-install-bundle Specification

## Purpose
TBD - created by archiving change unify-agents. Update Purpose after archive.
## Requirements
### Requirement: Agents install module exists
The system SHALL provide `dotf -i agents` (and the equivalent install script module) as the install entry for the agent tooling bundle.

#### Scenario: User installs agents bundle
- **WHEN** the user runs `dotf -i agents`
- **THEN** the system SHALL install or verify the declared agent-related CLI modules
- **THEN** the system SHALL print a per-module status summary
- **THEN** the command SHALL NOT rewrite MCP or skills configuration as its primary action

#### Scenario: Install is repeated
- **WHEN** the user runs `dotf -i agents` again on a machine where modules are already present
- **THEN** already-installed modules SHALL be skipped or reported as up-to-date
- **THEN** the overall command SHALL succeed if no required install step fails

### Requirement: Install bundle membership is explicit
The agents install bundle SHALL declare which install modules it includes, and SHALL only orchestrate those modules.

#### Scenario: Bundle manifest is read
- **WHEN** the install bundle definition is inspected
- **THEN** it SHALL list included modules such as Cursor Agent CLI and Codex CLI
- **THEN** modules outside the list SHALL NOT be installed by `dotf -i agents`

#### Scenario: Optional module is unavailable
- **WHEN** an included optional module cannot be installed on the current platform
- **THEN** the installer SHALL report a warning or skip with reason
- **THEN** required modules that failed SHALL still surface as failures

### Requirement: Install and config responsibilities stay separated
The agents install path SHALL install binaries/tooling, while the agents config path SHALL synchronize configuration artifacts.

#### Scenario: User only installs
- **WHEN** the user runs `dotf -i agents` without `-c agents`
- **THEN** CLI tools MAY be installed
- **THEN** skills/commands and managed MCP files SHALL NOT be required to change for the install command to succeed

#### Scenario: User only configures
- **WHEN** the user runs `dotf -c agents` without `-i agents`
- **THEN** configuration sync SHALL proceed using already-available tools
- **THEN** missing CLIs SHALL be reported by doctor or warnings rather than silently installed

### Requirement: Install shows readiness summary
The agents install flow SHALL finish with a lightweight readiness summary without requiring deep doctor checks.

#### Scenario: Post-install summary
- **WHEN** install completes
- **THEN** the system SHALL print which bundled CLIs are present or missing on `PATH`
- **THEN** it SHALL direct the user to `dotf -c agents` and doctor for full environment configuration and diagnosis

