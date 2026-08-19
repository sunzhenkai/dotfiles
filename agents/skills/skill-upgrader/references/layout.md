# 目录组装

把下列文件复制到目标 Skill（已存在且非空则跳过）。骨架文件只作日后写入格式参考，**不要**拷进目标目录冒充真实案例。

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

日后写案例用 `example-case.md` / `experience-entry.md` 的字段，不要在升级时生成假条目。
