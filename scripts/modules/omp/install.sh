#!/usr/bin/env bash
# 约定式 install — omp
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/common.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/modules/omp/lib.sh"
if dotf_skip_if_bin "omp"; then
  exit 0
fi
if install_omp; then
  dotf_result_changed "installed omp"
else
  dotf_result_failed "failed to install omp"
fi
