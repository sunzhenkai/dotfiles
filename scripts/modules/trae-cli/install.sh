#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/trae-cli.sh"
if [ -n "trae" ] && dotf_skip_if_bin "trae"; then
  exit 0
fi
if install_trae_cli; then
  dotf_result_changed "installed trae-cli"
else
  dotf_result_failed "trae-cli install failed"
fi
