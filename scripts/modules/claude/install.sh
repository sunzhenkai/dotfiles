#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/claude.sh"
if [ -n "claude" ] && dotf_skip_if_bin "claude"; then
  exit 0
fi
if install_claude_cli; then
  dotf_result_changed "installed claude"
else
  dotf_result_failed "claude install failed"
fi
