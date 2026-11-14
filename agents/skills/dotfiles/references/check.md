# 整体体检（check）

用户没点名模块，只问「这台机器怎么样 / 缺什么 / 有没有问题」。目标是给出**分级结论 + 可执行的修复建议**，不是把每个模块的 doctor 抄一遍。

## 与 `dotf status` 的关系

| | `dotf status` | 本节 |
|---|---|---|
| 视角 | 逐模块被动 L0 | 按能力域聚合 + 主动发现 |
| 范围 | 注册表里的模块 | 运行时、shell、程序、agents 生态、配置健康与安全 |
| 输出 | 清单 | 分级结论 + 修复建议 + 可选委托修复 |
| 改状态 | 否 | 默认否；用户同意后才委托 install |

先用 `dotf status` 拿基线，再按下面四维扩。

## 维度 1：基础运行时（缺失即阻断）

`bash` / `git` / `curl` 或 `wget` / `python3`（+ PyYAML）是否可用；版本是否满足 `modules.yaml` 要求；`brew` / `apt` / `dnf` / `pacman` 是否可用；`mise` 是否装（`sdk` 模块依赖）。

体检命令：在仓库根 `bash scripts/bootstrap.sh --check-only`——它只预检不装。

## 维度 2：shell 与环境

| 检查 | 命令 / 依据 |
|---|---|
| 默认 shell | `getent passwd "$USER"` 或 `echo "$SHELL"`；是否与 `zsh` 模块预期一致 |
| shell 配置文件 | `~/.zshrc`、`~/.bashrc` 是否指向托管源；有手改痕迹算漂移 |
| PATH | `dotf status` 的 L0 检查；常见缺失：`~/.local/bin`、`~/go/bin`、`~/.cargo/bin`、mise shims |
| 环境变量 | `GOPATH` / `GOROOT` / `EDITOR` / `LANG` 是否与模块配置一致 |
| 终端 | 当前终端是否为已被管理的模块（kitty / wezterm / ghostty / alacritty） |

## 维度 3：程序与模块（按能力域，不按字母表）

按「能干什么」分组报告，缺失才算缺口，装了没用到的也点出来：

| 能力域 | 相关模块 | 缺了会怎样 |
|---|---|---|
| 版本与语言运行时 | sdk / golang / npm | 装不了后续工具 |
| 版本控制与仓库管理 | git / delta / grepom | 多仓同步、diff 体验退化 |
| 文件与服务 | mdserve / ossutil / aws / aliyun / gcp | 文档预览、对象存储操作不可用 |
| AI 编码环境 | agents 及各家 CLI（codex / opencode / kimi-code / pi / omp / zcode / claude-code …） | 对应 agent 不可用 |
| 编辑与终端 | nvim / helix / zed / tmux / zellij / herdr / yazi / k9s | 编辑与多路复用体验缺失 |
| 桌面体验（仅桌面） | fonts / hypr / kitty / iterm2 | 字体、窗口管理 |

模块自身的深度诊断用 `dotf <mod> -d`；全量用 `dotf -d -a`。缺模块 → 给 `dotf <mod> -ic` 建议，不要默认全量装。

## 维度 4：agents / skills 生态

| 检查 | 命令 |
|---|---|
| 工具健康 | `dotf agents -d`（`--deep` 跑 L1） |
| skills 漂移 | `dotf agents --doctor` 的 skills 段；或 `dotf tui` 的 Status / Conflicts 面板 |
| 编目一致性 | `dotf skills list` 与 `~/.agents/skills` 对账 |
| 全局指令 | `~/.agents/AGENTS.md`、`~/.codex/AGENTS.md`、`~/.claude/CLAUDE.md`、`~/.cursor/rules/00-dotf-global.mdc`、`~/.pi/agent/AGENTS.md`、`~/.qoder/AGENTS.md` 的 `agents:instructions:` 漂移 |
| 第三方 lock | `agents/skills.lock.yaml` 与安装副本 revision 是否一致 |

漂移的修复统一是 `dotf agents -c`（本 skill 与全局指令都从 `agents/` 下发），不要手改安装产物。

## 配置健康与安全

| 检查 | 依据 |
|---|---|
| 配置漂移 | 托管目标被手改 / 外来软链 / 未托管目标 → `dotf agents --doctor`、`dotf tui` Conflicts |
| 敏感文件权限 | `~/.ssh`（700/600）、`~/.aws`、`~/.config/gh`、`~/.gitconfig`（可能含凭证）、`~/.netrc` |
| 可疑内容 | 仓库与本机配置里不该出现私钥 / token / 内部 URL |
| 备份与回滚 | `~/.local/state/dotf/backups/` 有无可回滚备份；`~/.dotf-env.md` 是否存在且与现场一致 |

发现密钥类问题时只报告位置与类型，不复述内容。

## 输出格式

按维度分组，每条标严重度：

- `[阻断]` 缺运行时不装什么都干不了
- `[重要]` 缺模块 / 漂移 / 权限过宽
- `[建议]` 版本旧、可选工具缺失、配置口味问题
- `[OK]` 只有全维度过时才写一句「无阻断项」

每条给：现象 → 依据（命令输出片段）→ 修复建议（具体命令）。结尾给出「要不要我修」的二选一，并说明修的是哪几项。

## 修复闭环

用户同意后，按建议顺序委托：

| 缺口 | 委托 |
|---|---|
| 未初始化 / 缺运行时 / 选 profile | `references/init.md` |
| 缺模块、要补装、要重配 | `references/install.md` |
| skills / 全局指令漂移 | `dotf agents -c`（install.md 的 config 段） |
| 失败的上一轮动作 | `dotf retry` |

修复后重跑对应维度的检查，只报变化，不重复整篇报告。

## 边界

- 只读探测，不改系统状态（修复阶段除外，且需用户同意）。
- 不为了「更彻底」而跑 `-a`、sudo、改 `/etc`；发现的问题按严重度排队。
- 探测命令没权限就用只读替代，不为体检提权。
- 本机的共用性判定与台账约定见 `references/safety.md`。
