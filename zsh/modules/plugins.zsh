# =============================================================================
# znap — Zsh plugin manager
# https://github.com/marlonrichert/zsh-snap
# =============================================================================

local _znap_dir=~/.local/share/znap
if [[ ! -r $_znap_dir/znap.zsh ]]; then
  echo "Installing znap..."
  git clone --depth 1 \
    https://github.com/marlonrichert/zsh-snap.git $_znap_dir
fi
source $_znap_dir/znap.zsh

# Plugins
znap source zsh-users/zsh-autosuggestions
znap source zsh-users/zsh-syntax-highlighting
znap source agkozak/zsh-z
