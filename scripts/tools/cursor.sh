#!/bin/bash
# Cursor Agent CLI 安装（cursor-agent / agent）

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 判断 cursor-agent 是否真实可执行（不被悬空 symlink 欺骗）
_cursor_agent_resolvable() {
  local resolved
  resolved="$(command -v cursor-agent 2>/dev/null || true)"
  if [ -n "$resolved" ] && [ -e "$resolved" ] && [ -x "$resolved" ]; then
    command -v cursor-agent
    return 0
  fi
  local local_path="${HOME}/.local/bin/cursor-agent"
  if [ -e "$local_path" ] && [ -x "$local_path" ]; then
    echo "$local_path"
    return 0
  fi
  return 1
}

install_cursor_cli() {
  if resolved_path="$(_cursor_agent_resolvable)"; then
    echo "Cursor Agent 已安装: $resolved_path"
    return 0
  fi

  echo "正在安装 Cursor Agent..."
  curl https://cursor.com/install -fsS | bash

  # 官方安装脚本通常放到 ~/.local/bin
  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if resolved_path="$(_cursor_agent_resolvable)"; then
    echo "✓ Cursor Agent 已就绪: $resolved_path"
    return 0
  fi
  echo "⚠️  安装完成但未找到 cursor-agent，请确认 ~/.local/bin 已在 PATH 中"
  return 1
}
