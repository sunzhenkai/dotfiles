# =============================================================================
# Vi mode & History
# =============================================================================

# History
[ -z "$HISTFILE" ] && HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=10000

setopt extended_history       # record timestamp
setopt hist_expire_dups_first # delete duplicates first when HISTFILE exceeds HISTSIZE
setopt hist_ignore_dups       # ignore duplicated commands
setopt hist_ignore_space      # ignore commands that start with space
setopt hist_verify            # show command with history expansion before running
setopt share_history          # share command history across sessions

# Vi mode
if command -v bindkey >/dev/null; then
  bindkey -v
fi
export KEYTIMEOUT=1
export LESSCHARSET=utf-8
