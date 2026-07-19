#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/golang.sh"
if dotf_skip_if_bin go; then exit 0; fi
if setup_golang; then dotf_result_changed "installed golang"; else dotf_result_failed "golang install failed"; fi
