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
}

# 若 bin 已在 PATH 或 ~/.local/bin，返回 unchanged
# 用法: dotf_skip_if_bin <bin_name> → 0=应跳过并已 emit，1=继续安装
dotf_skip_if_bin() {
  local bin_name="$1"
  local local_path="${HOME}/.local/bin/${bin_name}"
  if command -v "$bin_name" >/dev/null 2>&1 || [ -x "$local_path" ]; then
    dotf_result_unchanged "${bin_name} already installed"
    return 0
  fi
  return 1
}

# 按注册表 source/target 做通用 symlink 配置
dotf_registry_symlink_config() {
  local mod="${1:-${DOTF_MODULE:?}}"
  local src tgt
  if ! modules_has "$mod" config; then
    dotf_result_failed "$mod has no config capability"
    return 1
  fi
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
}
