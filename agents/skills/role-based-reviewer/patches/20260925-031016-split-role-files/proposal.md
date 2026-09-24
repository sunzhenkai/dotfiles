# 角色深度内容拆分为 references/roles/<role>.md 并补齐各角色清单

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260925-031016-split-role-files
- risk: medium
- status: proposed

## Intent

把原本挤在 role-vocabulary.md 一张表里的 9 个角色拆为每个角色一个深度文件 `references/roles/<role>.md`，并给每个角色补充紧凑核心检查清单（12–18 条/角色，🔴/🟡/⚪ 分级对齐 design 清单风格）。上一轮新增的 `references/ui-ux-checklist.md` 并入 `roles/design.md`，避免 design 内容散落两处。

非目标：不改变三道门禁、严重级别定义、brief-protocol 输出骨架；不追求各角色清单与 design（55 条）等量——深度后续由 skill-evolver 从真实执行进化。

## Conflict check

- 与上一轮 `20260925-030131-uiux-role` 无冲突：该轮创建的 `ui-ux-checklist.md` 被本轮整体并入 `roles/design.md`（内容不变，仅加头部与锚点/下游/redirect 段）。
- role-vocabulary.md 保留角色矩阵（我管/我不管）与共享对象归属表——它们是跨角色 redirect 的边界权威，不拆；组合规则新增一行声明角色文件职责分工。
- 与 role-chat 的 `references/roles/<id>.md` 命名惯例一致，但两 skill 独立，无引用关系。
- preload-protocol 的各角色锚点表下沉到各角色文件，通用层（通用四层加载、运行态上下文、检索边界）不变。

## Rationale

`design` 有专属清单后其余 8 个角色仍只有一行表格职责，审查时无抓手；拆分为「仅角色生效才加载」的角色文件后，每个角色获得锚点 + 分级清单 + 下游建议 + redirect，且多角色评审只读生效角色的文件，符合 ≤6 文件预算与耗时优化原则。

## Files

- `agents/skills/role-based-reviewer/SKILL.md`：流程第 2 步声明按角色加载 `references/roles/<role>.md` 且计入文件预算
- `agents/skills/role-based-reviewer/references/preload-protocol.md`：各角色优先锚点表 → 一行指针（未生效角色不加载）
- `agents/skills/role-based-reviewer/references/role-vocabulary.md`：组合规则加角色文件分工声明
- `agents/skills/role-based-reviewer/references/roles/{engineer,algo,data,sre,ops,biz,product,design,qa}.md`：新增 9 个角色文件
- `agents/skills/role-based-reviewer/references/ui-ux-checklist.md`：删除（并入 roles/design.md）

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；9 个角色文件与 b 侧预期逐字节一致；`grep -r ui-ux-checklist` 无残留引用；角色文件内 `../preload-protocol.md`、`../role-vocabulary.md` 链接目标存在；preload-protocol 指向的 `roles/<role>.md` 9 个齐全；SKILL.md frontmatter `name` 不变
