# agents-security Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Secrets are never committed
The system SHALL manage only secret references and validation rules in repository files, never real secret values.

#### Scenario: MCP server requires API key
- **WHEN** an MCP server requires an API key
- **THEN** the repository source SHALL reference an environment variable name or supported credential provider
- **THEN** it MUST NOT contain the API key value

#### Scenario: Doctor reports secret status
- **WHEN** doctor reports whether a secret variable is configured
- **THEN** it SHALL print only the variable name and presence status
- **THEN** it MUST NOT print the secret value, authorization header, cookie, or token

### Requirement: Local private configuration is isolated
The system SHALL keep machine-specific paths, browser profiles, private overrides, and experimental local settings in gitignored local files.

#### Scenario: Local override file is created
- **WHEN** a user creates an `agents/env` local override file
- **THEN** the file SHALL be ignored by git
- **THEN** sync and doctor SHALL be able to read it on that machine

#### Scenario: Private path is needed
- **WHEN** a configuration needs a private path such as a browser profile, local binary, workspace, or socket
- **THEN** the path SHALL be placed in a local override or environment variable
- **THEN** the committed repository source SHALL contain only a placeholder or documented example

### Requirement: Risk levels are declared for capabilities
The system SHALL classify agent environment capabilities by risk level and SHALL expose that classification to sync, doctor, and documentation.

#### Scenario: Low-risk capability is enabled
- **WHEN** a low-risk capability such as remote web reading is enabled
- **THEN** sync SHALL install it according to the selected profile
- **THEN** doctor SHALL report its risk classification

#### Scenario: High-risk capability is enabled
- **WHEN** a high-risk capability such as browser automation or local filesystem control is enabled
- **THEN** the capability SHALL be marked high risk in the catalog
- **THEN** doctor SHALL include a warning explaining the risk category

### Requirement: High-risk capabilities require explicit profile selection
The system SHALL NOT enable high-risk capabilities through the default profile unless the manifest explicitly documents that choice.

#### Scenario: User runs default install
- **WHEN** the user installs or syncs agent environment without selecting a high-risk profile
- **THEN** high-risk MCP servers SHALL remain disabled
- **THEN** doctor SHALL not require their dependencies

#### Scenario: User selects high-risk profile
- **WHEN** the user selects a high-risk profile
- **THEN** sync SHALL install the high-risk capability for compatible tools
- **THEN** doctor SHALL report the profile as high risk

### Requirement: Browser state is protected
The system SHALL protect browser cookies, sessions, downloads, screenshots, traces, and profiles from accidental repository tracking.

#### Scenario: Real browser profile is configured
- **WHEN** a user configures a real browser profile for automation
- **THEN** the profile path SHALL be stored only in local override or environment variable
- **THEN** doctor SHALL warn that logged-in browser state may be exposed to the agent

#### Scenario: Browser output appears inside repository
- **WHEN** doctor detects known browser output paths inside the repository
- **THEN** doctor SHALL warn if those paths are not ignored
- **THEN** doctor SHALL recommend moving them to a temporary or ignored directory

### Requirement: Generated configuration is auditable
The system SHALL make generated or managed agent environment configuration auditable without exposing secrets.

#### Scenario: Sync writes managed MCP configuration
- **WHEN** sync writes target MCP configuration
- **THEN** managed server ids SHALL be traceable back to `agents/env` source declarations
- **THEN** generated files SHALL not contain expanded secret values unless the target tool has no safe placeholder mechanism and the write is explicitly documented

#### Scenario: Secret expansion is unavoidable
- **WHEN** a target tool requires literal secret expansion in its config file
- **THEN** sync SHALL warn before writing
- **THEN** the written file SHALL be treated as user-level private state, not repository content

### Requirement: Repository scans catch obvious sensitive leakage
The system SHALL provide checks that catch obvious sensitive data patterns in `agents/env` source files and generated repository files.

#### Scenario: Potential secret pattern is detected
- **WHEN** doctor or validation detects a likely secret in a committed `agents/env` source path
- **THEN** it SHALL report a failure or high-severity warning
- **THEN** it SHALL identify the file path without printing the full sensitive value

#### Scenario: Internal information appears in public config
- **WHEN** a public repository config appears to contain internal URL, company-specific host, or private credential material
- **THEN** doctor SHALL warn according to configured sensitive pattern rules
- **THEN** the user SHALL be directed to move that information into local override when appropriate

