# 按需安装 / 配置 / 诊断

系统已经初始化过，现在要装某个工具、配某个模块、全量补装或重试失败动作。

## 前置

1. `dotf __path` 打印仓库根；失败说明没初始化或 PATH 缺，转 `references/init.md`，不要在这里硬装。
2. 读 `~/.dotf-env.md`（若有）拿共用性判定与已装模块。没有就按 `references/safety.md` 现场探测。

## 模块地图（非权威，速查用）

权威来源是 `modules.yaml`；`group` 只影响展示，不影响执行顺序。

| group | 模块 | 级别 | shared 下默认 |
|---|---|---|---|
| core | system / homebrew | 系统级（sudo、改源） | 需显式确认 |
| core | sdk / golang / git | 用户级 | 可装 |
| tools | senv grepom mdserve delta npm vcpkg ossutil aws aliyun gcp d2 | 多为用户级（cargo/go/bin） | 可装 |
| 办公 | dws / lark-cli | 用户级（npm/npx，需 sdk） | 可装 |
| agents | agents cursor opencode codex kimi-code pi omp zcode claude-code claude-plugins mcode | 用户级 CLI + 配置 | 可装 |
| shell | zsh / starship | zsh 可能 chsh | zsh 见 `references/safety.md` |
| editors | nvim helix zed | 用户级配置，可能装编辑器 | 装编辑器时确认 |
| terminals | kitty alacritty wezterm ghostty iterm2 | 用户级配置，可能装终端 | 装终端时确认 |
| multiplexers | tmux zellij herdr | 用户级 | 可装 |
| desktop | fonts hypr | fonts 可能系统级；hypr 改桌面 | 需显式确认 |
| utils | yazi / k9s | 用户级 | 可装 |

`trae-cli` / `cpp-dev` / `omo` / `fcitx5` / `logseq` 在 `modules.yaml` 里标了 `enabled: false`：`-a` 与 profile 不带它们，点名装仍可用。

查清单（在仓库根）：

```bash
PYTHONPATH=src python3 -m dotf_core.registry list                 # 全模块
PYTHONPATH=src python3 -m dotf_core.registry list --filter-os     # 当前 OS 适用
PYTHONPATH=src python3 -m dotf_core.registry list --capability config
dotf <mod> -i --dry-run                                           # 单模块计划预览
```

## Phases

### list（只读，缺省）

1. `dotf status`（只读 L0）。
2. 上表命令查可装模块。
3. 输出：已装 / 缺失、按 group 的可装清单、shared 下的安全标记。不改任何状态。

### install `<mod...>`

```bash
dotf <mod> -i               # 仅安装
dotf <mod> -ic              # 安装 + 配置
dotf <mod1> <mod2> -ic      # 多模块
dotf <mod> -i --dry-run     # 先看计划
dotf <mod> -i --yes         # 非交互（chsh / docker 副作用仍确认）
```

流程：dry-run 看计划 → 识别系统级动作（sudo / chsh / 改 `/etc` / docker 组）→ shared 下逐个要显式同意，不同意就跳过该模块或换用户级替代 → 执行（用户确认后；非 TTY 需 `--yes`）→ 回写台账，失败记踩坑。

### config `<mod...>`

只配置不安装。可写模块用 HOME 下的真实文件/目录 + `copy` / `merge` / `render`；只有注册表显式声明 `strategy: symlink` 的只读目标才用软链。仓库源修改后不会自动传播，必须重跑：

```bash
dotf <mod> -c --dry-run
dotf <mod> -c --yes
dotf agents -c                              # skills + 全局指令聚合同步
dotf agents skill apply <id> --on-conflict=backup
```

- 配置目标已是无主文件且内容不等价时，config 默认拒绝写入。TTY 下会汇总确认是否备份接管，或显式 `dotf <mod> -c --takeover=backup`（非 TTY 必须带 flag；symlink 等不安全目标不可接管）。见 ADR-0024。
- 历史整目录软链会被 unlink 后迁移为真实目录；外来软链、未托管目标、本机改过的文件默认 `conflict`，不静默覆盖。sync 冲突默认「先备份再继续」，备份在 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/`（ADR-0033）。
- copy 目录下文件的 mode 按源文件派生并裁剪到模块 `target_mode` 位面内；producer 显式给出的 mode 越权时 fail closed。

### all（全量补装）

```bash
dotf -a                    # 装全部 + 配全部（不含 doctor），按当前 OS 过滤
dotf -a --dry-run
dotf init --profile remote --dry-run   # 按使用场景收窄
```

`-a` 始终表示当前 OS 适用模块的完整 all 集合，不受使用场景 profile 缩小；要收窄范围用 `dotf init --profile <name>`。shared 下 `-a` 会包含 `system` 这类系统级模块，必须先 dry-run 逐项确认，或换成更小的 profile + 手动补用户级模块。

### doctor `[mod...]`

```bash
dotf <mod> -d                 # 单模块 L0
dotf -d -a                    # 全量
dotf agents -d --deep --json  # agents 深度诊断（脱敏 JSON）
```

### retry

`dotf retry` 读最近一次执行报告，重建并重跑 failed 子计划。`failed-rollback` 状态的动作用它救不回来：保留 journal 与备份，人工恢复。

## 依赖

`depends_on` 由 planner 拓扑排序，不用手装。例：`golang` → `sdk`，`senv`/`grepom`/`mdserve` → `golang`，`delta` → `git`。dry-run 计划里会展示完整依赖链。

## 常见交互

| 用户说 | 行为 |
|---|---|
| 「装一下 nvim」「配置 tmux」 | 单模块 install / config，先 dry-run |
| 「补装所有」 | `-a`；shared 下先 dry-run 逐项确认 |
| 「看看还缺啥」 | list（`dotf status` + 模块清单） |
| 「诊断一下 xx」 | doctor |
| 「重试失败的」 | `dotf retry` |
| 「装 nvim 和 tmux」 | `dotf nvim tmux -ic` |
| 「这是公司机，装 xx」 | 按台账 shared 处理；系统级确认，用户级直装 |
| 「新机器初始化」 | 转 `references/init.md` |

## 边界

- shared 下不确认不装系统级模块（system / homebrew / hypr / 系统字体 / 触发 chsh 的 zsh）。
- 不自己拼 sudo，全部走 dotf 的确认流程。
- 写入前确认目标在用户 HOME 下；shared-home 下尤其注意同名文件，依赖 dotf 的备份机制。
- 脚本行为与本表不符（「用户级」模块实际 sudo 了）时：记踩坑并提示更新 dotf 脚本或本节。
