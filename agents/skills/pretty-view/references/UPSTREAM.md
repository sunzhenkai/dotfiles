# references/ 上游快照清单

vendor 日期：2026-08-14。升级流程见 `../README.md`。第三方快照不要直接修改；第一方统一阅读页为 `html-page.md`。

## 当前 vendor

| 目录 | 上游仓库 | 上游路径 | commit |
|------|----------|----------|--------|
| baoyu-markdown-to-html | jimliu/baoyu-skills | skills/baoyu-markdown-to-html | 6b7a2e417500561a5ecdd0b168332f4142584617 |
| html-ppt | lewislulu/html-ppt-skill | 仓库根（skill 即仓库） | f3a8435d3901697d5ac5e64d356c933637e43107 |
| html-slides | claude-office-skills/skills | html-slides | 9c4c7d5cd2813a8936bf2c9fdb174ea883b85a11 |
| frontend-design | anthropics/claude-code | plugins/frontend-design/skills/frontend-design | 354757e5b2d9aa1ebb62e5d05ecd384f0e11c0f7 |

审计脚本：`agents/skills/skills-store/scripts/audit-skill.sh`。

- `baoyu-markdown-to-html`、`html-slides`：通过，无 findings。
- `html-ppt`：1 项 BLOCK 为误报——`LICENSE` 第 7 行 MIT 原文 `without limitation` 命中 `jailbreak_role`；另有 9 项 WARN：`localStorage` 命中 `browser_session`，`scripts/*.sh` 被判为 executable。

`html-ppt` 快照去掉 `.git/`、README 大图和 `scripts/verify-output/`；功能目录（`SKILL.md`、`assets/`、`templates/`、`references/`、`examples/`、`scripts/{new-deck,render}.sh`）保留。

## 已退出的阅读页 vendor

2026-08-14 起，普通 HTML 阅读页统一由第一方 `html-page.md` 生成，不再运行时路由到平行视觉系统。2026-08-20 起视觉方向改由 `frontend-design` 按内容推导，不再使用固定主题。以下快照已从分发树移除：

| 原目录 | 原上游 | 原 commit | 退出原因 |
|--------|--------|-----------|----------|
| spec-to-readable-html | kemezz/spec-to-readable-html | ff57433e7d1b2ed068511746426c30ed14e6fd29 | 规格能力合并为 `html-page` 的 `spec` 内容模式 |
| html-artifact | mesomya/html-artifact | 3948b97cec0860f180af6e7ef472a3d750193d35 | 图解能力合并为 `html-page` 的 `visual` 内容模式 |
| html-doc | jeffpoulton/html-doc 公开摘要 | 未 vendor（上游 404） | 技术文档能力合并为 `html-page` 的 `doc` 内容模式 |

保留本表仅用于来源追溯；这些名称不得重新出现在 `SKILL.md` 的运行路由中。若需新增阅读页组件，应修改第一方 `html-page.md`，而不是恢复平行 reference。
