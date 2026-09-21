# Result

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-160743-dedup-driver-protocol-discipline
- risk: medium
- status: applied
- applied-at: 2026-09-21T16:08:30+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available（无自动 runner）；改为人工逐项核对 evals/cases.yaml 全部 14 个 case——must / must_not 断言仍被 SKILL.md 覆盖（Driver 协议模板逐字未动，纪律小节保留全部模板外增量）
- privacy check: pass
- mode check: pass（纯 update，未触碰 Self-evolution 结构与模板固定文本）

## Notes

用户在 medium 风险门禁明确批准本 diff。变化：description 删去非触发能力陈述一句；`涉及面与交付分支`、`一轮结束` 两小节改为「Driver 协议模板为唯一真相 + 模板之外的增量」，消除与模板的重复（此前 154244/155458 两轮 patch 被迫双处同步维护）。未裁剪 Self-evolution 注入块（保持 skill-upgrader 幂等检查与跨 skill 一致性）。
