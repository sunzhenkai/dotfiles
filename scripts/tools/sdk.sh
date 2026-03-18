#!/bin/bash
# SDK 管理（通过 mise）

# 初始化 SDK（通过 mise 管理多版本）
setup_sdk() {
  echo "---- Setting up SDKs via mise ----"

  # 检查 mise 是否安装
  if ! command -v mise &>/dev/null; then
    echo "Warning: mise not found, skipping SDK setup"
    echo "Please install mise first (e.g., brew install mise)"
    return 0
  fi

  # 定义要安装的 SDK 及其版本
  local go_versions=("1.24.9")
  local python_versions=("3.13.12")
  local node_versions=("20.10.0")

  # 安装 Go 多版本
  echo ""
  echo "Installing Go versions: ${go_versions[*]}"
  for version in "${go_versions[@]}"; do
    echo "  Installing Go $version..."
    mise install go@"$version"
  done
  mise use -g go@"${go_versions[0]}"
  echo "  Global Go version set to: ${go_versions[0]}"

  # 安装 Python 多版本
  echo ""
  echo "Installing Python versions: ${python_versions[*]}"
  for version in "${python_versions[@]}"; do
    echo "  Installing Python $version..."
    mise install python@"$version"
  done
  mise use -g python@"${python_versions[0]}"
  echo "  Global Python version set to: ${python_versions[0]}"

  # 安装 Node.js 多版本
  echo ""
  echo "Installing Node.js versions: ${node_versions[*]}"
  for version in "${node_versions[@]}"; do
    echo "  Installing Node.js $version..."
    mise install node@"$version"
  done
  mise use -g node@"${node_versions[0]}"
  echo "  Global Node.js version set to: ${node_versions[0]}"

  # 激活 mise 环境（将 SDK 添加到 PATH）
  eval "$(mise activate bash)"

  echo ""
  echo "SDKs installed successfully!"
  mise ls
}
