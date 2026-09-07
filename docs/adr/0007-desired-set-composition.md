# Desired Set 只覆盖一手 catalog、默认选中项、lock 批准项与 overlay

默认集合是一手 skill ∪ `skills-defaults.yaml` 选中项 ∪ overlay 显式启用，减去 overlay 停用。overlay 可以 apply 已 lock、但不在默认选中里的第三方；未锁定上游拒绝。OpenSpec 生成的 `openspec-*` 不进 TUI 清单。MCP 默认仍是当前 profile，overlay 做单条或按工具加减。
