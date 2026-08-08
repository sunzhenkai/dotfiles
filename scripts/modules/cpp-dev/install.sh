#!/usr/bin/env bash
# 约定式 install — cpp-dev（可选 C/C++ 工具链）
# 不做 dotf_skip_if_bin：多二进制组合（llvm/gcc/cmake）无单一 bin 判定；
# brew install 本身幂等，已装的会跳过。
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"
source "$DOTFILES_ROOT/scripts/tools/cpp-dev.sh"
if install_cpp_dev; then
  dotf_result_changed "installed cpp-dev toolchain"
else
  dotf_result_failed "cpp-dev install failed"
fi
