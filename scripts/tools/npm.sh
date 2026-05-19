#!/bin/bash
# npm 全局包安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

# npm 国内镜像源列表
NPM_REGISTRIES=(
  "https://registry.npmmirror.com|淘宝镜像 (npmmirror)"
  "https://mirrors.huaweicloud.com/repository/npm/|华为云镜像"
  "https://mirrors.tencent.com/npm/|腾讯云镜像"
  "https://registry.npmjs.org|官方默认源"
)

# 检查 npm 是否可用
check_npm() {
  if ! command -v npm &>/dev/null; then
    echo "错误: npm 未安装"
    echo "请先通过 'sdk' 模块安装 Node.js"
    return 1
  fi
  return 0
}

# 选择并设置 npm 镜像源
set_npm_registry() {
  echo ""
  echo "请选择 npm 镜像源:"
  echo "-------------------"
  local i=1
  local current_registry
  current_registry=$(npm config get registry 2>/dev/null)

  for reg in "${NPM_REGISTRIES[@]}"; do
    local url="${reg%%|*}"
    local name="${reg##*|}"
    local marker=""
    if [[ "$url" == "$current_registry" ]]; then
      marker=" [当前]"
    fi
    echo "  $i) $name ($url)$marker"
    ((i++))
  done
  echo "  0) 跳过，不修改"
  echo "-------------------"

  read -r -p "请输入选项编号 [0-$((i-1))]: " choice

  # 验证输入
  if [[ -z "$choice" || "$choice" == "0" ]]; then
    echo "跳过 npm 镜像源设置"
    return 0
  fi

  if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice >= i )); then
    echo "无效选项，跳过 npm 镜像源设置"
    return 0
  fi

  local selected="${NPM_REGISTRIES[$((choice-1))]}"
  local url="${selected%%|*}"
  local name="${selected##*|}"

  npm config set registry "$url"
  echo "已将 npm 镜像源设置为: $name ($url)"
}

# 安装 npm 全局包
install_npm_packages() {
  if ! confirm "是否安装 npm 全局包（docsify-cli/openspec 等）?"; then
    echo "跳过 npm 全局包安装"
    return 0
  fi

  echo "---- Installing global packages via npm ----"

  # 检查 npm
  if ! check_npm; then
    return 1
  fi

  # 文档工具
  npm install -g docsify-cli@5.0.0-rc.4 --ignore-scripts
  npm install -g @fission-ai/openspec@latest

  echo "npm 全局包安装完成!"
}
