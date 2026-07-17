# agent-env-catalog Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Agent environment source catalog
The system SHALL provide `agent-env/` as the single handwritten source for reusable agent runtime environment definitions, separate from `agents/` skills and commands.

#### Scenario: Catalog directory exists
- **WHEN** the change is implemented
- **THEN** `agent-env/` SHALL exist at the repository root
- **THEN** it SHALL contain documented sources for MCP servers, profiles, environment variables, tool dependencies, browser settings, and security policy

#### Scenario: Skills remain outside agent environment catalog
- **WHEN** a maintainer adds or edits a shared skill or command
- **THEN** the maintainer SHALL continue to use `agents/`
- **THEN** `agent-env/` SHALL NOT become the handwritten source for skills or slash commands

### Requirement: Environment manifest declares supported modules
The system SHALL define an agent environment manifest that declares supported target tools, enabled environment modules, default profiles, and per-tool include/exclude rules.

#### Scenario: Tool support is declared
- **WHEN** the manifest is read
- **THEN** it SHALL identify supported target tools including Claude Code, Cursor, OpenCode, and Codex
- **THEN** each module SHALL be able to declare which tools it supports

#### Scenario: Unsupported tool combination is skipped
- **WHEN** a module excludes a target tool
- **THEN** sync SHALL skip that module for the excluded tool
- **THEN** doctor SHALL report the skip as intentional rather than a failure

### Requirement: Profiles compose environment capabilities
The system SHALL support named profiles that compose MCP servers, browser capabilities, tool checks, risk level, and documentation into reusable agent modes.

#### Scenario: Default profile is safe
- **WHEN** no local override selects a profile
- **THEN** the default profile SHALL include low-risk coding and research capabilities
- **THEN** it SHALL NOT enable high-risk browser automation by default

#### Scenario: Browser profile is explicit
- **WHEN** a user selects a browser-focused profile
- **THEN** the selected profile SHALL include browser automation MCP capabilities
- **THEN** the profile SHALL be marked as high risk in catalog metadata

### Requirement: Environment variable schema is documented
The system SHALL define an environment variable schema listing variable names, purpose, requiredness, sensitive classification, and the checks that use them.

#### Scenario: Required variable is missing
- **WHEN** doctor checks a selected profile that requires an environment variable
- **THEN** doctor SHALL report a failure or warning according to the variable requiredness
- **THEN** the report SHALL name the variable without printing its value

#### Scenario: Secret values are not stored
- **WHEN** env schema is committed to the repository
- **THEN** it SHALL contain variable names and descriptions
- **THEN** it MUST NOT contain real API keys, tokens, cookies, passwords, or private credentials

### Requirement: Tool dependency catalog is testable
The system SHALL define a tool dependency catalog for agent development tasks, including command names, check commands, optional install hints, and the profiles that require each tool.

#### Scenario: Required CLI is unavailable
- **WHEN** doctor checks a selected profile and a required CLI is missing
- **THEN** doctor SHALL report the missing command
- **THEN** doctor SHALL include a safe install hint when one is documented

#### Scenario: Optional CLI is unavailable
- **WHEN** doctor checks a selected profile and an optional CLI is missing
- **THEN** doctor SHALL report a warning or skip
- **THEN** the selected profile SHALL still be considered usable if all required checks pass

### Requirement: Local overrides remain private
The system SHALL support local override files for machine-specific choices and SHALL ensure those files are ignored by git.

#### Scenario: Local profile override exists
- **WHEN** a local override selects a default profile or browser path
- **THEN** sync and doctor SHALL use the local value on that machine
- **THEN** the local override file SHALL NOT be committed to the repository

#### Scenario: Local override is absent
- **WHEN** no local override file exists
- **THEN** sync and doctor SHALL use repository defaults
- **THEN** installation SHALL still complete with documented warnings for optional local settings

