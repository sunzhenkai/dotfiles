#!/bin/bash
# Font installation script with system adaptation

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
  
  # Check if fc-cache exists (fontconfig is installed)
  if command -v fc-cache >/dev/null 2>&1; then
    return 0
  fi
  
  return 1
}

# Install fonts on Linux
install_fonts_linux() {
  # Skip if no GUI environment
  if ! has_linux_gui; then
    echo "No GUI environment detected, skipping font installation."
    return 0
  fi
  
  echo "Installing fonts on Linux..."

  local dotfiles_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local fonts_dir="$dotfiles_root/assets/fonts"

  if [ ! -d "$fonts_dir" ]; then
    echo "Fonts directory not found: $fonts_dir"
    exit 1
  fi

  cd "$fonts_dir" || exit 1

  # Extract font archives (suppress macOS extended attributes warnings)
  for f in *.tar.gz; do
    [ -f "$f" ] && tar -xzf "$f" 2>/dev/null
  done

  # Create system fonts directory
  sudo mkdir -p /usr/share/fonts/local

  # Install fonts
  sudo mv *.ttf /usr/share/fonts/local/ 2>/dev/null || true

  # Refresh font cache
  if command -v fc-cache >/dev/null 2>&1; then
    sudo fc-cache -fv
  fi

  echo "Fonts installed successfully on Linux."
}

# Install fonts on macOS
install_fonts_macos() {
  echo "Installing fonts on macOS..."

  local dotfiles_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local fonts_dir="$dotfiles_root/assets/fonts"

  if [ ! -d "$fonts_dir" ]; then
    echo "Fonts directory not found: $fonts_dir"
    exit 1
  fi

  cd "$fonts_dir" || exit 1

  # Extract font archives (suppress macOS extended attributes warnings)
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
