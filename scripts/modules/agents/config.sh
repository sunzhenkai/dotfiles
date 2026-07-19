#!/usr/bin/env bash
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/config.sh"
# 额外参数由 runner 以位置参数传入（compat/agents）
if install_agents "$@"; then
  dotf_result_changed "agents synced"
else
  dotf_result_failed "agents sync failed"
fi
