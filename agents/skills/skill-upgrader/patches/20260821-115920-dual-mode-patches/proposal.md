# skill-upgrader：双模式门禁 + 统一 patches 协议

- target: agents/skills/skill-upgrader
- patch: 20260821-115920-dual-mode-patches
- risk: high
- status: proposed

## Intent

为公用的 `skill-upgrader` 增加与 `pwd-skill-manager` 同构的可审计更新能力，并强制模式门禁：

- `update`：更新任意已有 Skill 的生产内容（经 `<skill-dir>/patches/`）
- `self-upgrade`：切换/升级为自更新结构（examples/evals/experience），写入同样走 patch
- 经验驱动改正文 → 移交 `skill-evolver`；本仓库 `agents/skills/` 套壳角色留给 `pwd-skill-manager`（本轮只声明关系，不改该 Skill）

非目标：不实现 `pwd-skill-manager` 套壳改造；不与 `skill-evolver` 的 `evolutions/` 混用。

## Conflict check

- 扩大本 skill 职责（原仅自进化升级 → 兼通用 update），与旧 description/门禁冲突：以模式门禁与关系表消解。
- 与 `pwd-skill-manager`：改为「本仓库套壳、委托本 skill」，本轮仅文档约定，避免两套 patch 语义。
- 与 `skill-evolver`：明确经验进化不走本 skill 的 `patches/`。

## Rationale

用户确认：公用 skill 更新任意目标；patch 统一落在 `<skill-dir>/patches/<id>/`；入口区分「更新」与「切自更新」。可审计、可 `git apply` 校验，跨仓库可复用。

## Files

- `agents/skills/skill-upgrader/SKILL.md` — 双模式、patch 工作流、关系与交付格式
- `agents/skills/skill-upgrader/references/patch-protocol.md` — 新建协议模板
- `agents/skills/skill-upgrader/references/layout.md` — self-upgrade 须经 patch 组装
- `agents/skills/skill-upgrader/references/skill-injection.md` — 进化时区分 evolver / upgrader update

## Validation

- `git apply --check --recount` 对本 `change.patch`
- 应用后：`git diff --check -- agents/skills/skill-upgrader`
- frontmatter `name` 与目录一致；`references/patch-protocol.md` 可解析
- 无隐私/绝对家目录；未改 `.claude/skills` 等镜像
