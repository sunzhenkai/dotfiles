"""show_help 文案（与旧 bash 版逐字对齐）。"""

HELP_TEXT = """dotf — Dotfiles 管理工具

用法: dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd
      dotf <module...> --uninstall|--deconfig
      dotf -i|-c|-d|...             # 无模块 → 交互选择
      dotf -i -a | -c -a | -d -a    # 全量（按当前 OS 过滤）
      dotf -a                       # 全量安装 + 配置（不含 doctor）
      dotf tui                      # TTY 管理面（同一 planner）
      dotf <命令> [参数...]

命令:
  init [--os <id>] [--profile <name>] [--list]
                              按 OS + 使用场景 profile 初始化
  status [--profile <name>]   只读环境状态（L0）
  retry                       重试最近报告中的 failed 动作
  tui                         两区 TUI（需 TTY；无参数 dotf 仍是帮助）
  pull                        拉取 dotfiles 最新更新（保护性 pull）
  cd                          跳转到 dotfiles 目录（需 zsh wrapper）
  skills                      通过 npx skills 按需安装第三方 skill

动作:
  -i, --install               安装
  -c, --config                配置/链接
  -d, --doctor                诊断（L0 或模块专用实现）
  --uninstall                 卸载（仅注册表声明且有 uninstall.sh 的模块）
  --deconfig                  撤回 owned 且未漂的配置（有 config 即隐含）
  -ic                         先安装后配置
  -id                         先安装后诊断
  -cd                         先配置后诊断
  -icd                        安装 → 配置 → 诊断
  没有独立 update 动词；再跑已有动作即 re-apply
  -a, --all                   全量（配合 -i/-c/-d；单独 -a = 装+配，不含 doctor）
  --dry-run                   只展示执行计划，不执行（允许跨 OS 预览）
  --continue-on-error         失败后仅继续依赖无关动作；最终仍非零
  --yes, -y                   跳过计划确认与副作用确认（不绕过校验/备份）
  --json                      输出脱敏执行汇总 JSON
  -h, --help                  显示帮助

确认语义:
  执行前进行计划确认（默认 N）；通过后执行计划中的动作，不再逐模块询问
  副作用确认（改默认 shell、Docker 装/配）仍会单独询问，除非 --yes
  非 TTY 且无 --yes/--dry-run 时快速失败

agents 示例:
  dotf agents -i              # 安装 agent CLI 工具包
  dotf agents -c              # 同步 skills + MCP
  dotf agents -d              # 深度诊断
  dotf agents -d --json       # JSON 报告
  dotf agents -cd             # 先同步再诊断
  dotf agents -ic             # 先装后配
  dotf agents skill apply <id>
  dotf agents skill remove <id>   # 写本机 overlay 并 prune
  dotf agents mcp apply <id> --tool cursor
  dotf agents mcp remove <id> --all-tools
  dotf skills -i frontend-design

示例:
  dotf init                   # OS profile 完整初始化
  dotf init --list            # 列出 profile
  dotf pull                   # 拉取更新
  dotf sdk -i                 # 安装 SDK
  dotf nvim -c                # 配置 nvim
  dotf nvim -d                # 诊断 nvim（L0）
  dotf sdk golang -i          # 安装多个模块
  dotf -c -a                  # 配置全部（当前 OS）
  dotf -i -a                  # 安装全部（当前 OS）
  dotf -d -a                  # 诊断全部（当前 OS）
  dotf -a                     # 安装全部 + 配置全部
  dotf sdk -i --dry-run       # 预览安装计划
  dotf nvim -c --yes          # 非交互配置
  dotf init --dry-run         # 预览 init 计划"""
