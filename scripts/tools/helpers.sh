#!/bin/bash
# Go 二进制工具通用安装函数

# 通用 Go 项目编译安装
# 参数: $1=工具名称, $2=git仓库地址, $3=安装目录(可选,默认~/.local/bin)
install_go_binary() {
  local tool_name="$1"
  local git_repo="$2"
  local install_dir="${3:-$HOME/.local/bin}"
  local tool_path="$install_dir/$tool_name"

  echo "---- Installing $tool_name binary ----"

  # 检查 go 命令是否存在
  if ! command -v go &>/dev/null; then
    echo "Warning: go not found, skipping $tool_name binary installation"
    echo "Please install Go first (e.g., via mise)"
    return 0
  fi

  # 检查工具是否已存在
  if [ -f "$tool_path" ]; then
    echo "$tool_name is already installed at: $tool_path"
    local reply
    read -r -p "Do you want to update/reinstall $tool_name? [y/N]: " reply
    if [[ ! "$reply" =~ ^[Yy] ]]; then
      echo "Skipping $tool_name installation."
      return 0
    fi
    echo "Updating $tool_name..."
  else
    mkdir -p "$install_dir"
  fi

  # 创建临时目录并编译
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  echo "Building $tool_name in temporary directory: $tmp_dir"

  cd "$tmp_dir" || exit 1
  echo "Cloning $tool_name source code..."
  if ! git clone "$git_repo"; then
    echo "Error: Failed to clone $tool_name repository"
    cd "$SCRIPT_DIR" || exit 1
    rm -rf "$tmp_dir"
    return 1
  fi

  # 获取仓库名（去掉 .git 后缀和路径）
  local repo_name
  repo_name=$(basename "$git_repo" .git)
  cd "$repo_name" || exit 1

  echo "Building $tool_name..."

  # 优先尝试使用 make install
  if [ -f "Makefile" ]; then
    echo "Found Makefile, using 'make install'..."
    if make install PREFIX="$install_dir" INSTALL_DIR="$install_dir" DESTDIR="$install_dir"; then
      echo "$tool_name installed via make install"
    else
      echo "Warning: 'make install' failed, falling back to manual build"
      if ! go build -o "$tool_name" .; then
        echo "Error: Failed to build $tool_name"
        cd "$SCRIPT_DIR" || exit 1
        rm -rf "$tmp_dir"
        return 1
      fi
      # 手动安装
      cp "$tool_name" "$tool_path"
      chmod +x "$tool_path"
      echo "$tool_name installed to: $tool_path"
    fi
  else
    echo "No Makefile found, using manual build..."
    if ! go build -o "$tool_name" .; then
      echo "Error: Failed to build $tool_name"
      cd "$SCRIPT_DIR" || exit 1
      rm -rf "$tmp_dir"
      return 1
    fi
    # 手动安装
    cp "$tool_name" "$tool_path"
    chmod +x "$tool_path"
    echo "$tool_name installed to: $tool_path"
  fi

  # 清理
  cd "$SCRIPT_DIR" || exit 1
  rm -rf "$tmp_dir"
  echo "Temporary directory cleaned up"

  echo "$tool_name binary installed successfully!"
}
