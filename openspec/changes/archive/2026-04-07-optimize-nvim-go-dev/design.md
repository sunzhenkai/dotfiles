## Context

当前 Neovim Go 开发环境基于 LazyVim + Conform.nvim，formatter 链为 `gofumpt` → `goimports-reviser`。用户反馈保存时不会移除无用 import。

`goimports-reviser` 虽然支持移除无用 import，但其默认行为依赖于特定的分组设置，且与 `gofumpt` 组合使用时可能出现顺序问题。`goimports`（Go 官方工具）默认就会移除无用 import，行为更确定。

此外，`lazy.lua` 中仍导入 `lazyvim.plugins.extras.lsp.none-ls`，但 none-ls 已在 `p-disabled.lua` 中禁用，属于冗余配置。

## Goals / Non-Goals

**Goals:**
- 保存 Go 文件时自动移除无用 import
- 清理冗余的 none-ls 导入

**Non-Goals:**
- 不改变 gopls LSP 配置
- 不引入新的 Go 开发插件
- 不改变 format-on-save 的触发机制（LazyVim 默认行为已足够）

## Decisions

### 1. 使用 `goimports` 替代 `goimports-reviser`

**选择**: `goimports`（Go 官方工具）
**替代方案**: 给 `goimports-reviser` 添加 `-rm-unused` 参数
**理由**: `goimports` 是 Go 官方维护的工具，默认移除无用 import 且行为确定。`goimports-reviser` 额外提供 import 分组功能，但与 `gofumpt` 组合时行为不一致。`goimports` + `gofumpt` 是 Go 社区推荐的组合。

### 2. 移除 none-ls extra 导入

**选择**: 从 `lazy.lua` 中移除 `lazyvim.plugins.extras.lsp.none-ls`
**理由**: none-ls 已在 `p-disabled.lua` 中禁用，保留导入只会增加启动时的加载开销。

## Risks / Trade-offs

- [`goimports` 不提供 import 分组] → 可接受，`gofumpt` 已提供标准格式化，import 顺序遵循 Go 标准（标准库、第三方、本地）
- [移除 none-ls 导入可能影响其他依赖 none-ls 的配置] → 已确认 none-ls 被禁用，且当前格式化和 lint 分别使用 Conform 和 nvim-lint，不依赖 none-ls
