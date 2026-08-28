#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/cursor.sh"
# 检查实际 CLI 二进制 cursor-agent（不是 wrapper 脚本 cursor）。
# dotf_skip_if_bin 已能识别悬空 symlink —— 直接调用即可，不需要前置 [ -n ... ] 卫语句。
if dotf_skip_if_bin "cursor-agent"; then
  exit 0
fi
if install_cursor_cli; then
  dotf_result_changed "installed cursor-agent"
else
  dotf_result_failed "cursor-agent install failed"
fi
