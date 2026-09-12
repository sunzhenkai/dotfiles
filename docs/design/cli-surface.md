# CLI 面下沉设计（dotf_cli）

依据 ADR-0013。用户面命令从 `bin/dotf` 下沉到 Python 包 `src/dotf_cli/`，`bin/dotf` 退化为 shim。

## 目标与现状痛点

| 痛点 | 根因 | 下沉后 |
|---|---|---|
| `bin/dotf` 约 1300 行单文件 | 分发、解析、输出、守卫、点选混在一起 | 每命令一个模块，shim 不含逻辑 |
| shell/Python 双栈重复 | agents/skills 逻辑 bash 写一遍、src/ 再写一遍 | 命令面直接 import `src/` 实现 |
| TUI 追 CLI 成本高 | CLI 是 bash，TUI 要包装/复刻 | TUI 与 CLI 调同一 Python 入口 |
| 报错诊断不友好 | 错误从 planner/handler 层层冒泡，无分类 | 错误码 + 分级输出 |

## 包结构

```
src/dotf_cli/
├── __main__.py          # argparse 根 parser，子命令发现
├── commands/            # 每命令一文件
│   ├── pull.py          # git pull + stash 逻辑（subprocess git）
│   ├── init.py          # profile 选择与首次初始化引导
│   ├── status.py        # 现有 --json 契约保留并扩展
│   ├── agents.py        # agents skill/mcp artifact 动词
│   ├── skills.py        # skills -i/-r，group→id→npx 解析顺序
│   ├── retry.py
│   └── modules.py       # -i -c -d -u --deconfig + 编号点选入口
├── select.py            # interactive_select 的 Python 重写
├── output.py            # 人类输出（色彩/前缀）+ --json 序列化
└── errors.py            # 错误码、DotfError、--verbose 链路
```

`dotf_core/cli.py`（shell 桥：atomic-write / backup / sanitize / path-check）保留原位，是 handler 的内部依赖，与用户面无关。

## 命令清单与行为契约

平移以现有行为为准，契约由现有测试锁定；下表是分发边界，不是行为重设计。

| 命令 | 现状来源 | 下沉后要点 |
|---|---|---|
| `dotf pull` | cmd_pull | git 操作走 subprocess；stash 逻辑平移 |
| `dotf init` | cmd_init | profile 选择；非交互参数保留 |
| `dotf path` | cmd_path | 纯输出 |
| `dotf status` | cmd_status | 现有 `--json` 字段名不动 |
| `dotf tui` | cmd_tui | 仍 `python -m dotf_tui`；保留 tty 检查 |
| `dotf agents <skill|mcp> ...` | cmd_agents_artifact | 直接调 `src/agents/` |
| `dotf skills ...` | cmd_skills | group→id→npx 解析顺序不变（ADR-0012） |
| `dotf retry` | cmd_retry | 读执行状态重放 |
| `dotf <mod> -i -c -d` | do_*_one + plan_and_run | Python 调 `src/planner.py` 出 plan，`run_plan.sh` 执行（Executor/Handler 不动） |
| 反动作 `-u` / `--deconfig` | 同上 | 守卫校验平移（Dependent、Conflict 语义不变） |
| 无参数 / 旧语法 | reject_legacy_syntax | 守卫原样平移，报错文案不动 |

## 输出契约

- 每个命令支持人类可读输出与 `--json` 双模；`--json` 时 stdout 只输出一个 JSON 文档，诊断信息一律走 stderr。
- JSON 字段命名约定：snake_case；命令结果包 `ok`、`command`、`data`；错误包 `ok: false`、`error: {code, message, chain?}`。
- 现有 `--json` 字段名（status 等）不改，TUI 与 CI 已在消费。

## 错误模型

错误码表（`errors.py` 单一定义）：

| code | 含义 | 典型场景 |
|---|---|---|
| `usage` | 参数/语法错误 | argparse 拒绝、旧语法守卫触发 |
| `plan` | plan 生成失败 | planner 校验不过 |
| `handler` | handler 执行失败 | install/config 非零退出 |
| `conflict` | owned 目标被改 | deconfig/remove 遇 Conflict（ADR 语义：留下并报告） |
| `env` | 环境不满足 | 缺运行时、非 tty 要求 tty |
| `internal` | 未预期错误 | 兜底，附带 `--verbose` 链路 |

- stderr 统一 `[dotf]` 前缀 + 错误码；`--verbose`（或 `DOTF_VERBOSE=1`）追加 plan/handler 调用链。
- 退出码与错误码一一对应，测试按码断言。

## 交互点选

- `select.py` 重写编号点选：分组列表、数字/token 选择、空输入重刷，行为对齐现有 bash 版。
- 非 tty 时点选拒绝并报 `env`，与现状一致。
- 点选仍属 CLI，`dotf tui` 是另一条皮肤（CONTEXT.md 的 TUI 词条不变）。

## 迁移计划（一次性替换）

1. **搭骨架**：`dotf_cli` 包、`errors.py`/`output.py` 契约、shim 转发开关。
2. **平移命令**：按 `path → status → retry → modules 动作 → skills → agents → init → pull` 顺序（先易后难，modules 动作依赖 planner 接入）。
3. **平移守卫与点选**：reject_legacy_syntax、interactive_select（pty 测试先行）。
4. **测试平移**：现有 `tests/test_cli_baseline.py` 等 bash 测试逐条改写；新增 pty 交互测试与临时 git 仓库测试（慢测打 `slow` mark 单独跑）。
5. **切换**：shim 默认走 `dotf_cli`；旧脚本移入 `scripts/legacy/dotf.sh` 作为 `DOTF_LEGACY_CLI=1` 逃生门（不进 help）。
6. **收尾**：README / docs/Dotfiles.md 命令示例核对；`show_help` 内容由 argparse help 接管。

开发期自举：在 main 上 `git worktree add` 一份旧版，分支上任意折腾，日常维护用旧版 worktree 里的 `bin/dotf`。

## 明确不做

- 不重设计任何命令的语义、参数名、JSON 字段（guardrails 是现有测试）。
- 不动 Executor / Handler：`scripts/modules/<name>/`、`run_plan.sh` 保持 bash。
- 不合并 `dotf_core/cli.py` 桥；它服务 handler，不是用户面。
- 不删兼容守卫；旧语法报错行为原样保留。
