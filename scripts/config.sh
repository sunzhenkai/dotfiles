#!/bin/bash
# dotfiles 配置安装脚本（兼容 Bash 3.2+）
set -e

DOTFILES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%s)
BACKUP_DIR="$HOME/.config/backups"
export DOTFILES_ROOT
export DOTF_BACKUP_DIR="$BACKUP_DIR"

# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/modules.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"

# ============================================================
# 配置映射 — 真相源为 modules.yaml（经 modules.sh）
# ============================================================

# 获取配置定义 "source:target"，未知名称返回非零
get_config_def() {
  local name="$1" source target
  modules_exists "$name" || return 1
  modules_has "$name" config || return 1
  source=$(modules_source "$name") || return 1
  target=$(modules_target "$name") || return 1
  echo "${source}:${target}"
}

get_config_desc() {
  modules_desc "$1" 2>/dev/null || echo "$1"
}

# 获取所有配置名（空格分隔）；传 --filter-os 时按当前 OS 过滤
get_all_config_names() {
  if [[ "${1:-}" == "--filter-os" ]]; then
    _modules_py names --capability config --filter-os
  else
    modules_names config
  fi
}

# ============================================================
# 备份与安装
# ============================================================

backup_to() {
  local src="$1"
  local dest
  dest=$(dotf_backup_to "$src")
  echo "已备份 $(basename "$src") 到 $dest"
}

# 创建 symlink（带备份），source 为仓库内相对路径，target 为绝对路径。
link_file() {
  local source="$1"
  local target="$2"
  dotf_ensure_symlink "$source" "$target"
}

install_config() {
  local name="$1"
  local def
  def=$(get_config_def "$name") || {
    echo "未知配置: $name"
    echo "可用配置: $(get_all_config_names)"
    return 1
  }

  IFS=':' read -r source target <<<"$def"
  target=$(dotf_expand_path "$target")
  if ! dotf_ensure_symlink "$source" "$target"; then
    return 1
  fi
  if [ "${DOTF_CFG_STATUS:-}" = "unchanged" ]; then
    echo "已安装: $name"
  else
    echo "已安装: $name"
  fi
}

# ============================================================
# 特殊配置
# ============================================================

# 特殊配置：zsh
install_zsh() {
  install_config "zsh"
  if [ -e ~/.zshrc ]; then
    # 内容相同则跳过
    if diff -q "$DOTFILES_ROOT/config/shell/zsh/zshrc" ~/.zshrc >/dev/null 2>&1; then
      echo "~/.zshrc 已是最新"
      return
    fi
    mv ~/.zshrc ~/.zshrc-$TIMESTAMP
  fi
  cp "$DOTFILES_ROOT/config/shell/zsh/zshrc" ~/.zshrc
  echo "已安装: ~/.zshrc"
}

# 统一 agents sync（skills + MCP/env；可传 --skills-only/--env-only/--profile）
# 诊断请用: dotf agents -d
sync_agents() {
  "$DOTFILES_ROOT/scripts/agents/sync.sh" "$@"
}

install_agents() {
  # 用法: install_agents [tool|all] [--profile ... --skills-only ...]
  # 无 tool 时默认 all；显式 tool 名启用过滤同步
  local tool="all"
  if [ $# -gt 0 ] && [[ "$1" != --* ]]; then
    tool="$1"
    shift
  fi
  sync_agents "$tool" "$@"
}

# 特殊配置：claude（settings / .claude.json；MCP/skills 走统一 agents sync）
install_claude() {
  local claude_dir="$HOME/.claude"
  if [ ! -d "$claude_dir" ]; then
    mkdir -p "$claude_dir"
  fi

  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi

  local settings_target="$claude_dir/settings.json"
  local settings_template="$DOTFILES_ROOT/agents/vendors/claude/settings.json"

  if [ -e "$settings_target" ]; then
    mv "$settings_target" "$settings_target-$TIMESTAMP"
  fi

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$settings_template" >"$settings_target"
    echo "已安装: settings.json (已使用 ZHIPU_API_KEY)"
  else
    cp "$settings_template" "$settings_target"
    echo "已安装: settings.json (请手动设置 ZHIPU_API_KEY)"
  fi

  local claude_json_target="$HOME/.claude.json"
  local claude_json_source="$DOTFILES_ROOT/agents/vendors/claude/.claude.json"

  if [ ! -f "$claude_json_source" ]; then
    echo "⚠️  跳过 ~/.claude.json symlink: dotfiles 中不存在 $claude_json_source"
  elif [ -L "$claude_json_target" ]; then
    local current_link
    current_link=$(readlink -f "$claude_json_target" 2>/dev/null || readlink "$claude_json_target")
    local expected_abs
    expected_abs=$(readlink -f "$claude_json_source" 2>/dev/null || echo "$claude_json_source")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "已安装: .claude.json"
    else
      if [ -e "$claude_json_target" ]; then
        mkdir -p "$BACKUP_DIR"
        mv "$claude_json_target" "$BACKUP_DIR/.claude.json-${TIMESTAMP}"
        echo "已备份 .claude.json 到 $BACKUP_DIR/.claude.json-${TIMESTAMP}"
      fi
      ln -sf "$claude_json_source" "$claude_json_target"
      echo "已安装: .claude.json"
    fi
  else
    if [ -e "$claude_json_target" ]; then
      mkdir -p "$BACKUP_DIR"
      mv "$claude_json_target" "$BACKUP_DIR/.claude.json-${TIMESTAMP}"
      echo "已备份 .claude.json 到 $BACKUP_DIR/.claude.json-${TIMESTAMP}"
    fi
    ln -s "$claude_json_source" "$claude_json_target"
    echo "已安装: .claude.json"
  fi

  # 共享 skills/MCP 同步由 `dotf agents -c` 显式触发，单工具 config 不隐式 sync

  if [ -n "${SUDO_USER:-}" ] && [ "$(id -u)" -eq 0 ]; then
    local claude_state="$HOME/.claude.json"
    chown -R "$SUDO_USER:" "$claude_dir" 2>/dev/null || true
    chown "$SUDO_USER:" "$claude_state" 2>/dev/null || true
    echo "已为 \$SUDO_USER 调整 ~/.claude 和 ~/.claude.json 的所有者"
  fi
}

# 特殊配置：codex（依赖 MINIMAX_API_KEY 环境变量，无需 OpenAI 登录）
#
# ~/.codex/config.toml 不再使用软链，而是由「仓库 base + 本地 local」合并生成
# 的真实文件。原因：codex 会把 [projects."<path>"] 自动写进该文件，软链会穿透
# 污染仓库。projects 维护在 agents/vendors/codex/config.local.toml（gitignore），安装时合并。
#
# 注意：每次安装都用 base + local 重新覆盖 ~/.codex/config.toml。codex 新增的
#       信任不会自动回抽——需手动把对应 [projects."<path>"] 块加入 local 后重跑。
install_codex() {
  if [ -z "$MINIMAX_API_KEY" ]; then
    echo "⚠️  警告: MINIMAX_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
    echo "（本配置使用自定义 provider，无需 codex login / OPENAI_API_KEY）"
  fi

  mkdir -p "$HOME/.codex"

  local base="$DOTFILES_ROOT/agents/vendors/codex/config.toml"
  local local_cfg="$DOTFILES_ROOT/agents/vendors/codex/config.local.toml"
  local target="$HOME/.codex/config.toml"

  # 旧机制遗留：target 若是软链则移除，改用合并生成
  [ -L "$target" ] && rm "$target" && echo "已移除旧的 config.toml 软链"

  # 合并 base + local → target（真实文件，非软链；每次覆盖生成）
  {
    cat "$base"
    if [ -f "$local_cfg" ]; then
      echo ""
      echo "# ============================================================"
      echo "# ↓↓↓ 以下来自 agents/vendors/codex/config.local.toml（机器特定，不纳入 git） ↓↓↓"
      cat "$local_cfg"
    fi
  } > "$target"
  echo "已安装: ~/.codex/config.toml（base + local 合并生成）"

  # 模型能力目录（model catalog，只读，仍用软链）
  mkdir -p "$HOME/.codex/model-catalogs"
  link_file "agents/vendors/codex/model-catalogs/custom-catalog.json" "$HOME/.codex/model-catalogs/custom-catalog.json"
  echo "已安装: ~/.codex/model-catalogs/custom-catalog.json"
  # skills/MCP：dotf agents -c [--tool codex] 或 sync.sh codex
}

# 特殊配置：tmux（依赖 submodule tpm；补装 tmux-yank 剪贴板工具）
install_tmux() {
  git -C "$DOTFILES_ROOT" submodule update --init config/multiplexers/tmux/3rd/tpm
  install_config "tmux"

  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/tools/common.sh"
  install_tmux_clipboard_deps || true
}

# 特殊配置：cursor（MCP + skills 由统一 agents sync）
install_cursor() {
  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi

  mkdir -p "$HOME/.cursor"
  echo "Cursor vendor 目录已就绪；共享 sync 请运行: dotf agents -c"
}


install_opencode() {
  install_config "opencode"
  # skills/MCP：dotf agents -c 或 sync.sh opencode
}

# 特殊配置：kimi-code
# ~/.kimi-code/config.toml 用复制而非软链：/login 会写入 oauth/凭证相关字段，
# 软链会穿透污染仓库；已存在的配置也不覆盖，避免抹掉登录状态。
install_kimi_code_config() {
  local source="$DOTFILES_ROOT/agents/vendors/kimi-code/config.toml"
  local target="$HOME/.kimi-code/config.toml"

  mkdir -p "$HOME/.kimi-code"

  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "已存在: ~/.kimi-code/config.toml（跳过覆盖，避免丢失 /login 凭证）"
    echo "如需重置，请先备份并删除该文件后重新运行: dotf kimi-code -c"
  else
    cp "$source" "$target"
    echo "已安装: ~/.kimi-code/config.toml"
    echo "提示: 启动 kimi 后执行 /login 完成鉴权"
  fi
  # skills/MCP：dotf agents -c 或 sync.sh kimi-code
}

# 特殊配置：pi
# ~/.pi/agent/settings.json、auth.json 用文件而非软链：/settings、/login 会写入本地状态。
# settings：合并仓库托管键，保留本地 packages/theme 等。
# auth：仅在缺失 minimax-cn 时写入 "$MINIMAX_API_KEY" 引用（不落真实密钥）。
install_pi_config() {
  local settings_src="$DOTFILES_ROOT/agents/vendors/pi/settings.json"
  local settings_tgt="$HOME/.pi/agent/settings.json"
  local auth_tgt="$HOME/.pi/agent/auth.json"

  mkdir -p "$HOME/.pi/agent"

  if [ ! -f "$settings_src" ]; then
    echo "✗ 缺少仓库模板: $settings_src"
    return 1
  fi

  python3 - "$settings_src" "$settings_tgt" <<'PY'
import json, sys
from pathlib import Path

src_path, tgt_path = Path(sys.argv[1]), Path(sys.argv[2])
# 仓库托管键：可跨机器复用的默认行为；不覆盖本地专属状态键。
managed = {
    "enableSkillCommands",
    "quietStartup",
    "enableInstallTelemetry",
    "defaultProvider",
    "defaultModel",
}
src = json.loads(src_path.read_text(encoding="utf-8"))
tgt = {}
if tgt_path.exists():
    try:
        tgt = json.loads(tgt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        tgt = {}
    if not isinstance(tgt, dict):
        tgt = {}

changed = []
for key in managed:
    if key not in src:
        continue
    if tgt.get(key) != src[key]:
        tgt[key] = src[key]
        changed.append(key)

tgt_path.write_text(json.dumps(tgt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if changed:
    print(f"已更新: ~/.pi/agent/settings.json（托管键: {', '.join(changed)}）")
else:
    print("已存在: ~/.pi/agent/settings.json（托管键已对齐）")
PY

  # auth.json：缺省写入 env 引用；已有 minimax-cn 则不动
  python3 - "$auth_tgt" <<'PY'
import json, sys
from pathlib import Path

auth_path = Path(sys.argv[1])
data = {}
if auth_path.exists():
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}

entry = data.get("minimax-cn")
if isinstance(entry, dict) and entry.get("type") and entry.get("key"):
    print("已存在: ~/.pi/agent/auth.json（保留 minimax-cn）")
else:
    data["minimax-cn"] = {"type": "api_key", "key": "$MINIMAX_API_KEY"}
    auth_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    auth_path.chmod(0o600)
    print('已写入: ~/.pi/agent/auth.json（minimax-cn.key = "$MINIMAX_API_KEY"）')
PY

  if [ -z "${MINIMAX_API_KEY:-}" ] && [ -z "${MINIMAX_CN_API_KEY:-}" ]; then
    echo "⚠️  未检测到 MINIMAX_API_KEY / MINIMAX_CN_API_KEY；pi 鉴权会失败"
    echo "   国内站约定：export MINIMAX_API_KEY=...（与 Codex 同源），auth 会展开 \$MINIMAX_API_KEY"
  fi
  if [ -n "${AWS_ACCESS_KEY_ID:-}" ] || [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "提示: 环境中有 AWS_*；已固定 defaultProvider=minimax-cn，避免 Pi 误选 amazon-bedrock"
  fi
  echo "提示: 海外站可改 settings 为 defaultProvider=minimax，或 /model 切换"
  # skills/prompts：dotf agents -c 或 sync.sh pi（MCP skip）
}

install_all() {
  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/lib/runner.sh"
  local name
  for name in $(get_all_config_names --filter-os); do
    if [ "$name" = "agents" ]; then
      continue # 末尾统一 sync
    fi
    runner_run_action config "$name" || true
  done
  sync_agents all
}

# ============================================================
# 主函数
# ============================================================

main() {
  local config="${1:-}"

  if [ -z "$config" ]; then
    echo "用法: $0 <配置名|--all> [agents 选项...]"
    echo ""
    echo "可用配置:"
    for name in $(get_all_config_names); do
      printf "  %-12s %s\n" "$name" "$(get_config_desc "$name")"
    done
    echo ""
    echo "选项:"
    echo "  --all, -a       安装所有配置"
    echo "  --list          仅列出配置名"
    echo "  --list-desc     列出配置名及描述"
    echo ""
    echo "agents 附加选项（仅 agents）:"
    echo "  --profile NAME --skills-only --env-only --dry-run --strict"
    echo "诊断请用: dotf agents -d  或  dotf agents -cd"
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/lib/runner.sh"

  case "$config" in
  --list)
    for name in $(get_all_config_names); do
      echo "$name"
    done
    ;;
  --list-desc)
    for name in $(get_all_config_names); do
      printf "%s\t%s\n" "$name" "$(get_config_desc "$name")"
    done
    ;;
  --all | -a) install_all ;;
  agents)
    shift
    runner_run_action config agents "$@"
    ;;
  *)
    # 约定式处理器；无处理器时 runner 走 compat
    runner_run_action config "$config"
    ;;
  esac
}

# 仅直接执行时进入 CLI；可被约定式处理器 source
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
