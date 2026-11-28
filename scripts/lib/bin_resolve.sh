#!/usr/bin/env bash
# 二进制解析辅助（Bash 3.2 兼容）：识别失效的 mise shim 与悬空符号链接。

dotf_is_mise_shim() {
  local path="$1"
  local mise_data
  mise_data="${MISE_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/mise}"
  case "$path" in
    "${mise_data}/shims/"* | "${HOME}/.local/share/mise/shims/"* | */mise/shims/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

dotf_resolve_bin() {
  local bin_name="$1"
  local resolved mise_real

  resolved="$(command -v "$bin_name" 2>/dev/null || true)"
  case "$resolved" in
    /*) ;;
    *) return 1 ;;
  esac

  if [ ! -f "$resolved" ] || [ ! -x "$resolved" ]; then
    return 1
  fi

  if dotf_is_mise_shim "$resolved"; then
    if ! command -v mise >/dev/null 2>&1; then
      return 1
    fi
    mise_real="$(mise which "$bin_name" 2>/dev/null || true)"
    if [ -n "$mise_real" ] && [ -f "$mise_real" ] && [ -x "$mise_real" ]; then
      printf '%s\n' "$mise_real"
      return 0
    fi
    return 1
  fi

  printf '%s\n' "$resolved"
  return 0
}
