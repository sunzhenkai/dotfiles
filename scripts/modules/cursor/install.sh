#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/cursor.sh"
if [ -n "cursor" ] && dotf_skip_if_bin "cursor"; then
  exit 0
fi
if install_cursor_cli; then
  dotf_result_changed "installed cursor"
else
  dotf_result_failed "cursor install failed"
fi
