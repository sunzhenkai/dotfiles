#!/usr/bin/env bash
# Linux smoke：注册表校验 + CLI 帮助/拒绝路径（不修改真实 HOME）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TMP_HOME="$(mktemp -d)"
cleanup() { rm -rf "$TMP_HOME"; }
trap cleanup EXIT

export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_STATE_HOME="$TMP_HOME/.local/state"
export XDG_CACHE_HOME="$TMP_HOME/.cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

echo "==> modules.py validate"
python3 scripts/modules.py validate

echo "==> bootstrap --check-only"
bash scripts/bootstrap.sh --check-only >/dev/null

echo "==> dotf -h"
bin/dotf -h >/dev/null

echo "==> dotf init --list"
bin/dotf init --list >/dev/null

echo "==> reject legacy / bypass"
if bin/dotf -i sdk >/dev/null 2>&1; then
  echo "expected legacy syntax to fail" >&2
  exit 1
fi
if bin/dotf agents -c --doctor >/dev/null 2>&1; then
  echo "expected old --doctor bypass to fail" >&2
  exit 1
fi

echo "✓ Linux smoke passed (HOME=$HOME)"
