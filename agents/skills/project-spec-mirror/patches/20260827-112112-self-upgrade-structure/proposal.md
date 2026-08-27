# 升级为自进化结构

- target: agents/skills/project-spec-mirror
- mode: self-upgrade
- patch: 20260827-112112-self-upgrade-structure
- risk: medium
- status: proposed

## Intent

把 `project-spec-mirror` 从静态 Skill 升级为可积累经验、用 Eval 验收、禁止单次失败改正文的自进化结构。

触发：用户点名 `/skill-upgrader`，要求将上一轮创建的该 Skill 优化为自进化。

非目标：不改放置规则、specctl 契约、金字塔/粒度/知识层原文；不编造 examples 或 experience 条目；不按执行经验改核心行为。

## Conflict check

原文尚无 Self-evolution 段落，无 `examples/` `evals/` `experience/`。与 `skill-evolver` 的分工写在注入段：经验驱动改正文走 evolver。none 以外：注入不覆盖现有门禁。

## Rationale

标准 self-upgrade：补齐三目录、从原文抽取确定性 Eval、末尾追加注入。无真实成功案例故 examples 只留 README。现有 `tests/` 用一条 regression case 指向，不复制测试。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 末尾追加 Self-evolution
- `agents/skills/project-spec-mirror/examples/README.md`
- `agents/skills/project-spec-mirror/evals/README.md`
- `agents/skills/project-spec-mirror/evals/cases.yaml`
- `agents/skills/project-spec-mirror/experience/README.md`
- `agents/skills/project-spec-mirror/experience/failures/.gitkeep`
- `agents/skills/project-spec-mirror/experience/successes/.gitkeep`
- `agents/skills/project-spec-mirror/experience/patterns/.gitkeep`

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`；frontmatter 仍合法；无私有信息；未改历史 patches
