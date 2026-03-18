#!/bin/bash
# 用于安装必要 sdk、配置文件

# 记录 secret 项目的路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 初始化系统（调用 system.sh）
setup_system() {
  local setup_script="$SCRIPT_DIR/scripts/tools/system.sh"

  if [ -f "$setup_script" ]; then
    echo "Running system setup..."
    bash "$setup_script"
  else
    echo "Warning: system.sh not found, skipping system setup"
  fi
}

# 主函数
main() {
  # 加载工具脚本
  source "$SCRIPT_DIR/scripts/tools/homebrew.sh"
  source "$SCRIPT_DIR/scripts/tools/sdk.sh"
  source "$SCRIPT_DIR/scripts/tools/senv.sh"
  source "$SCRIPT_DIR/scripts/tools/git.sh"
  source "$SCRIPT_DIR/scripts/tools/golang.sh"
  source "$SCRIPT_DIR/scripts/tools/fonts.sh"

  setup_brew_path
  install_homebrew
  setup_system
  setup_sdk
  install_senv_binary
  setup_git
  setup_golang
  setup_fonts
}

main
