.PHONY: install registry validate test smoke bash32 shellcheck secret-scan acceptance ci skills-lock-update

PROJECT_DIR := $(shell pwd)
LINK_TARGET := $(HOME)/.config/dotfiles

registry validate:
	python3 src/dotf_core/registry.py validate --strict-handlers

test:
	python3 -m pytest -q

smoke:
	bash scripts/ci/smoke-linux.sh

bash32:
	bash scripts/ci/bash32-check.sh

shellcheck:
	bash scripts/ci/shellcheck-first-party.sh

secret-scan:
	python3 scripts/ci/secret-scan.py

acceptance:
	BASH_BIN="$${BASH_BIN:-bash}" bash scripts/ci/acceptance-isolated-home.sh

ci: registry test shellcheck secret-scan acceptance smoke bash32

# 把第三方 skills.lock.yaml 升到各 source 当前 HEAD（先审计再写仓库）。
# 警告默认 fail closed；确认后加 ACCEPT_WARN=1。
# critical 审计不过的条目会留在旧 revision，不阻断其它 source。
skills-lock-update:
	PYTHONUNBUFFERED=1 python3 src/agents/lock_update.py $(if $(filter 1,$(ACCEPT_WARN)),--accept-warn,)

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
