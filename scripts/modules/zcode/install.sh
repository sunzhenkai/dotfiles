#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/zcode.sh"
if dotf_skip_if_bin "zcode"; then
  exit 0
fi
if install_zcode; then
  dotf_result_changed "installed zcode"
else
  dotf_result_failed "zcode install failed"
fi
