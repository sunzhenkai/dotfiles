#!/bin/bash
# AWS CLI v2 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_aws_cli() {
  echo "---- Installing AWS CLI v2 ----"

  if command -v aws &>/dev/null; then
    echo "AWS CLI is already installed: $(aws --version 2>&1)"
    if ! confirm "Do you want to update/reinstall AWS CLI?" "N"; then
      echo "Skipping AWS CLI installation."
      return 0
    fi
    echo "Updating AWS CLI..."
  fi

  local arch
  case "$(uname -m)" in
  x86_64) arch="x86_64" ;;
  aarch64 | arm64) arch="aarch64" ;;
  *)
    echo "Error: Unsupported architecture: $(uname -m)"
    return 1
    ;;
  esac

  local os
  case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="darwin" ;;
  *)
    echo "Error: Unsupported OS: $(uname -s)"
    return 1
    ;;
  esac

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  local install_dir="$HOME/.local/aws-cli"
  local bin_dir="$HOME/.local/bin"
  mkdir -p "$bin_dir"

  if [[ "$os" == "linux" ]]; then
    local url="https://awscli.amazonaws.com/awscli-exe-linux-${arch}.zip"
    echo "Downloading AWS CLI v2 (linux-${arch})..."
    if ! curl -fsSL -o "$tmp_dir/awscliv2.zip" "$url"; then
      echo "Error: Failed to download AWS CLI"
      rm -rf "$tmp_dir"
      return 1
    fi
    if ! unzip -q "$tmp_dir/awscliv2.zip" -d "$tmp_dir"; then
      echo "Error: Failed to unzip AWS CLI"
      rm -rf "$tmp_dir"
      return 1
    fi
    if ! "$tmp_dir/aws/install" --install-dir "$install_dir" --bin-dir "$bin_dir" --update; then
      echo "Error: AWS CLI installation failed"
      rm -rf "$tmp_dir"
      return 1
    fi
  elif [[ "$os" == "darwin" ]]; then
    local url="https://awscli.amazonaws.com/AWSCLIV2.pkg"
    echo "Downloading AWS CLI v2 for macOS..."
    if ! curl -fsSL -o "$tmp_dir/AWSCLIV2.pkg" "$url"; then
      echo "Error: Failed to download AWS CLI"
      rm -rf "$tmp_dir"
      return 1
    fi
    echo "Installing AWS CLI (requires sudo)..."
    if ! sudo installer -pkg "$tmp_dir/AWSCLIV2.pkg" -target /; then
      echo "Error: AWS CLI installation failed"
      rm -rf "$tmp_dir"
      return 1
    fi
  fi

  rm -rf "$tmp_dir"
  echo "AWS CLI installed successfully!"
  echo "Run 'aws configure' to set up your credentials."
}
