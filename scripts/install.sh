#!/bin/bash
# 用于安装必要 sdk、配置文件

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 可用模块列表
MODULES=(homebrew system sdk golang senv grepom mdserve git delta fonts npm agents cursor qoder trae-cli codebuddy-code codex kimi-code vcpkg ossutil aws aliyun gcp d2)

# 模块描述（兼容 bash 3.2，不使用关联数组）
get_module_desc() {
  case "$1" in
  homebrew) echo "安装 Homebrew 包管理器" ;;
  system) echo "系统配置（软件源、依赖等）" ;;
  sdk) echo "安装 SDK（Go/Python/Node via mise）" ;;
  golang) echo "配置 Golang 环境（GOPATH 等）" ;;
  senv) echo "安装 senv 二进制工具" ;;
  grepom) echo "安装 grepom 多仓库管理工具" ;;
  mdserve) echo "安装 mdserve 二进制工具" ;;
  git) echo "配置 Git" ;;
  delta) echo "安装并配置 git-delta（git diff 高亮分页器）" ;;
  fonts) echo "安装字体（Maple Mono NF CN）" ;;
  npm) echo "安装 npm 全局包（docsify-cli 等）" ;;
  agents) echo "安装 agents CLI 工具包（cursor/codex/kimi-code；不写 MCP/skills）" ;;
  cursor) echo "安装 Cursor Agent CLI（cursor-agent）" ;;
  qoder) echo "安装 Qoder CLI" ;;
  trae-cli) echo "安装 Trae CLI" ;;
  codebuddy-code) echo "安装 CodeBuddy Code CLI" ;;
  codex) echo "安装 Codex CLI" ;;
  kimi-code) echo "安装 Kimi Code CLI" ;;
  vcpkg) echo "安装 vcpkg C++ 包管理器" ;;
  ossutil) echo "安装 ossutil 2.0（阿里云 OSS CLI）" ;;
  aws) echo "安装 AWS CLI v2" ;;
  aliyun) echo "安装阿里云 CLI" ;;
  gcp) echo "安装 Google Cloud CLI + gke-gcloud-auth-plugin" ;;
  d2) echo "安装 D2 图描述语言" ;;
  *) echo "$1" ;;
  esac
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
  source "$SCRIPT_DIR/scripts/tools/cursor.sh"
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
  cursor) install_cursor_cli ;;
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
  for m in "${MODULES[@]}"; do
    printf "  %-12s %s\n" "$m" "$(get_module_desc "$m")"
  done
  echo ""
  echo "别名: codebuddy -> codebuddy-code"
  echo ""
  echo "选项:"
  echo "  --all, -a    安装所有模块"
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
      for m in "${MODULES[@]}"; do
        run_module "$m"
      done
      print_timing_summary
      exit 0
      ;;
    --help | -h)
      show_help
      exit 0
      ;;
    --list)
      for m in "${MODULES[@]}"; do
        echo "$m"
      done
      exit 0
      ;;
    --list-desc)
      for m in "${MODULES[@]}"; do
        printf "%s\t%s\n" "$m" "$(get_module_desc "$m")"
      done
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
    # 验证模块名
    for m in "${modules[@]}"; do
      if [[ ! " ${MODULES[*]} " =~ " $m " ]]; then
        echo "错误: 未知模块 '$m'"
        echo ""
        show_help
        exit 1
      fi
    done
    interactive_install "${modules[@]}"
  fi
}

main "$@"
