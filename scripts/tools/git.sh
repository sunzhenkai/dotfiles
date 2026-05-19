#!/bin/bash
# Git 配置

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 初始化 git 配置
setup_git() {
  if ! confirm "是否配置 Git（pull.rebase/editor/defaultBranch）?" "N"; then
    echo "跳过 Git 配置"
    return 0
  fi

  echo "---- Configuring git ----"

  # pull 冲突后默认 merge（不使用 rebase）
  git config --global pull.rebase false

  # 设置默认编辑器
  git config --global core.editor vim

  # 设置默认分支名为 main
  git config --global init.defaultBranch main

  echo "Git configured successfully!"
  echo "  user.name: $(git config --global user.name)"
  echo "  user.email: $(git config --global user.email)"
  echo "  pull.rebase: $(git config --global pull.rebase)"
  echo "  core.editor: $(git config --global core.editor)"
  echo "  init.defaultBranch: $(git config --global init.defaultBranch)"
}
