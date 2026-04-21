# =============================================================================
# Language runtimes & version managers
# =============================================================================

# Helper: fix plugin binary paths for asdf/mise
# Usage: _fix_lang_plugin_path <command> <data_dir> <plugin> ...
function _fix_lang_plugin_path() {
  local mgr=$1; shift
  local data_dir=$1; shift
  local ver
  for plugin in $@; do
    ver=$(${mgr} current ${plugin} 2>/dev/null | awk 'END{if(NF>1) print $2; else print $1}')
    [[ -z "$ver" ]] && continue
    for d in "${data_dir}/installs/${plugin}/${ver}/bin" \
             "${data_dir}/installs/${plugin}/${ver}/packages/bin"; do
      [[ -d "$d" ]] && export PATH="$d:$PATH"
    done
  done
}

# nvm
if [[ -z "$NVM_DIR" && -e "$HOME/.nvm" ]]; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
fi

# asdf
if command -v asdf >/dev/null; then
  export ASDF_DATA_DIR="${ASDF_DATA_DIR:-$HOME/.asdf}"
  export PATH="${ASDF_DATA_DIR}/shims:$PATH"
  _fix_lang_plugin_path asdf "$ASDF_DATA_DIR" python golang nodejs
fi

# mise
if command -v mise >/dev/null; then
  export MISE_DATA_DIR="${MISE_DATA_DIR:-$HOME/.local/share/mise}"
  export PATH="${MISE_DATA_DIR}/shims:$PATH"
  _fix_lang_plugin_path mise "$MISE_DATA_DIR" python golang nodejs
fi

# anaconda3 / conda
for p in "$HOME/anaconda3" "$HOME/.ii/programs/anaconda3"; do
  if [[ -x "$p/bin/conda" ]]; then
    eval "$("$p/bin/conda" shell.zsh hook)"
    break
  fi
done

# rust / cargo
if [[ -e "$HOME/.cargo/env" ]]; then
  source "$HOME/.cargo/env"
elif [[ -d "$HOME/.cargo/bin" ]]; then
  export PATH="$HOME/.cargo/bin:$PATH"
fi

# golang
if [[ -n "$GOPATH" ]]; then
  export PATH="$GOPATH/bin:$PATH"
fi
