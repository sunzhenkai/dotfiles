#!/usr/bin/env bash
# macOS / Bash 3.2 基础 CLI 兼容：语法检查 + 帮助可运行
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASH_BIN="${BASH_BIN:-/bin/bash}"
if [ ! -x "$BASH_BIN" ]; then
  echo "错误: 找不到 bash: $BASH_BIN" >&2
  exit 1
fi

echo "==> bash version ($BASH_BIN)"
"$BASH_BIN" --version | head -1

# 语法检查主入口与关键 shell 封装（避免 bash 4+ 特性）
echo "==> bash -n syntax"
"$BASH_BIN" -n bin/dotf
"$BASH_BIN" -n scripts/modules.sh
"$BASH_BIN" -n scripts/doctor.sh
"$BASH_BIN" -n scripts/bootstrap.sh
"$BASH_BIN" -n scripts/run_plan.sh
"$BASH_BIN" -n scripts/lib/result.sh
"$BASH_BIN" -n scripts/lib/runner.sh
"$BASH_BIN" -n scripts/lib/compat_adapter.sh
"$BASH_BIN" -n scripts/lib/config_safe.sh
"$BASH_BIN" -n scripts/lib/handler_common.sh
"$BASH_BIN" -n scripts/lib/doctor_l0.sh
"$BASH_BIN" -n scripts/lib/doctor_run.sh
"$BASH_BIN" -n scripts/ci/smoke-linux.sh
"$BASH_BIN" -n scripts/ci/bash32-check.sh

TMP_HOME="$(mktemp -d)"
cleanup() { rm -rf "$TMP_HOME"; }
trap cleanup EXIT
export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_STATE_HOME="$TMP_HOME/.local/state"
export XDG_CACHE_HOME="$TMP_HOME/.cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

echo "==> run help under $BASH_BIN"
"$BASH_BIN" bin/dotf -h >/dev/null

# 若为 bash 3.x，额外标注
ver="$("$BASH_BIN" -c 'echo "${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"')"
echo "✓ Bash compatibility check passed (version $ver)"
