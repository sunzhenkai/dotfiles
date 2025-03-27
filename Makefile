.PHONY: starship nvim

starship:
	@ln -s $(shell pwd)/starship/starship.toml ~/.config/starship.toml
nvim:
	@ln -s $(shell pwd)/nvim ~/.config/nvim
