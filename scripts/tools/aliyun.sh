#!/bin/bash
# 阿里云 CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_aliyun_cli() {
  echo "---- Installing Aliyun CLI ----"

  local bin_dir="$HOME/.local/bin"
  local tool_path="$bin_dir/aliyun"

  if [ -f "$tool_path" ]; then
    echo "Aliyun CLI is already installed: $("$tool_path" version 2>&1 | head -1)"
    return 0
  fi

  local arch
  case "$(uname -m)" in
  x86_64) arch="amd64" ;;
  aarch64 | arm64) arch="arm64" ;;
  *)
    echo "Error: Unsupported architecture: $(uname -m)"
    return 1
    ;;
  esac

  local os
  case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="macosx" ;;
  *)
    echo "Error: Unsupported OS: $(uname -s)"
    return 1
    ;;
  esac

  # 从 GitHub Releases 获取最新版本号
  echo "Fetching latest Aliyun CLI version..."
  local version
  version="$(curl -fsSL "https://api.github.com/repos/aliyun/aliyun-cli/releases/latest" \
    | grep '"tag_name"' | sed 's/.*"tag_name": *"v\([^"]*\)".*/\1/')"
  if [[ -z "$version" ]]; then
    echo "Error: Failed to fetch latest version, using fallback version"
    version="3.0.271"
  fi

  local filename="aliyun-cli-${os}-${version}-${arch}.tgz"
  local url="https://github.com/aliyun/aliyun-cli/releases/download/v${version}/${filename}"

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  echo "Downloading Aliyun CLI v${version} (${os}-${arch})..."
  if ! curl -fsSL -o "$tmp_dir/$filename" "$url"; then
    echo "Error: Failed to download Aliyun CLI"
    rm -rf "$tmp_dir"
    return 1
  fi

  if ! tar -xzf "$tmp_dir/$filename" -C "$tmp_dir"; then
    echo "Error: Failed to extract Aliyun CLI"
    rm -rf "$tmp_dir"
    return 1
  fi

  mkdir -p "$bin_dir"
  if [ -f "$tmp_dir/aliyun" ]; then
    cp "$tmp_dir/aliyun" "$tool_path"
    chmod +x "$tool_path"
  else
    echo "Error: aliyun binary not found in extracted files"
    rm -rf "$tmp_dir"
    return 1
  fi

  rm -rf "$tmp_dir"
  echo "Aliyun CLI v${version} installed to: $tool_path"
  echo "Run 'aliyun configure' to set up your AccessKey."
}
