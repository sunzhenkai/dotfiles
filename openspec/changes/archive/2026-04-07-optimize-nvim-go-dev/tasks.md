## 1. 修复 Go import 清理

- [x] 1.1 在 `p-editor.lua` 中将 Go formatter 从 `goimports-reviser` 替换为 `goimports`
- [x] 1.2 在 `p-mason.lua` 中将 `goimports-reviser` 替换为 `goimports`

## 2. 清理冗余配置

- [x] 2.1 在 `lazy.lua` 中移除 `lazyvim.plugins.extras.lsp.none-ls` 导入
