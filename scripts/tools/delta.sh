#!/bin/bash
# git-delta 安装与配置
# 为 git diff/show/log/blame 提供语法高亮的分页器
# 项目: https://github.com/dandavison/delta

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_delta() {
  if ! confirm "是否安装并配置 git-delta（git diff 高亮分页器）?" "Y"; then
    echo "跳过 git-delta 安装"
    return 0
  fi

  # 确保 brew 可用（由 homebrew.sh 提供，此处兜底）
  command -v setup_brew_path &>/dev/null && setup_brew_path

  echo "---- Installing git-delta ----"

  # 安装 git-delta（brew 包名为 git-delta，命令名为 delta）
  if ! command -v delta &>/dev/null; then
    echo "通过 Homebrew 安装 git-delta..."
    if ! command -v brew &>/dev/null; then
      echo "✗ 未找到 Homebrew，请先运行: dotf -i homebrew"
      return 1
    fi
    brew install git-delta
  else
    echo "git-delta 已安装: $(delta --version 2>&1 | head -1)"
  fi

  echo ""
  echo "---- Configuring git to use delta ----"

  # 将 git 的 diff/show/log/blame 输出交给 delta 渲染
  git config --global core.pager delta

  # 交互模式（如 git add -p）下的 diff 过滤器
  git config --global interactive.diffFilter "delta --color-only"

  # delta 行为配置
  git config --global delta.navigate true        # n/N 在 diff 块间跳转
  git config --global delta.line-numbers true    # 显示行号
  git config --global delta.side-by-side false   # 默认非并排（可 delta -s 临时开启）

  # 冲突展示样式（zdiff3 同时显示 base，便于解决冲突）
  git config --global merge.conflictStyle zdiff3

  # 代码移动检测着色
  git config --global diff.colorMoved default

  echo ""
  echo "✔ git-delta 安装并配置成功！"
  echo "  core.pager:             $(git config --global core.pager)"
  echo "  interactive.diffFilter: $(git config --global interactive.diffFilter)"
  echo "  delta.navigate:         $(git config --global delta.navigate)"
  echo "  delta.line-numbers:     $(git config --global delta.line-numbers)"
  echo "  delta.side-by-side:     $(git config --global delta.side-by-side)"
  echo "  merge.conflictStyle:    $(git config --global merge.conflictStyle)"
  echo "  diff.colorMoved:        $(git config --global diff.colorMoved)"
  echo ""
  echo "试试: git diff / git show / git log -p"
}
