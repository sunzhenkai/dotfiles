# 任务索引骨架

`tasks/INDEX.md` 是派生目录。单任务真相在各 `TASK.md`。`new` / `save` / `decide` / `handoff` / `archive` / `reopen` 时改对应行；漂移则按目录重建。

Ongoing 按 `updated` 新到旧；Archived 按归档日新到旧。一句话取目标首条，不要抄进展日志。`handoff` 归档行以 `→ {task-name}-driver` 结尾。

```markdown
# Tasks

派生索引。编辑单任务请改对应 `TASK.md`，然后 `save`。

## Ongoing

| 任务 | 标题 | 更新 | 一句话 | 路径 |
|------|------|------|--------|------|
| gateway-timeout | 网关超时排查 | 2026-09-15 | 查清 5xx 来源 | `ongoing/gateway-timeout/` |

## Archived

| 任务 | 归档日 | 标题 | 一句话 | 路径 |
|------|--------|------|--------|------|
| quota-alert | 2026-09-01 | 配额告警误报 | 确认阈值与静默窗口 | `archive/2026-09-01/quota-alert/` |
| session-auth | 2026-09-15 | 会话方案 | 已决：服务端 session → session-auth-driver | `archive/2026-09-15/session-auth/` |
```

没有进行中或已归档任务时，保留表头，表体不写占位行。
