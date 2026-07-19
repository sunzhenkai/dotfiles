#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/vcpkg.sh"
if dotf_skip_if_bin vcpkg; then exit 0; fi
if setup_vcpkg; then dotf_result_changed "installed vcpkg"; else dotf_result_failed "vcpkg install failed"; fi
