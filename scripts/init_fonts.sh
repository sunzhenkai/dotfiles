#!/bin/bash
# Font installation script with system adaptation
# Maple Mono NF CN https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-NF-CN.zip

FONT_URL="https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-NF-CN.zip"
FONT_ZIP="MapleMono-NF-CN.zip"

# Detect OS
detect_os() {
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
  # Check for display server
  if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    return 0
  fi

  return 1
}

# Download fonts from GitHub
download_fonts() {
  local target_dir="$1"

  echo "Downloading Maple Mono NF CN font..."
  cd "$target_dir" || return 1

  # Download the font zip file
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$FONT_URL" -o "$FONT_ZIP"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$FONT_URL" -O "$FONT_ZIP"
  else
    echo "Neither curl nor wget found. Cannot download fonts."
    return 1
  fi

  if [ ! -f "$FONT_ZIP" ]; then
    echo "Failed to download font file."
    return 1
  fi

  echo "Extracting font archive..."
  unzip -oq "$FONT_ZIP" -d maple_font_extracted

  # Find and move all ttf files to target directory
  find maple_font_extracted -name "*.ttf" -exec mv {} "$target_dir/" \; 2>/dev/null || true

  # Cleanup
  rm -rf maple_font_extracted "$FONT_ZIP"

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

  local dotfiles_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local fonts_dir="$dotfiles_root/assets/fonts"

  mkdir -p "$fonts_dir"
  cd "$fonts_dir" || exit 1

  # Download and extract fonts from GitHub
  download_fonts "$fonts_dir"

  # Extract local font archives (suppress macOS extended attributes warnings)
  for f in *.tar.gz; do
    [ -f "$f" ] && tar -xzf "$f" 2>/dev/null
  done

  # Create system fonts directory
  sudo mkdir -p /usr/share/fonts/local

  # Install fonts
  sudo mv *.ttf /usr/share/fonts/local/ 2>/dev/null || true

  # Refresh font cache
  sudo fc-cache -fv

  echo "Fonts installed successfully on Linux."
}

# Install fonts on macOS
install_fonts_macos() {
  echo "Installing fonts on macOS..."

  local dotfiles_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local fonts_dir="$dotfiles_root/assets/fonts"

  mkdir -p "$fonts_dir"
  cd "$fonts_dir" || exit 1

  # Download and extract fonts from GitHub
  download_fonts "$fonts_dir"

  # Extract local font archives (suppress macOS extended attributes warnings)
  for f in *.tar.gz; do
    [ -f "$f" ] && tar -xzf "$f" 2>/dev/null
  done

  # Create user fonts directory
  mkdir -p ~/Library/Fonts

  # Install fonts to user directory
  mv *.ttf ~/Library/Fonts/ 2>/dev/null || true

  echo "Fonts installed successfully on macOS."
}

# Main
main() {
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

main "$@"
