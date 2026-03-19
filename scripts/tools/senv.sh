#!/bin/bash
# Senv 二进制安装

source "$SCRIPT_DIR/scripts/tools/helpers.sh"

install_senv_binary() {
  install_go_binary "senv" "https://github.com/solo-kingdom/senv.git"
}
