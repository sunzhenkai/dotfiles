# =============================================================================
# OpenSpec shell completions configuration
# =============================================================================
# fpath=("/home/wii/.oh-my-zsh/custom/completions" $fpath)
# OPENSPEC:END

export ICONFIG_FLAG=1
export EDITOR="nvim"

# =============================================================================
# Modules
# =============================================================================

local _mod_dir="${0:a:h}/modules"

# Plugin manager (znap) — must load first
source "$_mod_dir/plugins.zsh"

# oh-my-zsh lib toggle (ENABLE_OMZ=true)
source "$_mod_dir/omz.zsh"

# aliases
if [[ -f "${0:a:h}/aliases.zsh" ]]; then
  source "${0:a:h}/aliases.zsh"
fi

# vi mode, misc, paths, lang, private
source "$_mod_dir/vi-mode.zsh"
source "$_mod_dir/misc.zsh"
source "$_mod_dir/paths.zsh"
source "$_mod_dir/lang.zsh"

# =============================================================================
# Prompt (starship)
# =============================================================================
if command -v starship >/dev/null; then
  znap eval starship 'starship init zsh'
fi

[[ -e ~/.envrc ]] && source ~/.envrc
