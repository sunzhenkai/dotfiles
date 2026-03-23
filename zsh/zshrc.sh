export ICONFIG_FLAG=1

export EDITOR="nvim"

# aliases
if [[ -f ~/.config/dotfiles/zsh/aliases.zsh ]]; then
  source ~/.config/dotfiles/zsh/aliases.zsh
fi

# vi mode
if command -v bindkey >/dev/null; then
  bindkey -v
fi
# this makes the switch between modes quicker
export KEYTIMEOUT=1
export LESSCHARSET=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# envs
# personal binaries
# bash <(curl -L https://zellij.dev/launchbash <(curl -L https://zellij.dev/launch))
export PATH="${HOME}/.local/bin:${PATH}"
# LOCAL, DEV, PROD
export DEVELOPMENT_ENV=LOCAL

# homebrew
HOMEBREW_ROOT="/home/linuxbrew/.linuxbrew"
if [[ -e "$HOMEBREW_ROOT" ]]; then
  eval "$($HOMEBREW_ROOT/bin/brew shellenv)"
  # export LD_LIBRARY_PATH="$(brew --prefix)/lib:$LD_LIBRARY_PATH"
fi
HOMEBREW_ROOT_MACOS="/opt/homebrew"
if [[ -e "$HOMEBREW_ROOT_MACOS" ]]; then
  eval "$($HOMEBREW_ROOT_MACOS/bin/brew shellenv)"
  export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:$DYLD_FALLBACK_LIBRARY_PATH"
fi

# fix PKG_CONFIG_PATH if empty
if [[ -z "$PKG_CONFIG_PATH" ]]; then
  # common pkg-config paths
  PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/usr/local/share/pkgconfig"
  # Debian/Ubuntu multiarch
  if [[ -d "/usr/lib/x86_64-linux-gnu/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
  fi
  if [[ -d "/usr/lib/aarch64-linux-gnu/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/lib/aarch64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
  fi
  # Fedora/RHEL/CentOS (64-bit)
  if [[ -d "/usr/lib64/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/lib64/pkgconfig:$PKG_CONFIG_PATH"
  fi
  # Arch Linux / openSUSE / Gentoo / Fedora (32-bit fallback)
  if [[ -d "/usr/lib/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/lib/pkgconfig:$PKG_CONFIG_PATH"
  fi
  # FreeBSD
  if [[ -d "/usr/local/lib/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
  fi
  # macOS system
  if [[ -d "/usr/lib/pkgconfig" ]]; then
    PKG_CONFIG_PATH="/usr/lib/pkgconfig:$PKG_CONFIG_PATH"
  fi
  # add homebrew paths if available
  if [[ -n "$HOMEBREW_ROOT" && -e "$HOMEBREW_ROOT/lib/pkgconfig" ]]; then
    PKG_CONFIG_PATH="$HOMEBREW_ROOT/lib/pkgconfig:$PKG_CONFIG_PATH"
  fi
  if [[ -n "$HOMEBREW_ROOT_MACOS" && -e "$HOMEBREW_ROOT_MACOS/lib/pkgconfig" ]]; then
    PKG_CONFIG_PATH="$HOMEBREW_ROOT_MACOS/lib/pkgconfig:$PKG_CONFIG_PATH"
  fi
  export PKG_CONFIG_PATH
fi

# BREW_BISON=/opt/homebrew/opt/bison
# if [[ -e "$BREW_BISON" ]]; then
#   export PATH="$BREW_BISON/bin:$PATH"
#   export LDFLAGS="-L$BREW_BISON/lib"
# fi
# BREW_FLEX=/opt/homebrew/opt/flex
# if [[ -e "$BREW_FLEX" ]]; then
#   export PATH="$BREW_FLEX/bin:$PATH"
#   export LDFLAGS="-L$BREW_FLEX/lib"
#   export CPPFLAGS="-I$BREW_FLEX/include"
# fi

# using startship as alternative
#export Z10K_CONFIG=~/.config/zsh/p10k.zsh
#[[ ! -f $Z10K_CONFIG ]] || source $Z10K_CONFIG

# vcpkg root
DEFAULT_VCPKG_ROOT=$HOME/.local/vcpkg
if [[ "$VCPKG_ROOT" == "" && -e ${DEFAULT_VCPKG_ROOT} ]]; then
  export VCPKG_ROOT=${DEFAULT_VCPKG_ROOT}
  export PATH="$DEFAULT_VCPKG_ROOT:$PATH"
fi

# nvm
DFT_NVM_DIR="$HOME/.nvm"
if [[ "$NVM_DIR" == "" && -e "$DFT_NVM_DIR" ]]; then
  export NVM_DIR="$DFT_NVM_DIR"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion
fi

function fix_asdf_plugin_path() {
  local t_plugin=$1
  if asdf current ${t_plugin} >/dev/null; then
    local t_plugin_version=$(asdf current $t_plugin | grep $t_plugin | awk '{print$2}')
    local t_bin_path="${ASDF_DATA_DIR}/installs/${t_plugin}/${t_plugin_version}/bin"
    if [[ -e "$t_bin_path" ]]; then
      export PATH="$t_bin_path:$PATH"
    fi
    local t_pkg_bin_path="${ASDF_DATA_DIR}/installs/${t_plugin}/${t_plugin_version}/packages/bin"
    if [[ -e "$t_pkg_bin_path" ]]; then
      export PATH="$t_pkg_bin_path:$PATH"
    fi
  fi
}

# asdf
if command -v asdf >/dev/null; then
  export ASDF_DATA_DIR="${ASDF_DATA_DIR:-$HOME/.asdf}"
  export PATH="${ASDF_DATA_DIR}/shims:$PATH"
  # fix python binraries
  fix_asdf_plugin_path python
  fix_asdf_plugin_path golang
  fix_asdf_plugin_path nodejs
fi

function fix_mise_plugin_path() {
  local t_plugin=$1
  if mise current ${t_plugin} >/dev/null 2>&1; then
    local t_plugin_version=$(mise current $t_plugin | grep $t_plugin | awk '{print$2}')
    local t_bin_path="${MISE_DATA_DIR}/installs/${t_plugin}/${t_plugin_version}/bin"
    if [[ -e "$t_bin_path" ]]; then
      export PATH="$t_bin_path:$PATH"
    fi
    local t_pkg_bin_path="${MISE_DATA_DIR}/installs/${t_plugin}/${t_plugin_version}/packages/bin"
    if [[ -e "$t_pkg_bin_path" ]]; then
      export PATH="$t_pkg_bin_path:$PATH"
    fi
  fi
}

# mise
if command -v mise >/dev/null; then
  export MISE_DATA_DIR="${MISE_DATA_DIR:-$HOME/.local/share/mise}"
  export PATH="${MISE_DATA_DIR}/shims:$PATH"
  # fix python binraries
  fix_mise_plugin_path python
  fix_mise_plugin_path golang
  fix_mise_plugin_path nodejs
fi

# private config
PRIVATE_CONFIG_ENV="$HOME/.config/private-config/envs/env"
if [[ -e "$PRIVATE_CONFIG_ENV" ]]; then
  source "$PRIVATE_CONFIG_ENV"
fi

# rust / cargo
# put cargo at the end, and it will sometimes build the nightly version
export CARGO_ENV="$HOME/.cargo/env"
export CARGO_BIN="$HOME/.cargo/bin"
if [[ -e ${CARGO_ENV} ]]; then
  source ${CARGO_ENV}
elif [[ -e "${CARGO_BIN}" ]]; then
  export PATH="$CARGO_BIN:$PATH"
fi

# golang
if [[ -n "$GOPATH" ]]; then
  export PATH="$GOPATH/bin:$PATH"
fi

if command -v senv >/dev/null; then
  #echo "Init senv: $(senv env export)"
  eval $(senv env export)
fi

# anaconda3 / conda
# >>> conda initialize >>>
for p in "$HOME/anaconda3" "$HOME/.ii/programs/anaconda3"; do
  if [[ -x "$p/bin/conda" ]]; then
    eval "$("$p/bin/conda" shell.zsh hook)"
    break
  fi
done
# <<< conda initialize <<<
