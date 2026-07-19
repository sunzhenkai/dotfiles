#!/usr/bin/env bash
# agents 安装包：编排 agent 相关 CLI（不写 MCP/skills）
# 由 install.sh source。

# Bundle 成员（与 agents sync TOOLS 对齐；可在此扩展）
AGENTS_BUNDLE_MODULES=(claude cursor opencode codex kimi-code)

install_agents_bundle() {
  echo "========================================"
  echo "agents install bundle"
  echo "成员: ${AGENTS_BUNDLE_MODULES[*]}"
  echo "说明: 只安装 CLI；配置请随后运行: dotf agents -c"
  echo "========================================"

  local ok=0 skip=0 fail=0
  local results=()

  for mod in "${AGENTS_BUNDLE_MODULES[@]}"; do
    local status="ok"
    local detail=""

    case "$mod" in
    claude)
      if command -v claude &>/dev/null; then
        status="skip"
        detail="已安装: $(command -v claude)"
      else
        if install_claude_cli; then
          if command -v claude &>/dev/null; then
            status="ok"
            detail="新装完成"
          else
            status="skip"
            detail="用户跳过或未在 PATH"
          fi
        else
          status="fail"
          detail="安装失败"
        fi
      fi
      ;;
    cursor)
      if command -v cursor-agent &>/dev/null; then
        status="skip"
        detail="已安装: $(command -v cursor-agent)"
      else
        if install_cursor_cli; then
          if command -v cursor-agent &>/dev/null; then
            status="ok"
            detail="新装完成"
          else
            status="fail"
            detail="安装后未找到 cursor-agent"
          fi
        else
          # 用户跳过 confirm 时返回 0 且未安装
          if command -v cursor-agent &>/dev/null; then
            status="ok"
          else
            status="skip"
            detail="用户跳过或未安装"
          fi
        fi
      fi
      ;;
    opencode)
      if command -v opencode &>/dev/null; then
        status="skip"
        detail="已安装: $(command -v opencode)"
      else
        if install_opencode; then
          if command -v opencode &>/dev/null; then
            status="ok"
            detail="新装完成"
          else
            status="skip"
            detail="用户跳过或未在 PATH"
          fi
        else
          status="fail"
          detail="安装失败"
        fi
      fi
      ;;
    codex)
      if command -v codex &>/dev/null; then
        status="skip"
        detail="已安装: $(command -v codex)"
      else
        if install_codex; then
          if command -v codex &>/dev/null; then
            status="ok"
            detail="新装完成"
          else
            status="skip"
            detail="用户跳过或未在 PATH"
          fi
        else
          status="fail"
          detail="安装失败"
        fi
      fi
      ;;
    kimi-code)
      # 与 install_kimi_code 一致：官方装到 ~/.kimi-code/bin
      if [[ -d "$HOME/.kimi-code/bin" && ":$PATH:" != *":$HOME/.kimi-code/bin:"* ]]; then
        export PATH="$HOME/.kimi-code/bin:$PATH"
      fi
      if command -v kimi &>/dev/null || [[ -x "$HOME/.kimi-code/bin/kimi" ]]; then
        status="skip"
        detail="已安装: $(command -v kimi 2>/dev/null || echo "$HOME/.kimi-code/bin/kimi")"
      else
        if install_kimi_code; then
          if command -v kimi &>/dev/null || [[ -x "$HOME/.kimi-code/bin/kimi" ]]; then
            status="ok"
            detail="新装完成"
          else
            status="skip"
            detail="用户跳过或未在 PATH"
          fi
        else
          status="fail"
          detail="安装失败"
        fi
      fi
      ;;
    *)
      status="fail"
      detail="未知 bundle 成员: $mod"
      ;;
    esac

    case "$status" in
    ok) ok=$((ok + 1)) ;;
    skip) skip=$((skip + 1)) ;;
    fail) fail=$((fail + 1)) ;;
    esac
    results+=("$status|$mod|$detail")
    printf "  %-6s  %-12s %s\n" "$status" "$mod" "$detail"
  done

  echo ""
  echo "摘要: ok=$ok  skip(up-to-date/跳过)=$skip  fail=$fail"
  echo ""
  echo "下一步:"
  echo "  dotf agents -c              # 同步 skills + MCP"
  echo "  python3 scripts/agents/doctor.py   # 详细状态报告"
  echo "  （-i agents 不会写入 MCP/skills）"

  if [ "$fail" -gt 0 ]; then
    return 1
  fi
  return 0
}
