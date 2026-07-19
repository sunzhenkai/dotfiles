#!/usr/bin/env bash
# 约定式 install — senv
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/senv.sh"
if dotf_skip_if_bin "senv"; then
  exit 0
fi
if install_senv_binary; then
  dotf_result_changed "installed senv"
else
  dotf_result_failed "failed to install senv"
fi
