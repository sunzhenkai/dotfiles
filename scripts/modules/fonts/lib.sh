#!/bin/bash
# Font installation script with system adaptation
# 字体全部从上游 release 下载（固定版本），不再把字体压缩包放进仓库。

source "$SCRIPT_DIR/scripts/lib/common.sh"

# 格式：URL|文件名过滤（find -name 模式）
FONT_SOURCES=(
  "https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-NF-CN.zip|*.ttf"
  "https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMonoNormalNL-Variable.zip|*.ttf"
  "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip|JetBrainsMono*.ttf"
  "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/0xProto.tar.xz|*NerdFontMono-*.ttf"
  "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/SourceCodePro.tar.xz|*NerdFontMono-*.ttf"
)

# Detect OS
detect_os() {
  if [ -n "${DOTF_OS:-}" ]; then
    ID="$DOTF_OS"
    export ID
    echo "Planned OS: $ID"
    return 0
  fi
  if [ -f "/etc/os-release" ]; then
    . /etc/os-release
  elif [ -f "/etc/arch-release" ]; then
    export ID=arch
  elif [[ "$OSTYPE" =~ ^darwin ]]; then
    export ID=darwin
  else
    echo "Unknown OS."
    exit 1
  fi
  echo "Detected OS: $ID"
}

# Check if Linux has GUI (X11 or Wayland)
has_linux_gui() {
  # ${VAR-} 避免 set -u 下未设置变量直接展开报错
  if [ -n "${DISPLAY-}" ] || [ -n "${WAYLAND_DISPLAY-}" ]; then
    return 0
  fi

  return 1
}

# 下载并解出全部字体到 $1（只放 .ttf）
download_fonts() {
  local target_dir="$1" entry url pattern archive work
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl not found. Cannot download fonts."
    return 1
  fi
  work="$(mktemp -d "${TMPDIR:-/tmp}/dotf-fonts.XXXXXX")" || return 1
  for entry in "${FONT_SOURCES[@]}"; do
    url="${entry%%|*}"
    pattern="${entry#*|}"
    archive="$work/$(basename "$url")"
    echo "Downloading $(basename "$url")..."
    if ! curl -fsSL --proto '=https' --proto-redir '=https' --retry 3 -o "$archive" "$url"; then
      echo "  ⚠ 下载失败，跳过: $url"
      continue
    fi
    mkdir -p "$work/x"
    case "$archive" in
    *.zip) unzip -oq "$archive" -d "$work/x" ;;
    *.tar.xz) tar -xJf "$archive" -C "$work/x" ;;
    *.tar.gz) tar -xzf "$archive" -C "$work/x" ;;
    esac
    find "$work/x" -type f -name "$pattern" -exec mv -f {} "$target_dir/" \; 2>/dev/null || true
    rm -rf "$work/x" "$archive"
  done
  rm -rf "$work"
  echo "Font download completed."
}

# Install fonts on Linux
install_fonts_linux() {
  # Skip if no GUI environment
  if ! has_linux_gui; then
    echo "No GUI environment detected (DISPLAY or WAYLAND_DISPLAY not set), skipping font installation."
    return 0
  fi

  # Check if fc-cache is available
  if ! command -v fc-cache >/dev/null 2>&1; then
    echo "fc-cache not found, fontconfig may not be installed. Skipping font installation."
    return 0
  fi

  echo "Installing fonts on Linux..."

  # 下载到临时目录（旧实现误把 scripts/modules/assets/fonts 当仓库字体目录，本地压缩包从未生效）
  local fonts_dir
  fonts_dir="$(mktemp -d "${TMPDIR:-/tmp}/dotf-fonts-out.XXXXXX")" || return 1
  download_fonts "$fonts_dir" || { rm -rf "$fonts_dir"; return 1; }
  cd "$fonts_dir" || return 1

  # Create system fonts directory
  sudo mkdir -p /usr/share/fonts/local

  # Install fonts
  sudo mv -f ./*.ttf /usr/share/fonts/local/ 2>/dev/null || true

  # Refresh font cache
  sudo fc-cache -fv
  cd - >/dev/null && rm -rf "$fonts_dir"

  echo "Fonts installed successfully on Linux."
}

# Install fonts on macOS
install_fonts_macos() {
  echo "Installing fonts on macOS..."

  # 下载到临时目录（旧实现误把 scripts/modules/assets/fonts 当仓库字体目录，本地压缩包从未生效）
  local fonts_dir
  fonts_dir="$(mktemp -d "${TMPDIR:-/tmp}/dotf-fonts-out.XXXXXX")" || return 1
  download_fonts "$fonts_dir" || { rm -rf "$fonts_dir"; return 1; }
  cd "$fonts_dir" || return 1

  # Create user fonts directory
  mkdir -p ~/Library/Fonts

  # Install fonts to user directory
  mv -f ./*.ttf ~/Library/Fonts/ 2>/dev/null || true
  cd - >/dev/null && rm -rf "$fonts_dir"

  echo "Fonts installed successfully on macOS."
}

setup_fonts() {
  git submodule update --init
  detect_os

  case "$ID" in
  ubuntu | debian | pop | fedora | alinux | amzn | rhel | centos | rocky | opensuse-leap | arch | manjaro)
    install_fonts_linux
    ;;
  darwin)
    install_fonts_macos
    ;;
  *)
    echo "Your system ($ID) is not supported by this script."
    echo "Please install fonts manually."
    exit 1
    ;;
  esac
}
