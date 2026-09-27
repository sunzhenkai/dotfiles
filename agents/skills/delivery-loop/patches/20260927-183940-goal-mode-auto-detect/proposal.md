# delivery-loop 支持 goal 模式并自动识别进行中 goal

- target: agents/skills/delivery-loop
- mode: update
- patch: 20260927-183940-goal-mode-auto-detect
- risk: high
- status: proposed

## Intent

- 新增 `goal:` 输入前缀：显式指定时调用 task-wizard 走其「Goal 方案」分支。
- 自动识别：消息里有 `/goal`，或当前有进行中的 goal 且本条消息挂了 delivery-loop 时，自动按 goal 模式执行，不要求显式前缀。
- goal 模式下，delivery-loop 主循环内所有向用户确认的决定改为走 task-wizard 的「审阅」，与 task-explore 的「Goal 里的确认」一致；复杂门之后的阶段顺序不变。
- 非目标：不改变 normal / benchmark 语义，不改变硬边界与退出条件，不改 taskflow / task-explore。

## Conflict check

- 与 task-wizard 的 goal 分流、task-explore 的「Goal 里的确认」方向一致，无冲突。
- frontmatter description 同步提及 goal 模式以保持触发语义一致。

## Rationale

用户要求 delivery-loop 支持 goal 参数，并在 goal 环境里自动走 goal 路径；改动只落在输入契约与方案生成分支，主循环其余步骤复用，可审计、可验证。

## Files

- agents/skills/delivery-loop/SKILL.md：description、输入节（前缀 + goal 自动识别）、主循环第 2 步。

## Validation

- `git apply --check --recount` 通过。
- 应用后 `git diff --check` 无空白错误；人工核对 goal 判定与 task-wizard 分流句一致。
