# 四条能力 skill 改为内部引用

- target: agents/skills/dotf-ui-design
- patch: 20260828-203800-internal-refer-skills
- risk: medium
- status: proposed

## Intent

把 `shadcn`、`tailwind-css-patterns`、`tailwind-design-system`、`webapp-testing` 从「全局默认安装」改成本 skill `references/` 下的内部引用：随分发到位，不注册为独立 skill，也不再写入 `agents/skills-defaults.yaml`。`frontend-design` 仍走全局 defaults（本轮不改）。

触发场景与非目标不变。路由器改为：这 4 条 Read `references/<name>/SKILL.md`；`frontend-design` 仍 Read `~/.agents/skills/frontend-design/SKILL.md`。

## Conflict check

与上一版「不 vendor、靠 defaults 全局安装」的契约冲突，这是本轮要改的行为。不与 `pretty-view-html` / `pretty-view-ppt` 抢路径。不把 `frontend-design` 再 vendor 一份。不修改 `patches/` 历史。

## Rationale

用户明确要求这 4 个「作为内部引用，不要安装到全局」。与 `pretty-view-html` 的 refer skill 模式一致，避免 4 个实现向 skill 污染各 agent 的全局 skill 列表。快照只含执行所需正文与 sidecar，不带 png / evals。

## Files

- `SKILL.md`：加载路径与边界改为内部引用
- `references/catalog.md`：区分全局 / 内部引用
- `references/UPSTREAM.md`：来源、commit、审计结论
- `references/shadcn/`、`references/tailwind-css-patterns/`、`references/tailwind-design-system/`、`references/webapp-testing/`：上游快照
- `tests/test_skill_contract.py`：断言 4 条已 vendor、`frontend-design` 未 vendor

`agents/skills-defaults.yaml`、`agents/README.md`、`tests/test_agents_skill_defaults.py` 的配套删除不在本 patch 内（路径不属于本 skill），应用后另行改。

## Validation

- `git apply --check --recount` 通过后应用
- `python3 -m pytest` 跑本 skill 契约测试与 `tests/test_agents_skill_defaults.py`
- 隐私检查：快照无个人路径/密钥
