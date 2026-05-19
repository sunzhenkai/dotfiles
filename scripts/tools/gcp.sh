#!/bin/bash
# Google Cloud CLI (gcloud) 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_gcp_cli() {
  echo "---- Installing Google Cloud CLI ----"

  local install_dir="$HOME/google-cloud-sdk"

  if [ -d "$install_dir" ] && command -v gcloud &>/dev/null; then
    echo "Google Cloud CLI is already installed: $(gcloud --version 2>&1 | head -1)"
    if ! confirm "Do you want to update/reinstall Google Cloud CLI?" "N"; then
      echo "Skipping Google Cloud CLI installation."
      _install_gke_auth_plugin
      return 0
    fi
    echo "Updating Google Cloud CLI..."
  fi

  local arch
  case "$(uname -m)" in
  x86_64) arch="x86_64" ;;
  aarch64 | arm64) arch="arm" ;;
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

  # arm64 在 macOS 上使用 arm 后缀
  if [[ "$os" == "darwin" && "$(uname -m)" == "arm64" ]]; then
    arch="arm"
  fi

  local filename="google-cloud-cli-${os}-${arch}.tar.gz"
  local url="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/${filename}"

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  echo "Downloading Google Cloud CLI (${os}-${arch})..."
  if ! curl -fsSL -o "$tmp_dir/$filename" "$url"; then
    echo "Error: Failed to download Google Cloud CLI"
    rm -rf "$tmp_dir"
    return 1
  fi

  echo "Extracting Google Cloud CLI..."
  if ! tar -xzf "$tmp_dir/$filename" -C "$HOME"; then
    echo "Error: Failed to extract Google Cloud CLI"
    rm -rf "$tmp_dir"
    return 1
  fi
  rm -rf "$tmp_dir"

  echo "Running gcloud installer..."
  # --disable-installation-options 跳过交互提示
  if ! "$install_dir/install.sh" --quiet --path-update=true; then
    echo "Error: gcloud install.sh failed"
    return 1
  fi

  # 使 gcloud 在当前 shell 中可用
  # shellcheck source=/dev/null
  source "$install_dir/path.bash.inc" 2>/dev/null || true

  echo "Google Cloud CLI installed to: $install_dir"
  echo "Please restart your shell or run: source ~/google-cloud-sdk/path.bash.inc"

  _install_gke_auth_plugin
}

_install_gke_auth_plugin() {
  echo ""
  echo "---- Installing gke-gcloud-auth-plugin ----"

  if gcloud components list --filter="id=gke-gcloud-auth-plugin" --format="value(state.name)" 2>/dev/null | grep -q "Installed"; then
    echo "gke-gcloud-auth-plugin is already installed."
    return 0
  fi

  if ! gcloud components install gke-gcloud-auth-plugin --quiet; then
    echo "Error: Failed to install gke-gcloud-auth-plugin"
    return 1
  fi

  echo "gke-gcloud-auth-plugin installed successfully!"
  echo "Set USE_GKE_GCLOUD_AUTH_PLUGIN=True in your shell environment for kubectl."
}
