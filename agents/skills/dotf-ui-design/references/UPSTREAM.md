# references/ 上游快照清单

vendor 日期：2026-08-28。第三方快照不要直接修改；升级时按本表重新拉取并更新 commit。

## 当前 vendor

| 目录 | 上游仓库 | 上游路径 | commit |
|------|----------|----------|--------|
| shadcn | shadcn/ui | skills/shadcn | 683a5a9b370acdb7785a0529434e6a3b8c7e0441 |
| tailwind-css-patterns | giuseppe-trisciuoglio/developer-kit | plugins/developer-kit-typescript/skills/tailwind-css-patterns | 50f0b945bd81ee1dac377f609871e63b732347fa |
| tailwind-design-system | wshobson/agents | plugins/frontend-mobile-development/skills/tailwind-design-system | 38e19c20d2b154510b0e624a2e3e186b19b5c527 |
| webapp-testing | anthropics/skills | skills/webapp-testing | 3b3fad96af16a10759d930941b4520ba0c40edae |

未 vendor：`frontend-design`（`anthropics/skills`，走 `agents/skills-defaults.yaml`）。

快照去掉 png / evals / agent 适配文件；保留 SKILL.md、其引用的 rules/references、以及 `webapp-testing` 的 scripts/examples/LICENSE。各目录带上游 LICENSE。

## 审计

脚本：`agents/skills/skills-store/scripts/audit-skill.sh`。

| 快照 | 脚本结论 | 复核 |
|------|----------|------|
| shadcn | 4 BLOCK | 误报：`registry.md`「can act as a source registry」命中 `jailbreak_role`；`cli.md` 文档里的 `--yes` / Skip confirmation 命中 `bypass_approval` |
| webapp-testing | 1 BLOCK + 5 WARN | 误报：`LICENSE.txt` MIT 原文 `without limitation`；带 shebang 的 `.py` 被判 `binary_in_skill` |
| tailwind-design-system | 3 WARN | 误报：暗色主题示例里的 `localStorage` 命中 `browser_session` |
| tailwind-css-patterns | 5 WARN | 同上，暗色切换文档 |

## 升级

1. 浅克隆对应仓库，核对新 commit。
2. 对 skill 目录重跑 `audit-skill.sh`，BLOCK 须逐条复核。
3. 替换本目录快照，更新本表 commit 与日期。
4. 走 `pwd-skill-manager` 出新 patch，不要手改生产文件后补记录。
