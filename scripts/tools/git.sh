#!/bin/bash
# Git 配置

# 初始化 git 配置
setup_git() {
  echo "---- Configuring git ----"

  # 设置用户名和邮箱
  git config --global user.name "zhenkai.sun"
  git config --global user.email "zhenkai.sun@qq.com"

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
