#!/bin/bash
# npm 全局包安装

# 检查 npm 是否可用
check_npm() {
  if ! command -v npm &>/dev/null; then
    echo "错误: npm 未安装"
    echo "请先通过 'sdk' 模块安装 Node.js"
    return 1
  fi
  return 0
}

# 安装 npm 全局包
install_npm_packages() {
  echo "---- Installing global packages via npm ----"

  # 检查 npm
  if ! check_npm; then
    return 1
  fi

  # 文档工具
  npm install -g docsify-cli

  echo "npm 全局包安装完成!"
}
