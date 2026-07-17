#!/bin/bash
# Kimi Code CLI 安装
# 官方文档: https://www.kimi.com/code/docs/en/kimi-code-cli/guides/getting-started.html

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_kimi_code() {
  if command -v kimi &>/dev/null; then
    echo "Kimi Code CLI 已安装: $(command -v kimi) ($(kimi --version 2>/dev/null || echo '?'))"
    if ! confirm "是否重新安装 / 更新 Kimi Code CLI?" "N"; then
      echo "跳过 Kimi Code CLI 安装"
      return 0
    fi
  elif ! confirm "是否安装 Kimi Code CLI?" "N"; then
    echo "跳过 Kimi Code CLI 安装"
    return 0
  fi

  echo "正在安装 Kimi Code CLI..."
  curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash

  # 官方安装脚本通常放到 ~/.local/bin
  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if command -v kimi &>/dev/null; then
    echo "✓ Kimi Code CLI 已就绪: $(command -v kimi)"
  else
    echo "⚠️  安装完成但未找到 kimi，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
    return 1
  fi
}
