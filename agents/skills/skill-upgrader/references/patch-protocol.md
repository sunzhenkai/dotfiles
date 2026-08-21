# Patch Protocol

本协议定义 `skill-upgrader` 生成的更新记录。所有 diff 路径相对**包含目标 Skill 的 Git 仓库根**；记录目录落在目标 Skill 内。

## 目录

```text
<skill-dir>/patches/<YYYYMMDD-HHMMSS>-<slug>/
├── proposal.md
├── change.patch
└── result.md
```

`<skill-dir>` 是含有待改 `SKILL.md` 的目录（任意仓库中的任意 Skill）。本仓库共享 Skill 通常为 `agents/skills/<skill-name>`。

## proposal.md

```markdown
# <简短标题>

- target: <skill-dir>
- mode: update | self-upgrade
- patch: <YYYYMMDD-HHMMSS>-<slug>
- risk: low | medium | high
- status: proposed

## Intent

<要改变的模型行为、触发场景和非目标；须与 mode 一致>

## Conflict check

<与现有内容及其他 Skill 职责的冲突；没有则写 none>

## Rationale

<为什么该更新合理且可验证>

## Files

- <将修改的、相对仓库根的路径及原因>

## Validation

- <应用前检查>
- <应用后测试或确定性检查>
```

`status` 在 proposal 中保持 `proposed`，最终状态写入 `result.md`，不要回写历史提案。

## change.patch

使用 Git 可接受的 unified diff。示例：

```diff
diff --git a/agents/skills/example/SKILL.md b/agents/skills/example/SKILL.md
index 1111111..2222222 100644
--- a/agents/skills/example/SKILL.md
+++ b/agents/skills/example/SKILL.md
@@ -10,3 +10,4 @@
 Existing instruction.
+New general instruction.
```

要求：

1. 在包含目标 Skill 的仓库根可被 `git apply --check --recount` 校验。
2. `a/`、`b/` 后使用相对该仓库根的完整路径，且前缀为该 `<skill-dir>/`。
3. 只修改同一目标 Skill 的生产内容（含 `self-upgrade` 新增的 examples/evals/experience）。
4. 不包含 `patches/` 历史记录、agent 镜像目录、绝对路径或临时文件。
5. 不依赖已应用但未记录的手工编辑。
6. 找不到 Git 仓库根时不得伪造 apply；停止并交由用户处理。

## result.md

```markdown
# Result

- target: <skill-dir>
- mode: update | self-upgrade
- patch: <YYYYMMDD-HHMMSS>-<slug>
- risk: low | medium | high
- status: applied | failed
- applied-at: <ISO 8601 timestamp or n/a>

## Validation

- `git apply --check --recount`: pass | fail
- `git diff --check`: pass | fail | not-run
- target tests: <命令与结果，或 not-available>
- privacy check: pass | fail
- mode check: pass | fail

## Notes

<实际结果、失败原因或与 proposal 的偏差；没有则写 none>
```

## 状态规则

- `proposed`：patch 已生成，尚未应用或正在等待确认。
- `applied`：patch 已成功应用且验证通过。
- `failed`：应用或验证失败；停止继续修改生产内容。

已生成的 patch 目录是审计记录。若 proposed patch 尚未应用，可以在同一目录修正 `change.patch`；一旦应用尝试已经发生，不再改写该目录，后续修复创建新 patch。
