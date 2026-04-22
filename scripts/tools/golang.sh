#!/bin/bash
# Golang 环境配置

setup_golang() {
  echo "---- Setting up Golang environment ----"

  local gopath="${HOME}/.go"

  # 设置 GOPATH
  export GOPATH="$gopath"
  echo "  GOPATH set to: $GOPATH"

  # 创建 GOPATH 目录结构
  mkdir -p "$GOPATH/bin"
  mkdir -p "$GOPATH/src"
  mkdir -p "$GOPATH/pkg"
  echo "  Created GOPATH directories: bin, src, pkg"

  # 确保 PATH 包含 GOPATH/bin
  if [[ ":$PATH:" != *":$GOPATH/bin:"* ]]; then
    export PATH="$GOPATH/bin:$PATH"
    echo "  Added \$GOPATH/bin to PATH"
  fi

  echo "Golang environment configured!"
  echo "  GOPATH: $GOPATH"
  echo "  GOBIN:  $GOPATH/bin"
}
