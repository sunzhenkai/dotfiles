# agents-security Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Secrets are never committed
The system SHALL manage only secret references and validation rules in repository files, never real secret values.

#### Scenario: Repository declares no LLM provider keys
- **WHEN** repository agent vendor configuration is maintained
- **THEN** it SHALL NOT declare LLM providers, models, or provider API keys (removed per ADR-0017); provider/key configuration is machine-local only
- **THEN** the env schema MAY declare non-provider variables, referencing environment variable names or supported credential providers, never values

#### Scenario: Doctor reports secret status
- **WHEN** doctor reports whether a secret variable is configured
- **THEN** it SHALL print only the variable name and presence status
- **THEN** it MUST NOT print the secret value, authorization header, cookie, or token

### Requirement: Local private configuration is isolated
The system SHALL load machine-specific paths, private overrides, and experimental settings from an XDG user configuration location outside the dotfiles repository. Repository files SHALL contain only schemas, safe defaults, and examples; a legacy gitignored repository-local override MAY be read only for migration and SHALL trigger a deprecation warning.

#### Scenario: Local override file is created
- **WHEN** a user creates or initializes an agent local override
- **THEN** the file SHALL be stored below `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/`
- **THEN** sync and doctor SHALL read it without creating a file inside the repository

#### Scenario: Legacy repository-local override exists
- **WHEN** a gitignored `agents/env/local.yaml` or vendor local file exists
- **THEN** the system SHALL warn and provide a migration destination
- **THEN** it SHALL NOT copy private values into committed repository files

#### Scenario: Private path is needed
- **WHEN** a configuration needs a local binary, workspace, socket, endpoint, or private host
- **THEN** the value SHALL come from the external local override, environment, or supported credential provider
- **THEN** committed source SHALL contain only a safe placeholder or example

### Requirement: Risk levels are declared for capabilities
The system SHALL classify agent environment capabilities by risk level and SHALL expose that classification to sync, doctor, and documentation.

#### Scenario: Low-risk capability is enabled
- **WHEN** a low-risk capability such as remote external API access is enabled
- **THEN** sync SHALL install it according to the selected profile
- **THEN** doctor SHALL report its risk classification

#### Scenario: High-risk capability is enabled
- **WHEN** a high-risk capability such as broad local filesystem control is enabled
- **THEN** the capability SHALL be marked high risk in the catalog
- **THEN** doctor SHALL include a warning explaining the risk category

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

### Requirement: Sensitive agent output is confined and permissioned
Agent-generated files containing expanded credentials or private state SHALL be written only to declared user-level targets, SHALL use permissions no wider than `0600` for files and `0700` for parent directories, and SHALL never be written to repository templates or reports.

#### Scenario: Target requires literal credential
- **WHEN** a deployment must materialize a credential in a HOME config
- **THEN** secret resolution SHALL occur only during apply after plan approval
- **THEN** the target and any permitted backup SHALL use sensitive permissions
- **THEN** logs SHALL include only the secret variable name

### Requirement: Agent-managed paths reject symlink traversal
Agent sync SHALL validate target roots and every managed parent/leaf path without following symbolic links. An unexpected symlink SHALL be reported as a conflict before any managed file is written.

#### Scenario: Skill sidecar target is a symlink
- **WHEN** a destination sidecar or its parent resolves through a symlink
- **THEN** sync SHALL fail or mark the action conflict
- **THEN** the symlink target SHALL remain unchanged
