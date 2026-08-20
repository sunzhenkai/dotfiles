# references/ 上游快照清单

vendor 日期：2026-08-14。升级流程见 `../README.md`。第三方快照不要直接修改。

## 当前 vendor

| 目录 | 上游仓库 | 上游路径 | commit |
|------|----------|----------|--------|
| html-ppt | lewislulu/html-ppt-skill | 仓库根（skill 即仓库） | f3a8435d3901697d5ac5e64d356c933637e43107 |
| html-slides | claude-office-skills/skills | html-slides | 9c4c7d5cd2813a8936bf2c9fdb174ea883b85a11 |

审计脚本：`agents/skills/skills-store/scripts/audit-skill.sh`。

- `html-slides`：通过，无 findings。
- `html-ppt`：1 项 BLOCK 为误报——`LICENSE` 第 7 行 MIT 原文 `without limitation` 命中 `jailbreak_role`；另有 9 项 WARN：`localStorage` 命中 `browser_session`，`scripts/*.sh` 被判为 executable。

`html-ppt` 快照去掉 `.git/`、README 大图和 `scripts/verify-output/`；功能目录（`SKILL.md`、`assets/`、`templates/`、`references/`、`examples/`、`scripts/{new-deck,render}.sh`）保留。
