#!/usr/bin/env bash
# 约定式处理器公共辅助（由 modules/<name>/*.sh source）
# 依赖: DOTFILES_ROOT, DOTF_MODULE；通常已由 runner 注入 result.sh

dotf_handler_init() {
  : "${DOTFILES_ROOT:?DOTFILES_ROOT required}"
  export SCRIPT_DIR="$DOTFILES_ROOT"
  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/modules.sh"
  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
  if ! type dotf_result_changed >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    source "$DOTFILES_ROOT/scripts/lib/result.sh"
  fi
}

# 若 bin 已在 PATH 或 ~/.local/bin 且真实可执行，返回 unchanged
# 用法: dotf_skip_if_bin <bin_name> → 0=应跳过并已 emit，1=继续安装
#
# 注意：仅 [ -x ] / command -v 不够 —— 悬空 symlink（link 存在但 target 缺失）
# 在部分 shell 里会让 [ -x ] 仍为真，导致二进制实际丢失却误报已装。
# 必须解析到真实路径后检查文件存在并可执行。
dotf_skip_if_bin() {
  local bin_name="$1"
  local local_path="${HOME}/.local/bin/${bin_name}"
  local resolved

  resolved="$(command -v "$bin_name" 2>/dev/null || true)"
  if [ -n "$resolved" ] && [ -e "$resolved" ] && [ -x "$resolved" ]; then
    dotf_result_unchanged "${bin_name} already installed"
    return 0
  fi
  if [ -e "$local_path" ] && [ -x "$local_path" ]; then
    dotf_result_unchanged "${bin_name} already installed"
    return 0
  fi
  return 1
}

# Registry-driven generic config dispatch. Copy is owned by the Python planner /
# apply path. Merge/render modules must call the same Python API with a pure
# expected-content producer; they fail closed here rather than gaining a direct
# write escape hatch. Symlink remains only for explicitly safe registry entries.
dotf_registry_config() {
  local mod="${1:-${DOTF_MODULE:?}}"
  local strategy src tgt status pythonpath_value
  local -a state_args=()
  if [ -n "${XDG_STATE_HOME:-}" ]; then
    state_args=(--state-home "$XDG_STATE_HOME")
  fi
  if ! modules_has "$mod" config; then
    dotf_result_failed "$mod has no config capability"
    return 1
  fi
  strategy=$(modules_strategy "$mod") || {
    dotf_result_failed "$mod: missing config.strategy"
    return 1
  }
  case "$strategy" in
  copy | merge | render)
    pythonpath_value="${_DOTF_CORE_PYTHONPATH}"
    if [ -n "${PYTHONPATH:-}" ]; then
      pythonpath_value="${pythonpath_value}:${PYTHONPATH}"
    fi
    status=$(PYTHONPATH="$pythonpath_value" \
      python3 -m dotf_core.config_handler "$mod" \
      --repo-root "$DOTFILES_ROOT" --home "$HOME" \
      "${state_args[@]}" --run-id "$DOTF_RUN_ID") || {
      dotf_result_failed "$mod: safe $strategy deployment failed"
      return 1
    }
    if [ "$status" = "unchanged" ]; then
      dotf_result_unchanged "$mod already deployed"
    else
      dotf_result_changed "$mod deployed"
    fi
    ;;
  symlink)
    src=$(modules_source "$mod") || {
      dotf_result_failed "$mod: missing config.source"
      return 1
    }
    tgt=$(modules_target "$mod") || {
      dotf_result_failed "$mod: missing config.target"
      return 1
    }
    tgt=$(dotf_expand_path "$tgt")
    if ! dotf_ensure_symlink "$src" "$tgt"; then
      dotf_result_failed "$mod: symlink failed"
      return 1
    fi
    if [ "${DOTF_CFG_STATUS:-}" = "unchanged" ]; then
      dotf_result_unchanged "$mod already linked"
    else
      dotf_result_changed "$mod linked"
    fi
    ;;
  *)
    dotf_result_failed "$mod: unsupported config strategy $strategy"
    return 1
    ;;
  esac
}

# Compatibility name retained while module wrappers migrate; behavior is now
# registry-driven and no longer implies a symlink strategy.
dotf_registry_symlink_config() {
  dotf_registry_config "$@"
}
