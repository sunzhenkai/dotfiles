#!/bin/bash
# Senv 二进制安装

# 编译安装 senv 程序
install_senv_binary() {
  echo "---- Installing senv binary ----"

  # 检查 go 命令是否存在
  if ! command -v go &>/dev/null; then
    echo "Warning: go not found, skipping senv binary installation"
    echo "Please install Go first (e.g., via mise)"
    return 0
  fi

  local install_dir="$HOME/.local/bin"
  local senv_path="$install_dir/senv"

  # 检查 senv 是否已存在
  if [ -f "$senv_path" ]; then
    echo "senv is already installed at: $senv_path"
    local reply
    read -r -p "Do you want to update/reinstall senv? [y/N]: " reply
    if [[ ! "$reply" =~ ^[Yy] ]]; then
      echo "Skipping senv installation."
      return 0
    fi
    echo "Updating senv..."
  else
    # 确保 ~/.local/bin 存在
    mkdir -p "$install_dir"
  fi

  # 创建临时目录
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  echo "Building senv in temporary directory: $tmp_dir"

  # 克隆源代码
  cd "$tmp_dir" || exit 1
  echo "Cloning senv source code..."
  if ! git clone https://github.com/solo-kingdom/senv.git; then
    echo "Error: Failed to clone senv repository"
    cd "$SCRIPT_DIR" || exit 1
    rm -rf "$tmp_dir"
    return 1
  fi

  # 进入源码目录并编译
  cd senv || exit 1
  echo "Building senv..."
  if ! go build -o senv .; then
    echo "Error: Failed to build senv"
    cd "$SCRIPT_DIR" || exit 1
    rm -rf "$tmp_dir"
    return 1
  fi

  # 安装到 ~/.local/bin
  cp senv "$senv_path"
  chmod +x "$senv_path"
  echo "senv installed to: $senv_path"

  # 清理临时目录
  cd "$SCRIPT_DIR" || exit 1
  rm -rf "$tmp_dir"
  echo "Temporary directory cleaned up"

  echo "senv binary installed successfully!"
}
