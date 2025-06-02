.PHONY: starship nvim kitty alacritty starship tmux zellij ghostty zsh yazi wezterm helix hypr \
	all init git

TIMESTAMP := $(shell date +%s)
PWD := $(shell pwd)

define backup_config
	bash -c 'if [ ! -z "$(1)" ] && [ -e $(1) ]; then mv $(1) $(1)-$(TIMESTAMP); fi'
endef

define install_config
	@if [ "$(shell realpath $(PWD)/$(1))" != "$(shell realpath $(2))" ]; then ($(call backup_config,$(2))); fi
	@if [ ! -e "$(shell realpath $(2))" ]; then ln -s $(PWD)/$(1) $(2); echo "install $(1)"; fi
endef

init:
	@bash scripts/init.sh

all: starship nvim kitty alacritty starship tmux zellij ghostty zsh yazi wezterm helix hypr
starship:
	$(call install_config,starship/starship.toml,~/.config/starship.toml)
nvim:
	$(call install_config,nvim,~/.config/nvim)
kitty:
	$(call install_config,kitty,~/.config/kitty)
tmux:
	$(call install_config,tmux,~/.config/tmux)
alacritty:
	$(call install_config,alacritty,~/.config/alacritty)
zellij:
	$(call install_config,zellij,~/.config/zellij)
ghostty:
	$(call install_config,ghostty,~/.config/ghostty)
wezterm:
	$(call install_config,wezterm,~/.config/wezterm)
zsh:
	$(call install_config,zsh,~/.config/zsh)
	$(call backup_config,~/.zshrc)
	@cp zsh/zshrc ~/.zshrc
yazi:
	$(call install_config,yazi,~/.config/yazi)
hypr:
	$(call install_config,hypr,~/.config/hypr)
helix:
	$(call install_config,helix,~/.config/helix)

# personal configs of mine
git:
	$(call install_config,git,~/.config/git)
	@echo "WARN: extra operation should be processed"
	@echo "      append following texts into ~/.gitconfig after [user] scope"
	@echo '[includeIf "gitdir:~/.config/git/gitconfig"]'
	@echo ' path = ~/.config/git/gitconfig'
git-global:
	$(call install_config,git/gitconfig,~/.gitconfig)
