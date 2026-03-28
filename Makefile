.PHONY: all init

CONFIGS = starship nvim kitty tmux alacritty zellij ghostty wezterm zsh yazi hypr helix shell_gpt zed fcitx5 git opencode claude

init:
	@bash scripts/init.sh

all: init
	@bash scripts/install-config.sh --all

# Generate explicit phony targets for each config
define make_config_target
.PHONY: $(1)
$(1):
	@bash scripts/install-config.sh $(1)
endef

$(foreach config,$(CONFIGS),$(eval $(call make_config_target, $(config))))
