#!/usr/bin/env bash
# Codex profile selection feeds a pure producer; config_deploy owns the only target write.
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

codex_profile=""
while [ $# -gt 0 ]; do
  case "$1" in
  -f | --profile | --codex-profile)
    if [ -z "${2:-}" ] || [[ "${2}" == -* ]]; then
      echo "错误: $1 需要 Codex profile 名称" >&2
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

# company provider 的地址/密钥约定存放在 senv（feg 组优先）。
# 只补进本进程供 merge 展开 ${COMPANY_BASE_URL}，不打印任何值。
_codex_resolve_senv_var() {
  local var="$1"
  if [ -n "${!var:-}" ]; then
    return 0
  fi
  command -v senv >/dev/null 2>&1 || return 0
  local value=""
  local group
  for group in feg ai default; do
    value="$(senv env get "${group}:${var}" 2>/dev/null || true)"
    if [ -n "$value" ]; then
      export "${var}=${value}"
      return 0
    fi
  done
}

_codex_resolve_senv_var COMPANY_BASE_URL
_codex_resolve_senv_var COMPANY_API_KEY

dotf_registry_config
