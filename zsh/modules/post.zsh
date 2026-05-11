
# dotf wrapper — 拦截 cd 子命令（需要改变当前 shell 目录）
dotf() {
  case "$1" in
    cd) builtin cd "$(command dotf __path)" ;;
    *)  command dotf "$@" ;;
  esac
}

# grepom
if command -v grepom &>/dev/null; then
  gcd() {
    local dir
    if [ $# -eq 0 ]; then
      dir=$(grepom dir)
    else
      if command -v fzf >/dev/null 2>&1; then
        dir=$(grepom dir "$@" | fzf --select-1)
      else
        dir=$(grepom dir "$@" | head -n 1)
      fi
    fi || return
    cd "$dir"
  }
fi
