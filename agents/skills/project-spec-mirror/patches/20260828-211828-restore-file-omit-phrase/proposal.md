# 恢复 important 文件层「不得整份省略」

- target: agents/skills/project-spec-mirror
- patch: 20260828-211828-restore-file-omit-phrase
- risk: low
- status: proposed

## Intent

上一 patch 应用后，`test_important_briefs_not_omits` 失败：modes.md 丢掉了文件层禁令措辞「不得整份省略」。补回该句，方法层规则不动。

## Conflict check

none。与「核心方法写完整逻辑 / 方法不得漏列」并存：前者管文件覆盖，后者管方法深度。

## Rationale

文件不得整份省略仍是 important 的有效规则；恢复原验收措辞即可让既有测试通过，不必改测试去迁就漏写。

## Files

- `agents/skills/project-spec-mirror/references/modes.md` — important 档位补回「不得整份省略」。

## Validation

- `git apply --check --recount` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
