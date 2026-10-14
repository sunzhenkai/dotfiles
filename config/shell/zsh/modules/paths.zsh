# =============================================================================
# PATH & Homebrew
# =============================================================================

# personal binaries
export PATH="${HOME}/.local/bin:${PATH}"
export DEVELOPMENT_ENV=LOCAL

# dotfiles (dotf command) — 只把 bin/ 暴露到 PATH，避免仓库根目录污染
if [[ -d "${HOME}/.config/dotfiles/bin" ]]; then
  export PATH="${HOME}/.config/dotfiles/bin:${PATH}"
fi

# homebrew — 依次尝试 Apple Silicon / Intel / Linux，命中第一个即停
# （候选与 scripts/lib/common.sh 的 DOTF_BREW_CANDIDATES 保持一致）
local _brew_bin
for _brew_bin in /opt/homebrew/bin/brew /usr/local/bin/brew /home/linuxbrew/.linuxbrew/bin/brew; do
  if [[ -x "$_brew_bin" ]]; then
    znap eval "brew-${${_brew_bin:h:h}//\//-}" "$_brew_bin shellenv"
    if [[ "$OSTYPE" == darwin* ]]; then
      export DYLD_FALLBACK_LIBRARY_PATH="${HOMEBREW_PREFIX:-${_brew_bin:h:h}}/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
    fi
    break
  fi
done
unset _brew_bin

# tiup
local _tiup_path="${HOME}/.tiup/bin"
if [[ -e "$_tiup_path" ]]; then
  export PATH="${_tiup_path}:${PATH}"
fi

# kimi-code
local _kimi_code_path="${HOME}/.kimi-code/bin"
if [[ -d "$_kimi_code_path" ]]; then
  export PATH="${_kimi_code_path}:${PATH}"
fi

