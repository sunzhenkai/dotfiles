#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/codebuddy-code.sh"
if [ -n "codebuddy" ] && dotf_skip_if_bin "codebuddy"; then
  exit 0
fi
if install_codebuddy_code; then
  dotf_result_changed "installed codebuddy-code"
else
  dotf_result_failed "codebuddy-code install failed"
fi
