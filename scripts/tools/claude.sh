#!/bin/bash
# Claude Code CLI 安装（官方 native installer）
# 文档: https://code.claude.com/docs/en/install

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_claude_cli() {
  # 官方安装脚本通常放到 ~/.local/bin
  if [[ -d "$HOME/.local/bin" && ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if command -v claude &>/dev/null; then
    echo "Claude Code 已安装: $(command -v claude) ($(claude --version 2>/dev/null || echo '?'))"
    if ! confirm "是否重新安装 / 更新 Claude Code CLI?" "N"; then
      echo "跳过 Claude Code CLI 安装"
      return 0
    fi
  elif ! confirm "是否安装 Claude Code CLI?" "N"; then
    echo "跳过 Claude Code CLI 安装"
    return 0
  fi

  echo "正在安装 Claude Code CLI..."
  curl -fsSL https://claude.ai/install.sh | bash

  if [[ -d "$HOME/.local/bin" && ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if command -v claude &>/dev/null; then
    echo "✓ Claude Code 已就绪: $(command -v claude)"
  else
    echo "⚠️  安装完成但未找到 claude，请确认 ~/.local/bin 已在 PATH 中"
    return 1
  fi
}
