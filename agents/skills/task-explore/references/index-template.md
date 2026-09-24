# 任务索引骨架

`tasks/INDEX.md` 是派生目录。单任务真相在各 `TASK.md`。`new` / `save` / `decide` / `handoff` / `archive` / `reopen` 时改对应行；漂移则按目录重建。

Ongoing 按 `updated` 新到旧；Archived 按归档日新到旧。一句话取目标首条，不要抄进展日志。`handed-off` 行（含子任务）以 `→ {task-name}-driver` 结尾；父任务行一句话聚合子任务状态（如「2 子任务：1 已交接、1 设计中」）。子任务的任务列写 `{parent}/{sub}`、路径列写嵌套路径；父归档整树搬家后子任务行路径批量更新为新位置。

```markdown
# Tasks

派生索引。编辑单任务请改对应 `TASK.md`，然后 `save`。

## Ongoing

| 任务 | 标题 | 更新 | 一句话 | 路径 |
|------|------|------|--------|------|
| gateway-timeout | 网关超时排查 | 2026-09-15 | 查清 5xx 来源 | `ongoing/gateway-timeout/` |
| big-quest/api-style | 接口风格子任务 | 2026-09-20 | 定 REST 还是 RPC | `ongoing/big-quest/api-style/` |

## Archived

| 任务 | 归档日 | 标题 | 一句话 | 路径 |
|------|--------|------|--------|------|
| quota-alert | 2026-09-01 | 配额告警误报 | 确认阈值与静默窗口 | `archive/2026-09-01/quota-alert/` |
| session-auth | 2026-09-15 | 会话方案 | 已决：服务端 session → session-auth-driver | `archive/2026-09-15/session-auth/` |
| big-quest/auth | 2026-09-21 | 认证子任务 | 已交接：服务端 session → auth-driver | `archive/2026-09-21/big-quest/auth/` |
```

没有进行中或已归档任务时，保留表头，表体不写占位行。
