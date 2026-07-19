.PHONY: install test validate smoke bash32 shellcheck ci

PROJECT_DIR := $(shell pwd)
LINK_TARGET := $(HOME)/.config/dotfiles

validate:
	python3 scripts/modules.py validate

test:
	python3 -m pytest -q

smoke:
	bash scripts/ci/smoke-linux.sh

bash32:
	bash scripts/ci/bash32-check.sh

shellcheck:
	shellcheck -x bin/dotf scripts/modules.sh scripts/doctor.sh \
		scripts/bootstrap.sh scripts/run_plan.sh \
		scripts/ci/smoke-linux.sh scripts/ci/bash32-check.sh

ci: validate test
	@command -v shellcheck >/dev/null && $(MAKE) shellcheck || echo "skip shellcheck (not installed)"
	$(MAKE) smoke
	$(MAKE) bash32

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
