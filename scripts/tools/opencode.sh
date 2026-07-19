#!/bin/bash
# OpenCode CLI 安装（Homebrew: anomalyco/tap/opencode）

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_opencode() {
  command -v setup_brew_path &>/dev/null && setup_brew_path

  if command -v opencode &>/dev/null; then
    echo "OpenCode 已安装: $(command -v opencode) ($(opencode --version 2>/dev/null || echo '?'))"
    if ! confirm "是否重新安装 / 更新 OpenCode?" "N"; then
      echo "跳过 OpenCode 安装"
      return 0
    fi
  elif ! confirm "是否安装 OpenCode CLI?" "N"; then
    echo "跳过 OpenCode 安装"
    return 0
  fi

  if ! command -v brew &>/dev/null; then
    echo "✗ 未找到 Homebrew，请先运行: dotf homebrew -i"
    return 1
  fi

  echo "正在安装 OpenCode（anomalyco/tap/opencode）..."
  brew install anomalyco/tap/opencode

  if command -v opencode &>/dev/null; then
    echo "✓ OpenCode 已就绪: $(command -v opencode)"
  else
    echo "⚠️  安装完成但未找到 opencode，请确认 brew 的 bin 已在 PATH 中"
    return 1
  fi
}
