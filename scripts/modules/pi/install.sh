#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/pi.sh"
if [ -n "pi" ] && dotf_skip_if_bin "pi"; then
  exit 0
fi
if install_pi; then
  dotf_result_changed "installed pi"
else
  dotf_result_failed "pi install failed"
fi
