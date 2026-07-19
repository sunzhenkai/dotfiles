#!/usr/bin/env bash
# 约定式 install — d2
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/d2.sh"
if dotf_skip_if_bin "d2"; then
  exit 0
fi
if install_d2; then
  dotf_result_changed "installed d2"
else
  dotf_result_failed "failed to install d2"
fi
