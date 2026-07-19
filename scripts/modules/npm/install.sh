#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/npm.sh"
if install_npm_packages; then dotf_result_changed "npm packages ensured"; else dotf_result_failed "npm install failed"; fi
