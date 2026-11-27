#!/usr/bin/env bash
# 统一 agents sync：委托给 src/agents/sync_all.py 单进程执行。
# 诊断请用: dotf agents -d  或  PYTHONPATH=src python3 src/agents/doctor.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${DOTFILES_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 是 agents sync 所必需的" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/src:$ROOT/src/agents${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT/src/agents/sync_all.py" --root "$ROOT" "$@"
