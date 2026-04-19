.PHONY: all init

# Prefer Homebrew bash (5.x) over system bash (3.2) for associative array support
BASH := $(shell test -x /opt/homebrew/bin/bash && echo /opt/homebrew/bin/bash || echo /bin/bash)

CONFIGS = starship nvim kitty tmux alacritty zellij ghostty wezterm zsh yazi hypr helix shell_gpt zed fcitx5 git opencode claude

init:
	@$(BASH) scripts/init.sh

all: init
	@$(BASH) scripts/install-config.sh --all

# Generate explicit phony targets for each config
define make_config_target
.PHONY: $(1)
$(1):
	@$(BASH) scripts/install-config.sh $(1)
endef

$(foreach config,$(CONFIGS),$(eval $(call make_config_target, $(config))))
