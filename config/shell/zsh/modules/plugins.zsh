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

##### zsh-history-substring-search
# zsh-history-substring-search：按 ↑/↓ 主动过滤并选择历史。
#zsh-autosuggestions：输入时灰色提示完整命令，按 → 补全。
znap source zsh-users/zsh-history-substring-search
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

znap source zsh-users/zsh-autosuggestions
znap source zsh-users/zsh-syntax-highlighting
znap source agkozak/zsh-z
