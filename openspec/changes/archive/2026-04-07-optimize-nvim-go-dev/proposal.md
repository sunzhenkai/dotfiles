## Why

保存 Go 文件时不会自动移除无用 import，影响开发体验。当前配置使用 `goimports-reviser` 处理 import 整理，但该工具的行为与预期不一致。同时，`none-ls` extra 仍被导入但实际已被禁用，造成配置冗余。

## What Changes

- 修复保存时移除无用 import：将 Go formatter 从 `goimports-reviser` 替换为 `goimports`（默认移除无用 import 且行为确定）
- 清理冗余配置：移除已禁用的 `none-ls` extra 导入
- 补充 Mason 中缺少的 `goimports` 工具安装

## Capabilities

### New Capabilities

_(无新增能力)_

### Modified Capabilities

_(无现有 spec 变更)_

## Impact

- `nvim/lua/plugins/p-editor.lua`：修改 Go formatter 配置（`goimports-reviser` → `goimports`）
- `nvim/lua/plugins/p-mason.lua`：Mason ensure_installed 中 `goimports-reviser` → `goimports`
- `nvim/lua/config/lazy.lua`：移除 `lazyvim.plugins.extras.lsp.none-ls` 导入
