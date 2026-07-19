#!/bin/bash
# Kimi Code CLI 安装
# 官方文档: https://www.kimi.com/code/docs/en/kimi-code-cli/guides/getting-started.html

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 确保 kimi 常见安装目录在 PATH（官方默认 ~/.kimi-code/bin）
_ensure_kimi_path() {
  local d
  for d in "$HOME/.kimi-code/bin" "$HOME/.local/bin"; do
    if [[ -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_kimi_code() {
  _ensure_kimi_path

  if command -v kimi &>/dev/null || [[ -x "$HOME/.kimi-code/bin/kimi" ]]; then
    echo "Kimi Code CLI 已安装: $(command -v kimi 2>/dev/null || echo "$HOME/.kimi-code/bin/kimi") ($(kimi --version 2>/dev/null || echo '?'))"
    return 0
  fi

  echo "正在安装 Kimi Code CLI..."
  curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash

  _ensure_kimi_path

  if command -v kimi &>/dev/null; then
    echo "✓ Kimi Code CLI 已就绪: $(command -v kimi)"
  elif [[ -x "$HOME/.kimi-code/bin/kimi" ]]; then
    echo "✓ Kimi Code CLI 已安装: $HOME/.kimi-code/bin/kimi"
    echo "  提示: 当前 shell 已临时加入 PATH；新终端由 zsh/modules/paths.zsh 自动加载"
  else
    echo "⚠️  安装完成但未找到 kimi，请确认 ~/.kimi-code/bin 已在 PATH 中后重新打开终端"
    return 1
  fi
}
