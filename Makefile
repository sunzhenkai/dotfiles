.PHONY: all init

init:
	@bash scripts/init.sh

all: init
	@bash scripts/install-config.sh --all

%:
	@bash scripts/install-config.sh $@
