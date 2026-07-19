#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/system.sh"
if setup_system; then
  dotf_result_changed "system packages ensured"
else
  dotf_result_failed "system setup failed"
fi
