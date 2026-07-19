#!/usr/bin/env bash
# 执行 planner 机器可读计划（统一 runner + 结果协议）
# 用法: run_plan.sh [--yes] [--dry-run] [--json] --plan-file <path>
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DOTFILES_ROOT="$ROOT"

# shellcheck source=/dev/null
source "$ROOT/scripts/lib/runner.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/lib/report.sh"

ASSUME_YES=0
DRY_RUN=0
JSON_OUT=0
PLAN_FILE=""
CONFIG_EXTRA=()
DOCTOR_EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
  --yes) ASSUME_YES=1 ;;
  --dry-run) DRY_RUN=1 ;;
  --json) JSON_OUT=1 ;;
  --plan-file)
    shift
    PLAN_FILE="${1:-}"
    ;;
  --config-extra)
    shift
    CONFIG_EXTRA+=("$1")
    ;;
  --doctor-extra)
    shift
    DOCTOR_EXTRA+=("$1")
    ;;
  -h | --help)
    echo "用法: run_plan.sh [--yes] [--dry-run] [--json] --plan-file <path>"
    exit 0
    ;;
  *)
    echo "run_plan: 未知选项 $1" >&2
    exit 2
    ;;
  esac
  shift
done

if [ -z "$PLAN_FILE" ] || [ ! -f "$PLAN_FILE" ]; then
  echo "错误: 需要有效的 --plan-file" >&2
  exit 2
fi

confirm() {
  local prompt="$1"
  local reply
  if [ "$ASSUME_YES" -eq 1 ]; then
    return 0
  fi
  if [ ! -r /dev/tty ]; then
    echo "错误: 非 TTY 环境请使用 --yes 或 --dry-run" >&2
    return 1
  fi
  printf '%s [y/N]: ' "$prompt" >/dev/tty
  read -r reply </dev/tty || true
  [[ "$reply" =~ ^[Yy]$ ]]
}

ACTIONS=()
ERRORS=()
OS_ID=""
PROFILE=""
STATUS=""

while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue
  kind="${line%%$'\t'*}"
  if [ "$kind" = "$line" ]; then
    rest=""
  else
    rest="${line#*$'\t'}"
  fi
  case "$kind" in
  PLAN_OK) STATUS=ok ;;
  PLAN_ERR) STATUS=err ;;
  OS) OS_ID="$rest" ;;
  PROFILE) PROFILE="$rest" ;;
  ERROR) ERRORS+=("$rest") ;;
  ACTION) ACTIONS+=("$rest") ;;
  esac
done <"$PLAN_FILE"

if [ "$STATUS" = "err" ] || [ ${#ERRORS[@]} -gt 0 ]; then
  echo "计划校验失败:" >&2
  for e in "${ERRORS[@]}"; do
    echo "  - $e" >&2
  done
  exit 1
fi

echo "执行计划  OS=${OS_ID}${PROFILE:+  profile=$PROFILE}"
echo "共 ${#ACTIONS[@]} 个动作"
echo ""
if [ ${#ACTIONS[@]} -eq 0 ]; then
  echo "（空计划）"
  exit 0
fi
# 按模块合并展示：同一模块的 install/config 等合并到 ACTION 列（Bash 3.2 兼容）
printf '%-4s %-16s %-16s %s\n' "#" "ACTION" "MODULE" "REASON"
echo "------------------------------------------------------------"
_seen_modules=$'\n'
for row in "${ACTIONS[@]}"; do
  IFS=$'\t' read -r a_idx action module reason <<<"$row"
  case "$_seen_modules" in
  *$'\n'"$module"$'\n'*) continue ;;
  esac
  _seen_modules="${_seen_modules}${module}"$'\n'
  merged_actions="$action"
  merged_reason="$reason"
  for other in "${ACTIONS[@]}"; do
    IFS=$'\t' read -r o_idx o_action o_module o_reason <<<"$other"
    [ "$o_module" = "$module" ] || continue
    [ "$o_idx" = "$a_idx" ] && [ "$o_action" = "$action" ] && continue
    merged_actions="${merged_actions},${o_action}"
    case ",${merged_reason}," in
    *",${o_reason},"*) ;;
    *) merged_reason="${merged_reason},${o_reason}" ;;
    esac
  done
  printf '%-4s %-16s %-16s %s\n' "$a_idx" "$merged_actions" "$module" "$merged_reason"
done
echo ""

if [ "$DRY_RUN" -eq 1 ]; then
  echo "dry-run: 不执行任何动作"
  exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
  if [ ! -r /dev/tty ]; then
    echo "错误: 非 TTY 环境请使用 --yes 或 --dry-run" >&2
    exit 1
  fi
  if ! confirm "按计划执行?"; then
    echo "已取消"
    exit 1
  fi
fi

FAILED=0
CHANGED=0
UNCHANGED=0
SKIPPED=0
FAILED_N=0
RESULT_LINES=()

# 向处理器传播非交互授权（模块内 confirm 应尊重）
if [ "$ASSUME_YES" -eq 1 ]; then
  export DOTF_YES=1
  export ASSUME_YES=1
fi
# 深度 doctor（L1）
if [ "${DOTF_DEEP:-0}" = "1" ]; then
  export DOTF_DEEP=1
fi

for row in "${ACTIONS[@]}"; do
  IFS=$'\t' read -r _a_idx action module reason <<<"$row"
  echo "→ $action $module ($reason)"

  extra=()
  case "$action" in
  config)
    if [ "$module" = "agents" ] && [ ${#CONFIG_EXTRA[@]} -gt 0 ]; then
      extra=("${CONFIG_EXTRA[@]}")
    fi
    ;;
  doctor)
    if [ "$module" = "agents" ] && [ ${#DOCTOR_EXTRA[@]} -gt 0 ]; then
      extra=("${DOCTOR_EXTRA[@]}")
    fi
    ;;
  install) ;;
  *)
    echo "未知动作: $action" >&2
    exit 1
    ;;
  esac

  out=$(mktemp)
  set +e
  if [ ${#extra[@]} -gt 0 ]; then
    runner_run_action "$action" "$module" "${extra[@]}" >"$out" 2>&1
    rc=$?
  else
    runner_run_action "$action" "$module" >"$out" 2>&1
    rc=$?
  fi
  set -e

  # 透传输出
  cat "$out"

  # 统计最后一条 RESULT
  rline=$(grep -E $'^RESULT\t' "$out" 2>/dev/null | tail -n 1 || true)
  if [ -n "$rline" ]; then
    RESULT_LINES+=("$rline")
    IFS=$'\t' read -r _t st _m _a _d _e _reason <<<"$rline"
    case "$st" in
    changed) CHANGED=$((CHANGED + 1)) ;;
    unchanged) UNCHANGED=$((UNCHANGED + 1)) ;;
    skipped) SKIPPED=$((SKIPPED + 1)) ;;
    failed) FAILED_N=$((FAILED_N + 1)) ;;
    esac
  fi
  rm -f "$out"

  if [ "$rc" -ne 0 ]; then
    FAILED=1
    echo "计划因失败中止" >&2
    break
  fi
done

echo ""
echo "汇总: changed=$CHANGED unchanged=$UNCHANGED skipped=$SKIPPED failed=$FAILED_N"

# 持久化最近执行报告（status 模式不写）
if [ "${DOTF_STATUS_MODE:-0}" != "1" ] && [ ${#RESULT_LINES[@]} -gt 0 ]; then
  saved=$(dotf_report_save "$OS_ID" "$PROFILE" "${RESULT_LINES[@]+"${RESULT_LINES[@]}"}" 2>/dev/null || true)
  if [ -n "${saved:-}" ]; then
    echo "报告已保存: $saved"
  fi
fi

if [ "$JSON_OUT" -eq 1 ]; then
  # 脱敏 JSON：仅模块/动作/状态/耗时/原因，不含环境变量或文件内容
  python3 - "$OS_ID" "$PROFILE" "$CHANGED" "$UNCHANGED" "$SKIPPED" "$FAILED_N" "${RESULT_LINES[@]+"${RESULT_LINES[@]}"}" <<'PY'
import json, sys
os_id, profile, c, u, s, f = sys.argv[1:7]
actions = []
for line in sys.argv[7:]:
    parts = line.split("\t")
    if len(parts) < 7 or parts[0] != "RESULT":
        continue
    reason = parts[6][:200]
    actions.append({
        "status": parts[1],
        "module": parts[2],
        "action": parts[3],
        "duration_ms": int(parts[4] or 0),
        "exit_code": int(parts[5] or 0),
        "reason": reason,
    })
print(json.dumps({
    "os": os_id,
    "profile": profile or None,
    "summary": {
        "changed": int(c),
        "unchanged": int(u),
        "skipped": int(s),
        "failed": int(f),
    },
    "actions": actions,
}, ensure_ascii=False, indent=2))
PY
fi

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi

echo "✓ 计划执行完成"
exit 0
