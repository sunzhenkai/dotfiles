#!/usr/bin/env bash
# 第三方 Agent Skill 安全审计（安装前使用）
# 用法: audit-skill.sh <skill-dir> [--json]
# 退出码: 0=通过 | 1=仅有警告（需用户确认） | 2=存在阻断项（禁止安装）
set -euo pipefail

SKILL_DIR="${1:-}"
JSON=0
[[ "${2:-}" == "--json" ]] && JSON=1

if [[ -z "$SKILL_DIR" || ! -d "$SKILL_DIR" ]]; then
  echo "用法: $0 <skill-dir> [--json]" >&2
  exit 2
fi

SKILL_DIR="$(cd "$SKILL_DIR" && pwd)"

# name|severity(critical|warn)|regex
PATTERNS=(
  # --- critical: 阻断安装 ---
  "prompt_injection_override|critical|(?i)(ignore|disregard|forget|override).{0,40}(previous|prior|system|safety|security).{0,20}(instruction|rule|guideline|constraint)"
  # jailbreak_role 的 without limit 分支豁免 "without limitation"：MIT/BSD 授权套话
  # （"including without limitation the rights"）必然误报；"without any limits" 等
  # 真实越狱措辞仍命中，no restrictions 分支不受影响。
  "jailbreak_role|critical|(?i)(you are now|act as|pretend to be|DAN mode|jailbreak|no restrictions|without (any )?limit(?!ation))"
  "bypass_approval|critical|(?i)(disable|bypass|skip|turn off).{0,30}(approval|sandbox|security|guardrail|confirmation|human.{0,10}review)"
  "pipe_to_shell|critical|(?i)(curl|wget).{0,120}\|\s*(ba)?sh"
  "destructive_rm_root|critical|rm\s+-rf\s+(/|\~|\*|\$HOME\b|\$\{HOME\})"
  "destructive_mkfs|critical|(?i)\bmkfs\.|\bdd\s+if=.*of=/dev/"
  # credential_paths 的 ~/.ssh 分支排除 ~/.ssh/config（非密钥配置）与 ~/.ssh/senv/
  # （senv 自管理 SSH 片段树，其 skill 文档必然提及）；私钥路径仍由 /\.ssh/id_ 兜底。
  "credential_paths|critical|(?i)(~/?\.ssh(?!/(?:senv\b|config\b))|/\.ssh/id_|~/?\.aws/credentials|~/?\.gnupg|~/?\.config/gcloud|\.netrc\b|\.env\b.*\b(read|cat|source|export)\b|\b(cat|source)\b.{0,80}\.env\b)"
  "exfil_env_secret|critical|(?i)(curl|wget|fetch|post|upload|send).{0,80}(\$(API|TOKEN|KEY|SECRET|PASSWORD|ENV|HOME)|process\.env|getenv|os\.environ)"
  "hardcoded_secret|critical|(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"
  "bearer_literal|critical|(?i)Bearer\s+[A-Za-z0-9\-._~+/]{20,}=*"
  "eval_external|critical|(?i)\beval\s+.{0,80}(\$\(|\bcurl\b|\bwget\b|base64\s+(-d|--decode))"
  "obfuscated_exec|critical|(?i)base64\s+(-d|--decode).{0,40}\|\s*(ba)?sh"
  "modify_git_config|critical|(?i)git\s+config\s+(--global\s+)?(user\.|credential\.|url\.)"
  # --- warn: 需用户确认 ---
  "force_push|warn|(?i)git\s+push\s+.*(--force|-f)\b"
  "skip_hooks|warn|(?i)--no-verify|--no-gpg-sign"
  "sudo_usage|warn|(?i)\bsudo\b"
  "global_shell_rc|warn|(?i)(~/?\.(bashrc|zshrc|profile)|/etc/(profile|bash\.bashrc))"
  "download_execute|warn|(?i)(curl|wget).{0,80}(https?://(?!github\.com|raw\.githubusercontent\.com|gitlab\.com))[^\\s]*.{0,40}(chmod|execute|run|install)"
  "npm_pip_untrusted|warn|(?i)(npm|pnpm|yarn|pip|pip3)\s+(install|i)\s+(git\+|https?://|http://)"
  "browser_session|warn|(?i)(cookie|sessionStorage|localStorage|browser-profile|playwright.*storage)"
  "internal_url|warn|(?i)https?://[a-z0-9.-]*\.(internal|corp|intranet)(/|\b)"
  "codeup_private|warn|(?i)codeup\.aliyun\.com"
  "binary_in_skill|warn|__BINARY__"
)

TEXT_EXTS='\.(md|markdown|txt|sh|bash|zsh|py|js|ts|jsx|tsx|json|yaml|yml|toml|ini|cfg|conf|env\.example)$'
TEXT_NAMES='^(SKILL|README|LICENSE|CHANGELOG)(\.md)?$|^(Makefile|Dockerfile)$'

CRITICAL=0
WARN=0
FINDINGS=()

add_finding() {
  local sev="$1" name="$2" file="$3" line="$4" snippet="$5"
  FINDINGS+=("$sev|$name|$file|$line|$snippet")
  [[ "$sev" == "critical" ]] && CRITICAL=$((CRITICAL + 1)) || WARN=$((WARN + 1))
}

scan_text_file() {
  local file="$1"
  local rel="${file#"$SKILL_DIR"/}"

  for entry in "${PATTERNS[@]}"; do
    [[ "$entry" == *"__BINARY__"* ]] && continue
    local name="${entry%%|*}"
    local rest="${entry#*|}"
    local sev="${rest%%|*}"
    local regex="${rest#*|}"
    local line_num line
    while IFS= read -r line; do
      line_num="${line%%:*}"
      line="${line#*:}"
      case "$name" in
        skip_hooks | force_push | sudo_usage | modify_git_config | global_shell_rc | browser_session)
          if echo "$line" | grep -qiP '(不要|禁止|不记录|avoid|never|do not|don'\''t|不得|不可|warn|警告)' 2>/dev/null; then
            continue
          fi
          ;;
      esac
      local snippet="${line:0:120}"
      [[ ${#line} -gt 120 ]] && snippet="${snippet}..."
      add_finding "$sev" "$name" "$rel" "$line_num" "$snippet"
    done < <(grep -nPi -e "$regex" "$file" 2>/dev/null || true)
  done
}

scan_binaries() {
  while IFS= read -r -d '' file; do
    local rel="${file#"$SKILL_DIR"/}"
    local base
    base="$(basename "$file")"
    # GNU find -regex 默认 emacs 语法，TEXT_EXTS 的 ERE 分组不会排除 .py/.sh。
    if [[ "$file" =~ $TEXT_EXTS || "$base" =~ $TEXT_NAMES ]]; then
      continue
    fi
    local mime
    mime="$(file -b "$file" 2>/dev/null || true)"
    # shebang 纯文本会被 file 标成 "text executable"；只认真正的二进制格式。
    if echo "$mime" | grep -qiE 'ELF|Mach-O|PE32|shared object'; then
      add_finding "warn" "binary_in_skill" "$rel" "0" "${mime:0:80}"
    fi
  done < <(
    find "$SKILL_DIR" -type f \
      ! -path '*/.git/*' ! -path '*/node_modules/*' ! -path '*/vendor/*' \
      -print0 2>/dev/null
  )
}

scan_tree() {
  while IFS= read -r -d '' file; do
    local base
    base="$(basename "$file")"
    if [[ "$file" =~ $TEXT_EXTS || "$base" =~ $TEXT_NAMES ]]; then
      scan_text_file "$file"
    fi
  done < <(
    find "$SKILL_DIR" -type f \
      ! -path '*/.git/*' ! -path '*/node_modules/*' ! -path '*/vendor/*' \
      -print0 2>/dev/null
  )

  scan_binaries
}

# 必须存在 SKILL.md
if [[ ! -f "$SKILL_DIR/SKILL.md" ]]; then
  add_finding "critical" "missing_skill_md" "." "0" "目录缺少 SKILL.md"
fi

scan_tree

if [[ "$JSON" -eq 1 ]]; then
  printf '{"skill_dir":%q,"critical":%d,"warn":%d,"findings":[' "$SKILL_DIR" "$CRITICAL" "$WARN"
  first=1
  for f in "${FINDINGS[@]}"; do
    IFS='|' read -r sev name file line snippet <<< "$f"
    [[ $first -eq 0 ]] && printf ','
    first=0
    printf '{"severity":%q,"rule":%q,"file":%q,"line":%s,"snippet":%q}' \
      "$sev" "$name" "$file" "$line" "$snippet"
  done
  printf ']}\n'
else
  echo "=== Skill 安全审计: $SKILL_DIR ==="
  if [[ ${#FINDINGS[@]} -eq 0 ]]; then
    echo "结果: 通过（未发现风险模式）"
  else
    echo "发现: ${CRITICAL} 项阻断, ${WARN} 项警告"
    echo
    for f in "${FINDINGS[@]}"; do
      IFS='|' read -r sev name file line snippet <<< "$f"
      tag=$([[ "$sev" == "critical" ]] && echo "BLOCK" || echo "WARN ")
      printf '[%s] %s (%s:%s)\n    %s\n' "$tag" "$name" "$file" "$line" "$snippet"
    done
    echo
    if [[ $CRITICAL -gt 0 ]]; then
      echo "结论: 存在阻断项，禁止安装。"
    else
      echo "结论: 存在警告，需用户明确确认后方可安装。"
    fi
  fi
fi

if [[ $CRITICAL -gt 0 ]]; then
  exit 2
elif [[ $WARN -gt 0 ]]; then
  exit 1
fi
exit 0
