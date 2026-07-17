# agents-doctor Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Agent environment doctor command
The system SHALL provide a doctor command for checking the installed and configured agent development environment.

#### Scenario: Doctor runs with defaults
- **WHEN** the user runs the agent environment doctor without extra flags
- **THEN** it SHALL check the selected default profile
- **THEN** it SHALL report grouped results for environment variables, tools, MCP, browser, security, and agents synchronization

#### Scenario: Doctor targets a specific tool
- **WHEN** the user runs doctor for a specific target tool
- **THEN** doctor SHALL restrict tool-specific checks to that target
- **THEN** shared checks required by the selected profile SHALL still run

### Requirement: Doctor reports normalized statuses
The doctor command SHALL report each check as `pass`, `warn`, `fail`, or `skip`.

#### Scenario: Required check fails
- **WHEN** a required check for the selected profile fails
- **THEN** doctor SHALL report `fail`
- **THEN** doctor SHALL exit with a non-zero status

#### Scenario: Optional check is unavailable
- **WHEN** an optional check for the selected profile is unavailable
- **THEN** doctor SHALL report `warn` or `skip`
- **THEN** doctor SHALL continue checking other items

#### Scenario: Unsupported tool feature is declared
- **WHEN** a target tool does not support a requested environment feature
- **THEN** doctor SHALL report `skip` if the manifest marks the unsupported state as intentional
- **THEN** doctor SHALL NOT fail solely because of that declared skip

### Requirement: Doctor checks environment variables safely
The doctor command SHALL check required and optional environment variables without printing their secret values.

#### Scenario: Secret environment variable is set
- **WHEN** doctor checks a sensitive variable that exists
- **THEN** doctor SHALL report that the variable is present
- **THEN** doctor MUST NOT print the variable value

#### Scenario: Secret environment variable is missing
- **WHEN** doctor checks a required sensitive variable that is absent
- **THEN** doctor SHALL report the missing variable name
- **THEN** doctor SHALL include the documented setup hint when available

### Requirement: Doctor checks CLI and runtime dependencies
The doctor command SHALL verify command-line tools and runtime dependencies declared by the selected profile.

#### Scenario: Required command exists
- **WHEN** a required command is available on `PATH`
- **THEN** doctor SHALL report `pass`
- **THEN** doctor MAY include a version string when a version command is configured

#### Scenario: Required command is missing
- **WHEN** a required command is unavailable
- **THEN** doctor SHALL report `fail`
- **THEN** doctor SHALL include a documented install hint when one is configured

### Requirement: Doctor checks MCP configuration
The doctor command SHALL validate MCP manifest parsing, generated target configuration, required environment variables, and optional server reachability.

#### Scenario: MCP manifest is invalid
- **WHEN** doctor parses an invalid MCP source manifest
- **THEN** doctor SHALL report a failure with the source path and reason
- **THEN** doctor SHALL NOT continue as if MCP configuration were healthy

#### Scenario: MCP configuration differs from generated output
- **WHEN** doctor compares target configuration with generated output and finds drift in managed server ids
- **THEN** doctor SHALL report a warning or failure according to configured strictness
- **THEN** doctor SHALL recommend running sync

#### Scenario: Deep network check is requested
- **WHEN** doctor runs with a deep check option
- **THEN** doctor MAY test remote MCP server reachability
- **THEN** network failures SHALL be reported without printing authorization headers

### Requirement: Doctor checks agents synchronization
The doctor command SHALL verify that shared `agents/` skills and commands are synchronized for selected target tools.

#### Scenario: Agent skill output is stale
- **WHEN** doctor detects generated skill or command output differs from the shared source
- **THEN** doctor SHALL report drift
- **THEN** doctor SHALL recommend running the existing agents sync command

#### Scenario: Agents sync script is missing or unavailable
- **WHEN** doctor cannot run or inspect the agents sync mechanism
- **THEN** doctor SHALL report a warning
- **THEN** MCP and environment checks SHALL continue

### Requirement: Doctor supports machine-readable output
The doctor command SHALL support a machine-readable output mode for automation.

#### Scenario: JSON output is requested
- **WHEN** the user requests JSON output
- **THEN** doctor SHALL emit valid JSON containing check groups, item statuses, messages, and exit status meaning
- **THEN** secret values SHALL remain redacted or omitted

