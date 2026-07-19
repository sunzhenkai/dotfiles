#!/usr/bin/env bash
# 统一 doctor：L0 + 可选 L1（--deep），映射到结果协议
# 用法: dotf_doctor_run <module> [--deep] [extra...]

# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/doctor_l0.sh"
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/result.sh"
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config_safe.sh"

dotf_doctor_handlers_dir() {
  if [ -n "${DOTF_HANDLERS_DIR:-}" ]; then
    printf '%s\n' "$DOTF_HANDLERS_DIR"
  else
    printf '%s\n' "${DOTFILES_ROOT}/scripts/modules"
  fi
}

dotf_doctor_run() {
  local mod="$1"
  shift
  local deep=0
  local -a extra=()
  local arg
  for arg in "$@"; do
    if [ "$arg" = "--deep" ]; then
      deep=1
    else
      extra+=("$arg")
    fi
  done

  export DOTF_MODULE="$mod"
  export DOTF_ACTION="doctor"

  local capture rc_l0=0
  capture=$(mktemp)
  {
    set +e
    # shellcheck source=/dev/null
    source "$DOTFILES_ROOT/scripts/modules.sh"
    # shellcheck source=/dev/null
    source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
    # shellcheck source=/dev/null
    source "$DOTFILES_ROOT/scripts/lib/doctor_l0.sh"
    dotf_doctor_l0 "$mod"
    rc_l0=$?

    # status 模式禁止 L1（可能有网络/写副作用）；仅显式 --deep 且非 status 时运行
    if [ "$deep" -eq 1 ] && [ "${DOTF_STATUS_MODE:-0}" != "1" ]; then
      local l1
      l1="$(dotf_doctor_handlers_dir)/${mod}/doctor.sh"
      if [ -f "$l1" ]; then
        echo "doctor ($mod) — L1"
        # shellcheck source=/dev/null
        source "$l1" ${extra[@]+"${extra[@]}"}
        local rc_l1=$?
        if [ "$rc_l1" -ne 0 ]; then
          echo "fail  L1: exit $rc_l1"
        fi
      else
        echo "skip  L1: 无约定式处理器 scripts/modules/${mod}/doctor.sh"
      fi
    elif [ "$deep" -eq 1 ] && [ "${DOTF_STATUS_MODE:-0}" = "1" ]; then
      echo "skip  L1: status 模式仅运行只读 L0"
    fi
    set -e
  } >"$capture" 2>&1

  cat "$capture"

  local status reason
  if ! dotf_doctor_map_status "$capture"; then
    status="failed"
    reason="${DOTF_DOCTOR_REASON:-fail}"
    rm -f "$capture"
    dotf_emit_result failed "$reason"
    return 1
  fi
  status="${DOTF_DOCTOR_STATUS:-unchanged}"
  reason="${DOTF_DOCTOR_REASON:-ok}"
  rm -f "$capture"
  dotf_emit_result "$status" "$reason"
  return 0
}
