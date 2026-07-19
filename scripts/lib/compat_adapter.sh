#!/usr/bin/env bash
# 迁移期兼容适配器（临时）
# install/config 须走约定式处理器；doctor 走统一 L0(+可选 L1)。
# 用法: compat_run_action <action> <module> [extra args...]

compat_run_action() {
  local action="$1"
  local module="$2"
  shift 2
  local -a extra=("$@")

  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/lib/result.sh"
  export DOTF_MODULE="$module"
  export DOTF_ACTION="$action"

  case "$action" in
  install | config)
    dotf_emit_result failed "no convention handler for $module/$action" 0 1
    return 1
    ;;
  doctor)
    # shellcheck source=/dev/null
    source "$DOTFILES_ROOT/scripts/lib/doctor_run.sh"
    # 尊重全局 DOTF_DEEP=1
    if [ "${DOTF_DEEP:-0}" = "1" ]; then
      local has_deep=0
      local a
      for a in ${extra[@]+"${extra[@]}"}; do
        [ "$a" = "--deep" ] && has_deep=1
      done
      if [ "$has_deep" -eq 0 ]; then
        extra+=(--deep)
      fi
    fi
    dotf_doctor_run "$module" ${extra[@]+"${extra[@]}"}
    return $?
    ;;
  *)
    echo "compat_adapter: 未知动作 $action" >&2
    return 2
    ;;
  esac
}
