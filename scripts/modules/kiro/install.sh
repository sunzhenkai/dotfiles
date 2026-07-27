#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/kiro.sh"
if [ -n "kiro-cli" ] && dotf_skip_if_bin "kiro-cli"; then
  exit 0
fi
if install_kiro; then
  dotf_result_changed "installed kiro"
else
  dotf_result_failed "kiro install failed"
fi
