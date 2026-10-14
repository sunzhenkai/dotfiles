#!/bin/bash
# OpenCode CLI 安装（Homebrew: anomalyco/tap/opencode-v2）

source "$SCRIPT_DIR/scripts/lib/common.sh"

install_opencode() {
  command -v setup_brew_path &>/dev/null && setup_brew_path

  if command -v opencode &>/dev/null; then
    echo "OpenCode 已安装: $(command -v opencode) ($(opencode --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v brew &>/dev/null; then
    echo "✗ 未找到 Homebrew，请先运行: dotf homebrew -i"
    return 1
  fi

  # v2 formula 与 v1（opencode）binary 冲突，若已装 v1 需先卸载
  if brew list --formula opencode &>/dev/null; then
    echo "检测到 v1（anomalyco/tap/opencode），先卸载以安装 v2..."
    brew uninstall opencode
  fi

  echo "正在安装 OpenCode v2（anomalyco/tap/opencode-v2）..."
  brew install anomalyco/tap/opencode-v2

  if command -v opencode &>/dev/null; then
    echo "✓ OpenCode 已就绪: $(command -v opencode)"
  else
    echo "⚠️  安装完成但未找到 opencode，请确认 brew 的 bin 已在 PATH 中"
    return 1
  fi
}
