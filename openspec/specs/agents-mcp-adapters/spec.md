# agents-mcp-adapters Specification

## Purpose
TBD - created by archiving change agent-env. Update Purpose after archive.
## Requirements
### Requirement: Shared MCP server declarations
The system SHALL provide a shared MCP server declaration format that captures server id, transport, command or URL, authentication reference, enabled tools, profile membership, and risk level.

#### Scenario: Remote HTTP MCP server is declared
- **WHEN** a remote MCP server is declared in the shared source
- **THEN** the declaration SHALL include a stable server id, remote URL, transport type, and environment-variable-based authentication reference when authentication is required
- **THEN** the declaration MUST NOT inline secret values

#### Scenario: Local process MCP server is declared
- **WHEN** a local process MCP server is declared in the shared source
- **THEN** the declaration SHALL include the command, arguments, required runtime dependencies, and supported tools
- **THEN** doctor SHALL be able to check whether the command can be launched

### Requirement: MCP adapters generate target tool configuration
The system SHALL adapt shared MCP declarations into the configuration format used by each supported target tool.

#### Scenario: Cursor MCP configuration is generated
- **WHEN** sync runs for `cursor`
- **THEN** enabled MCP servers SHALL be written or merged into `~/.cursor/mcp.json`
- **THEN** Cursor-specific transport names and environment placeholder syntax SHALL be used

#### Scenario: Claude MCP configuration is generated
- **WHEN** sync runs for `claude`
- **THEN** enabled MCP servers SHALL be written to `~/.claude/.mcp.json`
- **THEN** enabled MCP servers SHALL be merged into `~/.claude.json` when that state file is usable

#### Scenario: OpenCode MCP configuration is generated
- **WHEN** sync runs for `opencode`
- **THEN** enabled MCP servers SHALL be written or merged into the `mcp` section of `~/.config/opencode/opencode.json`
- **THEN** the generated configuration SHALL use OpenCode-compatible remote or local server syntax

#### Scenario: Kimi Code stdio env maps placeholders from process environment
- **WHEN** sync generates MCP configuration for `kimi-code` with a stdio server whose `env` values contain `${VAR}` placeholders
- **THEN** the generated entry SHALL launch via `sh -c` so that `ZHIPU_API_KEY` is read from the Kimi process environment at spawn time and exported as `Z_AI_API_KEY`
- **THEN** the generated configuration MUST NOT put an unexpanded `${ZHIPU_API_KEY}` into stdio `env`
- **THEN** HTTP servers SHALL continue to use `bearerTokenEnvVar` rather than header placeholders

#### Scenario: ZCode MCP configuration expands secrets locally
- **WHEN** sync runs for `zcode`
- **THEN** enabled MCP servers SHALL be merged into `~/.zcode/cli/config.json` under `mcp.servers`
- **THEN** HTTP `Authorization` and stdio `env` placeholders such as `${ZHIPU_API_KEY}` SHALL be expanded from the process environment or `senv` into that home config
- **THEN** sync SHALL warn that secret values are written only to user-level private state
- **THEN** repository templates SHALL retain placeholders and MUST NOT contain expanded secret values
- **WHEN** `ZHIPU_API_KEY` is missing
- **THEN** sync SHALL fail before writing a ZCode config that still contains the unresolved placeholder

#### Scenario: Codex MCP configuration is unsupported
- **WHEN** sync runs for `codex` and the current Codex configuration format lacks stable MCP support
- **THEN** sync SHALL skip MCP generation for Codex
- **THEN** doctor SHALL report MCP support for Codex as unsupported or skipped rather than failed

### Requirement: MCP sync is idempotent and scoped
The system SHALL compile selected shared declarations and current target state into an immutable sync plan before apply. Apply SHALL update only owned managed server ids, preserve unrelated configuration, reconcile stale owned entries, and record expected and installed hashes. Equivalent output SHALL return unchanged without backup or replacement.

#### Scenario: Repeated sync has no changes
- **WHEN** sync runs twice with the same source, profile, local overlay, and target state
- **THEN** the second plan SHALL contain no update actions
- **THEN** apply SHALL NOT create backups or replace files

#### Scenario: Existing unmanaged MCP server is present
- **WHEN** a target contains an MCP id not owned by the managed manifest
- **THEN** plan and apply SHALL preserve it
- **THEN** the id SHALL be reported as unowned rather than stale

#### Scenario: Managed server is removed
- **WHEN** an owned server is absent from the new expected set and the installed value still matches the prior managed hash
- **THEN** plan SHALL mark it prune
- **THEN** apply SHALL remove only that owned entry

#### Scenario: Managed server changes
- **WHEN** an owned managed server declaration or expected rendering changes
- **THEN** plan SHALL mark only that managed entry for update
- **THEN** unchanged unmanaged configuration SHALL remain intact

#### Scenario: Managed server was edited locally
- **WHEN** an owned target differs from both expected output and prior managed hash
- **THEN** plan SHALL mark conflict
- **THEN** default apply SHALL leave it unchanged

### Requirement: MCP output validation
The system SHALL render, parse, permission-check, and stage all selected target outputs before committing any target. A multi-target apply SHALL use a transaction journal and SHALL either commit all planned targets or roll back targets already committed in that run.

#### Scenario: Placeholder remains unresolved
- **WHEN** staged output contains a placeholder that the target format cannot safely resolve at runtime
- **THEN** apply SHALL fail before changing any selected target
- **THEN** the error SHALL identify the variable name without its value

#### Scenario: Generated JSON is invalid
- **WHEN** staged JSON, YAML, or TOML output is invalid
- **THEN** apply SHALL fail and preserve all original targets

#### Scenario: Later target commit fails
- **WHEN** one target fails after an earlier target was committed in the same run
- **THEN** the system SHALL use the journal to restore earlier targets
- **THEN** the run SHALL end failed rather than partially successful

### Requirement: MCP profiles select active servers
The system SHALL choose active MCP servers from the selected profile and per-tool compatibility rules.

#### Scenario: Research profile is selected
- **WHEN** the selected profile includes web search and web reader MCP servers
- **THEN** sync SHALL install those servers for tools that support them
- **THEN** doctor SHALL check the required environment variables for those servers

#### Scenario: Browser profile is not selected
- **WHEN** the selected profile excludes browser automation
- **THEN** browser MCP servers SHALL NOT be installed for any target tool
- **THEN** doctor SHALL not require browser automation dependencies for that profile

### Requirement: Browser stdio MCP servers are rendered per target tool
The system SHALL render browser automation stdio MCP servers into each compatible target tool format using the shared `agents/env` declaration.

#### Scenario: Cursor or Claude browser MCP is generated
- **WHEN** sync generates MCP configuration for `cursor` or `claude` with the browser profile
- **THEN** the browser MCP server SHALL be rendered with `command` and `args`
- **THEN** the generated args SHALL include headless mode and an isolated user data directory unless a local override changes those settings

#### Scenario: OpenCode browser MCP is generated
- **WHEN** sync generates MCP configuration for `opencode` with the browser profile
- **THEN** the browser MCP server SHALL be rendered as a local command entry
- **THEN** the command array SHALL include the shared command and generated arguments

#### Scenario: Kimi Code browser MCP is generated
- **WHEN** sync generates MCP configuration for `kimi-code` with the browser profile
- **THEN** the browser MCP server SHALL be rendered as a stdio command with args
- **THEN** HTTP-only authentication placeholder handling SHALL NOT be applied to the stdio browser server

### Requirement: Browser MCP follows profile selection
The system SHALL omit browser automation from the default low-risk profile and include it only when the resolved profile explicitly enables browser capabilities and the selected tool is compatible.

#### Scenario: Default agents config sync includes browser MCP
- **WHEN** sync runs without an explicit high-risk profile or local consent
- **THEN** browser automation MCP servers SHALL NOT appear in expected output

#### Scenario: Research profile is synced
- **WHEN** sync runs with the research profile
- **THEN** browser automation MCP servers SHALL NOT be included

#### Scenario: Browser profile is synced
- **WHEN** sync runs with an explicitly selected browser profile for a compatible tool
- **THEN** the plan SHALL mark the capability high risk
- **THEN** apply MAY include the browser MCP server without embedding private browser state in repository files

#### Scenario: Browser MCP drift is detected
- **WHEN** doctor compares a selected browser profile target with expected output
- **THEN** missing, changed, stale, or conflicting owned entries SHALL be reported
- **THEN** remediation SHALL identify the scoped sync command

### Requirement: MCP planning is side-effect free
The system SHALL provide a machine-readable MCP/Agent sync plan that performs no network access, secret value lookup, backup, HOME write, or repository write. The plan SHALL list required secret names, risk, ownership, target paths, expected hashes, current state, and proposed actions.

#### Scenario: Dry-run without secrets
- **WHEN** a selected target will require a literal secret during apply but the secret is absent during plan
- **THEN** plan SHALL still succeed and list the required variable name
- **THEN** no placeholder-expanded value SHALL be produced

### Requirement: Runtime sync does not write repository templates
Normal user sync/apply SHALL modify only declared user-level targets and state directories. Repository template generation SHALL be a separate deterministic command that ignores local overlays and secret values.

#### Scenario: Normal sync uses local override
- **WHEN** runtime sync applies a machine-specific local override
- **THEN** no file under the dotfiles repository SHALL change

#### Scenario: Repository templates are verified
- **WHEN** maintainers run the explicit template generation command
- **THEN** output SHALL be derived only from committed safe sources
- **THEN** CI SHALL be able to verify that regeneration leaves no diff
