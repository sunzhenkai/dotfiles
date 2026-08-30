# 结果

- status: applied
- applied_at: 2026-08-30 12:33 (UTC+8)
- gate: 用户明确确认「应用：行为如上，旧命令全部保留，向后兼容」

## 实际改动

| 文件 | 变化 |
|------|------|
| `scripts/specctl.py` | 抽出 `sync_state`；新增 `cmd_finalize`；`COMMANDS` 与 parser 加 `finalize`；`add_sync_args` 复用参数定义 |
| `SKILL.md` | 命令表加 `finalize`；build 第 11 步、update 第 7 步改用一条命令 |
| `references/checklist.md` | 状态机自检项改为以 finalize 为主路径 |
| `evals/cases.yaml` | `state-lifecycle-finalize`、`coverage-file-table-vs-inventory` 同步 |
| `tests/test_skill_contract.py` | `EXPECTED` 加 `finalize` |
| `tests/test_specctl.py` | 新增 `FinalizeTest` 三例 |

## 验证

- `git apply --check --recount`：通过
- 临时副本预跑（应用前）：53 tests OK
- 正式应用后：`python3 -m unittest discover` → **53 tests OK**
- `git diff --check`：无空白错误
- `specctl finalize --help`：退出码 0，子命令注册成功

## 行为确认

- `finalize` 隐含 `--built`；coverage 未过时返回 `stage=coverage` / `reason=coverage_missing` 且**不写盘**（测试已覆盖）
- `set-sync`、`coverage`、`validate` 全部保留，分步排查路径未变
- 非 Git 源 `synced_commit` 仍为 `null`（测试已覆盖）

## 偏差

无。patch 由脚本从真实文件生成，一次校验通过；生成脚本与临时校验目录均已删除，未进入仓库。
