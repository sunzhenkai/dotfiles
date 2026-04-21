# =============================================================================
# PATH & Homebrew
# =============================================================================

# personal binaries
export PATH="${HOME}/.local/bin:${PATH}"
export DEVELOPMENT_ENV=LOCAL

# homebrew — linux
local _brew_linux="/home/linuxbrew/.linuxbrew"
if [[ -e "$_brew_linux" ]]; then
  znap eval brew-linux "$_brew_linux/bin/brew shellenv"
fi

# homebrew — macOS
local _brew_macos="/opt/homebrew"
if [[ -e "$_brew_macos" ]]; then
  znap eval brew-macos "$_brew_macos/bin/brew shellenv"
  export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
fi

# tiup
local _tiup_path="${HOME}/.tiup/bin"
if [[ -e "$_tiup_path" ]]; then
  export PATH="${_tiup_path}:${PATH}"
fi

