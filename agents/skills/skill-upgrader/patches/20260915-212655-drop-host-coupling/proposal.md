# 去掉对本仓库套壳与布局的感知

- target: agents/skills/skill-upgrader
- mode: update
- patch: 20260915-212655-drop-host-coupling
- risk: medium
- status: proposed

## Intent

通用 `skill-upgrader` 不再点名 `pwd-skill-manager`，也不再把本仓库的 `agents/skills/` 布局、`~/.agents/skills/` 镜像或 `dotf agents -c` 写进可复用正文。关系表只保留本 skill 与 `skill-evolver`。

非目标：不改 patch 工作流、模式门禁或 `self-upgrade` 模板；不改历史 `patches/`；不改 `.agents/skills/pwd-skill-manager`。

## Conflict check

与 `skill-evolver` 的分流不变。本仓维护 `agents/skills/` 的路由改由项目级套壳承担，不在通用 skill 里互指。

## Rationale

`agents/skills/` 会安装到任意仓库；点名仅存在于本仓 `.agents/skills/` 的工具会让其它环境看到不存在的 skill。公开性要求只写跨项目仍成立的规则。

## Files

- `agents/skills/skill-upgrader/SKILL.md`：删除套壳关系与本仓路径/sync 提醒
- `agents/skills/skill-upgrader/references/patch-protocol.md`：`<skill-dir>` 说明去掉本仓库特例
- `agents/skills/skill-upgrader/references/evals.md`：`tests/` 约定改为目标目录通用表述

## Validation

- `git apply --check --recount` 通过后再应用
- 生产稿不再出现 `pwd-skill-manager`、`dotf agents`、`scripts/agents/sync.sh`
- frontmatter `name` 仍为 `skill-upgrader`
- 不改历史 patches、镜像目录
