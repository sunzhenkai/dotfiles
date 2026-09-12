# Skills 归档

这里保存从共享真相源 `agents/skills/` 退役、但仍保留恢复价值的 skill，由 pwd-skill-manager 归档流程移入。

## 规则

- 目录与 `agents/skills/<name>/` 同构，保留归档时的生产内容（`SKILL.md` 及配套文件）。
- **不**编入 `agents/skills.yaml`，不参与 `dotf agents -c` 安装。
- `agents/skills/` 下不得残留同名目录：`agents/skills/` 与编目要求一一对应（`validate_first_party_coverage` fail closed），残留无编目目录会直接报错。
- 审计 patch 历史留在原位置 `agents/skills/<name>/patches/`，不在本目录重复保存。

## 恢复

以 task-grill 为例：

1. 移回真相源：`mv agents/skills-archive/task-grill agents/skills/task-grill`
2. 重新编目：`agents/skills.yaml` 的 `dotfiles` group 加回 `      - task-grill`
3. 恢复下游引用（共 6 处，原文取归档 patch 的删除 hunk：`agents/skills/task-grill/patches/20260912-125452-archive-skill/change.patch`）：
   - `agents/skills/taskflow/SKILL.md` 阶段路由表加回「收敛（可选）」行
   - `agents/skills/task-design/SKILL.md` 加回导语句、流程图 `task-grill?` 节点、「何时不用」表行、「相关」段条目
   - `agents/README.md` 示例条目段加回介绍
4. 重新安装：`dotf agents -c`

恢复之后的后续修改，按 `.agents/skills/pwd-skill-manager/` 的 patches/ 协议走。

## 现存归档

| skill | 归档时间 | 归档 patch |
|-------|----------|------------|
| task-grill | 2026-09-12 | `agents/skills/task-grill/patches/20260912-125452-archive-skill` |
