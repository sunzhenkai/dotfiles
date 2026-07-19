#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/sdk.sh"
if command -v mise >/dev/null 2>&1; then
  if setup_sdk; then
    dotf_result_unchanged "mise already present; sdk refreshed"
  else
    dotf_result_failed "sdk setup failed"
  fi
  exit 0
fi
if setup_sdk; then
  dotf_result_changed "installed sdk/mise"
else
  dotf_result_failed "sdk setup failed"
fi
