# Alias definitions
# You can add your custom aliases here

# Editor
alias vim='nvim'

# Zellij
alias zlj='zellij'
alias za='zellij a'
alias zs='zellij -s'

# Kitty
if command -v kitty >/dev/null; then
  alias kssh='kitty +kitten ssh'
fi

# Example aliases
# alias ll='ls -la'
# alias gs='git status'
# alias gp='git push'

alias ll='ls -lGh'
alias py3='python3'

# git alias
alias ga='git add'
alias gaa='git add --all'
alias gc='git commit'
alias gp='git push'
alias gpu='git push -u origin $(git branch --show-current)'
alias gpt='git push --tags'
alias gpa='git push --all'
alias gl='git pull'
alias glt='git tag --sort=-creatordate | head -n 15'
alias glrt='git ls-remote --tag --sort=-creatordate | head -n 15'
alias gs='git status'
alias gcm='git commit -m'
alias gd='git diff'
alias gb='git branch'
alias gbd='git branch -D'
alias glg='git log'
alias glg1='git log -n 1 --pretty=format:"%H " | cat'
alias gck='git checkout'
alias gckm='git checkout main'
alias gckb='git checkout -b'
alias gmm='git merge main'
alias gfmm='git fetch origin main:main'
alias gsmu='git submodule update --init'
alias gtgs='git fetch --tags && git tag --sort=-creatordate --list | head -n 10'
function gptg() { git tag $1 && git push origin $1 ; }
function gpm() { git add . && git commit -m "$1" && git push ; }

## docker
# delete container
function ddc() { docker stop "$1" && docker rm "$1"; }
alias dps='docker ps --format "table {{.ID}}\\t{{.Names}}\\t{{.Status}}\\t{{.Image}}"'
alias dpsa='docker ps --format "table {{.ID}}\\t{{.Names}}\\t{{.Status}}\\t{{.Image}}" -a'

# mvn alias
alias mvnp='mvn clean package'
alias mvnd='mvn clean deploy'
alias mvnt='mvn dependency:tree'

# arc
alias arcf='arc feature'
alias arcd='arc diff main'
alias arcp='arc diff --preview main'
alias arcl='arc land --onto main'

# others
alias rmf='rm -f'
