---
name: dotfiles
description: 用 dotf 管理开发环境：新机初始化（bootstrap / dotf init / profile）、按需安装或配置模块（dotf <mod> -i/-c/-ic、dotf -a）、整体体检与诊断（dotf status、dotf <mod> -d）、重试失败动作（dotf retry）、同步 agent skills 与全局指令（dotf agents -c），以及本仓开发改动（make registry validate / test / ci、skills.lock 重锁）。在用户要求装机、初始化、setup、装某工具、配某模块、补装、全量装、体检、检查环境、诊断、看看缺啥、跑 doctor、重试、同步 skills，或在 dotfiles 仓提交改动时使用。多用户/共用开发机默认走用户级；系统级动作（sudo / chsh / 改 /etc / 加 docker 组）必须显式确认。
---

# dotfiles

这台机器上「装什么、配什么、坏没坏」都走 `dotf`。本文件是入口：先看路由表，再读对应的 `references/` 文件，不要一次全读。

## 路由

| 用户要什么 | 读 |
|---|---|
| 装 / 配 / 补装某个模块、全量装、跑 doctor、重试失败 | `references/install.md` |
| 新机初始化、bootstrap、选 profile | `references/init.md` |
| 体检、整体检查、看看缺啥、健康检查 | `references/check.md` |
| 改本仓（模块、skill、编目、测试、lock） | `references/repo.md` |
| 共用性判定、系统级门禁、chsh、`~/.dotf-env.md` | `references/safety.md` |

凡是会改系统状态的活，动手前都先读 `references/safety.md`：它给出这台机器属于 solo / shared-user / shared-home 的判定，以及 shared 下的门禁。

## 四条不变量

1. **薄包装**：使用类操作不改 `modules.yaml`、不写临时安装脚本。执行一律走 `bin/dotf` 与 `scripts/bootstrap.sh`。仓库维护类改动（modules.yaml / handler / 编目）见 `references/repo.md`。
2. **dry-run 优先**：任何改状态的动作先 `--dry-run` 让用户看计划；非 TTY 又没 `--yes` 时 dotf 会快速失败。
3. **shared 门禁**：sudo、chsh、改 `/etc`、加 docker 组必须显式确认，能用户级就用户级。
4. **回写台账**：`~/.dotf-env.md` 记共用性判定、profile、已装模块、踩坑；不写密钥。

## Agent / 非 TTY 操作守则

在无终端会话里替人操作或被自动化调用时，遵守：

- **参数顺序**：模块名在前、flag 在后：`dotf <module...> -d`。写成 `dotf -d <module...>` 会被当作未知模块。
- **非 TTY 一律 `--yes`**：只读的 `dotf status` / `dotf <mod> -d` 也需要；`--json` 不豁免门禁。改状态的动作先 `--dry-run`，用户确认后再 `--yes`。
- **zsh 批量展开**：`mods="a b c"; dotf ${=mods} -d --yes`。zsh 默认不按空格分词，`dotf $mods ...` 会把整串当成一个模块名。
- **跨 OS 模块先剔除**：批量命令里混入当前 OS 不适用的模块会让整批计划校验直接失败；按 `PYTHONPATH=src python3 -m dotf_core.registry list --filter-os` 或先 dry-run 过滤。
- **机读输出**：结果行是 `RESULT<TAB>状态<TAB>模块<TAB>动作…`；用 `awk '$2 != "unchanged"'` 过滤变化/失败，不要用 `tail` 截断（失败行可能在最前）。
- **`--dry-run` 是迁移预览**：对历史软链目标，计划里能看到 unlink→落真实目录；实际迁移只在执行时发生。

## 命令速查

```shell
dotf __path                              # 仓库根（PATH 里没有 dotf 时看 ~/.config/dotfiles）
dotf <module...> -i|-c|-d|-ic|-icd       # 安装 / 配置 / 诊断
dotf <module...> --dry-run               # 只看计划，不执行（允许跨 OS 预览）
dotf <module...> --uninstall|--deconfig  # 撤软件 / 撤回 owned 且未漂的配置
dotf -a                                  # 全量装 + 配（不含 doctor）
dotf init [--os <id>] [--profile <name>] [--list] [--dry-run] [--yes]
dotf status [--profile <name>]           # 只读 L0 状态（fail-fast，见 references/check.md）
dotf retry                               # 重试最近报告里的 failed 动作
dotf update                              # 拉仓库更新，并提示后续同步命令
dotf agents -ic                          # agent CLI + skills / 全局指令同步
dotf agents -d [--deep] [--json]         # 诊断（--deep 跑 L1，--json 脱敏）
dotf agents skill apply|remove <id|alias>
dotf skills -c | skills list | skills -i/-r
```

- 模块没有 update 动作：对已有动作再跑一次就是 re-apply。`dotf update` 是独立命令（拉代码 + 提示 `dotf agents -c` 这类后续同步）。
- 模块清单的权威来源是 `modules.yaml`；在仓库根用 `PYTHONPATH=src python3 -m dotf_core.registry list[ --filter-os][ --capability install|config|doctor]` 查。
- L0/L1 各查什么、谁豁免谁、发现如何定性：见 `docs/design/doctor-check-contract.md`。

## 装完、改完记得

- 配置不自动传播：改了仓库里的 `config/` 要重跑 `dotf <module> -c`。
- 本 skill 与全局 `AGENTS.md` 的源都在本仓 `agents/`（`agents/skills/dotfiles/`、`agents/instructions/`），改完要 `dotf agents -c` 才在本机生效。
- 结论回写台账：`~/.dotf-env.md` 的「已初始化模块」与「踩坑」。
