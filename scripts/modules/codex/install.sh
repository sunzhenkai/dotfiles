#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/codex.sh"
if [ -n "codex" ] && dotf_skip_if_bin "codex"; then
  exit 0
fi
if install_codex; then
  dotf_result_changed "installed codex"
else
  dotf_result_failed "codex install failed"
fi
