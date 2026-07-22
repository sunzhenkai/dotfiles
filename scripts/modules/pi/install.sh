#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/pi.sh"

# 不因 bin 已存在而整段跳过：还要确保默认 packages
if install_pi; then
  dotf_result_changed "installed pi (+ packages)"
else
  dotf_result_failed "pi install failed"
fi
