# references/ 上游快照清单

vendor 日期：2026-08-13。升级流程见 `../README.md`。第三方快照不要直接修改。`html-page.md` 是本仓库第一方阅读页说明（默认全宽），不在上表，改它即可。

| 目录 | 上游仓库 | 上游路径 | commit |
|------|----------|----------|--------|
| baoyu-markdown-to-html | jimliu/baoyu-skills | skills/baoyu-markdown-to-html | 6b7a2e417500561a5ecdd0b168332f4142584617 |
| html-ppt | lewislulu/html-ppt-skill | 仓库根（skill 即仓库） | f3a8435d3901697d5ac5e64d356c933637e43107 |
| html-slides | claude-office-skills/skills | html-slides | 9c4c7d5cd2813a8936bf2c9fdb174ea883b85a11 |

审计：vendor 前均跑 `agents/skills/skills-store/scripts/audit-skill.sh`。

- `baoyu-markdown-to-html`、`html-slides`：通过，无 findings。
- `html-ppt`：1 项 BLOCK 为误报——`LICENSE` 第 7 行 MIT 原文 `without limitation` 命中 `jailbreak_role`（「without … limit」）。9 项 WARN：`localStorage` 命中 `browser_session`（演讲者窗口记住卡片布局，非窃取会话）；`scripts/*.sh` 被 `file` 判为 executable（正常 shell 脚本）。

`html-ppt` 未原样收入全部上游体积（约 11M，多为 README 动图与 `scripts/verify-output` 截图）。本快照去掉：

- `.git/`
- `docs/readme/*.png`、`docs/readme/*.gif`
- `scripts/verify-output/`

功能目录（`SKILL.md`、`assets/`、`templates/`、`references/`、`examples/`、`scripts/{new-deck,render}.sh`）保留。LICENSE 随仓库根一并拷入各 skill 目录。
