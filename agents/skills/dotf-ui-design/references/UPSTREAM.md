# references/ 上游快照清单

vendor 日期：2026-08-09。升级流程见 `../README.md` 第 6 节。**第三方快照不要直接修改**；first-party 策展见下方。

| 目录 | 上游仓库 | 上游路径 | commit |
|------|----------|----------|--------|
| web-design-guidelines | vercel-labs/agent-skills | skills/web-design-guidelines | 7c180d9044c9ae2b442b567aad4e42a28dd5ed62 |
| design-taste-frontend | leonxlnx/taste-skill | skills/taste-skill | e988add20dab0fa97d7a76781c48961c8184288e |
| redesign-existing-projects | leonxlnx/taste-skill | skills/redesign-skill | e988add20dab0fa97d7a76781c48961c8184288e |
| minimalist-ui | leonxlnx/taste-skill | skills/minimalist-skill | e988add20dab0fa97d7a76781c48961c8184288e |
| industrial-brutalist-ui | leonxlnx/taste-skill | skills/brutalist-skill | e988add20dab0fa97d7a76781c48961c8184288e |
| high-end-visual-design | leonxlnx/taste-skill | skills/soft-skill | e988add20dab0fa97d7a76781c48961c8184288e |
| ui-ux-pro-max | nextlevelbuilder/ui-ux-pro-max-skill | .claude/skills/ui-ux-pro-max | abb7f2fd5a083fa1ff55c326a963ff0d95c33f99 |

审计：vendor 前均通过 `agents/skills/skills-store/scripts/audit-skill.sh`，无 critical 阻断；少量 warn 为误报（文档文案命中 browser_session 模式、Python 脚本被 `file` 误判 binary）。

## first-party 策展（非 vendor）

| 目录 | 说明 | 维护 |
|------|------|------|
| `solo-ui-design` | 纸墨编辑感 UI 规范；从 `solo-blog` `.agents/skills/ui-design/` 去特例化提炼；按需迁入 frontend-design / baseline-ui / improve-ui 原文 | 可直接修订；细节见 `solo-ui-design/ORIGIN.md` |
