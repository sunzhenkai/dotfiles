#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/fonts.sh"
if setup_fonts; then
  dotf_result_changed "fonts ensured"
else
  dotf_result_failed "fonts failed"
fi
