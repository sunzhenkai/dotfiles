#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/lib/common.sh"
source "$DOTFILES_ROOT/scripts/modules/claude-code/lib.sh"
if dotf_skip_if_bin "claude"; then
  exit 0
fi
if install_claude_code; then
  dotf_result_changed "installed claude-code"
else
  dotf_result_failed "claude-code install failed"
fi
