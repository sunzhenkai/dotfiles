# 目录组装

`self-upgrade` 时把下列变更编入目标 Skill 的本轮 `change.patch` 再应用；**禁止**先直接写生产目录再补 patch。已存在且非空则跳过对应文件。骨架文件只作日后写入格式参考，**不要**拷进目标目录冒充真实案例。

| 源（本 skill 的 `references/`） | 目标 |
|--------------------------------|------|
| `examples-README.md` | `<skill>/examples/README.md` |
| `evals-README.md` | `<skill>/evals/README.md` |
| `experience-README.md` | `<skill>/experience/README.md` |
| `cases.template.yaml` | `<skill>/evals/cases.yaml`（再按 [evals.md](evals.md) 填 cases） |
| `skill-injection.md` | 追加到 `<skill>/SKILL.md` 末尾，把 `<skill-dir>` 换成实际目录 |

空目录各放 `.gitkeep`：

- `experience/failures/`
- `experience/successes/`
- `experience/patterns/`

本轮审计目录由 `skill-upgrader` 创建在 `<skill>/patches/<patch-id>/`，不要把 `patches/` 写进「复制清单」当业务内容。

日后写案例用 `example-case.md` / `experience-entry.md` 的字段，不要在升级时生成假条目。
