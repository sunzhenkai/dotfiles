# Put files in this folder to add your own custom functionality.
# See: https://github.com/ohmyzsh/ohmyzsh/wiki/Customization
#
# Files in the custom/ directory will be:
# - loaded automatically by the init script, in alphabetical order
# - loaded last, after all built-ins in the lib/ directory, to override them
# - ignored by git by default
#
# Example: add custom/shortcuts.zsh for shortcuts to your local projects
#
# brainstormr=~/Projects/development/planetargon/brainstormr
# cd $brainstormr

source ~/.config/zsh/antigen.zsh

# antigen
# nonstandard plugins
export ANTIGEN_ENABELD=true
antigen use oh-my-zsh
antigen bundle jsontools
#antigen bundle git
antigen bundle z
antigen bundle command-not-found
antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle zsh-users/zsh-autosuggestions
#antigen theme romkatv/powerlevel10k    # NOTE:  using startship as alternative
antigen apply

source ~/.config/zsh/zshrc
