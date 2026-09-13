# agents-doctor Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Agent environment doctor command
The system SHALL provide a doctor command for checking the installed and configured agent development environment.

#### Scenario: Doctor runs with defaults
- **WHEN** the user runs the agent environment doctor without extra flags
- **THEN** it SHALL check the selected default profile
- **THEN** it SHALL report grouped results for environment variables, tools, security, and agents synchronization

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

### Requirement: Doctor checks agents synchronization
The doctor command SHALL compare expected runtime bundle outputs with managed manifest ownership and actual target hashes. It SHALL distinguish `missing`, `changed`, `stale`, `unowned`, `conflict`, `malformed`, and permission or link-boundary errors instead of treating directory existence as synchronization.

#### Scenario: Agent skill output is stale
- **WHEN** an owned skill or sidecar remains installed after it was removed from expected runtime output
- **THEN** doctor SHALL report stale with the target path and expected remediation
- **THEN** it SHALL NOT print file contents

#### Scenario: Agent skill content changed locally
- **WHEN** an owned file differs from its prior managed hash and expected output
- **THEN** doctor SHALL report conflict
- **THEN** remediation SHALL NOT recommend silent overwrite

#### Scenario: Skills are in sync
- **WHEN** every expected runtime file matches its expected hash and no stale owned path remains
- **THEN** doctor SHALL report pass with managed item counts

#### Scenario: Agents sync script is missing or unavailable
- **WHEN** doctor cannot load the shared planner or manifest
- **THEN** doctor SHALL report warn or fail according to whether expected state can be determined
- **THEN** unrelated environment checks SHALL continue

### Requirement: Doctor supports machine-readable output
The doctor command SHALL support a machine-readable output mode for automation.

#### Scenario: JSON output is requested
- **WHEN** the user requests JSON output
- **THEN** doctor SHALL emit valid JSON containing check groups, item statuses, messages, and exit status meaning
- **THEN** secret values SHALL remain redacted or omitted

### Requirement: Doctor treats malformed targets as failures
An existing target that cannot be parsed according to its declared format SHALL be reported as malformed and SHALL NOT be treated as missing or skipped.

#### Scenario: Declared JSON target is malformed
- **WHEN** a declared JSON target exists but contains invalid JSON
- **THEN** doctor SHALL report fail with the target path and parse category
- **THEN** it SHALL preserve and omit the file content from output

### Requirement: Doctor audits state and link boundaries
Doctor SHALL detect repository-pointing directory links for writable or sensitive modules, unexpected symlinks inside managed targets, insecure sensitive permissions, expired sensitive backups, and private artifacts under repository-managed paths.

#### Scenario: Writable config root links to repository
- **WHEN** a writable module target is a directory symlink into dotfiles
- **THEN** doctor SHALL report fail and recommend the module migration command

#### Scenario: Allowed read-only file link
- **WHEN** a target is a correct symlink explicitly allowed by registry metadata
- **THEN** doctor SHALL report pass or unchanged

#### Scenario: Sensitive target permissions are broad
- **WHEN** a sensitive config is readable by group or others
- **THEN** doctor SHALL report fail without reading or printing its value
