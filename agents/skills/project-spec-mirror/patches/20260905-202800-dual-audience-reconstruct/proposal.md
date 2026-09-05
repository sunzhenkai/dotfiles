# 双读者树与可换栈复现验收

- target: agents/skills/project-spec-mirror
- patch: 20260905-202800-dual-audience-reconstruct
- risk: high
- status: proposed

## Intent

把 project-spec-mirror 的默认验收从「给人读的实现讲义 + 重建当前可运行系统」改为终态方案：

1. `briefing/` 只给人扫读架构、业务流与图，禁止实现泄漏。
2. `agent/specs/` 借用 OpenSpec 的 Requirement / Scenario，供 Agent 换栈复现功能（L2–L3）。
3. `evidence/source-map.md` 只做增量路由，不参与人读与复现。
4. 模式改为 `briefing` | `reconstructable`；`runtime/` `build/` 与 `facets/` 降为 opt-in。
5. `specctl` 的骨架、coverage、route、validate、finalize 对齐能力覆盖，不再按模块文件表验收。

非目标：不写入目标仓 `openspec/`；不改目标项目源码；不自动删除旧金字塔目录。

触发：用户要求按终态方案落地本 Skill。

## Conflict check

- 与现有档 C（只凭镜像重建可运行系统）、concise/detailed、模块文件表 coverage、默认 facets 直接冲突：这正是本轮要改的验收。
- 与 OpenSpec change 工作流：仍禁止写入 `openspec/`；只借用 spec 格式到 `spec_root/agent/specs/`。
- 与 archify：图改放到 `briefing/diagrams/`，仍委托 archify。
- 旧镜像无法通过新 `validate`：文档要求按新树 rebuild，遗留目录停更不删。

## Rationale

人读与换栈复现不能共用一棵实现讲义树。拆开后，briefing 可扫读、agent spec 可验证，coverage 验收能力而不是源文件清单。跨项目仍成立；unittest 覆盖新骨架、路由与门禁。

## Files

- `SKILL.md` — 身份、阶段、工作流与非目标
- `references/layout.md` — 双读者目录
- `references/modes.md` — briefing / reconstructable
- `references/knowledge.md` — 概念/流给人，能力/模型给 Agent
- `references/projections.md` — agent surface/data 与可选 realization
- `references/facets.md` — 非默认
- `references/diagrams.md` — briefing/diagrams
- `references/routing.md` — 文件 → 能力
- `references/checklist.md` — 新自检
- `scripts/specctl.py` — 骨架、coverage、route、validate
- `tests/` — 对齐新契约
- `evals/cases.yaml` 与 `evals/README.md` — 对齐新验收

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
