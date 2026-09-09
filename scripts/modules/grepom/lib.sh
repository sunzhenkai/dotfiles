#!/bin/bash
# grepom 二进制安装

source "$SCRIPT_DIR/scripts/lib/helpers.sh"

install_grepom_binary() {
  install_go_binary "grepom" "https://github.com/sunzhenkai/grepom.git"
}
