.PHONY: starship

starship:
	@ln -s $(shell pwd)/starship/starship.toml ~/.config/starship.toml
