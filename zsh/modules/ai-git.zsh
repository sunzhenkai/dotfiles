# AI Git Agent — 通过 Agent CLI 辅助 Git 工作流
# 默认使用 opencode，可通过环境变量 AI_GIT_AGENT 切换（opencode / codex / cursor-agent）

: "${AI_GIT_AGENT:=opencode}"

_ai_git_check_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "Error: 当前目录不是 Git 仓库" >&2
    return 1
  }
}

_ai_git_context() {
  local repo branch toplevel
  toplevel=$(git rev-parse --show-toplevel) || return 1
  repo=$(basename "$toplevel")
  branch=$(git branch --show-current)
  cat <<EOF
仓库名称：${repo}
仓库路径：${toplevel}
当前分支：${branch}
EOF
}

_ai_git_invoke() {
  local prompt="$1"
  local agent="$AI_GIT_AGENT"

  case "$agent" in
    opencode)
      command -v opencode >/dev/null || {
        echo "Error: opencode 未安装" >&2
        return 1
      }
      opencode run --auto "$prompt"
      ;;
    codex)
      command -v codex >/dev/null || {
        echo "Error: codex 未安装" >&2
        return 1
      }
      codex exec "$prompt"
      ;;
    cursor-agent)
      command -v cursor-agent >/dev/null || {
        echo "Error: cursor-agent 未安装" >&2
        return 1
      }
      cursor-agent "$prompt"
      ;;
    *)
      echo "Error: 未知的 AI_GIT_AGENT: $agent（支持 opencode / codex / cursor-agent）" >&2
      return 1
      ;;
  esac
}

# agc — AI 自动 commit
agc() {
  _ai_git_check_repo || return 1

  local hint="$*"
  local context prompt
  context=$(_ai_git_context) || return 1

  prompt="你正在一个 Git 仓库中工作。

${context}

请使用简体中文完成以下任务：
1. 检查 git diff（包括已暂存和未暂存的变更）
2. 编写符合 Conventional Commits 规范的 commit message
3. 执行 git commit

不要修改源代码，仅提交现有变更。所有输出和 commit message 均使用简体中文。"

  if [[ -n "$hint" ]]; then
    prompt="${prompt}

用户对 commit message 的补充说明：${hint}"
  fi

  _ai_git_invoke "$prompt"
}

# agcp — AI commit + push
agcp() {
  _ai_git_check_repo || return 1

  local hint="$*"
  local context branch prompt
  context=$(_ai_git_context) || return 1
  branch=$(git branch --show-current)

  prompt="你正在一个 Git 仓库中工作。

${context}

请使用简体中文完成以下任务：
1. 检查 git diff（包括已暂存和未暂存的变更）
2. 编写符合 Conventional Commits 规范的 commit message
3. 执行 git commit
4. 执行 git push origin ${branch}

不要修改源代码，仅提交并推送现有变更。所有输出和 commit message 均使用简体中文。"

  if [[ -n "$hint" ]]; then
    prompt="${prompt}

用户对 commit message 的补充说明：${hint}"
  fi

  _ai_git_invoke "$prompt"
}

# agrv — AI review 当前 diff
agrv() {
  _ai_git_check_repo || return 1

  local focus="$*"
  local context prompt
  context=$(_ai_git_context) || return 1

  prompt="你正在一个 Git 仓库中工作。

${context}

请使用简体中文审查当前的 git diff（包括已暂存和未暂存的变更）。

请提供：
1. 变更摘要
2. 潜在问题（bug、边界情况、安全等）
3. 改进建议

不要修改任何文件，不要 commit 或 push。所有输出均使用简体中文。"

  if [[ -n "$focus" ]]; then
    prompt="${prompt}

重点关注：${focus}"
  fi

  _ai_git_invoke "$prompt"
}
