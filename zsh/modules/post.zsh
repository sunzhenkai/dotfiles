
# dotf wrapper — 拦截 cd 子命令（需要改变当前 shell 目录）
dotf() {
  case "$1" in
    cd) builtin cd "$(command dotf __path)" ;;
    *)  command dotf "$@" ;;
  esac
}

# grepom
if command -v grepom &>/dev/null; then
  eval "$(grepom dir --shell)"
fi
