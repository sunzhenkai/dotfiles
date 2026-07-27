#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/minimax.sh"
if [ -n "mmx" ] && dotf_skip_if_bin "mmx"; then
  exit 0
fi
if install_minimax; then
  dotf_result_changed "installed minimax"
else
  dotf_result_failed "minimax install failed"
fi
