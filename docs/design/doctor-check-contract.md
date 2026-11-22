# doctor 检查契约（L0 / L1）

本文固化 `dotf <mod> -d` 与 `dotf agents -d --deep` 的语义边界，供 skill、handler 与测试共同引用。改检查行为时同步本文与 `agents/skills/dotfiles/references/check.md`。

相关实现：`src/agents/doctor.py`、`src/agents/managed_runtime.py`、`scripts/modules/<name>/doctor.sh`、`modules.yaml`。

## 两层检查

| 层 | 入口 | 范围 | 失败粒度 |
|---|---|---|---|
| L0 | `dotf <mod> -d`（无参 = 全量，按当前 OS 过滤） | 模块 handler：命令是否在 PATH、配置是否存在 | 单模块 |
| L1 | `dotf agents -d --deep` | `src/agents/doctor.py` 领域审计：env / tools / skills / instructions / config boundaries / declared formats / tracked security scan | 单检查项 |

## 执行语义

- **fail-fast**：计划内首个 `failed` 动作中止后续，其余记 `not-run`；`not-run` 不等于通过。
- **非 TTY 门禁**：无终端会话必须带 `--yes`，只读 doctor 同样；`--json` 不豁免。
- **输出**：结果行 `RESULT<TAB>状态<TAB>模块<TAB>动作…`；handler 日志只收在临时日志、失败时回放；`--verbose` 逐行输出。
- **明细**：L1 失败时 report 只留汇总行；直跑 `python3 src/agents/doctor.py --deep --verbose` 看全量 checks。

## L1 config 边界审计

审计对象 = `modules.yaml` 中声明了 `config` 的模块（与 `enabled` 无关）。

| 检查 | 语义 | pass 条件 |
|---|---|---|
| link-boundary | 从 HOME 到 target 的逐段 lstat，出现 symlink 即失败 | 仅 `strategy: symlink` 且非 writable/sensitive 的只读目标，且解析后等于 source |
| internal-link | target 目录树内部出现 symlink | 无 symlink，或被 `preserve` / `exclude` 规则裁剪 |
| permission | 仅 `sensitive: true` 的模块：目录 ≤ 0700、普通文件 ≤ 0600 | 全树满足；带任何执行位的普通文件、非文件/目录项都算 broad |
| root-permission | target 自身 mode | 同 permission |

- 规则匹配（`preserve` / `exclude`）：精确路径、`<前缀>/…`、glob（`fnmatch`）三选一命中即裁剪该子树；walk 用 nofollow 语义，不跟随链接。
- 结论行固定为 `registry targets audited=N findings=M`，tools 修复建议以「运行 dotf <mod> -c --dry-run」为主。

## 部署 mode 派生（managed_runtime）

- 部署文件 mode = 源文件有执行位 ? `755` : `644`，再裁剪到模块 `target_mode` 位面。
- 因此：无执行位的源文件派生不出 `0600`；instructions 运行时与 `sensitive` 目标的 0600 要求存在已知互斥，见 `agents/skills/dotfiles/references/repo.md`「已知口径冲突」。

## declared-formats

- 对 `config.source` 声明的 `.json` / `.yaml` / `.toml` 逐文件**严格**解析；JSONC（注释、尾逗号）按 malformed 报出，属工具格式约定，不是配置损坏。

## tracked security scan

- 对仓库 git-tracked 文件按 `rule_version` 模式匹配敏感串（与 `scripts/ci/secret-scan.py` 同源规则），命中只报位置与规则名，不复述内容。
