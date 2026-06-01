.PHONY: install

PROJECT_DIR := $(shell pwd)
LINK_TARGET := $(HOME)/.config/dotfiles

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
