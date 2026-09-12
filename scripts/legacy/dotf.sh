#!/usr/bin/env bash
# dotf — Dotfiles CLI 轻量入口
# 纯委托：参数解析 + 子命令路由，不含业务逻辑
# CLI: 主体优先 — dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd

# 旧版 bash CLI（DOTF_LEGACY_CLI=1 逃生门；不再演进）
# 脚本位于 scripts/legacy/，仓库根为其上两级
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# shellcheck source=/dev/null
source "$SCRIPT_DIR/scripts/modules.sh"

# Compatibility helpers always use the system Bash; hosted macOS validates 3.2.
get_bash() {
  echo "/bin/bash"
}

# ============================================================
# 通用工具函数
# ============================================================

# 全局计划控制（由 main 设置）
DOTF_YES=0
DOTF_DRY_RUN=0
DOTF_JSON=0
DOTF_DEEP=0
DOTF_CONTINUE_ON_ERROR=0
DOTF_USAGE_PROFILE=""

confirm() {
  local prompt="$1"
  local default="${2:-N}"
  local reply

  if [ "${DOTF_YES:-0}" -eq 1 ]; then
    return 0
  fi

  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n]: " reply
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
  else
    read -r -p "$prompt [y/N]: " reply
    [[ "$reply" =~ ^[Yy] ]]
  fi
}

# 生成计划并交给 run_plan.sh（唯一编排入口）
# 用法: plan_and_run <actions_csv> [--all|--modules m1,m2] [--os id] [--profile name]
plan_and_run() {
  local actions_csv="$1"
  shift
  local select_all=0
  local modules_csv=""
  local os_id=""
  local profile=""
  local -a plan_args=()
  local -a run_args=()
  local -a cfg_x=()
  local -a doc_x=()

  while [ $# -gt 0 ]; do
    case "$1" in
    --all) select_all=1 ;;
    --modules)
      shift
      modules_csv="${1:-}"
      ;;
    --os)
      shift
      os_id="${1:-}"
      ;;
    --profile)
      shift
      profile="${1:-}"
      ;;
    --config-extra)
      shift
      cfg_x+=("$1")
      ;;
    --doctor-extra)
      shift
      doc_x+=("$1")
      ;;
    *)
      echo "plan_and_run: 未知参数 $1" >&2
      return 2
      ;;
    esac
    shift
  done

  plan_args=(plan --actions "$actions_csv" --format machine)
  [ -n "$os_id" ] && plan_args+=(--os "$os_id")
  [ -n "$profile" ] && plan_args+=(--profile "$profile")
  [ "$select_all" -eq 1 ] && plan_args+=(--all)
  [ -n "$modules_csv" ] && plan_args+=(--modules "$modules_csv")

  local plan_file
  plan_file="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$plan_file'" RETURN

  # Preserve planner failure exactly; an unsuccessful planner never reaches runner.
  python3 "$SCRIPT_DIR/src/planner.py" "${plan_args[@]}" >"$plan_file"
  local planner_rc=$?
  if [ "$planner_rc" -ne 0 ]; then
    return "$planner_rc"
  fi

  run_args=(--plan-file "$plan_file")
  [ "$DOTF_YES" -eq 1 ] && run_args+=(--yes)
  [ "$DOTF_DRY_RUN" -eq 1 ] && run_args+=(--dry-run)
  [ "${DOTF_CONTINUE_ON_ERROR:-0}" -eq 1 ] && run_args+=(--continue-on-error)
  [ "${DOTF_JSON:-0}" -eq 1 ] && run_args+=(--json)
  [ "${DOTF_DEEP:-0}" -eq 1 ] && export DOTF_DEEP=1
  local x
  for x in "${cfg_x[@]+"${cfg_x[@]}"}"; do
    run_args+=(--config-extra "$x")
  done
  for x in "${doc_x[@]+"${doc_x[@]}"}"; do
    run_args+=(--doctor-extra "$x")
  done

  bash "$SCRIPT_DIR/scripts/run_plan.sh" "${run_args[@]}"
}

run_config() {
  local bash_bin
  bash_bin="$(get_bash)"
  "$bash_bin" "$SCRIPT_DIR/scripts/config.sh" "$@"
}

run_install() {
  bash "$SCRIPT_DIR/scripts/install.sh" "$@"
}

run_doctor() {
  bash "$SCRIPT_DIR/scripts/doctor.sh" "$@"
}

# ============================================================
# 子命令: pull
# ============================================================

cmd_pull() {
  cd "$SCRIPT_DIR" || exit 1

  if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || \
     [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
    echo "检测到未提交的改动，执行 stash..."
    git stash || { echo "错误: git stash 失败"; exit 1; }
    local stashed=1
  fi

  echo "拉取最新代码..."
  if ! git pull; then
    echo "错误: git pull 失败"
    [ "${stashed:-0}" -eq 1 ] && echo "改动已 stash，请手动恢复: git stash pop"
    exit 1
  fi

  if [ "${stashed:-0}" -eq 1 ]; then
    echo "恢复暂存的改动..."
    if ! git stash pop; then
      echo ""
      echo "⚠️  stash pop 发生冲突，请手动解决："
      echo "   1. 查看冲突文件: git status"
      echo "   2. 解决冲突后: git stash drop"
      exit 1
    fi
  fi

  echo "✓ dotfiles 已更新"
}

# ============================================================
# 子命令: init（OS profile 全量）
# ============================================================

cmd_init() {
  local force_os=""
  local list_only=0
  local usage_profile=""

  while [ $# -gt 0 ]; do
    case "$1" in
    --list)
      list_only=1
      ;;
    --os)
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: --os 需要参数"
        exit 1
      fi
      force_os="$1"
      ;;
    --profile)
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: --profile 需要参数"
        exit 1
      fi
      usage_profile="$1"
      ;;
    --yes | -y)
      DOTF_YES=1
      ;;
    --dry-run)
      DOTF_DRY_RUN=1
      ;;
    --continue-on-error)
      DOTF_CONTINUE_ON_ERROR=1
      ;;
    -h | --help)
      echo "用法: dotf init [--os <id>] [--profile <name>] [--yes] [--dry-run] [--continue-on-error] [--list]"
      echo ""
      echo "  OS 决定平台适用性；--profile 选择使用场景（默认 full）"
      echo "  --os <id>        强制 OS（darwin、ubuntu、arch…）"
      echo "  --profile <name> 使用场景 profile（minimal/remote/desktop/full）"
      echo "  --list           列出 OS 与使用场景 profile"
      echo "  --dry-run        只展示计划（允许跨 OS 预览）"
      echo "  --continue-on-error 失败后仅继续依赖无关动作（最终仍非零）"
      echo "  --yes            跳过计划确认与副作用确认"
      exit 0
      ;;
    *)
      echo "错误: 未知 init 选项 '$1'"
      echo "用法: dotf init [--os <id>] [--profile <name>] [--list]"
      exit 1
      ;;
    esac
    shift
  done

  if [ "$list_only" -eq 1 ]; then
    echo "可用 OS profile:"
    modules_profiles os | sed 's/^/  /'
    echo ""
    echo "可用使用场景 profile:"
    modules_profiles usage | sed 's/^/  /'
    exit 0
  fi

  if [ -z "$usage_profile" ]; then
    usage_profile="$(python3 "$SCRIPT_DIR/src/modules.py" profiles default 2>/dev/null || echo full)"
    [ -z "$usage_profile" ] && usage_profile=full
  fi

  local os_id
  if [ -n "$force_os" ]; then
    os_id="$force_os"
    echo "使用强制 OS: $os_id"
  else
    os_id="$(modules_detect_os)"
    echo "检测到 OS: $os_id"
  fi

  echo "============================================"
  echo "  Dotfiles 初始化 (os=$os_id profile=$usage_profile)"
  echo "============================================"
  echo ""

  plan_and_run "install,config" --os "$os_id" --profile "$usage_profile"
}

cmd_path() {
  echo "$SCRIPT_DIR"
}

# 只读环境状态：按 profile 生成期望计划并跑 L0 doctor
cmd_status() {
  local usage_profile=""
  local json=0
  while [ $# -gt 0 ]; do
    case "$1" in
    --profile)
      shift
      usage_profile="${1:-}"
      ;;
    --json) json=1 ;;
    -h | --help)
      echo "用法: dotf status [--profile <name>] [--json]"
      echo "  只读 L0 检查；不安装、不改配置、不跑 L1"
      exit 0
      ;;
    *)
      echo "错误: 未知选项 $1"
      exit 1
      ;;
    esac
    shift
  done
  if [ -z "$usage_profile" ]; then
    usage_profile="$(python3 "$SCRIPT_DIR/src/modules.py" profiles default 2>/dev/null || echo full)"
  fi

  export DOTF_STATUS_MODE=1
  export DOTF_YES=1
  [ "$json" -eq 1 ] && export DOTF_JSON=1

  if [ "$json" -eq 1 ]; then
    echo "环境状态  profile=$usage_profile (只读 L0)" >&2
  else
    echo "环境状态  profile=$usage_profile (只读 L0)"
  fi
  plan_and_run "doctor" --profile "$usage_profile"
}

# 重试最近报告中的 failed 动作
cmd_tui() {
  while [ $# -gt 0 ]; do
    case "$1" in
    -h | --help)
      echo "用法: dotf tui"
      echo "  需要 TTY；缺 Textual 时失败并提示用户级安装"
      echo "  提交后走与 CLI 相同的计划确认（/dev/tty）"
      exit 0
      ;;
    -i | -c | -d | --install | --config | --doctor | --uninstall | --deconfig | -ic | -id | -cd | -icd | -a | --all)
      echo "错误: tui 为独立命令，不能与动作旗标混用"
      echo "请改用 CLI，例如: dotf nvim --deconfig 或 dotf agents skill apply <id>"
      exit 1
      ;;
    *)
      echo "错误: tui 不接受参数 '$1'"
      echo "请改用 CLI 动词"
      exit 1
      ;;
    esac
    shift
  done
  if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo "错误: dotf tui 需要 TTY。请改用 CLI，例如: dotf nvim --deconfig 或 dotf agents skill apply <id>" >&2
    exit 2
  fi
  PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m dotf_tui
}

cmd_agents_artifact() {
  local kind="$1"
  shift
  local verb="${1:-}"
  if [ -z "$verb" ]; then
    echo "用法: dotf agents $kind apply|remove <id>"
    exit 1
  fi
  shift
  case "$kind" in
  skill | mcp) ;;
  *)
    echo "错误: 未知 agents 制品 '$kind'"
    exit 1
    ;;
  esac
  case "$verb" in
  apply | remove) ;;
  *)
    echo "用法: dotf agents $kind apply|remove <id>"
    exit 1
    ;;
  esac

  local id=""
  local tool=""
  local all_tools=0
  while [ $# -gt 0 ]; do
    case "$1" in
    --tool)
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: --tool 需要参数"
        exit 1
      fi
      tool="$1"
      ;;
    --all-tools)
      all_tools=1
      ;;
    --yes | -y)
      DOTF_YES=1
      ;;
    --dry-run)
      DOTF_DRY_RUN=1
      ;;
    --continue-on-error)
      DOTF_CONTINUE_ON_ERROR=1
      ;;
    --json)
      DOTF_JSON=1
      ;;
    -*)
      echo "错误: 未知选项 '$1'"
      exit 1
      ;;
    *)
      if [ -n "$id" ]; then
        echo "错误: 多余参数 '$1'"
        exit 1
      fi
      id="$1"
      ;;
    esac
    shift
  done
  if [ -z "$id" ]; then
    echo "错误: 需要 ${kind} id"
    exit 1
  fi

  local action selector modules_csv
  if [ "$kind" = "skill" ]; then
    if [ -n "$tool" ] || [ "$all_tools" -eq 1 ]; then
      echo "错误: skill apply/remove 以本机为粒度，不接受 --tool/--all-tools"
      exit 1
    fi
    action="skill.$verb"
    # A name may be a group (agents/skills.yaml groups:) expanding to several ids.
    local group_ids=""
    if ! group_ids="$(python3 "$SCRIPT_DIR/src/agents/skills_map.py" --expand-group "$id")"; then
      exit 1
    fi
    if [ -n "$group_ids" ]; then
      modules_csv=""
      local _gid
      while IFS= read -r _gid; do
        [ -z "$_gid" ] && continue
        modules_csv="${modules_csv:+$modules_csv,}skill:$_gid"
      done <<< "$group_ids"
      plan_and_run "$action" --modules "$modules_csv"
      return $?
    fi
    selector="skill:$id"
  else
    if [ "$all_tools" -eq 1 ] && [ -n "$tool" ]; then
      echo "错误: --tool 与 --all-tools 不能同时使用"
      exit 1
    fi
    if [ "$all_tools" -eq 0 ] && [ -z "$tool" ]; then
      echo "错误: mcp 需要 --tool <tool> 或显式 --all-tools"
      exit 1
    fi
    action="mcp.$verb"
    if [ "$all_tools" -eq 1 ]; then
      selector="mcp:*/$id"
    else
      selector="mcp:$tool/$id"
    fi
  fi
  plan_and_run "$action" --modules "$selector"
}

cmd_skills() {
  local verb="${1:-}"
  local mode="add"
  case "$verb" in
  -i | --install) ;;
  -r | --remove | --uninstall)
    mode="remove"
    ;;
  -h | --help)
    echo "用法: dotf skills -i <package> [选项...]"
    echo "      dotf skills -r|--uninstall [skill-name] [选项...]"
    echo "  -i 通过 npx skills 安装；<package> 一般直接写 skill 名称"
    echo "  -r 移除已安装 skill；省略名称时进入 npx skills 交互式移除"
    echo "  <name> 解析顺序：先匹配 agents/skills.yaml 的 group，再匹配 skill id，"
    echo "  最后按字面透传给 npx skills 搜索；一手 skill 请用 dotf agents skill apply"
    echo "  也可写 owner/repo 或 URL 来指定来源仓库"
    echo "  默认交互式：npx skills 会询问安装位置与目标 agents"
    echo "  -g 全局；--project 当前项目；-y 跳过询问；-a 指定 agents"
    echo "示例:"
    echo "  dotf skills -i frontend-design"
    echo "  dotf skills -i frontend-design --project"
    echo "  dotf skills -r design-taste-frontend"
    exit 0
    ;;
  "")
    echo "错误: 需要 -i/--install 或 -r/--remove 动作"
    echo "用法: dotf skills -i <package> [选项...]"
    exit 1
    ;;
  *)
    echo "错误: skills 仅支持 -i/--install 与 -r/--remove/--uninstall"
    echo "用法: dotf skills -i <package> [选项...]"
    exit 1
    ;;
  esac
  shift

  local package=""
  local want_global=0
  local want_project=0
  local -a extra_args=()
  while [ $# -gt 0 ]; do
    case "$1" in
    --project)
      want_project=1
      ;;
    -g | --global)
      want_global=1
      extra_args+=("-g")
      ;;
    --dry-run)
      DOTF_DRY_RUN=1
      ;;
    -a | --agent | -s | --skill | --subagent | --metadata)
      if [ -z "${2:-}" ]; then
        echo "错误: $1 需要参数"
        exit 1
      fi
      extra_args+=("$1" "$2")
      shift
      ;;
    -*)
      extra_args+=("$1")
      ;;
    *)
      if [ -n "$package" ]; then
        echo "错误: 多余参数 '$1'；一次只安装一个 package"
        exit 1
      fi
      package="$1"
      ;;
    esac
    shift
  done

  if [ -z "$package" ] && [ "$mode" = "add" ]; then
    echo "错误: 需要 skills package"
    echo "用法: dotf skills -i <package> [选项...]"
    exit 1
  fi
  if [ "$want_global" -eq 1 ] && [ "$want_project" -eq 1 ]; then
    echo "错误: -g/--global 与 --project 只能二选一"
    exit 1
  fi

  local -a package_args=()
  if [ -n "$package" ]; then
    local -a resolver_args=("$package")
    if [ "$mode" = "remove" ]; then
      resolver_args=("--remove" "$package")
    fi
    local resolve_out
    if ! resolve_out="$(python3 "$SCRIPT_DIR/src/agents/skills_map.py" "${resolver_args[@]}")"; then
      exit 1
    fi
    local map_line
    while IFS= read -r map_line; do
      if [ -n "$map_line" ]; then
        package_args+=("$map_line")
      fi
    done <<< "$resolve_out"
  fi

  local -a skills_args=("$mode" "${package_args[@]}")
  for x in "${extra_args[@]+"${extra_args[@]}"}"; do
    skills_args+=("$x")
  done

  echo "==> npx skills ${skills_args[*]}"
  [ "$DOTF_DRY_RUN" -eq 1 ] && return 0
  if ! command -v npx >/dev/null 2>&1; then
    echo "错误: 未找到 npx；请先安装 Node.js/npm"
    exit 1
  fi
  npx --yes skills "${skills_args[@]}"
}

cmd_retry() {
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/scripts/lib/report.sh"

  local report_json plan_file
  report_json="$(mktemp)"
  plan_file="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$report_json' '$plan_file'" RETURN

  if ! dotf_report_load >"$report_json"; then
    exit 1
  fi

  if ! python3 "$SCRIPT_DIR/src/retry_plan.py" "$report_json" "$plan_file"; then
    exit 1
  fi

  export DOTF_YES=1
  bash "$SCRIPT_DIR/scripts/run_plan.sh" --yes --plan-file "$plan_file"
}

# ============================================================
# 交互选择
# ============================================================

_modules_for_capability() {
  case "$1" in
  install) modules_list install --filter-os --registry-order ;;
  config) modules_list config --filter-os --registry-order ;;
  doctor) modules_list doctor --filter-os --registry-order ;;
  both) modules_list both --filter-os --registry-order ;;
  *) modules_list --filter-os --registry-order ;;
  esac
}

# 交互选择模块；capability: install|config|doctor|both|all
# 将选中的模块名写入全局数组 SELECTED_MODULES
interactive_select() {
  local capability="$1"
  local -a list=()
  local name i
  local cur_group=""
  local g

  SELECTED_MODULES=()

  while IFS= read -r name; do
    [ -z "$name" ] && continue
    list+=("$name")
  done < <(_modules_for_capability "$capability")

  if [ ${#list[@]} -eq 0 ]; then
    echo "当前 OS 下无可用模块"
    return 1
  fi

  while true; do
    echo ""
    echo "可选模块（按 group 展示；序号为选择用，执行顺序仍由 planner 决定）:"
    cur_group=""
    for i in "${!list[@]}"; do
      g=$(modules_group "${list[$i]}" 2>/dev/null || true)
      [ -z "$g" ] && g="other"
      if [ "$g" != "$cur_group" ]; then
        cur_group="$g"
        echo ""
        echo "  [$cur_group]"
      fi
      printf "  %2d) %-14s %s\n" "$((i + 1))" "${list[$i]}" "$(modules_desc "${list[$i]}")"
    done
    echo ""
    echo "输入序号、模块名或 a（全部），空格分隔；q 取消"
    read -r -p "> " input

    if [[ "$input" == "q" || "$input" == "Q" ]]; then
      echo "已取消"
      return 1
    fi

    if [[ "$input" == "a" || "$input" == "A" ]]; then
      SELECTED_MODULES=("${list[@]}")
      return 0
    fi

    local -a picked=()
    local token valid=1 idx
    for token in $input; do
      if [[ "$token" =~ ^[0-9]+$ ]]; then
        idx=$((token - 1))
        if [ "$idx" -lt 0 ] || [ "$idx" -ge ${#list[@]} ]; then
          echo "无效序号: $token"
          valid=0
          break
        fi
        picked+=("${list[$idx]}")
      else
        local found=0
        for name in "${list[@]}"; do
          if [ "$name" = "$token" ]; then
            picked+=("$name")
            found=1
            break
          fi
        done
        if [ "$found" -eq 0 ]; then
          echo "无效输入: $token"
          valid=0
          break
        fi
      fi
    done

    [ "$valid" -eq 0 ] && continue
    if [ ${#picked[@]} -eq 0 ]; then
      echo "未选择任何模块"
      continue
    fi

    # 去重（保序）
    SELECTED_MODULES=()
    for name in "${picked[@]}"; do
      local dup=0
      for existing in "${SELECTED_MODULES[@]+"${SELECTED_MODULES[@]}"}"; do
        [ "$existing" = "$name" ] && dup=1 && break
      done
      [ "$dup" -eq 0 ] && SELECTED_MODULES+=("$name")
    done
    return 0
  done
}

# ============================================================
# 执行动作
# ============================================================

do_install_one() {
  local mod="$1"
  if ! modules_exists "$mod"; then
    echo "错误: 未知模块 '$mod'"
    echo "可用模块:"
    modules_list | sed 's/^/  /'
    return 1
  fi
  if ! modules_has "$mod" install; then
    echo "错误: 模块 '$mod' 无安装步骤"
    echo "提示: 该模块可能仅支持配置，请使用: dotf $mod -c"
    return 1
  fi
  run_install "$mod"
}

do_config_one() {
  local mod="$1"
  shift
  local extra=("$@")
  if ! modules_exists "$mod"; then
    echo "错误: 未知模块 '$mod'"
    echo "可用模块:"
    modules_list | sed 's/^/  /'
    return 1
  fi
  if ! modules_has "$mod" config; then
    echo "错误: 模块 '$mod' 无配置步骤"
    echo "提示: 该模块可能仅支持安装，请使用: dotf $mod -i"
    return 1
  fi
  if [ ${#extra[@]} -gt 0 ]; then
    run_config "$mod" "${extra[@]}"
  else
    run_config "$mod"
  fi
}

do_doctor_one() {
  local mod="$1"
  shift
  local extra=("$@")
  if ! modules_exists "$mod"; then
    echo "错误: 未知模块 '$mod'"
    echo "可用模块:"
    modules_list | sed 's/^/  /'
    return 1
  fi
  if ! modules_has "$mod" doctor; then
    echo "错误: 模块 '$mod' 无诊断步骤"
    return 1
  fi
  if [ ${#extra[@]} -gt 0 ]; then
    run_doctor "$mod" "${extra[@]}"
  else
    run_doctor "$mod"
  fi
}

# 流水线：install → config → doctor（仅执行集合中包含的步骤）
do_pipeline_one() {
  local mod="$1"
  local do_i="$2"
  local do_c="$3"
  local do_d="$4"
  shift 4
  local -a config_extra=()
  local -a doctor_extra=()
  # 剩余参数以 -- 分隔：config_extra -- doctor_extra
  while [ $# -gt 0 ]; do
    if [ "$1" = "--" ]; then
      shift
      doctor_extra=("$@")
      break
    fi
    config_extra+=("$1")
    shift
  done

  if [ "$do_i" -eq 1 ]; then
    do_install_one "$mod" || return $?
  fi
  if [ "$do_c" -eq 1 ]; then
    if [ ${#config_extra[@]} -gt 0 ]; then
      do_config_one "$mod" "${config_extra[@]}" || return $?
    else
      do_config_one "$mod" || return $?
    fi
  fi
  if [ "$do_d" -eq 1 ]; then
    if [ ${#doctor_extra[@]} -gt 0 ]; then
      do_doctor_one "$mod" "${doctor_extra[@]}" || return $?
    else
      do_doctor_one "$mod" || return $?
    fi
  fi
  return 0
}

reject_legacy_syntax() {
  echo "错误: 旧语法已移除（动作优先不再支持）"
  echo ""
  echo "新用法（主体优先）:"
  echo "  dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd"
  echo "  dotf -i|-c|-d|...           # 交互选择"
  echo "  dotf -i -a | -c -a | -d -a | -a"
  echo ""
  echo "示例:"
  echo "  dotf sdk -i"
  echo "  dotf nvim -c"
  echo "  dotf nvim -d"
  echo "  dotf agents -ic"
  echo "  dotf agents -cd"
  exit 1
}

reject_old_doctor_bypass() {
  echo "错误: --doctor 已不再作为 config/sync 旁路旗标"
  echo ""
  echo "请改用:"
  echo "  dotf agents -d              # 仅诊断"
  echo "  dotf agents -cd             # 先配置再诊断"
  exit 1
}

# ============================================================
# 帮助
# ============================================================

show_help() {
  echo "dotf — Dotfiles 管理工具"
  echo ""
  echo "用法: dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd"
  echo "      dotf <module...> --uninstall|--deconfig"
  echo "      dotf -i|-c|-d|...             # 无模块 → 交互选择"
  echo "      dotf -i -a | -c -a | -d -a    # 全量（按当前 OS 过滤）"
  echo "      dotf -a                       # 全量安装 + 配置（不含 doctor）"
  echo "      dotf tui                      # TTY 管理面（同一 planner）"
  echo "      dotf <命令> [参数...]"
  echo ""
  echo "命令:"
  echo "  init [--os <id>] [--profile <name>] [--list]"
  echo "                              按 OS + 使用场景 profile 初始化"
  echo "  status [--profile <name>]   只读环境状态（L0）"
  echo "  retry                       重试最近报告中的 failed 动作"
  echo "  tui                         两区 TUI（需 TTY；无参数 dotf 仍是帮助）"
  echo "  pull                        拉取 dotfiles 最新更新（保护性 pull）"
  echo "  cd                          跳转到 dotfiles 目录（需 zsh wrapper）"
  echo "  skills                      通过 npx skills 按需安装第三方 skill"
  echo ""
  echo "动作:"
  echo "  -i, --install               安装"
  echo "  -c, --config                配置/链接"
  echo "  -d, --doctor                诊断（L0 或模块专用实现）"
  echo "  --uninstall                 卸载（仅注册表声明且有 uninstall.sh 的模块）"
  echo "  --deconfig                  撤回 owned 且未漂的配置（有 config 即隐含）"
  echo "  -ic                         先安装后配置"
  echo "  -id                         先安装后诊断"
  echo "  -cd                         先配置后诊断"
  echo "  -icd                        安装 → 配置 → 诊断"
  echo "  没有独立 update 动词；再跑已有动作即 re-apply"
  echo "  -a, --all                   全量（配合 -i/-c/-d；单独 -a = 装+配，不含 doctor）"
  echo "  --dry-run                   只展示执行计划，不执行（允许跨 OS 预览）"
  echo "  --continue-on-error         失败后仅继续依赖无关动作；最终仍非零"
  echo "  --yes, -y                   跳过计划确认与副作用确认（不绕过校验/备份）"
  echo "  --json                      输出脱敏执行汇总 JSON"
  echo "  -h, --help                  显示帮助"
  echo ""
  echo "确认语义:"
  echo "  执行前进行计划确认（默认 N）；通过后执行计划中的动作，不再逐模块询问"
  echo "  副作用确认（改默认 shell、Docker 装/配）仍会单独询问，除非 --yes"
  echo "  非 TTY 且无 --yes/--dry-run 时快速失败"
  echo ""
  echo "agents 示例:"
  echo "  dotf agents -i              # 安装 agent CLI 工具包"
  echo "  dotf agents -c              # 同步 skills + MCP"
  echo "  dotf agents -d              # 深度诊断"
  echo "  dotf agents -d --json       # JSON 报告"
  echo "  dotf agents -cd             # 先同步再诊断"
  echo "  dotf agents -ic             # 先装后配"
  echo "  dotf agents skill apply <id>"
  echo "  dotf agents skill remove <id>   # 写本机 overlay 并 prune"
  echo "  dotf agents mcp apply <id> --tool cursor"
  echo "  dotf agents mcp remove <id> --all-tools"
  echo "  dotf skills -i frontend-design"
  echo ""
  echo "示例:"
  echo "  dotf init                   # OS profile 完整初始化"
  echo "  dotf init --list            # 列出 profile"
  echo "  dotf pull                   # 拉取更新"
  echo "  dotf sdk -i                 # 安装 SDK"
  echo "  dotf nvim -c                # 配置 nvim"
  echo "  dotf nvim -d                # 诊断 nvim（L0）"
  echo "  dotf sdk golang -i          # 安装多个模块"
  echo "  dotf -c -a                  # 配置全部（当前 OS）"
  echo "  dotf -i -a                  # 安装全部（当前 OS）"
  echo "  dotf -d -a                  # 诊断全部（当前 OS）"
  echo "  dotf -a                     # 安装全部 + 配置全部"
  echo "  dotf sdk -i --dry-run       # 预览安装计划"
  echo "  dotf nvim -c --yes          # 非交互配置"
  echo "  dotf init --dry-run         # 预览 init 计划"
}

# ============================================================
# 参数解析（主体优先）
# ============================================================

main() {
  if [ $# -eq 0 ]; then
    show_help
    exit 0
  fi

  local -a modules=()
  local -a config_extra=()
  local -a doctor_extra=()
  local do_i=0
  local do_c=0
  local do_d=0
  local do_uninstall=0
  local do_deconfig=0
  local want_all=0
  local saw_action_flag=0
  local positional_before_action=0

  while [ $# -gt 0 ]; do
    case "$1" in
    pull)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: pull 为独立命令"
        exit 1
      fi
      cmd_pull
      exit $?
      ;;
    init)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: init 为独立命令"
        exit 1
      fi
      shift
      cmd_init "$@"
      exit $?
      ;;
    tui)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: tui 为独立命令，不能与模块或动作旗标混用"
        exit 1
      fi
      shift
      cmd_tui "$@"
      exit $?
      ;;
    agents)
      if [ "${2:-}" = "skill" ] || [ "${2:-}" = "mcp" ]; then
        if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
          echo "错误: agents skill|mcp 为独立命令"
          exit 1
        fi
        shift
        cmd_agents_artifact "$@"
        exit $?
      fi
      if [ "$saw_action_flag" -eq 0 ]; then
        positional_before_action=1
      else
        reject_legacy_syntax
      fi
      modules+=("agents")
      ;;
    skills)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: skills 为独立命令"
        exit 1
      fi
      shift
      cmd_skills "$@"
      exit $?
      ;;
    status)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: status 为独立命令"
        exit 1
      fi
      shift
      cmd_status "$@"
      exit $?
      ;;
    retry)
      if [ ${#modules[@]} -gt 0 ] || [ "$do_i$do_c$do_d$do_uninstall$do_deconfig" != "00000" ]; then
        echo "错误: retry 为独立命令"
        exit 1
      fi
      shift
      cmd_retry "$@"
      exit $?
      ;;
    __path)
      cmd_path
      exit $?
      ;;
    -i | --install)
      saw_action_flag=1
      # 旧模式：已有 -c 再单独 -i 且模块夹在中间 → 拒绝；允许 -c -i 作为组合
      if [ "$do_c" -eq 1 ] && [ ${#modules[@]} -gt 0 ] && [ "$positional_before_action" -eq 0 ]; then
        reject_legacy_syntax
      fi
      do_i=1
      ;;
    -c | --config)
      saw_action_flag=1
      if [ "$do_i" -eq 1 ] && [ ${#modules[@]} -gt 0 ] && [ "$positional_before_action" -eq 0 ]; then
        # 旧语法: -i sdk -c nvim
        reject_legacy_syntax
      fi
      do_c=1
      ;;
    -d)
      saw_action_flag=1
      do_d=1
      ;;
    --doctor)
      # 旧旁路: -c/--config 后再跟 --doctor → 拒绝
      if [ "$do_c" -eq 1 ] && [ "$do_d" -eq 0 ]; then
        reject_old_doctor_bypass
      fi
      saw_action_flag=1
      do_d=1
      ;;
    -ic)
      saw_action_flag=1
      do_i=1
      do_c=1
      ;;
    -id | -di)
      saw_action_flag=1
      do_i=1
      do_d=1
      ;;
    -cd | -dc)
      saw_action_flag=1
      do_c=1
      do_d=1
      ;;
    -icd | -idc | -cid | -cdi | -dic | -dci)
      saw_action_flag=1
      do_i=1
      do_c=1
      do_d=1
      ;;
    -a | --all)
      want_all=1
      ;;
    -h | --help)
      show_help
      exit 0
      ;;
    --skills-only | --env-only | --strict)
      config_extra+=("$1")
      ;;
    --uninstall)
      if [ "$do_i$do_c$do_d" != "000" ]; then
        echo "错误: --uninstall 不能与 -i/-c/-d 组合成新字母串"
        exit 1
      fi
      saw_action_flag=1
      do_uninstall=1
      ;;
    --deconfig)
      if [ "$do_i$do_c$do_d" != "000" ]; then
        echo "错误: --deconfig 不能与 -i/-c/-d 组合成新字母串"
        exit 1
      fi
      saw_action_flag=1
      do_deconfig=1
      ;;
    --dry-run)
      DOTF_DRY_RUN=1
      ;;
    --continue-on-error)
      DOTF_CONTINUE_ON_ERROR=1
      ;;
    --yes | -y)
      DOTF_YES=1
      ;;
    --json)
      # 执行汇总 JSON；与 agents -d 联用时同时传给 doctor
      DOTF_JSON=1
      doctor_extra+=("$1")
      ;;
    --deep)
      DOTF_DEEP=1
      doctor_extra+=("$1")
      ;;
    --verbose)
      doctor_extra+=("$1")
      ;;
    --fail-on)
      local opt="$1"
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: $opt 需要参数"
        exit 1
      fi
      doctor_extra+=("$opt" "$1")
      ;;
    --tool)
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: --tool 需要参数"
        exit 1
      fi
      # agents -c 过滤同步目标；agents -d 过滤诊断
      config_extra+=("$1")
      doctor_extra+=("--tool" "$1")
      ;;
    --profile)
      shift
      if [ -z "${1:-}" ]; then
        echo "错误: --profile 需要参数"
        exit 1
      fi
      # agents 诊断/配置 profile；非 agents 场景下作为使用场景 profile
      DOTF_USAGE_PROFILE="$1"
      config_extra+=("--profile" "$1")
      doctor_extra+=("--profile" "$1")
      ;;
    -*)
      echo "错误: 未知选项 '$1'"
      echo ""
      show_help
      exit 1
      ;;
    *)
      # 位置参数 = 模块名
      if [ "$saw_action_flag" -eq 0 ]; then
        positional_before_action=1
      else
        # 动作之后再跟模块名 → 旧语法（dotf -i sdk）
        reject_legacy_syntax
      fi
      modules+=("$1")
      ;;
    esac
    shift
  done

  if { [ "$do_uninstall" -eq 1 ] || [ "$do_deconfig" -eq 1 ]; } && [ "$do_i$do_c$do_d" != "000" ]; then
    echo "错误: --uninstall/--deconfig 不能与 -i/-c/-d 组合成新字母串"
    exit 1
  fi

  local has_action=0
  if [ "$do_i" -eq 1 ] || [ "$do_c" -eq 1 ] || [ "$do_d" -eq 1 ] ||
    [ "$do_uninstall" -eq 1 ] || [ "$do_deconfig" -eq 1 ]; then
    has_action=1
  fi

  # 组装动作 CSV
  local actions_csv=""
  [ "$do_i" -eq 1 ] && actions_csv="${actions_csv:+$actions_csv,}install"
  [ "$do_c" -eq 1 ] && actions_csv="${actions_csv:+$actions_csv,}config"
  [ "$do_d" -eq 1 ] && actions_csv="${actions_csv:+$actions_csv,}doctor"
  [ "$do_uninstall" -eq 1 ] && actions_csv="${actions_csv:+$actions_csv,}uninstall"
  [ "$do_deconfig" -eq 1 ] && actions_csv="${actions_csv:+$actions_csv,}deconfig"

  # --- 全量模式 ---
  if [ "$want_all" -eq 1 ]; then
    if [ ${#modules[@]} -gt 0 ]; then
      echo "错误: -a/--all 不能与模块名同时使用"
      exit 1
    fi

    # 单独 -a：装 + 配（不含 doctor）
    if [ "$has_action" -eq 0 ]; then
      do_i=1
      do_c=1
      do_d=0
      actions_csv="install,config"
    fi

    local -a pargs=(--all)
    [ -n "$DOTF_USAGE_PROFILE" ] && pargs+=(--profile "$DOTF_USAGE_PROFILE")
    local x
    for x in "${config_extra[@]+"${config_extra[@]}"}"; do
      pargs+=(--config-extra "$x")
    done
    for x in "${doctor_extra[@]+"${doctor_extra[@]}"}"; do
      pargs+=(--doctor-extra "$x")
    done
    plan_and_run "$actions_csv" "${pargs[@]}"
    exit $?
  fi

  # --- 必须有动作 ---
  if [ "$has_action" -eq 0 ]; then
    echo "错误: 请指定动作 -i / -c / -d / -ic / -id / -cd / -icd 或 --uninstall / --deconfig"
    echo ""
    show_help
    exit 1
  fi

  # --- 无模块 → 交互 ---
  if [ ${#modules[@]} -eq 0 ]; then
    local cap="all"
    if [ "$do_i" -eq 1 ] && [ "$do_c" -eq 0 ] && [ "$do_d" -eq 0 ]; then
      cap=install
    elif [ "$do_c" -eq 1 ] && [ "$do_i" -eq 0 ] && [ "$do_d" -eq 0 ]; then
      cap=config
    elif [ "$do_d" -eq 1 ] && [ "$do_i" -eq 0 ] && [ "$do_c" -eq 0 ]; then
      cap=doctor
    elif [ "$do_i" -eq 1 ] && [ "$do_c" -eq 1 ] && [ "$do_d" -eq 0 ]; then
      cap="" # 展示全部，执行时校验
    fi
    interactive_select "${cap:-all}" || exit 1
    modules=("${SELECTED_MODULES[@]}")
  fi

  # --- 校验额外选项 ---
  if [ ${#config_extra[@]} -gt 0 ] || [ ${#doctor_extra[@]} -gt 0 ]; then
    local only_agents=1
    for mod in "${modules[@]}"; do
      if [ "$mod" != "agents" ]; then
        only_agents=0
        break
      fi
    done
    if [ "$only_agents" -eq 0 ]; then
      # 允许 --profile 作为使用场景；其它 agents 选项仍受限
      local has_agents_only_flag=0
      for x in "${config_extra[@]+"${config_extra[@]}"}" "${doctor_extra[@]+"${doctor_extra[@]}"}"; do
        case "$x" in
        --profile) ;;
        --skills-only | --env-only | --strict | --json | --deep | --verbose | --fail-on | --tool)
          has_agents_only_flag=1
          ;;
        esac
      done
      if [ "$has_agents_only_flag" -eq 1 ]; then
        echo "错误: 诊断/agents 选项仅支持与 agents 一起使用（如: dotf agents -d --json）"
        exit 1
      fi
    fi
  fi

  # --- 统一计划执行 ---
  local modules_csv=""
  local first=1
  for mod in "${modules[@]}"; do
    if [ "$first" -eq 1 ]; then
      modules_csv="$mod"
      first=0
    else
      modules_csv="$modules_csv,$mod"
    fi
  done

  local -a pargs=(--modules "$modules_csv")
  for x in "${config_extra[@]+"${config_extra[@]}"}"; do
    pargs+=(--config-extra "$x")
  done
  for x in "${doctor_extra[@]+"${doctor_extra[@]}"}"; do
    pargs+=(--doctor-extra "$x")
  done
  plan_and_run "$actions_csv" "${pargs[@]}"
  exit $?
}


main "$@"
