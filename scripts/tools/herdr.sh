#!/usr/bin/env bash
# Herdr 安装：使用官方稳定版安装脚本。
# 文档: https://herdr.dev/docs/install/

source "$SCRIPT_DIR/scripts/tools/common.sh"

_ensure_herdr_path() {
  if [[ -d "$HOME/.local/bin" && ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
}

install_herdr() {
  _ensure_herdr_path

  if command -v herdr &>/dev/null; then
    echo "Herdr 已安装: $(command -v herdr) ($(herdr --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v curl &>/dev/null; then
    echo "✗ 未找到 curl，无法运行 Herdr 官方安装脚本"
    return 1
  fi

  echo "正在安装 Herdr（官方稳定版）..."
  if ! curl -fsSL https://herdr.dev/install.sh | sh; then
    echo "✗ Herdr 安装失败"
    return 1
  fi

  _ensure_herdr_path
  if command -v herdr &>/dev/null; then
    echo "✓ Herdr 已就绪: $(command -v herdr)"
    return 0
  fi

  echo "⚠️  安装完成但未找到 herdr，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  return 1
}
