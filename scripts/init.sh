#!/bin/bash
# 用于安装必要 sdk、配置文件

# 记录 secret 项目的路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

# 克隆并初始化 dotfiles
setup_dotfiles() {
  local dotfile_dir="$HOME/.config/dotfiles"

  if [ -d "$dotfile_dir" ]; then
    echo "dotfile directory already exists, pulling latest changes..."
    cd "$dotfile_dir" || exit 1

    # 检查是否是 git 仓库
    if [ -d ".git" ]; then
      # 拉取最新代码
      if git pull; then
        echo "Successfully pulled latest changes"
      else
        echo "Warning: Failed to pull latest changes, continuing with existing version"
      fi
    else
      echo "Warning: $dotfile_dir is not a git repository, skipping pull"
    fi
  else
    echo "Cloning dotfiles..."
    git clone git@github.com:sunzhenkai/dotfiles.git "$dotfile_dir"
    cd "$dotfile_dir" || exit 1
  fi

  if [ -d "$dotfile_dir" ]; then
    make all
    cd "$SCRIPT_DIR" || exit 1
  else
    echo "Error: dotfile directory not found"
    exit 1
  fi
}

# 克隆并初始化 senvdata
setup_senv() {
  local senv_dir="$HOME/.config/senv"

  if [ -d "$senv_dir" ]; then
    echo "senv directory already exists, pulling latest changes..."
    cd "$senv_dir" || exit 1

    # 检查是否是 git 仓库
    if [ -d ".git" ]; then
      # 拉取最新代码
      if git pull; then
        echo "Successfully pulled latest changes"
      else
        echo "Warning: Failed to pull latest changes, continuing with existing version"
      fi
    else
      echo "Warning: $senv_dir is not a git repository, skipping pull"
    fi
  else
    echo "Cloning senvdata..."
    git clone git@codeup.aliyun.com:wii/senvdata.git "$senv_dir"
  fi

  cd "$SCRIPT_DIR" || exit 1
}

# 编译安装 senv 程序
install_senv_binary() {
  echo "---- Installing senv binary ----"

  # 检查 go 命令是否存在
  if ! command -v go &>/dev/null; then
    echo "Warning: go not found, skipping senv binary installation"
    echo "Please install Go first (e.g., via mise)"
    return 0
  fi

  # 确保 ~/.local/bin 存在
  local install_dir="$HOME/.local/bin"
  mkdir -p "$install_dir"

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
  cp senv "$install_dir/senv"
  chmod +x "$install_dir/senv"
  echo "senv installed to: $install_dir/senv"

  # 清理临时目录
  cd "$SCRIPT_DIR" || exit 1
  rm -rf "$tmp_dir"
  echo "Temporary directory cleaned up"

  echo "senv binary installed successfully!"
}

# 初始化系统（调用 setup-system.sh）
setup_system() {
  local setup_script="$SCRIPT_DIR/scripts/setup-system.sh"

  if [ -f "$setup_script" ]; then
    echo "Running system setup..."
    bash "$setup_script"
  else
    echo "Warning: setup-system.sh not found, skipping system setup"
  fi
}

# 初始化 git 配置
setup_git() {
  echo "---- Configuring git ----"

  # 设置用户名和邮箱
  git config --global user.name "zhenkai.sun"
  git config --global user.email "zhenkai.sun@qq.com"

  # pull 冲突后默认 merge（不使用 rebase）
  git config --global pull.rebase false

  # 设置默认编辑器
  git config --global core.editor vim

  # 设置默认分支名为 main
  git config --global init.defaultBranch main

  echo "Git configured successfully!"
  echo "  user.name: $(git config --global user.name)"
  echo "  user.email: $(git config --global user.email)"
  echo "  pull.rebase: $(git config --global pull.rebase)"
  echo "  core.editor: $(git config --global core.editor)"
  echo "  init.defaultBranch: $(git config --global init.defaultBranch)"
}

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

# 初始化 Golang 环境
setup_golang() {
  echo "---- Configuring Golang ----"

  # 检查 go 命令是否存在
  if ! command -v go &>/dev/null; then
    echo "Warning: go not found, skipping Golang setup"
    echo "Please install Go first (e.g., via mise or homebrew)"
    return 0
  fi

  # 设置私有库，不走代理
  go env -w GOPRIVATE='gitlab.fegtech.com/*'
  go env -w GONOSUMDB='gitlab.fegtech.com/*'

  # 设置使用 fegtech gitlab ssh 认证
  git config --global url."git@gitlab.fegtech.com:".insteadOf "https://gitlab.fegtech.com/"

  echo "Golang configured successfully!"
  echo "  GOPRIVATE: $(go env GOPRIVATE)"
  echo "  GONOSUMDB: $(go env GONOSUMDB)"
}

# 主函数
main() {
  setup_brew_path
  install_homebrew
  setup_system
  setup_sdk
  install_senv_binary
  setup_dotfiles
  setup_senv
  setup_git
  setup_golang
}

main
