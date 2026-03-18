#!/bin/bash

# 初始化 Golang 环境
setup_golang() {
  echo "---- Configuring Golang ----"

  # 检查 go 命令是否存在
  if ! command -v go &>/dev/null; then
    echo "Warning: go not found, skipping Golang setup"
    echo "Please install Go first (e.g., via mise or homebrew)"
    return 0
  fi

  # 设置私有库，不走代理
  go env -w GOPRIVATE='gitlab.fegtech.com/*'
  go env -w GONOSUMDB='gitlab.fegtech.com/*'

  # 设置使用 fegtech gitlab ssh 认证
  git config --global url."git@gitlab.fegtech.com:".insteadOf "https://gitlab.fegtech.com/"

  echo "Golang configured successfully!"
  echo "  GOPRIVATE: $(go env GOPRIVATE)"
  echo "  GONOSUMDB: $(go env GONOSUMDB)"
}
