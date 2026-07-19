#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/aliyun.sh"
if dotf_skip_if_bin aliyun; then exit 0; fi
if install_aliyun_cli; then dotf_result_changed "installed aliyun"; else dotf_result_failed "aliyun install failed"; fi
