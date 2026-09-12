# 用户面 CLI 全面下沉 Python：`bin/dotf` 变 shim，新包 `src/dotf_cli/`

`bin/dotf`（约 1300 行 bash 单文件）承载的全部命令解析、交互点选、输出与错误处理下沉到 Python 包 `src/dotf_cli/`（argparse 子命令）；`bin/dotf` 退化为设置 `PYTHONPATH` 并 `exec python3 -m dotf_cli` 的 shim。理由：bash 与 Python 双栈重复维护同一份 agents/skills 逻辑；TUI 要追 CLI 新动作；报错层层冒泡无法诊断。下沉后命令面与 `src/` 共享同一份实现，根治双栈重复与 TUI/CLI 漂移。

## 决策

- **范围**：全部命令——`pull` / `init` / `path` / `status` / `tui` / `agents` / `skills` / `retry` / 模块 `-i -c -d` 及反动作，以及 `plan_and_run`（改为 Python 直接调 `src/planner.py`，再经 `run_plan.sh` 执行）。Executor / Handler 边界不动：`scripts/` 里 handler 与 `run_plan.sh` 保持 bash。
- **命名**：用户面包叫 `dotf_cli`；`dotf_core/cli.py` 是 shell 桥（atomic-write / backup / sanitize 等），属实现细节，与用户面无关、不进词汇表。
- **交互**：编号点选在 Python 重写，CLI 保留独立点选，不强制进 TUI。
- **兼容守卫**：`reject_legacy_syntax` 等守卫原样平移，行为不变。
- **输出契约**：所有命令人类可读 + `--json` 双模，字段命名同一套约定；TUI、测试、CI 共用。
- **错误模型**：错误码表（usage / plan / handler / conflict / env / internal）+ stderr 统一前缀，`--verbose` 输出链路详情。
- **迁移**：一次性替换，无新旧并存期；开发期用 main 的 worktree 跑旧版自举。
- **逃生门**：`DOTF_LEGACY_CLI=1` 时 shim 转发到仓库保留的旧 bash 脚本（`scripts/legacy/dotf.sh`），不进 help、不宣传，纯应急。
- **测试**：现有 bash CLI 测试全量平移——pytest 单测覆盖 argparse/契约/错误码，交互点选用 pty 真终端测试，`pull`/`init` 的 git 操作用临时真仓库（local remote + clone）跑，慢测单独标记。

## Considered Options

- **混合下沉**（仅 agents/skills/status 下沉，模块动作留 bash）：改动小，但双栈问题只解一半，边界随时间再漂。 rejected：用户四痛里双栈重复与 TUI 漂移都需要单一实现面。
- **纯 bash 模块化**（`bin/dotf` 变 loader + `scripts/cli/*.sh`）：风险最低，但诊断、help、双栈重复照旧。rejected：不触根因。

## Consequences

- `bin/dotf` 里现存的所有命令级 bash 逻辑（含约 100 行 `interactive_select`、约 80 行手写 help、重复 4 次的 action-guard 校验）是平移对象，不是删除对象；行为契约由现有测试锁定。
- 新命令从此在 `dotf_cli` 里加一个子命令即可，TUI 直接调同一 Python 入口。
- `dotf tui` 入口不变（仍 `python -m dotf_tui`），但 TUI 与 CLI 共享的实现从"CLI 是 bash"变为"两者都是 Python 调 src/"。
