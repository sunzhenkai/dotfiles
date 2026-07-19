#!/bin/bash
# 安装入口：委托约定式处理器（scripts/modules/<name>/install.sh）
# 保留 CLI 以便直接调用；编排主路径为 bin/dotf → run_plan → runner。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTFILES_ROOT="$SCRIPT_DIR"
export DOTFILES_ROOT
export SCRIPT_DIR

# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/modules.sh"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/tools/common.sh"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/lib/runner.sh"

get_install_modules() {
  if [[ "${1:-}" == "--filter-os" ]]; then
    modules_list install --filter-os
  else
    modules_list install
  fi
}

get_module_desc() {
  modules_desc "$1" 2>/dev/null || echo "$1"
}

# 执行单个模块（约定式处理器 + 计时汇总）
run_module() {
  local module="$1"
  echo ""
  echo "========================================"
  echo "执行模块: $module"
  echo "========================================"

  local _timer_start=$SECONDS
  local _module_status="✓"
  local _exit_code=0

  runner_run_action install "$module" || _exit_code=$?

  local _elapsed=$((SECONDS - _timer_start))
  if [[ $_exit_code -ne 0 ]]; then
    _module_status="✗"
  fi

  local _formatted
  _formatted=$(timer_format "$_elapsed")

  if [[ "$_module_status" == "✓" ]]; then
    echo "✔ $module 完成 ($_formatted)"
  else
    echo "✗ $module 失败 ($_formatted)"
  fi

  _timing_record "$module" "$_elapsed" "$_module_status"
  return "$_exit_code"
}

interactive_install() {
  local modules=("$@")
  local m
  for m in "${modules[@]}"; do
    run_module "$m" || true
  done
}

show_help() {
  echo "用法: $0 [模块...] [选项]"
  echo ""
  echo "模块:"
  while IFS= read -r m; do
    [ -z "$m" ] && continue
    printf "  %-12s %s\n" "$m" "$(get_module_desc "$m")"
  done < <(get_install_modules)
  echo ""
  echo "别名: codebuddy -> codebuddy-code"
  echo ""
  echo "选项:"
  echo "  --all, -a    安装所有模块（按当前 OS 过滤）"
  echo "  --help, -h   显示此帮助"
}

main() {
  if [[ $# -eq 0 ]]; then
    show_help
    exit 0
  fi

  local modules=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --all | -a)
      while IFS= read -r m; do
        [ -z "$m" ] && continue
        run_module "$m" || true
      done < <(get_install_modules --filter-os)
      print_timing_summary
      exit 0
      ;;
    --help | -h)
      show_help
      exit 0
      ;;
    --list)
      get_install_modules
      exit 0
      ;;
    --list-desc)
      while IFS= read -r m; do
        [ -z "$m" ] && continue
        printf "%s\t%s\n" "$m" "$(get_module_desc "$m")"
      done < <(get_install_modules)
      exit 0
      ;;
    -*)
      echo "未知选项: $1"
      show_help
      exit 1
      ;;
    *)
      if [[ "$1" == "codebuddy" ]]; then
        modules+=("codebuddy-code")
      else
        modules+=("$1")
      fi
      ;;
    esac
    shift
  done

  if [[ ${#modules[@]} -gt 0 ]]; then
    for m in "${modules[@]}"; do
      if ! modules_exists "$m"; then
        echo "错误: 未知模块 '$m'"
        echo "可用安装模块:"
        get_install_modules | sed 's/^/  /'
        exit 1
      fi
      if ! modules_has "$m" install; then
        echo "错误: 模块 '$m' 无安装步骤"
        exit 1
      fi
    done
    interactive_install "${modules[@]}"
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
