#!/bin/bash
# mdserve 二进制安装

source "$SCRIPT_DIR/scripts/lib/helpers.sh"

install_mdserve_binary() {
  install_go_binary "mdserve" "git@github.com:sunzhenkai/mdserve.git"
}
