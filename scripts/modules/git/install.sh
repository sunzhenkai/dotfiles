#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/lib/common.sh"
source "$DOTFILES_ROOT/scripts/modules/git/lib.sh"
if setup_git; then
  dotf_result_changed "git ensured"
else
  dotf_result_failed "git failed"
fi
