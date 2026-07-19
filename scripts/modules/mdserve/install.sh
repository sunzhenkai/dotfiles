#!/usr/bin/env bash
# 约定式 install — mdserve
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/mdserve.sh"
if dotf_skip_if_bin "mdserve"; then
  exit 0
fi
if install_mdserve_binary; then
  dotf_result_changed "installed mdserve"
else
  dotf_result_failed "failed to install mdserve"
fi
