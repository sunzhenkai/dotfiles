#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/kimi-code.sh"
if [ -n "kimi" ] && dotf_skip_if_bin "kimi"; then
  exit 0
fi
if install_kimi_code; then
  dotf_result_changed "installed kimi-code"
else
  dotf_result_failed "kimi-code install failed"
fi
