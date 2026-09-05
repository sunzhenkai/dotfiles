# 旧详尽档漏掉跨文件契约（已作废）

- Date: 2026-08-29
- Kind: failure
- Skill: project-spec-mirror
- Status: superseded
- Context: 旧模型 `detail_level=complete` 曾要求按模块文件表写镜像

## What happened

当时按文件表交卷后，用户指出跨文件契约、失败路径差异和并发假设没有单独写清。旧规则把这类内容放在 `modules/*/notes/`，且曾误用「同组已镜像仓」做对照。

## Lesson

- **不得**再按 complete / notes / 同组对照执行。现行模型把可验证行为写进 `agent/specs/` 的 Requirement / Scenario，人读写 `briefing/`。
- 本条只说明为何丢掉了旧档位，不恢复那些目录。
