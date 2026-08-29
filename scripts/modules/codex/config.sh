#!/usr/bin/env bash
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/config.sh"

codex_profile=""
while [ $# -gt 0 ]; do
  case "$1" in
  -f | --profile | --codex-profile)
    if [ -z "${2:-}" ] || [[ "${2}" == -* ]]; then
      echo "错误: $1 需要 Codex profile 名称" >&2
      python3 "$DOTFILES_ROOT/scripts/modules/codex/merge_config.py" \
        --vendor-dir "$DOTFILES_ROOT/agents/vendors/codex" \
        --describe-profiles >&2 || true
      dotf_result_failed "missing Codex profile name"
      exit 1
    fi
    shift
    codex_profile="$1"
    ;;
  *)
    echo "错误: 未知选项 '$1'（Codex 配置支持 -f/--profile <name>）" >&2
    dotf_result_failed "unknown Codex config option"
    exit 1
    ;;
  esac
  shift
done

if [ -n "$codex_profile" ]; then
  export DOTF_CODEX_PROFILE="$codex_profile"
fi

if install_codex; then
  if [ -n "$codex_profile" ]; then
    dotf_result_changed "codex config applied (profile=${codex_profile})"
  else
    dotf_result_changed "codex config applied"
  fi
else
  dotf_result_failed "codex config failed"
fi
