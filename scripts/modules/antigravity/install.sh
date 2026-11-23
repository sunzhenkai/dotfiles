#!/usr/bin/env bash
# shellcheck source=scripts/lib/handler_common.sh
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=scripts/lib/common.sh
source "$DOTFILES_ROOT/scripts/lib/common.sh"
# shellcheck source=scripts/modules/antigravity/lib.sh
source "$DOTFILES_ROOT/scripts/modules/antigravity/lib.sh"

_antigravity_ensure_path
if dotf_skip_if_bin "agy"; then
  exit 0
fi
if install_antigravity_cli; then
  dotf_result_changed "installed agy"
else
  dotf_result_failed "agy install failed"
fi
