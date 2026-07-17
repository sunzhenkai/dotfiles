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
- **THEN** enabled MCP servers SHALL be written or merged into the `mcp` section of `opencode/opencode.json`
- **THEN** the generated configuration SHALL use OpenCode-compatible remote or local server syntax

#### Scenario: Codex MCP configuration is unsupported
- **WHEN** sync runs for `codex` and the current Codex configuration format lacks stable MCP support
- **THEN** sync SHALL skip MCP generation for Codex
- **THEN** doctor SHALL report MCP support for Codex as unsupported or skipped rather than failed

### Requirement: MCP sync is idempotent and scoped
The system SHALL update only MCP server ids managed by `agents/env` and SHALL preserve unrelated user or tool-managed configuration where possible.

#### Scenario: Repeated sync has no changes
- **WHEN** sync runs twice with the same shared MCP source and selected profile
- **THEN** the second run SHALL succeed
- **THEN** managed MCP output SHALL remain equivalent after both runs

#### Scenario: Existing unmanaged MCP server is present
- **WHEN** a target configuration contains an MCP server id not declared by `agents/env`
- **THEN** sync SHALL preserve that unmanaged server unless the target tool requires full file replacement
- **THEN** any full replacement SHALL first create a backup

#### Scenario: Managed server changes
- **WHEN** a managed MCP server declaration changes
- **THEN** sync SHALL update that server in target tool configuration
- **THEN** unchanged unmanaged configuration SHALL remain intact where the target format allows merging

### Requirement: MCP output validation
The system SHALL validate generated MCP configuration before declaring sync successful.

#### Scenario: Placeholder remains unresolved
- **WHEN** generated MCP output contains an unresolved template placeholder
- **THEN** sync SHALL fail with a clear error
- **THEN** target configuration SHALL NOT be silently left in a partially generated state

#### Scenario: Generated JSON is invalid
- **WHEN** an adapter generates JSON configuration
- **THEN** sync SHALL parse the generated JSON before writing or after writing atomically
- **THEN** invalid JSON SHALL cause sync to fail

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

