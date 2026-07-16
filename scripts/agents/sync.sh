#!/usr/bin/env bash
# 将 agents/ 下共享 skills/commands 适配并安装到各工具。
# 用法: sync.sh [claude|cursor|opencode|codex|all] [--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 是 agents sync 所必需的" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/sync.py" --root "$ROOT" "$@"
