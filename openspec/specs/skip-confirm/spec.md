## Purpose
记录 `SKIP_CONFIRM` 环境变量与自动确认行为的移除状态，确保新实现不再提供跳过确认的旁路，并使后续读者了解历史背景。

## Status: Removed

`SKIP_CONFIRM` 环境变量和自动确认行为已于 `remove-skip-confirm` 变更中移除。

`--all` 标志保留为遍历全模块的快捷方式，但每个模块仍需用户单独确认（不再跳过交互）。
## Requirements
### Requirement: 确认语义委托 plan-confirm
`SKIP_CONFIRM` 环境变量与自动确认绕过 SHALL 保持已移除状态，不得恢复。`--all` SHALL 仅表示遍历适用模块的快捷方式，不再隐含「每个模块单独确认」或「跳过一切确认」。计划路径下的确认行为 SHALL 遵循 `plan-confirm` 能力（计划确认 + 副作用确认；`--yes` 为唯一全自动开关）。

#### Scenario: --all 走计划确认而非逐模块确认
- **WHEN** 用户运行会生成多模块计划的 `--all` 类入口且未传 `--yes`
- **THEN** 系统 SHALL 在执行前进行计划确认（或等价 orchestrator 确认）
- **THEN** SHALL NOT 要求用户对每个模块再回答一次「是否安装/配置」

#### Scenario: 不恢复 SKIP_CONFIRM
- **WHEN** 环境中设置已废弃的 `SKIP_CONFIRM`
- **THEN** 系统 SHALL NOT 将其作为跳过确认的授权信号
