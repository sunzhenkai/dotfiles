#!/bin/bash
# C/C++ 开发工具链（编译器 + 构建系统 + 调试）— 可选模块，默认不进 full profile
# 通过 `dotf install cpp-dev` 显式安装。

install_cpp_dev() {
  echo "---- Installing C/C++ toolchain via Homebrew ----"
  # pkg-config 在 homebrew 模块已装，这里幂等补一次以防单独执行
  brew install pkg-config ninja bear ctags valgrind llvm make cmake gcc
}
