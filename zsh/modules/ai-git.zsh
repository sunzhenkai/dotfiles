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
Repository: ${repo}
Repository path: ${toplevel}
Current branch: ${branch}
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

  prompt="You are in a Git repository.

${context}

Please:
1. Inspect git diff (staged and unstaged)
2. Split into logical commits if needed
3. Write Conventional Commits compliant commit messages
4. git commit

Do NOT modify source code. Only commit existing changes."

  if [[ -n "$hint" ]]; then
    prompt="${prompt}

User hint for commit message: ${hint}"
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

  prompt="You are in a Git repository.

${context}

Please:
1. Inspect git diff (staged and unstaged)
2. Split into logical commits if needed
3. Write Conventional Commits compliant commit messages
4. git commit
5. git push origin ${branch}

Do NOT modify source code. Only commit and push existing changes."

  if [[ -n "$hint" ]]; then
    prompt="${prompt}

User hint for commit message: ${hint}"
  fi

  _ai_git_invoke "$prompt"
}

# agrv — AI review 当前 diff
agrv() {
  _ai_git_check_repo || return 1

  local focus="$*"
  local context prompt
  context=$(_ai_git_context) || return 1

  prompt="You are in a Git repository.

${context}

Please review the current git diff (staged and unstaged).

Provide:
1. Summary of changes
2. Potential issues (bugs, edge cases, security)
3. Suggestions for improvement

Do NOT modify any files, commit, or push."

  if [[ -n "$focus" ]]; then
    prompt="${prompt}

Focus areas: ${focus}"
  fi

  _ai_git_invoke "$prompt"
}
