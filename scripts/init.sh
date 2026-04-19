#!/bin/bash
# 用于安装必要 sdk、配置文件

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 可用模块列表
MODULES=(homebrew system sdk senv mdserve git fonts npm)

# 模块描述（兼容 bash 3.2，不使用关联数组）
get_module_desc() {
  case "$1" in
  homebrew) echo "安装 Homebrew 包管理器" ;;
  system) echo "系统配置（软件源、依赖等）" ;;
  sdk) echo "安装 SDK（Go/Python/Node via mise）" ;;
  senv) echo "安装 senv 二进制工具" ;;
  mdserve) echo "安装 mdserve 二进制工具" ;;
  git) echo "配置 Git" ;;
  fonts) echo "安装字体（Maple Mono NF CN）" ;;
  npm) echo "安装 npm 全局包（docsify-cli 等）" ;;
  *) echo "$1" ;;
  esac
}

# 确认函数
confirm() {
  local prompt="$1"
  local default="${2:-Y}"
  local reply

  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n]: " reply
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
  else
    read -r -p "$prompt [y/N]: " reply
    [[ "$reply" =~ ^[Yy] ]]
  fi
}

# 加载所有模块
load_modules() {
  source "$SCRIPT_DIR/scripts/tools/homebrew.sh"
  source "$SCRIPT_DIR/scripts/tools/sdk.sh"
  source "$SCRIPT_DIR/scripts/tools/senv.sh"
  source "$SCRIPT_DIR/scripts/tools/mdserve.sh"
  source "$SCRIPT_DIR/scripts/tools/git.sh"
  source "$SCRIPT_DIR/scripts/tools/fonts.sh"
  source "$SCRIPT_DIR/scripts/tools/system.sh"
  source "$SCRIPT_DIR/scripts/tools/npm.sh"
}

# 执行单个模块
run_module() {
  local module="$1"
  echo ""
  echo "========================================"
  echo "执行模块: $module"
  echo "========================================"
  case "$module" in
  homebrew)
    setup_brew_path
    install_homebrew
    init_homebrew
    ;;
  system) setup_system ;;
  sdk) setup_sdk ;;
  senv) install_senv_binary ;;
  mdserve) install_mdserve_binary ;;
  git)
    setup_git
    setup_golang
    ;;
  fonts) setup_fonts ;;
  npm) install_npm_packages ;;
  esac
}

# 交互式安装（指定模块列表）
interactive_install() {
  local modules=("$@")

  load_modules

  for module in "${modules[@]}"; do
    if confirm "安装 $(get_module_desc "$module")?"; then
      run_module "$module"
    else
      echo "跳过 $module"
    fi
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
  echo "选项:"
  echo "  --all, -a    安装所有模块（跳过确认）"
  echo "  --help, -h   显示此帮助"
  echo ""
  echo "示例:"
  echo "  $0              # 交互式安装所有模块"
  echo "  $0 homebrew sdk # 只安装指定模块（仍需确认）"
  echo "  $0 --all        # 全部安装（跳过确认）"
}

# 主函数
main() {
  # 无参数：交互式安装所有模块
  if [[ $# -eq 0 ]]; then
    echo "============================================"
    echo "  Dotfiles 初始化脚本"
    echo "============================================"
    echo ""
    echo "将安装以下模块:"
    for m in "${MODULES[@]}"; do
      printf "  - %-12s %s\n" "$m" "$(get_module_desc "$m")"
    done
    echo ""

    if ! confirm "是否开始初始化流程?" "N"; then
      echo "已取消初始化。"
      echo "提示: 使用 '$0 --help' 查看更多选项。"
      exit 0
    fi

    interactive_install "${MODULES[@]}"
    exit 0
  fi

  # 解析参数
  local modules=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --all | -a)
      load_modules
      echo "全部安装模式（跳过确认）"
      for m in "${MODULES[@]}"; do
        run_module "$m"
      done
      exit 0
      ;;
    --help | -h)
      show_help
      exit 0
      ;;
    -*)
      echo "未知选项: $1"
      show_help
      exit 1
      ;;
    *)
      modules+=("$1")
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
