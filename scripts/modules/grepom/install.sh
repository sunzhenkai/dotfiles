#!/usr/bin/env bash
# 约定式 install — grepom
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/grepom.sh"
if dotf_skip_if_bin "grepom"; then
  exit 0
fi
if install_grepom_binary; then
  dotf_result_changed "installed grepom"
else
  dotf_result_failed "failed to install grepom"
fi
