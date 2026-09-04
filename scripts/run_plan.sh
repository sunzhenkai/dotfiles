#!/usr/bin/env bash
# Validate and execute a versioned planner document (Bash 3.2 compatible).
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
CONTINUE_ON_ERROR=0
PLAN_FILE=""
CONFIG_EXTRA=()
DOCTOR_EXTRA=()

usage() {
  echo "用法: run_plan.sh [--yes] [--dry-run] [--json] [--continue-on-error] --plan-file <path>"
}

while [ $# -gt 0 ]; do
  case "$1" in
  --yes) ASSUME_YES=1 ;;
  --dry-run) DRY_RUN=1 ;;
  --json) JSON_OUT=1 ;;
  --continue-on-error) CONTINUE_ON_ERROR=1 ;;
  --plan-file)
    shift
    PLAN_FILE="${1:-}"
    ;;
  --config-extra)
    shift
    CONFIG_EXTRA+=("${1:-}")
    ;;
  --doctor-extra)
    shift
    DOCTOR_EXTRA+=("${1:-}")
    ;;
  -h | --help)
    usage
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

# The Python validator performs complete protocol/registry/handler/OS validation
# before this script can call runner_run_action (and therefore before handler load).
NORMALIZED="$(mktemp)"
RUN_ID=""
CURRENT_OUT=""
RUN_FINALIZED=0
JSON_FD=""

cleanup_run_plan() {
  rm -f "$NORMALIZED"
  [ -n "$CURRENT_OUT" ] && rm -f "$CURRENT_OUT"
  return 0
}

interrupt_run_plan() {
  local signal_code="$1"
  trap - INT TERM
  if [ -n "$RUN_ID" ] && [ "$RUN_FINALIZED" -eq 0 ]; then
    python3 "$ROOT/scripts/execution_state.py" interrupt --run-id "$RUN_ID" >/dev/null 2>&1 || true
    RUN_FINALIZED=1
  fi
  cleanup_run_plan
  exit "$signal_code"
}

trap cleanup_run_plan EXIT
trap 'interrupt_run_plan 130' INT
trap 'interrupt_run_plan 143' TERM

# In JSON mode stdout is exclusively the final bounded machine document.
if [ "$JSON_OUT" -eq 1 ]; then
  exec 4>&1
  # shellcheck disable=SC2034  # descriptor number documents the JSON output channel
  JSON_FD=4
  exec 1>&2
fi
validate_args=(validate --plan "$PLAN_FILE" --emit-tsv)
[ "$DRY_RUN" -eq 1 ] && validate_args+=(--dry-run)
set +e
python3 "$ROOT/scripts/plan_protocol.py" "${validate_args[@]}" >"$NORMALIZED"
validate_rc=$?
set -e
if [ "$validate_rc" -ne 0 ]; then
  exit "$validate_rc"
fi

ACTIONS=()
DEPENDENCIES=()
OS_ID=""
PROFILE=""
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue
  kind="${line%%$'\t'*}"
  rest="${line#*$'\t'}"
  case "$kind" in
  META)
    IFS=$'\t' read -r OS_ID PROFILE <<<"$rest"
    ;;
  ACTION) ACTIONS+=("$rest") ;;
  DEPENDENCIES) DEPENDENCIES+=("$rest") ;;
  *)
    echo "错误: validator 输出未知记录: $kind" >&2
    exit 2
    ;;
  esac
done <"$NORMALIZED"

if [ -z "$OS_ID" ]; then
  echo "错误: validator 未输出 planned OS" >&2
  exit 2
fi

echo "执行计划  OS=${OS_ID}${PROFILE:+  profile=$PROFILE}"
echo "共 ${#ACTIONS[@]} 个动作"
echo ""
if [ ${#ACTIONS[@]} -eq 0 ]; then
  echo "（空计划）"
  exit 0
fi
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

is_tty_available() {
  if ! exec 3</dev/tty 2>/dev/null; then return 1; fi
  exec 3<&-
  if ! exec 3>/dev/tty 2>/dev/null; then return 1; fi
  exec 3>&-
  return 0
}

confirm() {
  local prompt="$1"
  local reply=""
  [ "$ASSUME_YES" -eq 1 ] && return 0
  if ! is_tty_available; then
    echo "错误: 非 TTY 环境请使用 --yes 或 --dry-run" >&2
    return 1
  fi
  printf '%s [y/N]: ' "$prompt" >/dev/tty
  read -r reply </dev/tty || reply=""
  [[ "$reply" =~ ^[Yy]$ ]]
}

if [ "$ASSUME_YES" -ne 1 ]; then
  if ! is_tty_available; then
    echo "错误: 非 TTY 环境请使用 --yes 或 --dry-run" >&2
    exit 1
  fi
  if ! confirm "按计划执行?"; then
    echo "已取消"
    exit 1
  fi
fi

# Planned OS is fixed for the whole execution. Because handlers are sourced in
# subshells of this shell, readonly is inherited and a handler cannot reassign it.
DOTF_OS="$OS_ID"
export DOTF_OS
readonly DOTF_OS
if [ "$ASSUME_YES" -eq 1 ]; then
  export DOTF_YES=1
  export ASSUME_YES=1
fi
[ "${DOTF_DEEP:-0}" = "1" ] && export DOTF_DEEP=1

# This is the first state-changing execution step and occurs before any handler.
if [ "${DOTF_STATUS_MODE:-0}" != "1" ]; then
  state_info="$(python3 "$ROOT/scripts/execution_state.py" create --plan "$PLAN_FILE")" || exit $?
  RUN_ID="${state_info%%$'\t'*}"
  RUN_JOURNAL="${state_info#*$'\t'}"
  if [ -z "$RUN_ID" ] || [ "$RUN_JOURNAL" = "$state_info" ]; then
    echo "错误: 无法创建执行 journal" >&2
    exit 2
  fi
fi

FAILED=0
CHANGED=0
UNCHANGED=0
SKIPPED=0
FAILED_N=0
BLOCKED=0
NOT_RUN=0
RESULT_LINES=()
FAILED_ITEMS=()
FAILED_MODULES=()

add_failed_module() {
  local wanted="$1"
  local value
  for value in "${FAILED_MODULES[@]+"${FAILED_MODULES[@]}"}"; do
    [ "$value" = "$wanted" ] && return 0
  done
  FAILED_MODULES+=("$wanted")
}

state_finish_action() {
  local index="$1" state="$2" result_status="$3" duration="$4" exit_code="$5" reason="$6"
  [ -z "$RUN_ID" ] && return 0
  local payload
  payload="$(python3 - "$result_status" "$duration" "$exit_code" "$reason" <<'PY'
import json, sys
print(json.dumps({
    "result_status": sys.argv[1],
    "duration_ms": int(sys.argv[2]),
    "exit_code": int(sys.argv[3]),
    "reason": sys.argv[4],
}, ensure_ascii=False))
PY
)"
  printf '%s\n' "$payload" | python3 "$ROOT/scripts/execution_state.py" action-finish \
    --run-id "$RUN_ID" --index "$index" --status "$state"
}

record_scheduled_state() {
  local state="$1" index="$2" module="$3" action="$4" reason="$5"
  local line
  line=$(printf 'RESULT\t%s\t%s\t%s\t0\t0\t%s' "$state" "$module" "$action" "$reason")
  RESULT_LINES+=("$line")
  printf '%s\n' "$line"
  state_finish_action "$index" "$state" "$state" 0 0 "$reason"
  case "$state" in
  blocked) BLOCKED=$((BLOCKED + 1)) ;;
  not-run) NOT_RUN=$((NOT_RUN + 1)) ;;
  esac
}

blocked_reason() {
  local module="$1" failed row planned dependencies dependency
  for failed in "${FAILED_MODULES[@]+"${FAILED_MODULES[@]}"}"; do
    if [ "$module" = "$failed" ]; then
      printf '%s\n' "same-module-failed"
      return 0
    fi
  done
  for row in "${DEPENDENCIES[@]+"${DEPENDENCIES[@]}"}"; do
    IFS=$'\t' read -r planned dependencies <<<"$row"
    [ "$planned" = "$module" ] || continue
    IFS=',' read -r -a dependency_list <<<"$dependencies"
    for dependency in "${dependency_list[@]+"${dependency_list[@]}"}"; do
      for failed in "${FAILED_MODULES[@]+"${FAILED_MODULES[@]}"}"; do
        if [ "$dependency" = "$failed" ]; then
          printf '%s\n' "dependency-failed"
          return 0
        fi
      done
    done
    return 1
  done
  echo "错误: 已验证计划缺少模块依赖元数据: $module" >&2
  return 2
}

for action_pos in "${!ACTIONS[@]}"; do
  row="${ACTIONS[$action_pos]}"
  IFS=$'\t' read -r _a_idx action module reason <<<"$row"

  if [ ${#FAILED_MODULES[@]} -gt 0 ]; then
    set +e
    why="$(blocked_reason "$module")"
    blocked_rc=$?
    set -e
    if [ "$blocked_rc" -eq 0 ]; then
      record_scheduled_state blocked "$_a_idx" "$module" "$action" "$why"
      continue
    elif [ "$blocked_rc" -ne 1 ]; then
      echo "错误: 依赖调度校验失败" >&2
      exit "$blocked_rc"
    fi
  fi

  if [ -n "$RUN_ID" ]; then
    python3 "$ROOT/scripts/execution_state.py" action-start --run-id "$RUN_ID" --index "$_a_idx"
  fi
  echo "→ $action $module ($reason)"
  extra=()
  case "$action" in
  config)
    if [ ${#CONFIG_EXTRA[@]} -gt 0 ]; then
      case "$module" in
      agents) extra=("${CONFIG_EXTRA[@]}") ;;
      codex)
        skip_val=0
        for x in "${CONFIG_EXTRA[@]}"; do
          if [ "$skip_val" -eq 1 ]; then extra+=("$x"); skip_val=0; continue; fi
          case "$x" in --codex-profile | -f) extra+=("$x"); skip_val=1 ;; esac
        done
        ;;
      opencode)
        skip_val=0
        for x in "${CONFIG_EXTRA[@]}"; do
          if [ "$skip_val" -eq 1 ]; then
            extra+=("$x")
            skip_val=0
            continue
          fi
          case "$x" in
          --opencode-profile | -f)
            extra+=("$x")
            skip_val=1
            ;;
          esac
        done
        ;;
      esac
    fi
    ;;
  doctor)
    [ "$module" = "agents" ] && [ ${#DOCTOR_EXTRA[@]} -gt 0 ] && extra=("${DOCTOR_EXTRA[@]}")
    ;;
  install) ;;
  *) echo "未知动作: $action" >&2; exit 2 ;;
  esac

  out="$(mktemp)"
  chmod 600 "$out"
  CURRENT_OUT="$out"
  set +e
  if [ ${#extra[@]} -gt 0 ]; then
    runner_run_action "$action" "$module" "${extra[@]}" >"$out" 2>&1
  else
    runner_run_action "$action" "$module" >"$out" 2>&1
  fi
  rc=$?
  set -e
  python3 "$ROOT/scripts/execution_state.py" sanitize-file "$out"

  rline=$(grep -E $'^RESULT\t' "$out" 2>/dev/null | tail -n 1 || true)
  st="failed"
  _d=0
  _e="$rc"
  _reason="handler failed"
  if [ -n "$rline" ]; then
    RESULT_LINES+=("$rline")
    IFS=$'\t' read -r _t st _m _a _d _e _reason <<<"$rline"
    case "$st" in
    changed) CHANGED=$((CHANGED + 1)) ;;
    unchanged) UNCHANGED=$((UNCHANGED + 1)) ;;
    skipped) SKIPPED=$((SKIPPED + 1)) ;;
    failed) FAILED_N=$((FAILED_N + 1)) ;;
    esac
    [ "$st" = "failed" ] && FAILED_ITEMS+=("$module/$action: handler-failed")
  elif [ "$rc" -ne 0 ]; then
    FAILED_N=$((FAILED_N + 1))
    FAILED_ITEMS+=("$module/$action: handler-failed")
  else
    st="changed"
    _e=0
    _reason="ok"
    CHANGED=$((CHANGED + 1))
  fi
  if [ "$rc" -ne 0 ] || [ "$st" = "failed" ]; then
    state_finish_action "$_a_idx" failed failed "${_d:-0}" "${_e:-$rc}" "${_reason:-handler failed}"
  else
    state_finish_action "$_a_idx" completed "$st" "${_d:-0}" "${_e:-0}" "${_reason:-$st}"
  fi
  rm -f "$out"
  CURRENT_OUT=""

  if [ "$rc" -ne 0 ]; then
    FAILED=1
    add_failed_module "$module"
    if [ "$CONTINUE_ON_ERROR" -eq 1 ]; then
      echo "动作失败；仅继续调度依赖无关动作: $module/$action" >&2
      continue
    fi

    # Default fail-fast: classify every remaining action without loading it.
    next_pos=$((action_pos + 1))
    while [ "$next_pos" -lt ${#ACTIONS[@]} ]; do
      pending="${ACTIONS[$next_pos]}"
      IFS=$'\t' read -r _p_idx p_action p_module _p_reason <<<"$pending"
      set +e
      why="$(blocked_reason "$p_module")"
      blocked_rc=$?
      set -e
      if [ "$blocked_rc" -eq 0 ]; then
        record_scheduled_state blocked "$_p_idx" "$p_module" "$p_action" "$why"
      elif [ "$blocked_rc" -eq 1 ]; then
        record_scheduled_state not-run "$_p_idx" "$p_module" "$p_action" "fail-fast"
      else
        echo "错误: 依赖调度校验失败" >&2
        exit "$blocked_rc"
      fi
      next_pos=$((next_pos + 1))
    done
    break
  fi
done

echo ""
echo "汇总: changed=$CHANGED unchanged=$UNCHANGED skipped=$SKIPPED failed=$FAILED_N blocked=$BLOCKED not-run=$NOT_RUN"
if [ ${#FAILED_ITEMS[@]} -gt 0 ]; then
  echo "错误项目:"
  for item in "${FAILED_ITEMS[@]}"; do echo "  - $item"; done
fi

if [ -n "$RUN_ID" ]; then
  final_status="completed"
  [ "$FAILED" -ne 0 ] && final_status="failed"
  final_info="$(python3 "$ROOT/scripts/execution_state.py" finalize --run-id "$RUN_ID" --status "$final_status")" || exit $?
  RUN_FINALIZED=1
  saved="${final_info#*$'\t'}"
  [ -n "${saved:-}" ] && echo "报告已保存: $saved"
fi

if [ "$JSON_OUT" -eq 1 ]; then
  if [ -n "$RUN_ID" ]; then
    python3 "$ROOT/scripts/execution_state.py" emit-json --run-id "$RUN_ID" >&4
  else
    python3 - "$ROOT" "$OS_ID" "$PROFILE" "$CHANGED" "$UNCHANGED" "$SKIPPED" "$FAILED_N" "$BLOCKED" "$NOT_RUN" "${RESULT_LINES[@]}" <<'PY' >&4
import json, sys
sys.path.insert(0, sys.argv[1] + "/scripts")
from dotf_core.sanitize import sanitize_for_json
os_id, profile, c, u, s, f, b, n = sys.argv[2:10]
actions = []
for line in sys.argv[10:]:
    parts = line.split("\t")
    if len(parts) < 7 or parts[0] != "RESULT":
        continue
    actions.append({
        "status": parts[1], "module": parts[2], "action": parts[3],
        "duration_ms": int(parts[4] or 0), "exit_code": int(parts[5] or 0),
        "reason_code": parts[1], "message": parts[6][:200],
    })
payload = {
    "os": os_id,
    "profile": profile or None,
    "summary": {"changed": int(c), "unchanged": int(u), "skipped": int(s),
                "failed": int(f), "blocked": int(b), "not_run": int(n)},
    "actions": actions,
}
print(json.dumps(sanitize_for_json(payload), ensure_ascii=False, sort_keys=True, indent=2))
PY
  fi
fi

[ "$FAILED" -ne 0 ] && exit 1
echo "✓ 计划执行完成"
exit 0
