#!/bin/bash
# 用于安装必要 sdk、配置文件

# 记录 secret 项目的路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 主函数
main() {
  # 加载工具脚本
  source "$SCRIPT_DIR/scripts/tools/homebrew.sh"
  source "$SCRIPT_DIR/scripts/tools/sdk.sh"
  source "$SCRIPT_DIR/scripts/tools/senv.sh"
  source "$SCRIPT_DIR/scripts/tools/git.sh"
  source "$SCRIPT_DIR/scripts/tools/fonts.sh"
  source "$SCRIPT_DIR/scripts/tools/system.sh"

  setup_brew_path
  install_homebrew
  setup_system
  setup_sdk
  install_senv_binary
  setup_git
  setup_fonts
}

main
