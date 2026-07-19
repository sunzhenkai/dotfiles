#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/aws.sh"
if dotf_skip_if_bin aws; then exit 0; fi
if install_aws_cli; then dotf_result_changed "installed aws"; else dotf_result_failed "aws install failed"; fi
