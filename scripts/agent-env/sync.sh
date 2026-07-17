#!/usr/bin/env bash
# 兼容入口：委托统一 agents sync（仅 MCP/env）。
# 用法: sync.sh [claude|cursor|opencode|codex|kimi-code|all] [--profile NAME] [--dry-run]
#
# 注意：请优先使用 scripts/agents/sync.sh（或 dotf -c agents）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "提示: scripts/agent-env/sync.sh 为兼容层，请改用: scripts/agents/sync.sh --env-only" >&2
exec "$ROOT/scripts/agents/sync.sh" --env-only "$@"
