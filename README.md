# iConfig

```shell
# install
git clone git@github.com:sunzhenkai/iconfig.git ~/.config/iconfig
cd ~/.config/iconfig && make all

# config
cd ~/.config/iconfig/init
./activate

# config oh-my-zsh
vim ~/.zshrc
## config
ZSH_CUSTOME=~/.config/zsh/oh-my-zsh
## before source $ZSH/oh-my-zsh.sh
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# install programs
ii homebrew -i
ii homebrew -c

ii cargo -i 
ii carge -c

ii asdf -i
ii asdf -c

ii zsh -c
```

# Workflow

- Local
  - Kitty
  - zsh
    - Oh My Zsh
    - Starship
  - Homebrew
  - NVM
- Remote
  - Zellij
  - Neovim
