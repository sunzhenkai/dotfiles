#!/bin/bash
# Homebrew 安装和配置

# brew 可能的路径（支持 macOS 和 Linux）
BREW_PATHS=(
  "/opt/homebrew/bin/brew"              # macOS Apple Silicon
  "/usr/local/bin/brew"                 # macOS Intel
  "/home/linuxbrew/.linuxbrew/bin/brew" # Linux
)

# 设置 brew PATH
setup_brew_path() {
  # 如果 brew 命令已可用，直接返回
  if command -v brew &>/dev/null; then
    return 0
  fi

  # 遍历可能的 brew 路径
  for brew_path in "${BREW_PATHS[@]}"; do
    if [ -x "$brew_path" ]; then
      local bin_dir
      bin_dir="$(dirname "$brew_path")"
      export PATH=$PATH:$bin_dir
      echo "Found brew at: $brew_path"
      return 0
    fi
  done
}

# 检查并安装 Homebrew
install_homebrew() {
  if ! command -v brew &>/dev/null; then
    echo "Homebrew not found, installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    setup_brew_path
  else
    echo "Homebrew is already installed"
  fi
}
