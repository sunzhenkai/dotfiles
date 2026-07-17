#!/bin/bash
# 探测系统信息，并安装必要软件，搭建开发环境

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 检测操作系统
detect_os() {
  if [ -f "/etc/os-release" ]; then
    # shellcheck source=/dev/null
    . /etc/os-release
  elif [ -f "/etc/arch-release" ]; then
    export ID=arch
  elif [[ "$OSTYPE" =~ ^darwin ]]; then
    export ID=darwin
  else
    echo "Error: Unknown OS"
    exit 1
  fi
  echo "Detected OS: $ID"
}

common_init() {
  echo "---- common init ----"
}

init_docker() {
  # 已安装：询问是否配置；未安装：询问是否安装并配置
  if command -v docker &>/dev/null; then
    echo "Docker 已安装: $(docker --version)"
    if ! confirm "是否配置 Docker（用户组/验证）?" "N"; then
      echo "跳过 Docker 配置。"
      return 0
    fi
  else
    if ! confirm "是否安装并配置 Docker Engine?" "N"; then
      echo "跳过 Docker 安装。"
      return 0
    fi

    case "$ID" in
    ubuntu | debian | pop | linuxmint)
      # Add Docker's official GPG key:
      sudo apt-get update
      sudo apt-get install -y ca-certificates curl
      sudo install -m 0755 -d /etc/apt/keyrings
      sudo curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
      sudo chmod a+r /etc/apt/keyrings/docker.asc

      # Add the repository to Apt sources:
      sudo tee "/etc/apt/sources.list.d/docker.sources" >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/${ID}
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

      sudo apt-get update
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      ;;

    fedora | rhel | centos | rocky | almalinux | alinux | amzn)
      sudo dnf -y install dnf-plugins-core
      sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
      sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      ;;

    arch | manjaro | endeavouros)
      sudo pacman -Sy --noconfirm docker docker-compose docker-buildx
      ;;

    *)
      echo "不支持的操作系统，无法安装 Docker: $ID"
      echo "请手动安装: https://docs.docker.com/engine/install/"
      return 1
      ;;
    esac
  fi

  # 启动并启用 docker 服务（仅 Linux）
  if command -v systemctl &>/dev/null; then
    echo "正在启用 Docker 服务..."
    sudo systemctl enable --now docker
  fi

  # 将当前用户加入 docker 组（免密使用 docker）
  if ! groups | grep -q '\bdocker\b'; then
    echo "正在将用户 '$USER' 加入 docker 组..."
    if [[ "$ID" == "darwin" ]]; then
      # macOS 使用 dseditgroup 将用户加入 docker 组
      sudo dseditgroup -o edit -a "$USER" -t user docker 2>/dev/null || \
        echo "注意: macOS 上 Docker Desktop 会自动管理组成员。"
    else
      sudo usermod -aG docker "$USER"
    fi
    echo ""
    echo "注意: 需要登出后重新登录（或执行 'newgrp docker'）以使组成员变更生效。"
  else
    echo "用户 '$USER' 已在 docker 组中。"
  fi

  # 验证安装
  echo ""
  if [[ "$ID" == "darwin" ]]; then
    # macOS (Docker Desktop): 不需要 sudo
    if docker run --rm hello-world &>/dev/null; then
      echo "Docker 验证成功！"
    else
      echo "⚠️  Docker 验证失败。"
      echo "   请确保 Docker Desktop 正在运行: open -a Docker"
    fi
  else
    # Linux: 使用 sudo 验证
    if sudo docker run --rm hello-world &>/dev/null; then
      echo "Docker 验证成功！"
    else
      echo "⚠️  Docker 验证失败。"
      echo "   请尝试: sudo systemctl start docker"
    fi
  fi
}

# Ubuntu/Debian 系初始化
init_debian() {
  echo "---- Initializing Debian/Ubuntu ----"

  # 基础工具
  sudo apt-get update
  sudo apt-get install -y curl wget pkg-config

  # 开发工具链
  sudo apt-get install -y git autoconf automake binutils bison findutils flex gawk \
    gettext grep gzip libtool m4 make patch pkgconf sed texinfo

  # GCC 版本（使用系统默认或指定版本）
  local GCC_VERSION="${GCC_VERSION:-$(gcc -dumpversion 2>/dev/null | cut -d. -f1 || echo 12)}"
  sudo apt-get install -y gcc-${GCC_VERSION} g++-${GCC_VERSION} ||
    sudo apt-get install -y gcc g++

  # Python 环境
  sudo apt-get install -y python3-pip python3-virtualenv python3-venv

  # 实用工具
  sudo apt-get install -y gdb vim zip unzip tar xz-utils

  # 构建依赖
  sudo apt-get install -y build-essential libreadline-dev libssl-dev procps sqlite3 libsqlite3-dev

  # ImageMagick
  sudo apt-get install -y imagemagick libmagickwand-dev

  # MySQL/MariaDB 客户端
  sudo apt-get install -y libmariadb-dev mariadb-client libmysqlclient-dev

  # tmux-yank 剪贴板（X11: xclip/xsel；Wayland: wl-clipboard）
  sudo apt-get install -y xclip xsel wl-clipboard

  # 设置 pkg-config 路径（解决 Homebrew/Linuxbrew 覆盖路径的问题）
  export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig"

  # 安装 Python mysqlclient 包
  pip_install_system mysqlclient
}

# Arch/Manjaro 系初始化
init_arch() {
  echo "---- Initializing Arch/Manjaro ----"

  # 基础工具
  sudo pacman -Sy --noconfirm curl wget pkgconf

  # 开发工具链 (base-devel 包含大部分)
  sudo pacman -Sy --noconfirm base-devel git autoconf automake binutils bison flex gawk \
    gettext grep gzip libtool m4 make patch sed texinfo

  # GCC
  sudo pacman -Sy --noconfirm gcc

  # Python 环境
  sudo pacman -Sy --noconfirm python-pip python-virtualenv

  # 实用工具
  sudo pacman -Sy --noconfirm gdb vim zip unzip tar xz procps-ng

  # 构建依赖
  sudo pacman -Sy --noconfirm readline openssl sqlite

  # ImageMagick
  sudo pacman -Sy --noconfirm imagemagick

  # MySQL/MariaDB 客户端
  sudo pacman -Sy --noconfirm mariadb-libs mariadb-clients python-pymysql

  # tmux-yank 剪贴板（X11: xclip/xsel；Wayland: wl-clipboard）
  sudo pacman -Sy --noconfirm xclip xsel wl-clipboard

  # 设置 pkg-config 路径
  export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/usr/lib/pkgconfig"

  # 安装 Python mysqlclient 包
  pip_install_system mysqlclient
}

# Fedora 系初始化
init_fedora() {
  echo "---- Initializing Fedora ----"

  # 基础工具
  sudo dnf install -y curl wget pkgconf-pkg-config

  # 开发工具链
  sudo dnf install -y git autoconf automake binutils bison flex gawk \
    gettext gzip libtool m4 make patch sed texinfo

  # GCC
  sudo dnf install -y gcc gcc-c++

  # Python 环境
  sudo dnf install -y python3-pip python3-virtualenv

  # 实用工具
  sudo dnf install -y gdb vim-enhanced zip unzip tar xz procps-ng

  # 构建依赖
  sudo dnf install -y readline-devel openssl-devel sqlite sqlite-devel

  # ImageMagick
  sudo dnf install -y ImageMagick ImageMagick-devel

  # MySQL/MariaDB 客户端
  sudo dnf install -y mariadb-devel mariadb

  # tmux-yank 剪贴板（X11: xclip/xsel；Wayland: wl-clipboard）
  sudo dnf install -y xclip xsel wl-clipboard

  # 设置 pkg-config 路径
  export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/usr/lib64/pkgconfig:/usr/lib/pkgconfig"

  # 安装 Python mysqlclient 包
  pip_install_system mysqlclient
}

# RHEL/CentOS 系初始化
init_rhel() {
  echo "---- Initializing RHEL/CentOS/Rocky ----"

  # 基础工具
  sudo yum install -y curl wget pkgconfig

  # 开发工具链
  sudo yum install -y git autoconf automake binutils bison flex gawk \
    gettext gzip libtool m4 make patch sed texinfo

  # GCC
  sudo yum install -y gcc gcc-c++

  # Python 环境
  sudo yum install -y python3-pip python3-virtualenv

  # 实用工具
  sudo yum install -y gdb vim-enhanced zip unzip tar xz procps-ng

  # 构建依赖
  sudo yum install -y readline-devel openssl-devel sqlite sqlite-devel

  # ImageMagick
  sudo yum install -y ImageMagick ImageMagick-devel

  # MySQL/MariaDB 客户端
  sudo yum install -y mariadb-devel mariadb

  # tmux-yank 剪贴板（尽量装齐；部分发行版可能没有 wl-clipboard）
  sudo yum install -y xclip xsel || sudo yum install -y xclip
  sudo yum install -y wl-clipboard 2>/dev/null || true

  # 设置 pkg-config 路径
  export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/usr/lib64/pkgconfig:/usr/lib/pkgconfig"

  # 安装 Python mysqlclient 包
  pip_install_system mysqlclient
}

# macOS 初始化
init_darwin() {
  echo "---- Initializing macOS ----"
  xcode-select --install 2>/dev/null || true

  # 确保 PATH 包含 homebrew
  if [ -x "/opt/homebrew/bin/brew" ]; then
    eval "$("/opt/homebrew/bin/brew" shellenv 2>/dev/null)"
  elif [ -x "/usr/local/bin/brew" ]; then
    eval "$("/usr/local/bin/brew" shellenv 2>/dev/null)"
  fi

  # macOS 通过 Homebrew 安装大部分工具（见 init_homebrew）
  # 这里只安装 Homebrew 未覆盖或需要特殊处理的包

  # 设置 pkg-config 路径
  if [ -d "/opt/homebrew/lib/pkgconfig" ]; then
    export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/opt/homebrew/lib/pkgconfig"
  elif [ -d "/usr/local/lib/pkgconfig" ]; then
    export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:/usr/local/lib/pkgconfig"
  fi

  # 安装 Python mysqlclient 包
  pip_install_system mysqlclient
}

# 更改用户默认 shell 为 zsh（优先使用 homebrew 安装的 zsh）
change_default_shell() {
  # 检查当前 shell 是否已经是 zsh
  if [[ "$SHELL" == */zsh ]]; then
    echo "Current shell is already zsh: $SHELL"
    return 0
  fi

  # 设置 brew PATH（确保能找到 homebrew 安装的 zsh）
  local brew_prefix=""
  if [[ "$ID" == "darwin" ]]; then
    if [ -x "/opt/homebrew/bin/brew" ]; then
      brew_prefix="/opt/homebrew"
    elif [ -x "/usr/local/bin/brew" ]; then
      brew_prefix="/usr/local"
    fi

    # 加载 brew 环境变量
    if [ -n "$brew_prefix" ]; then
      eval "$("$brew_prefix/bin/brew" shellenv 2>/dev/null)"
    fi
  fi

  # 确定 zsh 路径：优先使用 homebrew 安装的 zsh
  local zsh_path=""

  # 尝试通过 brew --prefix 获取 zsh 路径
  if command -v brew &>/dev/null; then
    local brew_zsh
    brew_zsh="$(brew --prefix zsh 2>/dev/null)"
    if [ -n "$brew_zsh" ] && [ -x "$brew_zsh/bin/zsh" ]; then
      zsh_path="$brew_zsh/bin/zsh"
      echo "Found Homebrew zsh: $zsh_path"
    fi
  fi

  # 回退：直接检查常见路径
  if [ -z "$zsh_path" ]; then
    for path in "/opt/homebrew/bin/zsh" "/usr/local/bin/zsh"; do
      if [ -x "$path" ]; then
        zsh_path="$path"
        echo "Found Homebrew zsh: $zsh_path"
        break
      fi
    done
  fi

  # 回退到系统自带的 zsh
  if [ -z "$zsh_path" ] && [ -x "/bin/zsh" ]; then
    zsh_path="/bin/zsh"
    echo "Found system zsh: $zsh_path"
  fi

  # 如果没有找到 zsh
  if [ -z "$zsh_path" ]; then
    echo "Warning: zsh not found. Please install zsh first."
    return 1
  fi

  # 确保 zsh 在 /etc/shells 中
  if ! grep -Fxq "$zsh_path" /etc/shells 2>/dev/null; then
    echo "Adding $zsh_path to /etc/shells..."
    echo "$zsh_path" | sudo tee -a /etc/shells >/dev/null
  fi

  # 让用户确认是否更改 shell
  echo ""
  echo "当前 Shell: $SHELL"
  echo "将更改默认 Shell 为: $zsh_path"
  echo ""
  if ! confirm "是否将默认 Shell 更改为 zsh?" "N"; then
    echo "跳过默认 Shell 更改。"
    return 0
  fi

  # 更改默认 shell
  echo "正在将默认 Shell 更改为 $zsh_path..."
  chsh -s "$zsh_path"

  if [ $? -eq 0 ]; then
    echo "默认 Shell 更改成功！"
    echo "请重启终端或重新登录以生效。"
  else
    echo "更改默认 Shell 失败，可尝试手动运行: chsh -s $zsh_path"
    return 1
  fi
}

# 配置 zsh
config_zsh() {
  if ! confirm "是否配置 zsh（oh-my-zsh/默认 Shell）?" "N"; then
    echo "跳过 zsh 配置。"
    return 0
  fi

  echo "---- Configuring zsh ----"

  # 设置 ZSH_CUSTOM 路径
  if [ -f ~/.zshrc ]; then
    if [[ "$ID" == "darwin" ]]; then
      sed -i '' 's/^# ZSH_CUSTOM.*/ZSH_CUSTOM=~\/.config\/zsh\/oh-my-zsh/g' ~/.zshrc
    else
      sed -i 's/^# ZSH_CUSTOM.*/ZSH_CUSTOM=~\/.config\/zsh\/oh-my-zsh/g' ~/.zshrc
    fi
  fi

  # 安装 oh-my-zsh
  if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Installing oh-my-zsh..."
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
  else
    echo "oh-my-zsh is already installed"
  fi

  # 更改用户默认 shell 为 zsh
  change_default_shell

  echo "zsh configured successfully!"
}

# 通用后置初始化
post_init() {
  echo "---- Post Initialization ----"
  # 配置 zsh
  config_zsh
  init_docker
}

# 系统初始化分发器
dispatch_init() {
  # 显示将要执行的操作并请求用户确认
  echo ""
  echo "============================================"
  echo "  System: $ID"
  echo "============================================"
  echo ""
  echo "将通过系统包管理器安装软件包。"
  echo "需要 root/sudo 权限。"
  echo ""

  if ! confirm "是否安装系统软件包?" "N"; then
    echo "跳过系统软件包安装。"
    return 0
  fi

  case "$ID" in
  ubuntu | debian | pop | linuxmint)
    init_debian
    ;;
  arch | manjaro | endeavouros)
    init_arch
    ;;
  fedora)
    init_fedora
    ;;
  rhel | centos | rocky | almalinux)
    init_rhel
    ;;
  alinux | amzn)
    echo "Cloud Linux ($ID) detected, using RHEL init"
    init_rhel
    ;;
  opensuse-leap | opensuse-tumbleweed)
    echo "openSUSE detected, manual setup may be required"
    ;;
  darwin)
    init_darwin
    ;;
  *)
    echo "Error: Your system ($ID) is not supported"
    echo "Please install dependencies manually"
    exit 1
    ;;
  esac
}

# 初始化系统
setup_system() {
  echo "Running system setup..."

  common_init
  detect_os
  dispatch_init
  post_init

  echo "System initialization completed!"
}
