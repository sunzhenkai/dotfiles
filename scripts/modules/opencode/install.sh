#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/lib/common.sh"
source "$DOTFILES_ROOT/scripts/modules/opencode/lib.sh"
if dotf_skip_if_bin "opencode"; then
  exit 0
fi
if install_opencode; then
  dotf_result_changed "installed opencode"
else
  dotf_result_failed "opencode install failed"
fi
