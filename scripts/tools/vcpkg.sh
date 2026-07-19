#!/bin/bash
# vcpkg C++ 包管理器安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

setup_vcpkg() {
  echo "---- Setting up vcpkg ----"

  local install_dir="$HOME/.local/vcpkg"

  # 检查是否已安装（幂等：已存在则跳过）
  if [ -f "$install_dir/vcpkg" ]; then
    echo "vcpkg is already installed at: $install_dir/vcpkg"
    return 0
  fi

  # 克隆仓库并引导
  mkdir -p "$install_dir"
  echo "Cloning vcpkg to: $install_dir"
  if ! git clone https://github.com/Microsoft/vcpkg.git "$install_dir"; then
    echo "Error: Failed to clone vcpkg repository"
    return 1
  fi

  echo "Bootstrapping vcpkg..."
  bash "$install_dir/bootstrap-vcpkg.sh"

  echo ""
  echo "vcpkg installed successfully!"
  echo "  VCPKG_ROOT: $install_dir"
  echo "  PATH entry: $install_dir"
  echo ""
  echo "Note: VCPKG_ROOT and PATH are auto-configured in zsh/modules/misc.zsh"
  echo "      Please restart your shell or run: source ~/.zshrc"
}
