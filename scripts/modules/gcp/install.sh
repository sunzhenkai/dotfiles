#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/gcp.sh"
if dotf_skip_if_bin gcloud; then exit 0; fi
if install_gcp_cli; then dotf_result_changed "installed gcp"; else dotf_result_failed "gcp install failed"; fi
