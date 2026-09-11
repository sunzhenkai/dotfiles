#!/usr/bin/env bash
# Codex config is a pure producer; config_deploy owns the only target write.
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

if [ $# -gt 0 ]; then
  echo "错误: 未知选项 '$1'" >&2
  dotf_result_failed "unknown Codex config option"
  exit 1
fi

dotf_registry_config
