# task-grill 移入归档目录

## 意图

上一轮 `20260912-125452-archive-skill` 直接删除了 task-grill 生产内容（依赖 git 历史恢复）。用户要求改为**目录归档**：把生产内容保留在仓库内的归档目录，并记录恢复方式。

本轮改动（新增，承继上一轮已完成的删除与引用清理）：

1. 新建 `agents/skills-archive/`，写入归档约定与恢复步骤的 `README.md`（含 task-grill 的具体恢复清单）；
2. 以归档时原样恢复 task-grill 生产内容：`agents/skills-archive/task-grill/SKILL.md`、`agents/skills-archive/task-grill/agents/openai.yaml`（内容取自 `git show HEAD:agents/skills/task-grill/...`，与删除前逐字节一致）；
3. `agents/README.md` 在「不要手改」段后补一句归档目录说明，指向恢复方式。

## 归档位置的选择

`agents/skills-archive/` 是 `agents/skills/` 的兄弟目录，而非其子目录：src/agents/skills_catalog.py 的 `validate_first_party_coverage` 要求 `agents/skills/` 下每个带 SKILL.md 的目录都必须编入 `agents/skills.yaml`（fail closed），留在原目录下会导致校验报错；`agents/skills.yaml` 编目不含归档条目，故归档 skill 不参与 `dotf agents -c` 安装。

## 协议偏差说明

pwd-skill-manager 要求 patch 路径为 `agents/skills/<skill-name>/...`。本轮改动本质是跨目录移动（新建 `agents/skills-archive/...`），无法满足该前缀约束；已在 result 记录。目标 skill 的审计历史仍保留在 `agents/skills/task-grill/patches/`。

## 风险

medium：新增归档目录与文档，不改变任何安装/校验行为（coverage 只扫 `agents/skills/`）。

## 验证

- `git apply --check --recount` 通过；
- 应用后 `git diff --check`；
- 归档副本与原删除内容一致（与 HEAD 版本 diff 为空）；
- 相关 pytest 通过。
