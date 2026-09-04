#!/usr/bin/env bash
# tmux clipboard dependencies belong to install, not config deployment.
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"

if has_clipboard_tool; then
  dotf_result_unchanged "tmux clipboard dependency already available"
elif install_tmux_clipboard_deps; then
  dotf_result_changed "tmux clipboard dependency installed"
else
  dotf_result_failed "tmux clipboard dependency install failed"
fi
