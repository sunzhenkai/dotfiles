#!/bin/bash
# ossutil 2.0 阿里云 OSS 命令行工具安装

install_ossutil() {
  echo "---- Installing ossutil 2.0 ----"

  local install_dir="$HOME/.local/bin"
  local tool_path="$install_dir/ossutil"

  # 检查是否已安装
  if [ -f "$tool_path" ]; then
    echo "ossutil is already installed at: $tool_path"
    local reply
    read -r -p "Do you want to update/reinstall ossutil? [y/N]: " reply
    if [[ ! "$reply" =~ ^[Yy] ]]; then
      echo "Skipping ossutil installation."
      return 0
    fi
    echo "Updating ossutil..."
  else
    mkdir -p "$install_dir"
  fi

  # 检测系统架构
  local arch
  case "$(uname -m)" in
  x86_64) arch="amd64" ;;
  aarch64 | arm64) arch="arm64" ;;
  *)
    echo "Error: Unsupported architecture: $(uname -m)"
    return 1
    ;;
  esac

  # 检测操作系统
  local os
  case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="mac" ;;
  *)
    echo "Error: Unsupported OS: $(uname -s)"
    return 1
    ;;
  esac

  local version="2.2.1"
  local filename="ossutil-${version}-${os}-${arch}.zip"
  local url="https://gosspublic.alicdn.com/ossutil/v2/${version}/${filename}"

  # 创建临时目录
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  echo "Downloading ossutil ${version} (${os}-${arch})..."

  if ! curl -fsSL -o "$tmp_dir/$filename" "$url"; then
    echo "Error: Failed to download ossutil"
    rm -rf "$tmp_dir"
    return 1
  fi

  # 解压
  if ! unzip -o "$tmp_dir/$filename" -d "$tmp_dir"; then
    echo "Error: Failed to unzip ossutil"
    rm -rf "$tmp_dir"
    return 1
  fi

  # 查找并安装二进制文件
  local extracted_dir="$tmp_dir/ossutil-${version}-${os}-${arch}"
  if [ -f "$extracted_dir/ossutil" ]; then
    cp "$extracted_dir/ossutil" "$tool_path"
    chmod +x "$tool_path"
    echo "ossutil ${version} installed to: $tool_path"
  else
    echo "Error: ossutil binary not found in extracted files"
    rm -rf "$tmp_dir"
    return 1
  fi

  # 清理
  rm -rf "$tmp_dir"
  echo "ossutil installed successfully!"
  echo "Run 'ossutil config' to configure your AccessKey and region."
}
