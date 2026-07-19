# AI Git Agent — 通过 Agent CLI 辅助 Git 工作流
# 默认使用 opencode，可通过环境变量 AI_GIT_AGENT 切换（opencode / codex / cursor-agent）
#
# 性能相关：
#   AI_GIT_DIFF_MAX_BYTES  注入 prompt 的 diff 上限（默认 24000），大改动时截断以降低延迟
#   AI_GIT_LOG_COUNT       参考的近期 commit 条数（默认 5）
#   AI_GIT_MODEL            可选，覆盖模型（opencode: provider/model；codex/cursor-agent 同各自 -m）

: "${AI_GIT_AGENT:=opencode}"
: "${AI_GIT_DIFF_MAX_BYTES:=24000}"
: "${AI_GIT_LOG_COUNT:=5}"

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

_ai_git_has_changes() {
  ! git diff --quiet || ! git diff --cached --quiet ||
    [[ -n $(git ls-files --others --exclude-standard) ]]
}

# 探测并缓存 opencode 自动批准权限的 flag（不同版本名称不同）
# 新版: --auto；旧版: --dangerously-skip-permissions
# 传入未知 flag 时 opencode 会直接打印 help 后退出，因此必须按版本选择
# 注意：不要用 $() 调用本函数，否则缓存赋值会在子 shell 中丢失
_ai_git_detect_opencode_auto_flag() {
  [[ -n ${_AI_GIT_OPENCODE_AUTO_FLAG+x} ]] && return 0
  local help
  help=$(opencode run --help 2>&1) || true
  if print -r -- "$help" | grep -qE -- '(^|[[:space:]])--auto([[:space:]]|$)'; then
    _AI_GIT_OPENCODE_AUTO_FLAG=--auto
  elif print -r -- "$help" | grep -qF -- '--dangerously-skip-permissions'; then
    _AI_GIT_OPENCODE_AUTO_FLAG=--dangerously-skip-permissions
  else
    _AI_GIT_OPENCODE_AUTO_FLAG=
  fi
}

# 判断是否为二进制变更（跟踪文件看 numstat；未跟踪用 grep -I）
_ai_git_is_binary_path() {
  local f="$1"
  if git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    git diff --numstat HEAD -- "$f" 2>/dev/null | awk '{ exit !($1 == "-" && $2 == "-") }'
  else
    [[ -f $f ]] && ! grep -Iq . "$f" 2>/dev/null
  fi
}

# 写出单个文件的 patch 到指定路径
_ai_git_write_file_patch() {
  local f="$1" out="$2"
  if git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    git diff HEAD -- "$f" >"$out" 2>/dev/null || : >"$out"
  else
    # --no-index 在有 diff 时退出码为 1
    git diff --no-index -- /dev/null "$f" >"$out" 2>/dev/null || true
  fi
}

# 智能收集变更上下文：始终给满 status/stat/name-status/log；
# diff 按文件填充预算，优先完整小文件，跳过二进制与超大文件
_ai_git_collect_changes() {
  local max_bytes=$AI_GIT_DIFF_MAX_BYTES
  local tmp used=0 skipped=0
  local -a files=() ordered=()
  local f size untracked idx rest remain

  print -r -- "## git status"
  git status --porcelain=v1
  print -r -- ""

  print -r -- "## diff --stat (相对 HEAD，含已暂存+未暂存)"
  git diff --stat HEAD
  untracked=$(git ls-files --others --exclude-standard)
  if [[ -n $untracked ]]; then
    print -r -- "未跟踪文件:"
    print -r -- "$untracked" | sed 's/^/  /'
  fi
  print -r -- ""

  print -r -- "## name-status"
  git diff --name-status HEAD
  if [[ -n $untracked ]]; then
    print -r -- "$untracked" | sed 's/^/?\t/'
  fi
  print -r -- ""

  print -r -- "## 最近 commit"
  git log -n "$AI_GIT_LOG_COUNT" --oneline
  print -r -- ""

  print -r -- "## diff（按预算截断，上限 ${max_bytes} 字节）"

  tmp=$(mktemp -d) || return 1

  while IFS= read -r f; do
    [[ -n $f ]] && files+=("$f")
  done < <(git diff --name-only HEAD)

  while IFS= read -r f; do
    [[ -n $f ]] && files+=("$f")
  done < <(print -r -- "$untracked")

  idx=0
  for f in "${files[@]}"; do
    if _ai_git_is_binary_path "$f"; then
      print -r -- "### ${f}（二进制，已跳过）"
      skipped=$((skipped + 1))
      continue
    fi

    idx=$((idx + 1))
    _ai_git_write_file_patch "$f" "$tmp/$idx"
    size=$(wc -c <"$tmp/$idx" | tr -d ' ')
    [[ -z $size ]] && size=0
    # size \t idx \t path（路径中极少含 tab）
    ordered+=("${size}"$'\t'"${idx}"$'\t'"${f}")
  done

  # 按 patch 体积升序，尽量多收录完整文件；超预算则截断纳入（而非整文件丢弃）
  if ((${#ordered[@]} > 0)); then
    while IFS=$'\t' read -r size idx f; do
      [[ -z $f ]] && continue
      remain=$((max_bytes - used))
      if ((remain <= 0)); then
        print -r -- "### ${f}（${size} 字节，预算已满已跳过）"
        skipped=$((skipped + 1))
        continue
      fi
      if ((size <= remain)); then
        cat "$tmp/$idx"
        used=$((used + size))
      else
        print -r -- "### ${f}（原 ${size} 字节，截断保留前 ${remain} 字节）"
        head -c "$remain" "$tmp/$idx"
        print -r -- ""
        print -r -- "... [截断]"
        used=$max_bytes
        skipped=$((skipped + 1))
      fi
    done < <(printf '%s\n' "${ordered[@]}" | sort -n)
  fi

  if ((skipped > 0)); then
    print -r -- ""
    print -r -- "（${skipped} 个文件的 diff 已截断或跳过；请结合 status/stat 撰写 message）"
  fi

  rm -rf "$tmp"
}
# 从模型输出中提取纯 commit message
_ai_git_clean_message() {
  local raw="$1"
  local cleaned

  # 去掉 ANSI
  cleaned=$(print -r -- "$raw" | sed -e 's/\x1b\[[0-9;]*[a-zA-Z]//g')

  # 若有 ``` 代码块，取第一块内容
  if print -r -- "$cleaned" | grep -q '```'; then
    cleaned=$(print -r -- "$cleaned" | awk '
      /^```/ { if (++n == 1) next; else exit }
      n == 1 { print }
    ')
  fi

  # 去掉常见前缀
  cleaned=$(print -r -- "$cleaned" | sed -e 's/^[[:space:]]*Commit Message:[[:space:]]*//I' \
    -e 's/^[[:space:]]*commit message:[[:space:]]*//I')

  # trim 首尾空行
  cleaned=$(print -r -- "$cleaned" | sed -e '/./,$!d' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')
  # 更稳妥的 trim
  cleaned=${cleaned##$'\n'}
  cleaned=${cleaned%%$'\n'}
  while [[ $cleaned == $'\n'* ]]; do cleaned=${cleaned#$'\n'}; done
  while [[ $cleaned == *$'\n' ]]; do cleaned=${cleaned%$'\n'}; done

  print -r -- "$cleaned"
}

# 尝试从 opencode --format json 事件流提取最终文本
_ai_git_extract_opencode_json() {
  python3 -c '
import sys, json
chunks = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        o = json.loads(line)
    except Exception:
        continue
    t = o.get("type") or o.get("event") or ""
    if t in ("text", "message", "assistant", "content"):
        for k in ("part", "text", "content", "message", "delta"):
            v = o.get(k)
            if isinstance(v, str) and v:
                chunks.append(v)
                break
            if isinstance(v, dict):
                for kk in ("text", "content", "part"):
                    if isinstance(v.get(kk), str) and v[kk]:
                        chunks.append(v[kk])
                        break
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        chunks.append(item)
                    elif isinstance(item, dict):
                        for kk in ("text", "content"):
                            if isinstance(item.get(kk), str):
                                chunks.append(item[kk])
    # 部分版本：type=part + part.type=text
    part = o.get("part")
    if isinstance(part, dict) and part.get("type") in ("text", "content"):
        if isinstance(part.get("text"), str):
            chunks.append(part["text"])
print("".join(chunks))
'
}

# 仅生成文本（用于 commit message），避免 Agent 多轮跑 git
_ai_git_invoke_text() {
  local prompt="$1"
  local agent="$AI_GIT_AGENT"
  local out="" outfile

  case "$agent" in
    opencode)
      command -v opencode >/dev/null || {
        echo "Error: opencode 未安装" >&2
        return 1
      }
      local -a args=(run --format json --agent plan)
      [[ -n ${AI_GIT_MODEL:-} ]] && args+=(-m "$AI_GIT_MODEL")
      out=$(opencode "${args[@]}" "$prompt" 2>/dev/null) || true
      if [[ -n $out ]]; then
        local extracted
        extracted=$(print -r -- "$out" | _ai_git_extract_opencode_json)
        if [[ -n $extracted ]]; then
          print -r -- "$extracted"
          return 0
        fi
        # json 解析失败则当纯文本
        print -r -- "$out"
        return 0
      fi
      # json 空输出时回退 default 格式
      args=(run --agent plan)
      [[ -n ${AI_GIT_MODEL:-} ]] && args+=(-m "$AI_GIT_MODEL")
      opencode "${args[@]}" "$prompt" 2>/dev/null
      ;;
    codex)
      command -v codex >/dev/null || {
        echo "Error: codex 未安装" >&2
        return 1
      }
      outfile=$(mktemp)
      local -a cargs=(exec --sandbox read-only -o "$outfile")
      [[ -n ${AI_GIT_MODEL:-} ]] && cargs+=(-m "$AI_GIT_MODEL")
      codex "${cargs[@]}" "$prompt" >/dev/null 2>&1 || true
      if [[ -s $outfile ]]; then
        cat "$outfile"
      fi
      rm -f "$outfile"
      ;;
    cursor-agent)
      command -v cursor-agent >/dev/null || {
        echo "Error: cursor-agent 未安装" >&2
        return 1
      }
      local -a uargs=(-p --mode ask --output-format text)
      [[ -n ${AI_GIT_MODEL:-} ]] && uargs+=(--model "$AI_GIT_MODEL")
      cursor-agent "${uargs[@]}" "$prompt" 2>/dev/null
      ;;
    *)
      echo "Error: 未知的 AI_GIT_AGENT: $agent（支持 opencode / codex / cursor-agent）" >&2
      return 1
      ;;
  esac
}

# 保留完整 Agent 调用（review 等仍可能需要工具）
_ai_git_invoke() {
  local prompt="$1"
  local agent="$AI_GIT_AGENT"

  case "$agent" in
    opencode)
      command -v opencode >/dev/null || {
        echo "Error: opencode 未安装" >&2
        return 1
      }
      _ai_git_detect_opencode_auto_flag
      local -a args=(run)
      [[ -n $_AI_GIT_OPENCODE_AUTO_FLAG ]] && args+=("$_AI_GIT_OPENCODE_AUTO_FLAG")
      [[ -n ${AI_GIT_MODEL:-} ]] && args+=(-m "$AI_GIT_MODEL")
      opencode "${args[@]}" "$prompt"
      ;;
    codex)
      command -v codex >/dev/null || {
        echo "Error: codex 未安装" >&2
        return 1
      }
      if [[ -n ${AI_GIT_MODEL:-} ]]; then
        codex exec -m "$AI_GIT_MODEL" "$prompt"
      else
        codex exec "$prompt"
      fi
      ;;
    cursor-agent)
      command -v cursor-agent >/dev/null || {
        echo "Error: cursor-agent 未安装" >&2
        return 1
      }
      if [[ -n ${AI_GIT_MODEL:-} ]]; then
        cursor-agent --model "$AI_GIT_MODEL" "$prompt"
      else
        cursor-agent "$prompt"
      fi
      ;;
    *)
      echo "Error: 未知的 AI_GIT_AGENT: $agent（支持 opencode / codex / cursor-agent）" >&2
      return 1
      ;;
  esac
}

_ai_git_generate_commit_message() {
  local hint="$1"
  local context changes prompt msg

  context=$(_ai_git_context) || return 1
  changes=$(_ai_git_collect_changes) || return 1

  prompt="你是 Git commit message 生成器。根据下方已提供的变更信息，写一条符合 Conventional Commits 的 commit message。

${context}

要求：
1. 使用简体中文
2. 格式：type(scope): subject，必要时可加正文
3. 只输出 commit message 本身，不要解释，不要使用工具，不要包裹多余说明
4. 不要使用 markdown 代码块

"

  if [[ -n $hint ]]; then
    prompt+="用户补充说明：${hint}

"
  fi

  prompt+="变更信息：
${changes}
"

  msg=$(_ai_git_invoke_text "$prompt") || return 1
  msg=$(_ai_git_clean_message "$msg")

  if [[ -z $msg ]]; then
    echo "Error: 未能生成 commit message" >&2
    return 1
  fi

  print -r -- "$msg"
}

_ai_git_do_commit() {
  local hint="$*"
  local msg msgfile

  _ai_git_check_repo || return 1

  if ! _ai_git_has_changes; then
    echo "没有可提交的变更" >&2
    return 1
  fi

  echo "收集变更并生成 commit message..."
  msg=$(_ai_git_generate_commit_message "$hint") || return 1

  echo "Commit message:"
  print -r -- "$msg"
  echo ""

  git add -A || return 1

  msgfile=$(mktemp)
  print -r -- "$msg" >"$msgfile"
  if git commit -F "$msgfile"; then
    rm -f "$msgfile"
    return 0
  else
    rm -f "$msgfile"
    return 1
  fi
}

# agc — AI 自动 commit（本地采集 diff + 仅生成 message + shell 提交）
agc() {
  _ai_git_do_commit "$@"
}

# agcp — AI commit + push
agcp() {
  local branch
  _ai_git_do_commit "$@" || return 1
  branch=$(git branch --show-current)
  git push -u origin "$branch"
}

# agrv — AI review 当前 diff（预注入截断后的变更，减少 Agent 自己跑 git）
agrv() {
  _ai_git_check_repo || return 1

  local focus="$*"
  local context changes prompt

  if ! _ai_git_has_changes; then
    echo "没有可审查的变更" >&2
    return 1
  fi

  context=$(_ai_git_context) || return 1
  echo "收集变更上下文..."
  changes=$(_ai_git_collect_changes) || return 1

  prompt="你正在一个 Git 仓库中工作。

${context}

下方已提供 git 变更摘要与截断后的 diff，请直接基于这些信息审查，不要再运行 git diff（除非信息明显不足）。

请使用简体中文提供：
1. 变更摘要
2. 潜在问题（bug、边界情况、安全等）
3. 改进建议

不要修改任何文件，不要 commit 或 push。

变更信息：
${changes}"

  if [[ -n $focus ]]; then
    prompt="${prompt}

重点关注：${focus}"
  fi

  _ai_git_invoke "$prompt"
}
