#!/usr/bin/env bash
# 约定式 install — ossutil
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/ossutil.sh"
if dotf_skip_if_bin "ossutil"; then
  exit 0
fi
if install_ossutil; then
  dotf_result_changed "installed ossutil"
else
  dotf_result_failed "failed to install ossutil"
fi
