# =============================================================================
# Locale, pkg-config, vcpkg, Google Cloud SDK
# =============================================================================

# locale
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# pkg-config — simplified loop
if [[ -z "$PKG_CONFIG_PATH" ]]; then
  local _pc_paths=(
    /usr/lib/x86_64-linux-gnu/pkgconfig
    /usr/lib64/pkgconfig
    /usr/lib/pkgconfig
    /usr/local/lib/pkgconfig
    /usr/local/share/pkgconfig
  )
  for p in $_pc_paths; do
    [[ -d "$p" ]] && PKG_CONFIG_PATH="${p}${PKG_CONFIG_PATH+:$PKG_CONFIG_PATH}"
  done
  # homebrew pkg-config paths
  for b in /home/linuxbrew/.linuxbrew /opt/homebrew; do
    [[ -d "$b/lib/pkgconfig" ]] && PKG_CONFIG_PATH="$b/lib/pkgconfig${PKG_CONFIG_PATH+:$PKG_CONFIG_PATH}"
  done
  export PKG_CONFIG_PATH
fi

# vcpkg
local _vcpkg=$HOME/.local/vcpkg
if [[ -z "$VCPKG_ROOT" && -e "$_vcpkg" ]]; then
  export VCPKG_ROOT=$_vcpkg
  export PATH="$_vcpkg:$PATH"
fi

# Google Cloud SDK
if [[ -f "${HOME}/google-cloud-sdk/path.zsh.inc" ]]; then
  source "${HOME}/google-cloud-sdk/path.zsh.inc"
fi
if [[ -f "${HOME}/google-cloud-sdk/completion.zsh.inc" ]]; then
  source "${HOME}/google-cloud-sdk/completion.zsh.inc"
fi

# senv
if command -v senv >/dev/null; then
  eval $(senv env export)
fi
