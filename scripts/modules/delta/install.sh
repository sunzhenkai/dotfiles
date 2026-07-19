#!/usr/bin/env bash
# 约定式 install — delta
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/delta.sh"
if dotf_skip_if_bin "delta"; then
  exit 0
fi
if install_delta; then
  dotf_result_changed "installed delta"
else
  dotf_result_failed "failed to install delta"
fi
