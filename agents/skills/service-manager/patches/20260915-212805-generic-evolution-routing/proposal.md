# Evolution 改为通用 skill-upgrader / skill-evolver 分流

- target: agents/skills/service-manager
- mode: update
- patch: 20260915-212805-generic-evolution-routing
- risk: medium
- status: proposed

## Intent

Self-evolution 不再点名 `pwd-skill-manager` 或本仓库 `agents/skills/` 布局。经验进化委托 `skill-evolver`；显式修订委托 `skill-upgrader` 的 `update`。配套 eval 同步改为通用分流。

非目标：不改服务启停流程；不改历史 `patches/`；不改 examples/experience。

## Conflict check

与标准 `skill-upgrader` 注入模板一致。本仓套壳仍可维护本 Skill，但不由本 Skill 正文感知。

## Rationale

通用 Skill 安装到其它仓库后不应假设存在项目级 `pwd-skill-manager`。双通道问题用通用的 skill-evolver / skill-upgrader 分工即可表达。

## Files

- `agents/skills/service-manager/SKILL.md`：目录树改为 `<skill-dir>/`；Evolution 对齐通用分流
- `agents/skills/service-manager/evals/cases.yaml`：`evolution-prefers-patch-audit` 去掉本仓套壳名

## Validation

- `git apply --check --recount` 通过后再应用
- 生产稿与 evals 不再出现 `pwd-skill-manager`
- frontmatter `name` 仍为 `service-manager`
