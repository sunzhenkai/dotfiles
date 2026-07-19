#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/homebrew.sh"
setup_brew_path
if command -v brew >/dev/null 2>&1; then
  init_homebrew || true
  dotf_result_unchanged "homebrew already present"
  exit 0
fi
if install_homebrew && init_homebrew; then
  dotf_result_changed "installed homebrew"
else
  dotf_result_failed "homebrew install failed"
fi
