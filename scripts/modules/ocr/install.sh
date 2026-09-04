#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/ocr.sh"
if dotf_skip_if_bin "ocr"; then
  exit 0
fi
if install_ocr; then
  dotf_result_changed "installed ocr"
else
  dotf_result_failed "ocr install failed"
fi
