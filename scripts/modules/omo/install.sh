#!/usr/bin/env bash
# 约定式 install — omo
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/modules/omo/lib.sh"
if dotf_skip_if_bin "omo"; then
  exit 0
fi
if install_omo; then
  dotf_result_changed "installed omo"
else
  dotf_result_failed "failed to install omo"
fi
