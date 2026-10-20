#!/usr/bin/env bash
# claude-plugins install：幂等同步 desired set（marketplace + 插件）
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/modules/claude-plugins/lib.sh"

if claude_plugins_sync; then
  if [ "${CLAUDE_PLUGINS_SYNC_CHANGED:-0}" = "1" ]; then
    dotf_result_changed "claude plugins synced"
  else
    dotf_result_unchanged "claude plugins already in desired state"
  fi
else
  dotf_result_failed "claude plugins sync failed"
fi
