.PHONY: install registry validate test smoke bash32 shellcheck templates secret-scan acceptance ci

PROJECT_DIR := $(shell pwd)
LINK_TARGET := $(HOME)/.config/dotfiles
TEMPLATE_OUTPUTS := \
	agents/vendors/cursor/mcp.json \
	agents/vendors/kiro/mcp.json \
	agents/vendors/opencode/opencode.json \
	agents/vendors/kimi-code/mcp.json \
	agents/vendors/zcode/mcp.json

registry validate:
	python3 scripts/modules.py validate --strict-handlers

test:
	python3 -m pytest -q

smoke:
	bash scripts/ci/smoke-linux.sh

bash32:
	bash scripts/ci/bash32-check.sh

shellcheck:
	bash scripts/ci/shellcheck-first-party.sh

templates:
	python3 scripts/agents/generate_templates.py
	git diff --exit-code -- $(TEMPLATE_OUTPUTS)

secret-scan:
	python3 scripts/ci/secret-scan.py

acceptance:
	BASH_BIN="$${BASH_BIN:-bash}" bash scripts/ci/acceptance-isolated-home.sh

ci: registry test shellcheck templates secret-scan acceptance smoke bash32

install:
	@if [ -L "$(LINK_TARGET)" ]; then \
		current=$$(readlink "$(LINK_TARGET)"); \
		if [ "$$current" = "$(PROJECT_DIR)" ]; then \
			echo "✓ $(LINK_TARGET) 已指向当前目录，无需更改"; \
		else \
			echo "⚠ $(LINK_TARGET) 是指向 $$current 的软链接"; \
			mv "$(LINK_TARGET)" "$(LINK_TARGET).bak.$$(date +%Y%m%d%H%M%S)"; \
			ln -s "$(PROJECT_DIR)" "$(LINK_TARGET)"; \
			echo "✓ 已备份旧链接并创建新链接 → $(PROJECT_DIR)"; \
		fi; \
	elif [ -d "$(LINK_TARGET)" ]; then \
		echo "⚠ $(LINK_TARGET) 是一个已存在的目录"; \
		mv "$(LINK_TARGET)" "$(LINK_TARGET).bak.$$(date +%Y%m%d%H%M%S)"; \
		ln -s "$(PROJECT_DIR)" "$(LINK_TARGET)"; \
		echo "✓ 已备份旧目录并创建软链接 → $(PROJECT_DIR)"; \
	elif [ -e "$(LINK_TARGET)" ]; then \
		echo "⚠ $(LINK_TARGET) 是一个已存在的文件"; \
		mv "$(LINK_TARGET)" "$(LINK_TARGET).bak.$$(date +%Y%m%d%H%M%S)"; \
		ln -s "$(PROJECT_DIR)" "$(LINK_TARGET)"; \
		echo "✓ 已备份旧文件并创建软链接 → $(PROJECT_DIR)"; \
	else \
		ln -s "$(PROJECT_DIR)" "$(LINK_TARGET)"; \
		echo "✓ 已创建软链接 $(LINK_TARGET) → $(PROJECT_DIR)"; \
	fi
