# Decision — 20260829-complete-mode-notes-mandatory

- Status: promoted
- Date: 2026-08-29
- Risk: medium
- Eval: pass (see eval.md)

## Promotion

`SKILL.md` / `references/modes.md` / `evals/cases.yaml` 已覆盖到生产稿，3 个文件 byte-identical to candidate。

## Modified files

| 文件 | 变更摘要 |
|------|---------|
| `SKILL.md` | 非目标段 +1 条（notes 命名是 topic）；build 步骤 7 末 +1 句（build 前 grep）；新增步骤 8.5（complete 必建） |
| `references/modes.md` | 表格行改为分档位（concise/lightweight 不建 / important opt-in / complete 必建）；新增 5 类触发条件清单 |
| `evals/cases.yaml` | 新增 `complete-mode-notes-mandatory` case；`hotspot-notes-need-scope` 加 complete-mode must |

## Post-promotion

- 生产稿已改，**未自动 commit / push / sync**
- 用户需在 dotfiles 仓下：`git add SKILL.md references/modes.md evals/cases.yaml experience/ evolutions/` → commit → push
- 然后跑 sync（`scripts/agents/sync.sh` 或 `dotf agents -c`）把变更推到 `~/.agents/skills/project-spec-mirror/` 镜像

## Rejected alternative

保留候选稿作为演化历史。后续如需 revert，可从 git 历史恢复。
