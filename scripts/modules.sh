#!/usr/bin/env bash
# 模块注册表 bash 封装 — 委托 scripts/modules.py
# 用法: source "$DOTFILES_ROOT/scripts/modules.sh"

# 在 source 时锚定仓根（勿在函数内用 BASH_SOURCE，否则指向调用方）
_MODULES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_MODULES_PY="$_MODULES_ROOT/scripts/modules.py"

_modules_py() {
  python3 "$_MODULES_PY" "$@"
}

# 列出模块名（一行一个）
# 用法: modules_list [install|config|both] [--os ID|--filter-os]
modules_list() {
  local cap=""
  local extra=()
  while [ $# -gt 0 ]; do
    case "$1" in
    install | config | both)
      cap="$1"
      ;;
    --os)
      shift
      extra+=(--os "$1")
      ;;
    --filter-os)
      extra+=(--filter-os)
      ;;
    --desc)
      extra+=(--desc)
      ;;
    *)
      echo "modules_list: 未知参数 $1" >&2
      return 1
      ;;
    esac
    shift
  done
  if [ -n "$cap" ]; then
    _modules_py list --capability "$cap" "${extra[@]}"
  else
    _modules_py list "${extra[@]}"
  fi
}

modules_names() {
  local cap="${1:-}"
  if [ -n "$cap" ]; then
    _modules_py names --capability "$cap"
  else
    _modules_py names
  fi
}

modules_exists() {
  _modules_py exists "$1"
}

modules_has() {
  # modules_has <name> install|config
  _modules_py has "$1" "$2"
}

modules_desc() {
  _modules_py field "$1" desc
}

modules_source() {
  _modules_py field "$1" source
}

modules_target() {
  _modules_py field "$1" target
}

modules_detect_os() {
  _modules_py detect-os
}

modules_profiles() {
  _modules_py profiles
}

modules_get() {
  _modules_py get "$1"
}
