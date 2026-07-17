# agent-env-browser Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Browser automation capability is explicit
The system SHALL provide browser automation as an explicit high-risk agent environment capability, separate from low-risk web search and web reader MCP servers.

#### Scenario: Default environment is installed
- **WHEN** a user installs the default agent environment
- **THEN** browser automation MCP servers SHALL NOT be enabled by default
- **THEN** low-risk web search or web reader MCP servers MAY be enabled by the selected default profile

#### Scenario: Browser profile is selected
- **WHEN** a user selects a profile that includes browser automation
- **THEN** sync SHALL install browser automation MCP configuration for compatible tools
- **THEN** doctor SHALL run browser-specific dependency and security checks

### Requirement: Browser automation uses isolated state by default
The system SHALL configure browser automation to use isolated browser state by default rather than the user's primary browser profile.

#### Scenario: Browser MCP starts with default settings
- **WHEN** browser automation runs without a local override
- **THEN** it SHALL use an isolated browser context or profile
- **THEN** it SHALL NOT read cookies, sessions, or extensions from the user's primary browser profile

#### Scenario: User opts into real browser profile
- **WHEN** a local override requests a real browser profile or Chrome DevTools connection
- **THEN** doctor SHALL mark the configuration as high risk
- **THEN** the repository-managed config SHALL NOT store the private profile path unless it is in a gitignored local override

### Requirement: Browser provider strategy is documented
The system SHALL document the selected default browser automation provider and any optional providers, including their dependencies, launch mode, supported tools, and risks.

#### Scenario: Playwright provider is selected
- **WHEN** Playwright-based browser automation is configured
- **THEN** the browser capability SHALL declare required Node/package/browser binary checks
- **THEN** doctor SHALL verify that the provider can be launched or provide a clear remediation hint

#### Scenario: Chrome DevTools provider is selected
- **WHEN** Chrome DevTools based automation is configured
- **THEN** the capability SHALL declare required browser executable and debugging endpoint checks
- **THEN** doctor SHALL warn that connecting to a real browser may expose authenticated pages and local browsing state

### Requirement: Browser configuration supports headless and headed modes
The system SHALL support both headless and headed browser automation modes through repository defaults and local overrides.

#### Scenario: Headless mode is configured
- **WHEN** the selected browser configuration uses headless mode
- **THEN** sync SHALL generate MCP configuration compatible with unattended agent runs
- **THEN** doctor SHALL check that a browser binary is available

#### Scenario: Headed mode is configured
- **WHEN** a local override enables headed mode for debugging
- **THEN** doctor SHALL check for a graphical environment when applicable
- **THEN** the local override SHALL remain private and gitignored

### Requirement: Browser artifacts and state are not committed
The system SHALL prevent browser-generated private state from being treated as repository-managed content.

#### Scenario: Browser state directory is created
- **WHEN** browser automation creates profiles, screenshots, traces, downloads, or temporary data
- **THEN** those paths SHALL be outside tracked source files or covered by ignore rules
- **THEN** doctor SHALL warn if known browser state paths appear unignored inside the repository

#### Scenario: Browser screenshots are needed for debugging
- **WHEN** browser automation produces screenshots or traces
- **THEN** the system MAY place them in a documented temporary or artifact directory
- **THEN** the user SHALL be warned not to commit screenshots containing private or internal information

### Requirement: Browser MCP health checks are available
The system SHALL provide health checks for browser automation readiness.

#### Scenario: Browser dependency is missing
- **WHEN** doctor checks browser automation and a required package or binary is missing
- **THEN** doctor SHALL report a failure
- **THEN** doctor SHALL provide the documented install or setup hint

#### Scenario: Browser MCP can launch
- **WHEN** doctor runs browser checks in deep mode
- **THEN** it SHALL attempt a minimal provider startup or equivalent validation
- **THEN** it SHALL report success only if the provider is usable for agent automation

