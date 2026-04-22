#!/bin/bash
# Golang 环境配置

setup_golang() {
  echo "---- Setting up Golang environment ----"

  local gopath="${HOME}/.go"

  # 设置 GOPATH
  export GOPATH="$gopath"
  echo "  GOPATH set to: $GOPATH"

  # 设置 Go 模块模式
  export GO111MODULE=on
  echo "  GO111MODULE set to: $GO111MODULE"

  # 设置 Go 代理（国内加速）
  export GOPROXY="https://goproxy.cn,https://mirrors.aliyun.com/goproxy/,direct"
  echo "  GOPROXY set to: $GOPROXY"

  # 设置 Go 构建缓存
  export GOCACHE="$HOME/.cache/go-build"
  mkdir -p "$GOCACHE"
  echo "  GOCACHE set to: $GOCACHE"

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
  echo "  GOPATH:       $GOPATH"
  echo "  GOBIN:        $GOPATH/bin"
  echo "  GO111MODULE:  $GO111MODULE"
  echo "  GOPROXY:      $GOPROXY"
  echo "  GOCACHE:      $GOCACHE"
}
