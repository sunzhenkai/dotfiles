#!/bin/bash
# 用于安装必要 sdk、配置文件

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTFILES_ROOT="$SCRIPT_DIR"

# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/modules.sh"

# 模块清单与描述 — 真相源 modules.yaml
get_install_modules() {
  # 可选: get_install_modules [--filter-os]
  if [[ "${1:-}" == "--filter-os" ]]; then
    modules_list install --filter-os
  else
    modules_list install
  fi
}

get_module_desc() {
  modules_desc "$1" 2>/dev/null || echo "$1"
}

# 确认函数（由 common.sh 提供，此处为独立运行时的兜底定义）
source "$SCRIPT_DIR/scripts/tools/common.sh"

# 加载所有模块
load_modules() {
  source "$SCRIPT_DIR/scripts/tools/homebrew.sh"
  source "$SCRIPT_DIR/scripts/tools/sdk.sh"
  source "$SCRIPT_DIR/scripts/tools/golang.sh"
  source "$SCRIPT_DIR/scripts/tools/senv.sh"
  source "$SCRIPT_DIR/scripts/tools/grepom.sh"
  source "$SCRIPT_DIR/scripts/tools/mdserve.sh"
  source "$SCRIPT_DIR/scripts/tools/git.sh"
  source "$SCRIPT_DIR/scripts/tools/delta.sh"
  source "$SCRIPT_DIR/scripts/tools/fonts.sh"
  source "$SCRIPT_DIR/scripts/tools/system.sh"
  source "$SCRIPT_DIR/scripts/tools/npm.sh"
  source "$SCRIPT_DIR/scripts/tools/agents.sh"
  source "$SCRIPT_DIR/scripts/tools/claude.sh"
  source "$SCRIPT_DIR/scripts/tools/cursor.sh"
  source "$SCRIPT_DIR/scripts/tools/opencode.sh"
  source "$SCRIPT_DIR/scripts/tools/qoder.sh"
  source "$SCRIPT_DIR/scripts/tools/trae-cli.sh"
  source "$SCRIPT_DIR/scripts/tools/codebuddy-code.sh"
  source "$SCRIPT_DIR/scripts/tools/codex.sh"
  source "$SCRIPT_DIR/scripts/tools/kimi-code.sh"
  source "$SCRIPT_DIR/scripts/tools/vcpkg.sh"
  source "$SCRIPT_DIR/scripts/tools/ossutil.sh"
  source "$SCRIPT_DIR/scripts/tools/aws.sh"
  source "$SCRIPT_DIR/scripts/tools/aliyun.sh"
  source "$SCRIPT_DIR/scripts/tools/gcp.sh"
  source "$SCRIPT_DIR/scripts/tools/d2.sh"
}

# 执行单个模块（带计时）
run_module() {
  local module="$1"
  echo ""
  echo "========================================"
  echo "执行模块: $module"
  echo "========================================"

  local _timer_start=$SECONDS
  local _module_status="✓"

  case "$module" in
  homebrew)
    setup_brew_path
    install_homebrew
    init_homebrew
    ;;
  system) setup_system ;;
  sdk) setup_sdk ;;
  senv) install_senv_binary ;;
  grepom) install_grepom_binary ;;
  mdserve) install_mdserve_binary ;;
  golang) setup_golang ;;
  git)
    setup_git
    ;;
  delta)
    install_delta
    ;;
  fonts) setup_fonts ;;
  npm) install_npm_packages ;;
  agents) install_agents_bundle ;;
  claude) install_claude_cli ;;
  cursor) install_cursor_cli ;;
  opencode) install_opencode ;;
  qoder) install_qoder ;;
  trae-cli) install_trae_cli ;;
  codebuddy-code) install_codebuddy_code ;;
  codex) install_codex ;;
  kimi-code) install_kimi_code ;;
  vcpkg) setup_vcpkg ;;
  ossutil) install_ossutil ;;
  aws) install_aws_cli ;;
  aliyun) install_aliyun_cli ;;
  gcp) install_gcp_cli ;;
  d2) install_d2 ;;
  esac

  local _exit_code=$?
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
}

# 交互式安装（指定模块列表）
# 注：确认职责由各模块内部函数承担，此处不再做外层逐模块确认，避免双重确认。
interactive_install() {
  local modules=("$@")

  load_modules

  for module in "${modules[@]}"; do
    run_module "$module"
  done
}

# 显示帮助
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
  echo ""
  echo "示例:"
  echo "  $0 homebrew sdk # 只安装指定模块（仍需确认）"
  echo "  $0 --all        # 全部安装"
}

# 主函数
main() {
  # 无参数：显示帮助
  if [[ $# -eq 0 ]]; then
    show_help
    exit 0
  fi

  # 解析参数
  local modules=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --all | -a)
      load_modules
      while IFS= read -r m; do
        [ -z "$m" ] && continue
        run_module "$m"
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
      # 兼容别名: codebuddy -> codebuddy-code
      if [[ "$1" == "codebuddy" ]]; then
        modules+=("codebuddy-code")
      else
        modules+=("$1")
      fi
      ;;
    esac
    shift
  done

  # 执行指定模块
  if [[ ${#modules[@]} -gt 0 ]]; then
    # 验证模块名（须在注册表且具备 install）
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

main "$@"
