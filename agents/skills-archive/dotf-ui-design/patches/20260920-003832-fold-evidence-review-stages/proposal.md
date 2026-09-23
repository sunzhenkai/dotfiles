# 取证与验收内嵌：visual-evidence 收为取证环节，diff 评审收为 review 可选阶段

- target: agents/skills/dotf-ui-design
- mode: update
- patch: 20260920-003832-fold-evidence-review-stages
- risk: high（触发词扩展：description 增加 diff 级验收场景；用户已明确批准该方向与内容）
- status: proposed

## Intent

用户决策：视觉取证与 diff 级评审不做独立 skill，收编为 dotf-ui-design 的内部能力。上一轮已创建的 `agents/skills/visual-evidence/` 与 `agents/skills/dotf-ui-review/` 直接删除（从零创建物，非 patch 管理对象），编目条目已回退；本 patch 负责 dotf-ui-design 一侧的改造：

1. 新增 `references/visual-evidence.md`：取证环节（采集计划 → 截图/慢放/reduced-motion → 命名存档 → 带条件引用），内容同上一轮 skill 版，去掉 frontmatter、改为环节措辞。
2. 新增 `references/review.md`：diff 级验收可选阶段（读 diff → 机械核对 → 取证 → PASS / PASS-WITH-NITS / CHANGES-REQUESTED）。收编后动效红线直接引用仓内 vendor `improve-animations/AUDIT.md`，不再内联副本。
3. 入口：判断规则中"单个 diff 的动效评审不在此列"改为指向 review 阶段；"配套能力"小节改为"取证与验收"内部指针；description 补 diff 级验收触发场景。
4. modes/* 与 plans.md 中所有"visual-evidence / dotf-ui-review（若环境中可用）"引用改为内部文件链接。

非目标：不改三模式流程骨架；不改 vendor；不动 plans.md 状态机。

## Conflict check

- description 扩展触发面（UI PR / diff 验收），属用户明确批准的方向；review 阶段只读，与 audit/motion 的边界一致。
- review.md 引用 vendor AUDIT.md 为仓内相对路径，随 skill 整体分发，无跨 skill 依赖；上一轮"若环境中可用"降级措辞全部移除（内嵌后必然可用）。
- 与编目无冲突：visual-evidence、dotf-ui-review 条目已回退，编目恢复上一状态。

## Rationale

- 内嵌后 review 阶段可直接引用 vendor AUDIT.md 精确数值，消除内联红线的双写漂移。
- 取证与验收只服务本 skill 的三模式与 plans 闭环，独立成 skill 反而引入可选安装带来的降级分支；收编后引用关系确定。
- 可验证：全部引用为仓内相对链接，存在性可机械检查；编目解析应通过且无新增条目。

## Files

- `agents/skills/dotf-ui-design/references/visual-evidence.md`（新增）
- `agents/skills/dotf-ui-design/references/review.md`（新增）
- `agents/skills/dotf-ui-design/SKILL.md`（description 补触发、判断规则改指向、小节改名换指针）
- `agents/skills/dotf-ui-design/references/modes/design.md`（取证与验收引用改内部链接）
- `agents/skills/dotf-ui-design/references/modes/audit.md`（override 取证行改内部链接）
- `agents/skills/dotf-ui-design/references/modes/motion.md`（override feel check 行改内部链接）
- `agents/skills/dotf-ui-design/references/plans.md`（执行承接改内部链接）

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check`；全部相对链接存在；`parse_catalog` 通过且 dotfiles 组无 visual-evidence / dotf-ui-review；无"若环境中可用"残留指向已删除 skill；无隐私信息。
