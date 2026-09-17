# 内网规则不要把 localhost 当命中

- target: agents/skills/skills-store
- mode: update
- patch: 20260917-233400-drop-localhost-internal-url
- risk: low
- status: proposed

## Intent

上一轮从 `internal_url` 去掉 `.local` 时误加了 `localhost`，会把 HITL 模板里的 `http://localhost:3000` 打成警告。只保留 `.internal` / `.corp` / `.intranet`。

## Conflict check

none。`.corp` 等内网主机仍 WARN。

## Rationale

diagnosing-bugs 的 `Open the app at http://localhost:3000` 不是内网泄露。

## Files

- `agents/skills/skills-store/scripts/audit-skill.sh`
- `agents/skills/skills-store/SKILL.md`

## Validation

- `git apply --check --recount`
- localhost 开发地址不 WARN；`.corp` 仍 WARN
