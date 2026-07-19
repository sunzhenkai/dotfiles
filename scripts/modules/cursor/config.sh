#!/usr/bin/env bash
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/config.sh"
if install_cursor; then
  dotf_result_changed "cursor config applied"
else
  dotf_result_failed "cursor config failed"
fi
