# 用 specctl coverage 核对文件表覆盖

- target: agents/skills/project-spec-mirror
- patch: 20260829-233946-specctl-coverage
- risk: medium
- status: proposed

## Intent

新增 `specctl coverage`：把 `inventory` 中的代码文件与各模块 README「文件」表对照，输出 `missing` / `extra` / `unscoped`。Agent 在 build / update 写完文件表后必须跑它，禁止手对清单。

- `detailed` + `important` / `complete`：`enforce=true`，`missing` 非空则退出码 1，不得 `set-sync`。
- `concise` 与 `lightweight`：仍报告缺口，但不强制。
- 只要求代码扩展名（`CODE_EXTS`）出现在文件表；README、清单、CI、compose 等非代码文件不进 `missing`（它们走恢复投影 / 切面）。
- 文件表单元格可以是精确路径或目录范围（与「合并登记」一致）。
- 非目标：不扫符号是否列全、不扫密钥、不改正文、不改变 `validate` 在 init 后仍可通过的行为。

## Conflict check

与「CLI 不写概述、不抽概念」不冲突。`validate` 仍只检查骨架，避免 init 后误失败。不与 `route` / `inventory` 职责重叠：`route` 管变更落到哪一页，`coverage` 管范围内代码文件是否都有表行。

## Rationale

`important` / `complete` 已要求「不得整份省略」，但只靠 Agent 对表，真实执行里漏过。对照是确定性的，适合脚本；跨项目仍成立。unittest 可验证 enforce、目录范围、`scope` 与非代码排除。

## Files

- `agents/skills/project-spec-mirror/scripts/specctl.py` — 实现 `coverage`。
- `agents/skills/project-spec-mirror/SKILL.md` — 命令表与工作流。
- `agents/skills/project-spec-mirror/references/modes.md` — 写完文件表后跑 coverage。
- `agents/skills/project-spec-mirror/references/routing.md` — 增删文件后以 CLI 为准。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 验收与非 git update。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — coverage 回归。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 命令表加入 `coverage`。

## Validation

- `git apply --check --recount` 通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 通过。
- 无隐私信息；不改 `patches/` 历史。
