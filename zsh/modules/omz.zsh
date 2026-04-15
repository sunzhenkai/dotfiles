# =============================================================================
# oh-my-zsh lib — controlled by ENABLE_OMZ environment variable
# Set ENABLE_OMZ=true to load ~/.oh-my-zsh/lib/*.zsh
# =============================================================================

if [[ "$ENABLE_OMZ" == true ]]; then
  if [[ -d ~/.oh-my-zsh/lib ]]; then
    for _f in ~/.oh-my-zsh/lib/*.zsh(N); do source "$_f"; done
  else
    echo "⚠️  ENABLE_OMZ=true but ~/.oh-my-zsh/lib not found" >&2
  fi
fi
