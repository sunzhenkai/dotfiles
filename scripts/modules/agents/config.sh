#!/usr/bin/env bash
# agents 聚合配置：先保留 registry 安全部署，再执行 skills/MCP 聚合 sync。
set -euo pipefail

# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

# agents 的 registry config 是锁文件快照；聚合 sync 是独立 managed runtime。
# 这里必须始终执行，不能因 registry 目标 unchanged 而短路。
registry_log="$(mktemp)"
if ! dotf_registry_config >"$registry_log" 2>&1; then
  cat "$registry_log"
  dotf_result_failed "agents registry config failed"
  exit 1
fi
cat "$registry_log"
registry_changed=0
if grep -q $'^RESULT\tchanged\t' "$registry_log"; then
  registry_changed=1
fi

sync_log="$(mktemp)"
if ! bash "$DOTFILES_ROOT/scripts/agents/sync.sh" "$@" >"$sync_log" 2>&1; then
  cat "$sync_log"
  dotf_result_failed "agents sync failed"
  exit 1
fi
cat "$sync_log"

if [ "$registry_changed" -eq 1 ] || grep -Eq '^  [+~-] |(^| )changed=[1-9]|: (changed|created|updated|deleted|pruned|chmod) →' "$sync_log"; then
  dotf_result_changed "agents registry config deployed and sync completed"
else
  dotf_result_unchanged "agents registry config and sync are current"
fi
rm -f "$registry_log" "$sync_log"
