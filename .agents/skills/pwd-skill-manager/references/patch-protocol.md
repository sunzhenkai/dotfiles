# Patch Protocol

本协议定义 `pwd-skill-manager` 生成的更新记录。所有路径均相对仓库根。

## proposal.md

```markdown
# <简短标题>

- target: agents/skills/<skill-name>
- patch: <YYYYMMDD-HHMMSS>-<slug>
- risk: low | medium | high
- status: proposed

## Intent

<要改变的模型行为、触发场景和非目标>

## Conflict check

<与现有内容及其他 Skill 职责的冲突；没有则写 none>

## Rationale

<为什么该更新通用、合理且可验证>

## Files

- <将修改的仓库相对路径及原因>

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

1. 从仓库根可被 `git apply --check --recount` 校验。
2. `a/`、`b/` 后使用完整仓库相对路径。
3. 只修改同一目标 Skill 的生产内容。
4. 不包含 `patches/`、agent 镜像、绝对路径或临时文件。
5. 不依赖已应用但未记录的手工编辑。

## result.md

```markdown
# Result

- target: agents/skills/<skill-name>
- patch: <YYYYMMDD-HHMMSS>-<slug>
- risk: low | medium | high
- status: applied | failed
- applied-at: <ISO 8601 timestamp or n/a>

## Validation

- `git apply --check --recount`: pass | fail
- `git diff --check`: pass | fail | not-run
- target tests: <命令与结果，或 not-available>
- privacy check: pass | fail

## Notes

<实际结果、失败原因或与 proposal 的偏差；没有则写 none>
```

## 状态规则

- `proposed`：patch 已生成，尚未应用或正在等待确认。
- `applied`：patch 已成功应用且验证通过。
- `failed`：应用或验证失败；停止继续修改生产内容。

已生成的 patch 目录是审计记录。若 proposed patch 尚未应用，可以在同一目录修正 `change.patch`；一旦应用尝试已经发生，不再改写该目录，后续修复创建新 patch。

