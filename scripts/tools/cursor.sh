#!/bin/bash
# Cursor Agent CLI 安装（cursor-agent / agent）

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_cursor_cli() {
  if command -v cursor-agent &>/dev/null; then
    echo "Cursor Agent 已安装: $(command -v cursor-agent)"
    return 0
  fi

  echo "正在安装 Cursor Agent..."
  curl https://cursor.com/install -fsS | bash

  # 官方安装脚本通常放到 ~/.local/bin
  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if command -v cursor-agent &>/dev/null; then
    echo "✓ Cursor Agent 已就绪: $(command -v cursor-agent)"
  else
    echo "⚠️  安装完成但未找到 cursor-agent，请确认 ~/.local/bin 已在 PATH 中"
    return 1
  fi
}
