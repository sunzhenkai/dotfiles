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

# 通过 Homebrew 安装常用软件
init_homebrew() {
  echo "---- Installing packages via Homebrew ----"

  # 让用户确认
  read -p "Do you want to install packages via Homebrew? [y/N] " -n 1 -r
  echo ""

  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipped Homebrew packages installation."
    return 0
  fi

  # 工具类
  brew install watch fswatch htop wget curl tree nmap

  # 搜索/编辑
  brew install bat the_silver_searcher perl universal-ctags
  brew install fd fzf ripgrep nvim

  # 文档/排版
  brew install luarocks hunspell tectonic ghostscript
  brew install poppler imagemagick resvg

  # 文件/媒体
  brew install yazi ffmpeg sevenzip jq zoxide chafa
  # pngpaste 仅在 macOS 上可用
  if [[ "$ID" == "darwin" ]]; then
    brew install pngpaste
  fi

  # 开发工具
  brew install mise tmux zsh uv pkg-config mysql-connector-c
  brew install anomalyco/tap/opencode
  # ghostty 仅在 macOS 上可用
  if [[ "$ID" == "darwin" ]]; then
    brew install --cask ghostty
  fi

  # Shell
  brew install nushell fish starship

  # Git
  brew install lazygit gitui

  # C/C++
  brew install pkg-config ninja bear ctags valgrind llvm make cmake gcc clangd

  # Java
  brew install openjdk@17 bison flex

  # Go (NOTE: Go 本体通过 mise 安装)
  brew install gotests

  echo "Homebrew packages installed successfully!"
}
