# important 核心方法写完整逻辑

- target: agents/skills/project-spec-mirror
- patch: 20260828-211654-important-method-full-logic
- risk: medium
- status: proposed

## Intent

上一轮只改了文件覆盖（不整份省略、其余写简述），方法层仍把「核心符号」理解成一句话职责。本次改为：

1. `important` 整理文件时，**核心方法必须梳理完整逻辑**（有序步骤、关键分支、成功/失败如何结束、副作用），不是一句话点到为止。
2. **不得遗漏方法**：工具/辅助方法可以简述，但必须列名。
3. **测试方法只简述**，不梳理用例或断言步骤；`complete` 同样生效。

非目标：不改文件表「不得整份省略」；不改密钥脱敏；不铺 `notes/`；不把函数体贴进规格；不改 `lightweight` / concise 的方法省略规则。

## Conflict check

与上一档「核心符号用一句话说清做什么」冲突，这正是要加深的部分。与「不要贴大段源码 / 禁止倒 AST」不冲突：完整逻辑用人话步骤写，不搬函数体。与 `complete`「完整整理所有源文件」不冲突：文件仍全覆盖，但测试方法深度封顶为简述。concise 仍可只列核心符号、省略辅助方法。

## Rationale

详尽默认档的阅读价值在方法，不在文件名清单。核心路径不写步骤就无法重建行为；漏列工具方法会让调用关系断裂；测试方法写完整逻辑只会膨胀且与 VERIFY「不抄测试正文」重复。规则跨语言成立，可用措辞与 eval 验收。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — build 步骤：核心方法完整逻辑、方法不得漏列、测试方法只简述。
- `agents/skills/project-spec-mirror/references/modes.md` — 方法层规则、更新示例与 complete 例外。
- `agents/skills/project-spec-mirror/references/layout.md` — 核心符号模板区分完整逻辑与简述。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 同步 important / complete 验收。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 锁定新措辞。
- `agents/skills/project-spec-mirror/experience/failures/20260828-important-method-one-liners.md` — 记录本次纠正。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- 生产正文不含真实产品名或密钥原文。
