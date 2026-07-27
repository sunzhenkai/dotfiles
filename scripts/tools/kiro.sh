#!/bin/bash
# Kiro CLI 安装（bin: kiro-cli）
# 文档: https://kiro.dev/docs/cli/installation/
# 主目录: ~/.kiro（可用 KIRO_HOME 重定向）

source "$SCRIPT_DIR/scripts/tools/common.sh"

_ensure_kiro_path() {
  if [[ -d "$HOME/.local/bin" && ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
}

install_kiro() {
  _ensure_kiro_path

  if command -v kiro-cli &>/dev/null; then
    echo "Kiro CLI 已安装: $(command -v kiro-cli) ($(kiro-cli --version 2>/dev/null || echo '?'))"
    return 0
  fi

  echo "正在安装 Kiro CLI..."
  # --force 跳过已有 Amazon Q / kiro 交互确认；安装包内脚本会设 KIRO_CLI_SKIP_SETUP
  if ! curl -fsSL https://cli.kiro.dev/install | bash -s -- --force; then
    echo "✗ Kiro CLI 安装失败"
    return 1
  fi

  _ensure_kiro_path

  if command -v kiro-cli &>/dev/null; then
    echo "✓ Kiro CLI 已就绪: $(command -v kiro-cli)"
    return 0
  fi

  echo "⚠️  安装完成但未找到 kiro-cli，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  return 1
}
