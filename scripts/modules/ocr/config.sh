#!/usr/bin/env bash
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/config.sh"
if install_ocr_config; then
  dotf_result_changed "ocr config applied"
else
  dotf_result_failed "ocr config failed"
fi
