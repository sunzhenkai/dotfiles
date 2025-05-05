#!/bin/bash
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

install_fonts() {
  cd assets/fonts
  for f in *.tar.gz; do tar -xzf "$f"; done
  sudo mkdir -p /usr/share/fonts/local
  sudo mv *.ttf /usr/share/fonts/local/
  sudo fc-cache -fv
}

prepare() {
  git submodule update --init
  if [ "$ID" != "darwin" ]; then
    install_fonts
  fi
}

common_init() {
  echo "---- common init ----"
  ./init/activate
  . ~/.local/env-init/env

  . init/scripts/tool.sh
  # iconfig
  pushd ~/.config/iconfig
  make all
  popd
  tool::append_to_profiles "source ~/.config/zsh/zshrc.sh"
  echo "---- common init done ----"
}

ubuntu_init() {
  echo "---- ubuntu init ----"
  ii ubuntu -c
}

arch_init() {
  echo "---- arch init ----"
  ii arch -c
}

post_init() {
  echo "---- post init ----"
  # install
  ii homebrew -i
  # config
  ii zsh -c
  . ~/.zshrc
  ii homebrew -c
  ii asdf -i
  ii asdf -c
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

post_init
