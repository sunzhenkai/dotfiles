#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/lib/common.sh"
source "$DOTFILES_ROOT/scripts/modules/herdr/lib.sh"
if dotf_skip_if_bin herdr; then
  exit 0
fi
if install_herdr; then
  dotf_result_changed "installed herdr"
else
  dotf_result_failed "herdr install failed"
fi
