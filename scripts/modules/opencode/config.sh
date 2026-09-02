#!/usr/bin/env bash
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/config.sh"

opencode_profile=""
while [ $# -gt 0 ]; do
  case "$1" in
  -f | --profile | --opencode-profile)
    if [ -z "${2:-}" ] || [[ "${2}" == -* ]]; then
      echo "错误: $1 需要 OpenCode provider 名称" >&2
      python3 "$DOTFILES_ROOT/scripts/modules/opencode/merge_config.py" \
        --describe-profiles >&2 || true
      dotf_result_failed "missing OpenCode provider name"
      exit 1
    fi
    shift
    opencode_profile="$1"
    ;;
  *)
    echo "错误: 未知选项 '$1'（OpenCode 配置支持 -f/--profile <name>）" >&2
    dotf_result_failed "unknown OpenCode config option"
    exit 1
    ;;
  esac
  shift
done

if [ -n "$opencode_profile" ]; then
  export DOTF_OPENCODE_PROFILE="$opencode_profile"
fi

if install_opencode; then
  if [ -n "$opencode_profile" ]; then
    dotf_result_changed "opencode config applied (profile=${opencode_profile})"
  else
    dotf_result_changed "opencode config applied"
  fi
else
  dotf_result_failed "opencode config failed"
fi
