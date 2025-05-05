#!/bin/bash
set -e
# check os information
if [ -f "/etc/os-release" ]; then
  . /etc/os-release
elif [ -f "/etc/arch-release" ]; then
  export ID=arch
elif [[ "$OSTYPE" =~ ^darwin ]]; then
  export ID="darwin"
else
  echo "unknown os."
  exit 1
fi

prepare() {
  git submodule update --init
}

common_init() {
  echo "---- common init ----"
  ./init/activate
  which ii
  . ~/.local/env-init/env
}

ubuntu_init() {
  echo "---- ubuntu init ----"
  ii ubuntu -c
  # homebrew
  ii homebrew -i
  ii homebrew -c
  # asdf
  ii asdf -i
  ii asdf -c
  # zsh
  ii zsh -c
}

arch_init() {
  echo "arch"
}

osx_init() {
  echo "os x"
}

prepare
common_init
case "$ID" in
ubuntu | debian | pop)
  ubuntu_init
  ;;
fedora) ;;
# alinux: ali-yun linux os
alinux) ;;
# amzn: amazon linux os
amzn) ;;
rhel | centos | rocky | alinux) ;;
opensuse-leap) ;;
arch | manjaro)
  arch_init
  ;;
darwin)
  osx_init
  ;;
*)
  echo "Your system ($ID) is not supported by this script. Please install dependencies manually."
  exit 1
  ;;
esac
