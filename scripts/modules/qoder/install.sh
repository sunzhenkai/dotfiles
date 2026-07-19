#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/qoder.sh"
if [ -n "qoder" ] && dotf_skip_if_bin "qoder"; then
  exit 0
fi
if install_qoder; then
  dotf_result_changed "installed qoder"
else
  dotf_result_failed "qoder install failed"
fi
