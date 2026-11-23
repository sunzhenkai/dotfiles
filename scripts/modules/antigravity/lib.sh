#!/bin/bash
# Antigravity CLI (agy) 安装

# shellcheck source=scripts/lib/common.sh
source "$SCRIPT_DIR/scripts/lib/common.sh"

_antigravity_ensure_path() {
  case ":$PATH:" in
    *":${HOME}/.local/bin:"*) ;;
    *) export PATH="${HOME}/.local/bin:${PATH}" ;;
  esac
  case ":$PATH:" in
    *":${HOME}/.gemini/antigravity/bin:"*) ;;
    *)
      if [ -d "${HOME}/.gemini/antigravity/bin" ]; then
        export PATH="${HOME}/.gemini/antigravity/bin:${PATH}"
      fi
      ;;
  esac
}

# 判断 agy 是否真实可执行（不被悬空 symlink 欺骗）
_antigravity_cli_resolvable() {
  local resolved candidate
  resolved="$(command -v agy 2>/dev/null || true)"
  if [ -n "$resolved" ] && [ -e "$resolved" ] && [ -x "$resolved" ]; then
    printf '%s\n' "$resolved"
    return 0
  fi
  for candidate in "${HOME}/.local/bin/agy" "${HOME}/.gemini/antigravity/bin/agy"; do
    if [ -e "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

install_antigravity_cli() {
  local resolved_path=""
  _antigravity_ensure_path

  if resolved_path="$(_antigravity_cli_resolvable)"; then
    echo "Antigravity CLI 已安装: $resolved_path"
    return 0
  fi

  echo "正在安装 Antigravity CLI (agy)..."
  dotf_fetch_run https://antigravity.google/cli/install.sh
  _antigravity_ensure_path

  if resolved_path="$(_antigravity_cli_resolvable)"; then
    echo "✓ Antigravity CLI 已就绪: $resolved_path"
    echo "  运行 dotf antigravity -c 部署 ~/.gemini/config/skills.json 桥接配置"
    return 0
  fi
  echo "⚠️  安装完成但未找到 agy，请确认 ~/.local/bin 或 ~/.gemini/antigravity/bin 已在 PATH 中"
  return 1
}
